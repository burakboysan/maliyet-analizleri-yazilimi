import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import Toplevel, messagebox
from tkinter import ttk

from core.config import APP_EXE_NAME, APP_VERSION
from core.runtime_config import ensure_user_config_dir


UPDATE_CONFIG_FILE_NAME = "update_config.json"
UPDATE_CHECK_TIMEOUT_SECONDS = 10


class _UpdateProgressDialog:
    def __init__(self, root, version_text: str):
        self.window = Toplevel(root)
        self.window.title("Guncelleme Indiriliyor")
        self.window.resizable(False, False)
        self.window.transient(root)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = ttk.Frame(self.window, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=f"Surum {version_text} indiriliyor").pack(anchor="w")
        self.status_label = ttk.Label(frame, text="Guncelleme paketi indirilmeye hazirlaniyor...")
        self.status_label.pack(anchor="w", pady=(10, 8))

        self.progressbar = ttk.Progressbar(frame, mode="indeterminate", length=320, maximum=100)
        self.progressbar.pack(fill="x")
        self.progressbar.start(12)

        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x_pos = int((self.window.winfo_screenwidth() - width) / 2)
        y_pos = int((self.window.winfo_screenheight() - height) / 2)
        self.window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def set_status(self, text: str):
        self.status_label.configure(text=text)
        self.window.update_idletasks()

    def set_progress(self, downloaded_bytes: int, total_bytes: int):
        if total_bytes > 0:
            if str(self.progressbar.cget("mode")) != "determinate":
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate", value=0, maximum=100)
            percent = min(100.0, (downloaded_bytes / total_bytes) * 100)
            self.progressbar.configure(value=percent)
        elif str(self.progressbar.cget("mode")) != "indeterminate":
            self.progressbar.configure(mode="indeterminate")
            self.progressbar.start(12)

    def close(self):
        try:
            self.progressbar.stop()
        except Exception:
            pass
        try:
            self.window.grab_release()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass


def _debug_log_path() -> Path:
    return _runtime_base_dir() / "logs" / "update_debug.log"


def _debug_log(message: str) -> None:
    try:
        log_path = _debug_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass


def _urlopen_without_proxy(request_or_url, timeout):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(request_or_url, timeout=timeout)


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _update_config_search_paths():
    return [
        Path(ensure_user_config_dir()) / UPDATE_CONFIG_FILE_NAME,
        _runtime_base_dir() / UPDATE_CONFIG_FILE_NAME,
    ]


def _load_update_config():
    for path in _update_config_search_paths():
        _debug_log(f"Konfig aranıyor: {path}")
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig") as file_obj:
            payload = json.load(file_obj)
        if isinstance(payload, dict):
            _debug_log(f"Konfig yüklendi: {path}")
            return payload
    _debug_log("Update konfig bulunamadı")
    return {}


def _manifest_url():
    config = _load_update_config()
    return str(config.get("manifest_url", "")).strip()


def _parse_version(version_text):
    parts = [int(part) for part in str(version_text or "").strip().split(".")]
    if len(parts) != 3:
        raise ValueError("Gecersiz surum formati")
    return tuple(parts)


def _is_newer_version(candidate, current):
    return _parse_version(candidate) > _parse_version(current)


def _download_json(url):
    with _urlopen_without_proxy(url, timeout=UPDATE_CHECK_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def _fetch_update_manifest():
    manifest_url = _manifest_url()
    if not manifest_url:
        _debug_log("Manifest URL boş")
        return None

    _debug_log(f"Manifest indiriliyor: {manifest_url}")
    payload = _download_json(manifest_url)
    if not isinstance(payload, dict):
        _debug_log("Manifest dict değil")
        return None

    candidate_version = str(payload.get("version", "")).strip()
    installer_url = str(payload.get("installer_url", "")).strip()
    if not candidate_version or not installer_url:
        _debug_log("Manifest içinde version veya installer_url eksik")
        return None

    payload["manifest_url"] = manifest_url
    payload["resolved_installer_url"] = urllib.parse.urljoin(manifest_url, installer_url)
    _debug_log(
        f"Manifest okundu: current={APP_VERSION}, candidate={candidate_version}, installer={payload['resolved_installer_url']}"
    )
    return payload


def _download_file(url, destination, progress_callback=None):
    request = urllib.request.Request(url, headers={"User-Agent": f"BomaksanUpdater/{APP_VERSION}"})
    with _urlopen_without_proxy(request, timeout=60) as response, open(destination, "wb") as file_obj:
        total_bytes_header = response.headers.get("Content-Length")
        total_bytes = int(total_bytes_header) if total_bytes_header and total_bytes_header.isdigit() else 0
        downloaded_bytes = 0
        while True:
            chunk = response.read(1024 * 64)
            if not chunk:
                break
            file_obj.write(chunk)
            downloaded_bytes += len(chunk)
            if progress_callback:
                progress_callback(downloaded_bytes, total_bytes)


def _sha256_of_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file_obj:
        while True:
            chunk = file_obj.read(1024 * 64)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _download_installer(manifest, progress_callback=None):
    installer_url = manifest["resolved_installer_url"]
    installer_name = os.path.basename(urllib.parse.urlparse(installer_url).path) or "Bomaksan_Update_Setup.exe"
    temp_dir = Path(tempfile.mkdtemp(prefix="bomaksan_update_"))
    installer_path = temp_dir / installer_name
    _debug_log(f"Installer indiriliyor: {installer_url} -> {installer_path}")
    _download_file(installer_url, installer_path, progress_callback=progress_callback)

    expected_hash = str(manifest.get("sha256", "")).strip().lower()
    if expected_hash and _sha256_of_file(installer_path).lower() != expected_hash:
        _debug_log("SHA256 doğrulaması başarısız")
        raise ValueError("Indirilen guncelleme dosyasi dogrulanamadi.")

    _debug_log(f"Installer indirildi: {installer_path.stat().st_size} byte")
    return installer_path


def _launch_installer(installer_path):
    if not getattr(sys, "frozen", False):
        _debug_log("Launch atlandı: frozen değil")
        raise RuntimeError("Otomatik guncelleme sadece paketlenmis surumde desteklenir.")

    current_pid = os.getpid()
    app_path = _runtime_base_dir() / APP_EXE_NAME
    script_path = Path(tempfile.gettempdir()) / "bomaksan_run_update.ps1"
    escaped_installer_path = str(installer_path).replace("'", "''")
    escaped_app_path = str(app_path).replace("'", "''")
    script_path.write_text(
        "\n".join(
            [
                f"$installer = '{escaped_installer_path}'",
                f"$appPath = '{escaped_app_path}'",
                "$appDir = Split-Path -Parent $appPath",
                "$pythonDll = Join-Path $appDir '_internal\\python313.dll'",
                f"$pidToWait = {current_pid}",
                "while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 500 }",
                "Start-Process -FilePath $installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CLOSEAPPLICATIONS' -Wait",
                "$started = $false",
                "for ($attempt = 0; $attempt -lt 15; $attempt++) {",
                "  Start-Sleep -Seconds 2",
                "  if ((Test-Path $appPath) -and (Test-Path $pythonDll)) {",
                "    try {",
                "      Start-Process -FilePath $appPath",
                "      $started = $true",
                "      break",
                "    } catch {",
                "      Start-Sleep -Seconds 2",
                "    }",
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    _debug_log(f"Installer başlatma scripti oluşturuldu: {script_path}")


def _prompt_and_install(root, manifest):
    notes = str(manifest.get("notes", "")).strip()
    prompt = f"Yeni surum bulundu: {manifest['version']}\nMevcut surum: {APP_VERSION}"
    if notes:
        prompt += f"\n\nYenilikler:\n{notes}"
    prompt += "\n\nSimdi indirip kurmak ister misiniz?"

    if not messagebox.askyesno("Guncelleme Hazir", prompt, parent=root):
        _debug_log("Kullanıcı güncellemeyi reddetti")
        return

    def _worker():
        try:
            _debug_log("İndirme iş parçacığı başladı")
            installer_path = _download_installer(manifest)

            def _finish():
                _debug_log("İndirme tamamlandı, kurulum başlatılıyor")
                messagebox.showinfo(
                    "Guncelleme",
                    "Guncelleme indirildi. Uygulama kapanip yeni surum kurulacak.",
                    parent=root,
                )
                _launch_installer(installer_path)
                root.destroy()

            root.after(0, _finish)
        except Exception as exc:
            _debug_log(f"İndirme/kurulum hatası: {exc}")
            root.after(0, lambda: messagebox.showerror("Guncelleme", str(exc), parent=root))

    threading.Thread(target=_worker, daemon=True).start()


def _prompt_and_install_with_progress(root, manifest):
    notes = str(manifest.get("notes", "")).strip()
    prompt = f"Yeni surum bulundu: {manifest['version']}\nMevcut surum: {APP_VERSION}"
    if notes:
        prompt += f"\n\nYenilikler:\n{notes}"
    prompt += "\n\nSimdi indirip kurmak ister misiniz?"

    if not messagebox.askyesno("Guncelleme Hazir", prompt, parent=root):
        _debug_log("Kullanici guncellemeyi reddetti")
        return

    progress_dialog = _UpdateProgressDialog(root, manifest["version"])

    def _worker():
        try:
            _debug_log("Indirme is parcacigi basladi")
            root.after(0, lambda: progress_dialog.set_status("Guncelleme paketi indiriliyor..."))

            def _report_progress(downloaded_bytes, total_bytes):
                if total_bytes > 0:
                    downloaded_mb = downloaded_bytes / (1024 * 1024)
                    total_mb = total_bytes / (1024 * 1024)
                    percent = (downloaded_bytes / total_bytes) * 100
                    status_text = (
                        f"Guncelleme paketi indiriliyor... %{percent:.0f} "
                        f"({downloaded_mb:.1f} / {total_mb:.1f} MB)"
                    )
                else:
                    downloaded_mb = downloaded_bytes / (1024 * 1024)
                    status_text = f"Guncelleme paketi indiriliyor... {downloaded_mb:.1f} MB"
                root.after(
                    0,
                    lambda text=status_text, downloaded=downloaded_bytes, total=total_bytes: (
                        progress_dialog.set_status(text),
                        progress_dialog.set_progress(downloaded, total),
                    ),
                )

            installer_path = _download_installer(manifest, progress_callback=_report_progress)

            def _finish():
                _debug_log("Indirme tamamlandi, kurulum baslatiliyor")
                progress_dialog.set_status("Indirme tamamlandi. Dosya dogrulaniyor...")
                progress_dialog.set_progress(1, 1)
                progress_dialog.window.update_idletasks()
                progress_dialog.set_status("Kurulum baslatiliyor. Uygulama birazdan kapanacak...")
                progress_dialog.window.update_idletasks()
                progress_dialog.close()
                messagebox.showinfo(
                    "Guncelleme",
                    "Guncelleme indirildi. Uygulama kapanip yeni surum kurulacak.",
                    parent=root,
                )
                _launch_installer(installer_path)
                root.destroy()

            root.after(0, _finish)
        except Exception as exc:
            _debug_log(f"Indirme/kurulum hatasi: {exc}")
            root.after(0, progress_dialog.close)
            root.after(0, lambda: messagebox.showerror("Guncelleme", str(exc), parent=root))

    threading.Thread(target=_worker, daemon=True).start()


def check_for_updates_in_background(root):
    if not getattr(sys, "frozen", False):
        _debug_log("Update kontrolü atlandı: frozen değil")
        return
    if not _manifest_url():
        _debug_log("Update kontrolü atlandı: manifest URL yok")
        return

    def _worker():
        try:
            _debug_log("Arka plan update kontrolü başladı")
            manifest = _fetch_update_manifest()
            if not manifest:
                _debug_log("Manifest alınamadı")
                return
            if not _is_newer_version(manifest["version"], APP_VERSION):
                _debug_log(f"Yeni sürüm yok: current={APP_VERSION}, candidate={manifest['version']}")
                return
            _debug_log(f"Yeni sürüm bulundu: {manifest['version']}")
            root.after(0, lambda: _prompt_and_install_with_progress(root, manifest))
        except Exception as exc:
            _debug_log(f"Update kontrol hatası: {exc}")
            return

    threading.Thread(target=_worker, daemon=True).start()
