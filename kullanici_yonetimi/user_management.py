import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from core.api_client import (
    ApiClientError,
    create_user,
    delete_user,
    list_roles,
    list_users,
    resend_user_verification,
    update_user_email,
    update_user_password,
)
from core.email_verification import is_valid_email, verify_email_code
from core.roles import can_access_user_management
from core.session import get_app_token
from core.utils import apply_bomaksan_table_style, apply_zebra_striping, setup_responsive_table


def kullanici_yonetim_ekrani(parent=None, kullanici_rolu=None):
    if not can_access_user_management(kullanici_rolu):
        messagebox.showwarning("Yetki", "Kullanıcı yönetimi ekranına yalnızca Owner rolü erişebilir.", parent=parent)
        return

    token = get_app_token()
    if not token:
        messagebox.showerror("Oturum", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=parent)
        return

    secili_kullanici_var = tk.StringVar(value="Seçili kullanıcı: Yok")
    fallback_roles = ["Owner", "Master Admin", "Satınalmacı", "Tasarımcı", "Kullanıcı", "Proje Yetkilisi"]
    role_names = list(fallback_roles)

    pencere = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    if parent:
        pencere.transient(parent)
    pencere.lift()
    pencere.focus_force()

    def pencereyi_kapat():
        try:
            pencere.grab_release()
        except Exception:
            pass
        pencere.destroy()

    try:
        pencere.grab_set()
    except Exception:
        pass
    pencere.protocol("WM_DELETE_WINDOW", pencereyi_kapat)
    pencere.after(50, lambda: pencere.attributes("-topmost", True))
    pencere.after(200, lambda: pencere.attributes("-topmost", False))
    pencere.title("Kullanıcı Yönetimi")
    pencere.state("zoomed")

    columns = ("ID", "Kullanıcı Adı", "E-posta", "Rol", "E-posta Doğrulandı", "Aktif")
    tree = ttk.Treeview(pencere, columns=columns, show="headings", height=15)
    apply_bomaksan_table_style(tree)
    for column in columns:
        tree.heading(column, text=column)

    kolon_oranlari = {
        "ID": 0.08,
        "Kullanıcı Adı": 0.20,
        "E-posta": 0.28,
        "Rol": 0.16,
        "E-posta Doğrulandı": 0.14,
        "Aktif": 0.14,
    }
    min_genislikler = {
        "ID": 50,
        "Kullanıcı Adı": 140,
        "E-posta": 220,
        "Rol": 120,
        "E-posta Doğrulandı": 130,
        "Aktif": 90,
    }
    setup_responsive_table(tree, pencere, kolon_oranlari, min_genislikler, 0)
    tree.pack(padx=10, pady=10, fill="x")

    secili_frame = ctk.CTkFrame(pencere)
    secili_frame.pack(pady=(0, 5), padx=10, fill="x")
    ctk.CTkLabel(
        secili_frame,
        textvariable=secili_kullanici_var,
        font=ctk.CTkFont(size=13, weight="bold"),
    ).pack(anchor="w", padx=10, pady=8)

    frame_ekle = ctk.CTkFrame(pencere)
    frame_ekle.pack(pady=10, padx=10, fill="x")

    entry_ad = ctk.CTkEntry(frame_ekle, placeholder_text="Kullanıcı Adı", width=150)
    entry_ad.grid(row=0, column=0, padx=5, pady=5)

    entry_email = ctk.CTkEntry(frame_ekle, placeholder_text="E-posta", width=220)
    entry_email.grid(row=0, column=1, padx=5, pady=5)

    entry_sifre = ctk.CTkEntry(frame_ekle, placeholder_text="Şifre", show="*", width=150)
    entry_sifre.grid(row=0, column=2, padx=5, pady=5)

    entry_sifre_tekrar = ctk.CTkEntry(frame_ekle, placeholder_text="Şifre (Tekrar)", show="*", width=150)
    entry_sifre_tekrar.grid(row=0, column=3, padx=5, pady=5)

    sifre_goster = tk.BooleanVar(value=False)

    def sifre_goster_degistir():
        show = "" if sifre_goster.get() else "*"
        entry_sifre.configure(show=show)
        entry_sifre_tekrar.configure(show=show)

    ctk.CTkCheckBox(frame_ekle, text="Göster", variable=sifre_goster, command=sifre_goster_degistir).grid(
        row=0, column=4, padx=5, pady=5
    )

    combo_rol = ctk.CTkComboBox(frame_ekle, values=role_names, width=160)
    combo_rol.set("Rol Seç")
    combo_rol.grid(row=0, column=5, padx=5, pady=5)

    frame_sifre = ctk.CTkFrame(pencere)
    frame_sifre.pack(pady=10, padx=10, fill="x")

    entry_yeni_sifre = ctk.CTkEntry(frame_sifre, placeholder_text="Yeni Şifre", show="*", width=200)
    entry_yeni_sifre.grid(row=0, column=0, padx=5, pady=5)

    yeni_sifre_goster = tk.BooleanVar(value=False)

    def yeni_sifre_goster_degistir():
        entry_yeni_sifre.configure(show="" if yeni_sifre_goster.get() else "*")

    ctk.CTkCheckBox(frame_sifre, text="Göster", variable=yeni_sifre_goster, command=yeni_sifre_goster_degistir).grid(
        row=0, column=1, padx=5, pady=5
    )

    def format_bool(value):
        return "Evet" if bool(value) else "Hayır"

    def call_api(func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ApiClientError as exc:
            raise ValueError(str(exc)) from exc

    def load_roles_into_combobox():
        nonlocal role_names
        try:
            roles = call_api(list_roles, token)
            role_names = [role.get("rol_adi") for role in roles if role.get("rol_adi")] or list(fallback_roles)
        except Exception as exc:
            print(f"Rol listesi yüklenirken hata: {exc}")
            role_names = list(fallback_roles)
        combo_rol.configure(values=role_names)
        combo_rol.set("Rol Seç")

    def kullanicilari_yukle():
        for item in tree.get_children():
            tree.delete(item)

        rows = call_api(list_users, token)
        items = []
        for row in rows:
            normalized_row = (
                row.get("id"),
                row.get("kullanici_adi"),
                row.get("email") or "",
                row.get("rol_adi") or "",
                format_bool(row.get("email_verified")),
                format_bool(row.get("is_active")),
            )
            item = tree.insert("", "end", values=normalized_row)
            items.append(item)
        apply_zebra_striping(tree, items)

    def get_selected_user():
        secili = tree.selection()
        if not secili:
            messagebox.showwarning("Seçim Yok", "Lütfen bir kullanıcı seçin.", parent=pencere)
            return None
        values = tree.item(secili[0])["values"]
        return {
            "id": values[0],
            "kullanici_adi": values[1],
            "email": values[2],
            "rol": values[3],
        }

    def secili_kullaniciyi_forma_yukle(event=None):
        secili = tree.selection()
        if not secili:
            secili_kullanici_var.set("Seçili kullanıcı: Yok")
            return

        values = tree.item(secili[0])["values"]
        secili_kullanici_var.set(f"Seçili kullanıcı: {values[1]}")

        entry_ad.delete(0, "end")
        entry_ad.insert(0, values[1])

        entry_email.delete(0, "end")
        if values[2]:
            entry_email.insert(0, values[2])

        combo_rol.set(values[3] or "Rol Seç")

    def kullanici_ekle():
        ad = entry_ad.get().strip()
        email = entry_email.get().strip()
        sifre = entry_sifre.get()
        sifre_tekrar = entry_sifre_tekrar.get()
        rol = combo_rol.get()

        if not ad or not email or not sifre or not sifre_tekrar or rol == "Rol Seç":
            messagebox.showwarning("Eksik Bilgi", "Tüm alanlar zorunludur.", parent=pencere)
            return
        if not is_valid_email(email):
            messagebox.showwarning("E-posta", "Geçerli bir e-posta adresi girin.", parent=pencere)
            return
        if sifre != sifre_tekrar:
            messagebox.showerror("Hata", "Şifreler eşleşmiyor.", parent=pencere)
            return

        try:
            result = call_api(
                create_user,
                token,
                {
                    "kullanici_adi": ad,
                    "email": email,
                    "sifre": sifre,
                    "rol_adi": rol,
                },
            )
            messagebox.showinfo(
                "Başarılı",
                f"Kullanıcı eklendi.\n\nDoğrulama e-postası {result.get('email') or email} adresine gönderildi.",
                parent=pencere,
            )
            entry_ad.delete(0, "end")
            entry_email.delete(0, "end")
            entry_sifre.delete(0, "end")
            entry_sifre_tekrar.delete(0, "end")
            combo_rol.set("Rol Seç")
            secili_kullanici_var.set("Seçili kullanıcı: Yok")
            kullanicilari_yukle()
        except Exception as exc:
            messagebox.showerror("Hata", str(exc), parent=pencere)

    def kullanici_sil():
        kullanici = get_selected_user()
        if not kullanici:
            return

        if messagebox.askyesno(
            "Emin misiniz?",
            f"{kullanici['kullanici_adi']} kullanıcısını silmek istiyor musunuz?",
            parent=pencere,
        ):
            try:
                call_api(delete_user, token, kullanici["id"])
                kullanicilari_yukle()
            except Exception as exc:
                messagebox.showerror("Hata", str(exc), parent=pencere)

    def sifre_degistir():
        kullanici = get_selected_user()
        yeni_sifre = entry_yeni_sifre.get()
        if not kullanici or not yeni_sifre:
            messagebox.showwarning("Eksik", "Kullanıcı ve yeni şifre seçilmelidir.", parent=pencere)
            return
        try:
            call_api(update_user_password, token, kullanici["id"], yeni_sifre)
            messagebox.showinfo("Başarılı", "Şifre güncellendi.", parent=pencere)
            entry_yeni_sifre.delete(0, "end")
        except Exception as exc:
            messagebox.showerror("Hata", str(exc), parent=pencere)

    def email_guncelle():
        kullanici = get_selected_user()
        yeni_email = entry_email.get().strip()
        if not kullanici:
            return
        if not yeni_email or not is_valid_email(yeni_email):
            messagebox.showwarning("E-posta", "Geçerli bir e-posta adresi girin.", parent=pencere)
            return
        try:
            call_api(update_user_email, token, kullanici["id"], yeni_email)
            messagebox.showinfo("Başarılı", "E-posta güncellendi ve yeni doğrulama kodu gönderildi.", parent=pencere)
            kullanicilari_yukle()
        except Exception as exc:
            messagebox.showerror("Hata", str(exc), parent=pencere)

    def dogrulama_maili_gonder():
        kullanici = get_selected_user()
        if not kullanici:
            return
        try:
            result = call_api(resend_user_verification, token, kullanici["id"])
            messagebox.showinfo("Bilgi", result["message"], parent=pencere)
            kullanicilari_yukle()
        except Exception as exc:
            messagebox.showerror("Hata", str(exc), parent=pencere)

    def dogrulama_kodu_dialogu():
        kullanici = get_selected_user()
        if not kullanici:
            return

        dialog = ctk.CTkToplevel(pencere)
        dialog.title("E-posta Doğrulama")
        dialog.geometry("420x260")
        dialog.transient(pencere)
        try:
            dialog.grab_set()
        except Exception:
            pass

        def dialog_kapat():
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", dialog_kapat)

        container = ctk.CTkFrame(dialog)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            container,
            text=f"{kullanici['kullanici_adi']} için doğrulama kodunu girin",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(10, 15))

        ctk.CTkLabel(container, text=f"E-posta: {kullanici['email']}").pack(pady=(0, 10))

        code_entry = ctk.CTkEntry(container, placeholder_text="6 haneli doğrulama kodu", width=240)
        code_entry.pack(pady=(0, 15))

        def on_verify():
            code = code_entry.get().strip()
            if not code:
                messagebox.showwarning("Kod", "Doğrulama kodunu girin.", parent=dialog)
                return
            try:
                result = verify_email_code(kullanici["email"], code)
                messagebox.showinfo("Başarılı", result["message"], parent=dialog)
                dialog_kapat()
                kullanicilari_yukle()
            except Exception as exc:
                messagebox.showerror("Hata", str(exc), parent=dialog)

        ctk.CTkButton(container, text="Doğrula", command=on_verify).pack(pady=(0, 10))
        ctk.CTkButton(container, text="Kapat", command=dialog_kapat, fg_color="gray").pack()

    tree.bind("<<TreeviewSelect>>", secili_kullaniciyi_forma_yukle)

    ctk.CTkButton(frame_ekle, text="Kullanıcı Ekle", command=kullanici_ekle, width=150).grid(
        row=0, column=6, padx=5, pady=5
    )
    ctk.CTkButton(frame_sifre, text="Şifreyi Güncelle", command=sifre_degistir).grid(
        row=0, column=2, padx=5, pady=5
    )
    ctk.CTkButton(frame_sifre, text="E-postayı Güncelle", command=email_guncelle).grid(
        row=0, column=3, padx=5, pady=5
    )
    ctk.CTkButton(frame_sifre, text="Doğrulama Maili Gönder", command=dogrulama_maili_gonder).grid(
        row=0, column=4, padx=5, pady=5
    )
    ctk.CTkButton(frame_sifre, text="Kod Doğrula", command=dogrulama_kodu_dialogu).grid(
        row=0, column=5, padx=5, pady=5
    )
    ctk.CTkButton(
        pencere,
        text="Seçili Kullanıcıyı Sil",
        command=kullanici_sil,
        fg_color="red",
        hover_color="#cc0000",
    ).pack(pady=10)

    try:
        load_roles_into_combobox()
        kullanicilari_yukle()
    except Exception as exc:
        messagebox.showerror("API Hatası", str(exc), parent=pencere)
        pencereyi_kapat()
