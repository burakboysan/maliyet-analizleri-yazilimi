#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bomaksan Maliyet Analizleri - Executable Build Script
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys

from core.config import APP_EXE_NAME
from core.runtime_config import (
    get_user_db_protected_config_path,
    get_user_smtp_protected_config_path,
)


CONFIG_PATH = os.path.join("core", "config.py")
VERSION_ISS_PATH = os.path.join("installer", "version.iss")
DEFAULT_BUMP_PART = "patch"
DEFAULT_TIMESTAMP_URL = "http://timestamp.digicert.com"
DEFAULT_DIGEST_ALGORITHM = "SHA256"
REPORTS_SOURCE_DIR = os.path.join("..", "\u00dcr\u00fcn Konfig App", "mobile_api", "reports")


def load_app_version():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file_obj:
        config_text = file_obj.read()
    match = re.search(r'APP_VERSION\s*=\s*"(\d+\.\d+\.\d+)"', config_text)
    if not match:
        raise RuntimeError("APP_VERSION bulunamadi.")
    return match.group(1)


def update_app_version(new_version):
    with open(CONFIG_PATH, "r", encoding="utf-8") as file_obj:
        config_text = file_obj.read()
    updated_text = re.sub(
        r'(APP_VERSION\s*=\s*")(\d+\.\d+\.\d+)(")',
        rf"\g<1>{new_version}\g<3>",
        config_text,
        count=1,
    )
    with open(CONFIG_PATH, "w", encoding="utf-8") as file_obj:
        file_obj.write(updated_text)


def bump_version(version, part=DEFAULT_BUMP_PART):
    major, minor, patch = [int(piece) for piece in version.split(".")]
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def render_inno_version_file(app_version):
    version_tag = app_version.replace(".", "_")
    contents = (
        f'#define MyAppVersion "{app_version}"\n'
        f'#define MyAppExeName "{APP_EXE_NAME}"\n'
        f'#define MyOutputBaseFilename "Bomaksan_Maliyet_Analizleri_Setup_{version_tag}"\n'
    )
    with open(VERSION_ISS_PATH, "w", encoding="utf-8") as file_obj:
        file_obj.write(contents)


def sha256_of_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file_obj:
        while True:
            chunk = file_obj.read(1024 * 64)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _load_release_config_payload(config_filename, protected_path):
    if os.path.exists(config_filename):
        with open(config_filename, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)

    if os.path.exists(protected_path):
        from core.secure_storage import load_protected_json

        return load_protected_json(protected_path)

    return None


def install_requirements():
    print("[INFO] Gerekli paketler yukleniyor...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])


def copy_reports_payload(target_root):
    source_dir = os.path.abspath(REPORTS_SOURCE_DIR)
    target_dir = os.path.join(target_root, "App", "mobile_api", "reports")

    if not os.path.isdir(source_dir):
        print(f"[WARN] Rapor klasoru bulunamadi, kopyalama atlaniyor: {source_dir}")
        return False

    os.makedirs(target_dir, exist_ok=True)
    copied_count = 0
    for filename in ("verty_valid_combinations.csv", "ecog_valid_combinations.csv"):
        source_path = os.path.join(source_dir, filename)
        if not os.path.exists(source_path):
            print(f"[WARN] Rapor dosyasi bulunamadi: {source_path}")
            continue
        shutil.copy2(source_path, os.path.join(target_dir, filename))
        copied_count += 1

    if copied_count:
        print(f"[INFO] {copied_count} rapor dosyasi kopyalandi: {os.path.abspath(target_dir)}")
        return True

    print(f"[WARN] Rapor dosyalari kopyalanamadi: {source_dir}")
    return False


def find_signtool():
    candidates = [
        os.getenv("BOMAKSAN_SIGNTOOL_PATH"),
        shutil.which("signtool.exe"),
        shutil.which("signtool"),
        r"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64\signtool.exe",
    ]
    return next((path for path in candidates if path and os.path.exists(path)), None)


def resolve_signing_settings(require_sign=False, skip_sign=False):
    if skip_sign:
        print("[INFO] Kod imzalama bu calistirmada devre disi birakildi (--skip-sign).")
        return None

    settings = {
        "signtool_path": find_signtool(),
        "subject_name": os.getenv("BOMAKSAN_SIGN_CERT_SUBJECT"),
        "thumbprint": os.getenv("BOMAKSAN_SIGN_CERT_SHA1"),
        "pfx_path": os.getenv("BOMAKSAN_SIGN_PFX_PATH"),
        "pfx_password": os.getenv("BOMAKSAN_SIGN_PFX_PASSWORD"),
        "timestamp_url": os.getenv("BOMAKSAN_SIGN_TIMESTAMP_URL", DEFAULT_TIMESTAMP_URL),
        "file_digest": os.getenv("BOMAKSAN_SIGN_FILE_DIGEST", DEFAULT_DIGEST_ALGORITHM),
        "timestamp_digest": os.getenv("BOMAKSAN_SIGN_TIMESTAMP_DIGEST", DEFAULT_DIGEST_ALGORITHM),
    }

    has_certificate_selector = any(
        [settings["subject_name"], settings["thumbprint"], settings["pfx_path"]]
    )
    if not has_certificate_selector:
        if require_sign:
            raise RuntimeError(
                "Kod imzalama zorunlu ancak sertifika bilgisi bulunamadi. "
                "BOMAKSAN_SIGN_CERT_SUBJECT, BOMAKSAN_SIGN_CERT_SHA1 veya "
                "BOMAKSAN_SIGN_PFX_PATH degiskenlerinden biri tanimlanmali."
            )
        print("[INFO] Kod imzalama atlandi. Sertifika ortam degiskeni tanimli degil.")
        return None

    if not settings["signtool_path"]:
        raise RuntimeError(
            "Kod imzalama ayarlari bulundu ancak signtool.exe bulunamadi. "
            "BOMAKSAN_SIGNTOOL_PATH degiskeni ile yolu tanimlayin."
        )

    if settings["pfx_path"] and not os.path.exists(settings["pfx_path"]):
        raise RuntimeError(f"PFX dosyasi bulunamadi: {settings['pfx_path']}")

    print(f"[INFO] Kod imzalama etkin. Signtool: {settings['signtool_path']}")
    return settings


def sign_file(file_path, signing_settings, description):
    if not signing_settings:
        return
    if not os.path.exists(file_path):
        raise RuntimeError(f"Imzalanacak dosya bulunamadi: {file_path}")

    cmd = [
        signing_settings["signtool_path"],
        "sign",
        "/fd",
        signing_settings["file_digest"],
        "/td",
        signing_settings["timestamp_digest"],
        "/tr",
        signing_settings["timestamp_url"],
        "/d",
        description,
    ]

    if signing_settings["pfx_path"]:
        cmd.extend(["/f", signing_settings["pfx_path"]])
        if signing_settings["pfx_password"]:
            cmd.extend(["/p", signing_settings["pfx_password"]])
    elif signing_settings["thumbprint"]:
        cmd.extend(["/sha1", signing_settings["thumbprint"]])
    else:
        cmd.extend(["/n", signing_settings["subject_name"]])

    cmd.append(file_path)

    print(f"[INFO] Dosya imzalaniyor: {os.path.abspath(file_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Kod imzalama basarisiz oldu:\n"
            f"{result.stdout}\n{result.stderr}".strip()
        )
    print(f"[OK] Imza tamamlandi: {os.path.abspath(file_path)}")


def build_executable(signing_settings=None):
    print("[INFO] Executable olusturuluyor...")
    pyinstaller_path = None
    scripts_dir = os.path.join(os.path.dirname(sys.executable), "Scripts")
    pyinstaller_exe = os.path.join(scripts_dir, "pyinstaller.exe")

    if os.path.exists(pyinstaller_exe):
        pyinstaller_path = pyinstaller_exe
    else:
        try:
            result = subprocess.run(["where", "pyinstaller"], capture_output=True, text=True)
            if result.returncode == 0:
                pyinstaller_path = result.stdout.strip().split("\n")[0]
        except Exception:
            pass

    if not pyinstaller_path:
        print("[ERROR] PyInstaller bulunamadi. Manuel olarak yukleniyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
        pyinstaller_path = os.path.join(scripts_dir, "pyinstaller.exe")

    print(f"[INFO] PyInstaller yolu: {pyinstaller_path}")

    hidden_imports = [
        "customtkinter",
        "PIL",
        "psycopg",
        "psycopg_pool",
        "tkcalendar",
        "openpyxl",
        "bcrypt",
        "reportlab",
        "reportlab.lib.pagesizes",
        "reportlab.pdfbase",
        "reportlab.pdfbase.pdfmetrics",
        "reportlab.pdfbase.ttfonts",
        "reportlab.pdfgen",
        "reportlab.pdfgen.canvas",
        "proje_yonetimi.add_project",
        "proje_yonetimi.edit_project",
        "proje_yonetimi.project_management",
        "teklif_yonetimi.add_quote",
        "teklif_yonetimi.edit_quote",
    ]

    app_dist_dir = os.path.join("dist", os.path.splitext(APP_EXE_NAME)[0])

    if os.path.exists(app_dist_dir):
        shutil.rmtree(app_dist_dir, ignore_errors=True)

    cmd = [
        pyinstaller_path,
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--noupx",
        f"--name={os.path.splitext(APP_EXE_NAME)[0]}",
        "--icon=assets/logo_icon.ico",
        "--add-data=assets;assets",
        "--add-data=tkcalendar;tkcalendar",
        "--add-data=bcrypt;bcrypt",
    ] + [f"--hidden-import={imp}" for imp in hidden_imports] + ["main.py"]

    if os.path.isdir(REPORTS_SOURCE_DIR):
        cmd.insert(-1, f"--add-data={REPORTS_SOURCE_DIR};App/mobile_api/reports")
    else:
        print(f"[WARN] Rapor klasoru bulunamadi, build'e eklenemedi: {os.path.abspath(REPORTS_SOURCE_DIR)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        copy_reports_payload(app_dist_dir)
        exe_path = os.path.join(app_dist_dir, APP_EXE_NAME)
        sign_file(exe_path, signing_settings, "Bomaksan Maliyet Analizleri")
        print("[OK] Executable basariyla olusturuldu.")
        print(f"[INFO] Dosya konumu: {os.path.abspath(exe_path)}")
    else:
        print("[ERROR] Executable olusturulurken hata olustu:")
        print(result.stderr)


def create_installer(signing_settings=None):
    print("[INFO] Kurulum paketi hazirlaniyor...")
    installer_dir = "Bomaksan_Maliyet_Analizleri_Setup"

    def _remove_readonly(func, path, exc):
        try:
            os.chmod(path, stat.S_IWRITE)
        except Exception:
            pass
        try:
            func(path)
        except Exception:
            pass

    if os.path.exists(installer_dir):
        try:
            shutil.rmtree(installer_dir, onerror=_remove_readonly)
        except Exception as exc:
            print(f"[WARN] Mevcut kurulum klasoru silinemedi: {exc}. Yeniden adlandiriliyor...")
            try:
                os.rename(installer_dir, installer_dir + "_old")
            except Exception as rename_exc:
                print(f"[WARN] Yeniden adlandirma da basarisiz: {rename_exc}")
    os.makedirs(installer_dir, exist_ok=True)

    built_app_dir = os.path.join("dist", os.path.splitext(APP_EXE_NAME)[0])
    if not os.path.isdir(built_app_dir):
        raise RuntimeError(f"PyInstaller cikti klasoru bulunamadi: {built_app_dir}")

    app_payload_dir = os.path.join(installer_dir, "app")
    shutil.copytree(built_app_dir, app_payload_dir, dirs_exist_ok=True)
    copy_reports_payload(app_payload_dir)

    db_config_payload = _load_release_config_payload("db_config.json", get_user_db_protected_config_path())
    if db_config_payload:
        with open(os.path.join(app_payload_dir, "db_config.json"), "w", encoding="utf-8") as file_obj:
            json.dump(db_config_payload, file_obj, ensure_ascii=False, indent=2)
        print("[INFO] Veritabani baglanti ayarlari kurulum paketine eklendi.")

    smtp_config_payload = _load_release_config_payload("smtp_config.json", get_user_smtp_protected_config_path())
    if smtp_config_payload:
        with open(os.path.join(app_payload_dir, "smtp_config.json"), "w", encoding="utf-8") as file_obj:
            json.dump(smtp_config_payload, file_obj, ensure_ascii=False, indent=2)
        print("[INFO] SMTP ayarlari kurulum paketine eklendi.")

    shutil.copy("assets/logo_icon.ico", installer_dir)
    if os.path.exists("update_config.json"):
        shutil.copy("update_config.json", installer_dir)
    if os.path.exists("update_config.template.json"):
        shutil.copy("update_config.template.json", installer_dir)

    readme_content = """# Bomaksan Maliyet Analizleri Yazilimi

## Kurulum Talimatlari

1. Kurulum tamamlandiktan sonra uygulamayi baslatin
2. Giris ekraninda kullanici adi ve sifreniz ile oturum acin
3. Ilk calistirmada Windows Defender uyarisi gelebilir. Gerekirse "Yine de calistir" secenegini secin

## Guvenlik

- `Beni Hatirla` bilgileri Windows hesabina bagli sifreli olarak saklanir

## Sistem Gereksinimleri

- Windows 10/11 (64-bit)
- Internet baglantisi (veritabani erisimi icin)
- Minimum 4GB RAM
- 100MB bos disk alani

## Destek

Teknik destek materyalleri uygulama klasorune acik dosya olarak kurulmaz.
Gerekli dokumanlar uygulama icindeki yetkili ekranlardan veya Bomaksan IT uzerinden paylasilir.

Copyright 2025 Bomaksan A.S.
"""

    with open(os.path.join(installer_dir, "README.txt"), "w", encoding="utf-8") as file_obj:
        file_obj.write(readme_content)

    create_inno_setup_script(installer_dir, signing_settings)
    print(f"[OK] Kurulum paketi hazirlandi: {installer_dir}")


def create_inno_setup_script(installer_dir, signing_settings=None):
    script_path = os.path.join("installer", "Bomaksan_Maliyet_Analizleri.iss")
    if not os.path.exists(script_path):
        return

    app_version = load_app_version()
    render_inno_version_file(app_version)
    shutil.copy(script_path, os.path.join(installer_dir, "Bomaksan_Maliyet_Analizleri.iss"))

    iscc_candidates = [
        shutil.which("ISCC.exe"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    iscc_path = next((path for path in iscc_candidates if path and os.path.exists(path)), None)

    if not iscc_path:
        print("[WARN] Inno Setup bulunamadi. .iss dosyasi kurulum klasorune kopyalandi.")
        return

    print("[INFO] Inno Setup installer olusturuluyor...")
    result = subprocess.run([iscc_path, script_path], capture_output=True, text=True)
    if result.returncode == 0:
        installer_filename = f"Bomaksan_Maliyet_Analizleri_Setup_{app_version.replace('.', '_')}.exe"
        installer_path = os.path.join("dist_installer", installer_filename)
        sign_file(installer_path, signing_settings, f"Bomaksan Maliyet Analizleri Setup {app_version}")
        print("[OK] Inno Setup installer basariyla olusturuldu.")
        create_update_manifest(app_version)
    else:
        print("[WARN] Inno Setup derlenemedi:")
        print(result.stderr)


def create_update_manifest(app_version):
    installer_filename = f"Bomaksan_Maliyet_Analizleri_Setup_{app_version.replace('.', '_')}.exe"
    installer_path = os.path.join("dist_installer", installer_filename)
    if not os.path.exists(installer_path):
        print("[WARN] Installer dosyasi bulunamadi, latest.json olusturulamadi.")
        return

    manifest = {
        "version": app_version,
        "installer_url": installer_filename,
        "sha256": sha256_of_file(installer_path),
        "mandatory": False,
        "notes": f"Bomaksan Maliyet Analizleri {app_version} guncellemesi",
    }
    manifest_path = os.path.join("dist_installer", "latest.json")
    with open(manifest_path, "w", encoding="utf-8") as file_obj:
        json.dump(manifest, file_obj, ensure_ascii=False, indent=2)
    print(f"[INFO] Guncelleme manifesti hazirlandi: {os.path.abspath(manifest_path)}")


def parse_args():
    parser = argparse.ArgumentParser(description="Bomaksan release build")
    parser.add_argument("--release", action="store_true", help="Surumu otomatik artirip release build al")
    parser.add_argument(
        "--part",
        choices=["major", "minor", "patch"],
        default=DEFAULT_BUMP_PART,
        help="Otomatik surum artisi tipi",
    )
    parser.add_argument("--version", help="Belirli bir surum ile build al")
    parser.add_argument(
        "--require-sign",
        action="store_true",
        help="Kod imzalama yoksa build'i hata ile durdur",
    )
    parser.add_argument(
        "--skip-sign",
        action="store_true",
        help="Kod imzalama ayarlari olsa bile bu calistirmada imzalama yapma",
    )
    return parser.parse_args()


def main():
    print("[INFO] Bomaksan Maliyet Analizleri - Build islemi baslatiliyor")
    print("=" * 60)

    try:
        args = parse_args()
        current_version = load_app_version()
        target_version = current_version

        if args.version:
            target_version = args.version
        elif args.release:
            target_version = bump_version(current_version, args.part)

        if target_version != current_version:
            update_app_version(target_version)
            print(f"[INFO] Surum guncellendi: {current_version} -> {target_version}")

        signing_settings = resolve_signing_settings(
            require_sign=args.require_sign,
            skip_sign=args.skip_sign,
        )
        install_requirements()
        build_executable(signing_settings)
        create_installer(signing_settings)

        print("\n[OK] Build islemi tamamlandi.")
        print("[INFO] Kurulum paketi 'Bomaksan_Maliyet_Analizleri_Setup' klasorunde hazir")
        if not args.release and not args.version:
            print("[INFO] Sonraki release icin: py build_exe.py --release")
    except Exception as exc:
        print(f"[ERROR] Hata olustu: {exc}")


if __name__ == "__main__":
    main()
