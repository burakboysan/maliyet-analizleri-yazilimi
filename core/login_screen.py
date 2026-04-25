import customtkinter as ctk
from customtkinter import CTkImage
from core.api_client import app_signup
from core.config import APP_VERSION, COPYRIGHT, ENABLE_LOGIN_PREFILL
from PIL import Image, ImageDraw
from tkinter import messagebox
from core.auth import LoginError, kullanici_giris_yap
from core.password_reset import reset_password_with_code, send_password_reset_code
from core.main_menu import ana_menu_ac
from core.email_verification import send_verification_email_for_email, verify_email_code
from core.session import clear_session, set_session
from core.updater import check_for_updates_in_background
import threading
import os
import sys
import traceback
from core.secure_storage import clear_saved_credentials, load_credentials, save_credentials

# Tema
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


# Inter fontu için font ayarları
def get_inter_font(size, weight="normal"):
    return ctk.CTkFont(family="Inter", size=size, weight=weight)

# Ana pencere
root = ctk.CTk()
root.title("Bomaksan Maliyet Analizleri - Giriş")
root.resizable(False, False)
root.configure(fg_color="#f5f5f5")

# Pencereyi ekranın ortasında konumlandır
def center_window():
    # Pencere boyutunu ayarla
    window_width = 800
    window_height = 860
    
    # Ekran boyutlarını al
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Pencereyi ekranın ortasına konumlandır
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    
    # Pencereyi konumlandır ve boyutlandır
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Pencereyi ortala
center_window()

# PyInstaller ile paketlenmiş exe içinde ve geliştirme ortamında varlık dosyası yolu üretici
def get_asset_path(filename: str):
    try:
        base_path = sys._MEIPASS  # PyInstaller geçici klasör
        return os.path.join(base_path, "assets", filename)
    except Exception:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.join(project_root, "assets", filename)

# Ana container - gri arka plan
main_container = ctk.CTkFrame(root, fg_color="#f5f5f5")
main_container.pack(fill="both", expand=True, padx=40, pady=36)

# Beyaz kart container
card_container = ctk.CTkFrame(main_container, fg_color="#ffffff", corner_radius=20)
card_container.pack(expand=True, fill="both", padx=76, pady=32)

# İç container
inner_container = ctk.CTkFrame(card_container, fg_color="transparent")
inner_container.pack(expand=True, fill="both", padx=52, pady=42)

# Header bölümü
header_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
header_frame.pack(pady=(0, 28))

# Logo ikonu
try:
    logo_path = get_asset_path("logo.png")
    # Logo oranını 245:80 olarak ayarla
    logo_image = ctk.CTkImage(light_image=Image.open(logo_path), dark_image=Image.open(logo_path), size=(245, 80))
    logo_label = ctk.CTkLabel(header_frame, image=logo_image, text="")
    logo_label.pack(pady=(0, 20))
except Exception as e:
    print(f"Logo yüklenirken hata: {e}")
    # Logo yüklenemezse varsayılan kırmızı kare ikon
    icon_frame = ctk.CTkFrame(header_frame, fg_color="#d32f2f", corner_radius=12, width=60, height=60)
    icon_frame.pack(pady=(0, 20))
    shield_label = ctk.CTkLabel(icon_frame, text="BM", font=get_inter_font(20, "bold"), text_color="#ffffff")
    shield_label.pack(expand=True)



# Alt başlık
subtitle_label = ctk.CTkLabel(
    header_frame,
    text="Maliyet Analizleri Yazılımı",
    font=get_inter_font(14),
    text_color="#666666"
)
subtitle_label.pack()

version_label = ctk.CTkLabel(
    header_frame,
    text=f"Surum {APP_VERSION}",
    font=get_inter_font(12),
    text_color="#888888"
)
version_label.pack(pady=(6, 0))

# Form bölümü
form_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
form_frame.pack(fill="x", pady=(0, 20))

# Kullanıcı adı alanı
username_frame = ctk.CTkFrame(form_frame, fg_color="#f8f9fa", corner_radius=12, height=50)
username_frame.pack(fill="x", pady=(0, 20))

# Kullanıcı ikonu
user_icon = ctk.CTkLabel(username_frame, text="K", font=get_inter_font(16, "bold"), text_color="#424242")
user_icon.pack(side="left", padx=(15, 10))

# Kullanıcı adı entry
entry_kullanici_adi = ctk.CTkEntry(
    username_frame,
    placeholder_text="Kullanıcı Adı",
    font=get_inter_font(14),
    fg_color="transparent",
    border_width=0,
    text_color="#424242"
)
entry_kullanici_adi.pack(side="left", fill="x", expand=True, padx=(0, 15))

# Åifre alanÄ±
password_frame = ctk.CTkFrame(form_frame, fg_color="#f8f9fa", corner_radius=12, height=50)
password_frame.pack(fill="x", pady=(0, 20))

# Åifre ikonu
password_icon = ctk.CTkLabel(password_frame, text="*", font=get_inter_font(16, "bold"), text_color="#424242")
password_icon.pack(side="left", padx=(15, 10))

# Åifre entry
entry_sifre = ctk.CTkEntry(
    password_frame,
    placeholder_text="Şifre",
    show="*",
    font=get_inter_font(14),
    fg_color="transparent",
    border_width=0,
    text_color="#424242"
)
entry_sifre.pack(side="left", fill="x", expand=True, padx=(0, 10))

# Göz ikonu (şifre göster/gizle)
eye_icon = ctk.CTkLabel(password_frame, text="Goster", font=get_inter_font(12), text_color="#424242", cursor="hand2")
eye_icon.pack(side="right", padx=(0, 15))

# Seçenekler satırı
options_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
options_frame.pack(fill="x", pady=(0, 22))

# Beni hatırla checkbox
remember_var = ctk.BooleanVar()
remember_checkbox = ctk.CTkCheckBox(
    options_frame,
    text="Beni Hatırla",
    font=get_inter_font(12),
    text_color="#424242",
    fg_color="#d32f2f",
    hover_color="#c62828",
    variable=remember_var
)
remember_checkbox.pack(side="left")

# Åifremi unuttum linki
forgot_password_label = ctk.CTkLabel(
    options_frame,
    text="Şifremi Unuttum",
    font=get_inter_font(12),
    text_color="#d32f2f",
    cursor="hand2"
)
forgot_password_label.pack(side="right")

verify_email_label = ctk.CTkLabel(
    options_frame,
    text="E-posta Doğrula",
    font=get_inter_font(12),
    text_color="#d32f2f",
    cursor="hand2"
)
verify_email_label.pack(side="right", padx=(0, 15))

# Giriş butonu
giris_button = ctk.CTkButton(
    form_frame,
    text="Giriş Yap",
    font=get_inter_font(14, "bold"),
    fg_color="#d32f2f",
    hover_color="#c62828",
    corner_radius=12,
    height=50,
    text_color="#ffffff"
)
giris_button.pack(fill="x")

# Footer bölümü
footer_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
footer_frame.pack(side="bottom", fill="x", pady=(18, 0))

# Hesap yok mu metni
no_account_label = ctk.CTkLabel(
    footer_frame,
    text="Henüz hesabınız yok mu?",
    font=get_inter_font(12),
    text_color="#666666"
)
no_account_label.pack(pady=(0, 5))

# Destek ile iletişim linki
support_label = ctk.CTkLabel(
    footer_frame,
    text="Hesap Oluştur",
    font=get_inter_font(12),
    text_color="#d32f2f",
    cursor="hand2"
)
support_label.pack()

# Destek ile iletişim fonksiyonu
def show_support_dialog():
    """Destek ile iletişim dialog penceresi"""
    dialog = ctk.CTkToplevel(root)
    dialog.title("Destek ile İletişim")
    dialog.geometry("550x350")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#f5f5f5")
    
    # Pencereyi ortala
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.transient(root)
    dialog.grab_set()
    
    # Ana container
    main_container = ctk.CTkFrame(dialog, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=30, pady=30)
    
    # Beyaz kart container
    card_container = ctk.CTkFrame(main_container, fg_color="#ffffff", corner_radius=15)
    card_container.pack(expand=True, fill="both", padx=20, pady=20)
    
    # İç container
    inner_container = ctk.CTkFrame(card_container, fg_color="transparent")
    inner_container.pack(expand=True, fill="both", padx=40, pady=40)
    
    # Başlık
    title_label = ctk.CTkLabel(
        inner_container,
        text="Destek ile İletişim",
        font=get_inter_font(18, "bold"),
        text_color="#424242"
    )
    title_label.pack(pady=(0, 20))
    
    # Açıklama
    description_label = ctk.CTkLabel(
        inner_container,
        text="Teknik destek ve yardım için aşağıdaki iletişim kanallarını kullanabilirsiniz:",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=350
    )
    description_label.pack(pady=(0, 25))
    
    # İletişim bilgileri
    support_info = [
        ("E-posta:", "it@bomaksan.com"),
        ("Telefon:", "+90 216 541 93 34"),
    ]
    
    for label_text, value_text in support_info:
        info_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 10))
        
        label = ctk.CTkLabel(
            info_frame,
            text=label_text,
            font=get_inter_font(12, "bold"),
            text_color="#424242"
        )
        label.pack(side="left")
        
        value = ctk.CTkLabel(
            info_frame,
            text=value_text,
            font=get_inter_font(12),
            text_color="#666666"
        )
        value.pack(side="right")
    
    # Kapat butonu
    close_button = ctk.CTkButton(
        inner_container,
        text="Kapat",
        font=get_inter_font(12),
        fg_color="#d32f2f",
        hover_color="#c62828",
        corner_radius=8,
        height=35,
        command=dialog.destroy
    )
    close_button.pack(side="bottom", pady=(20, 0))


signup_overlay = None


def close_signup_dialog():
    global signup_overlay
    if signup_overlay is not None:
        try:
            signup_overlay.destroy()
        except Exception:
            pass
        signup_overlay = None
    try:
        entry_kullanici_adi.focus()
    except Exception:
        pass


def show_signup_dialog():
    global signup_overlay
    close_signup_dialog()

    signup_overlay = ctk.CTkFrame(card_container, fg_color="#ffffff", corner_radius=20)
    signup_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
    signup_overlay.lift()

    inner_container = ctk.CTkFrame(signup_overlay, fg_color="transparent")
    inner_container.pack(expand=True, fill="both", padx=52, pady=42)

    top_bar = ctk.CTkFrame(inner_container, fg_color="transparent")
    top_bar.pack(fill="x", pady=(0, 22))

    close_label = ctk.CTkLabel(
        top_bar,
        text="Kapat",
        font=get_inter_font(12),
        text_color="#888888",
        cursor="hand2"
    )
    close_label.pack(side="right")
    close_label.bind("<Button-1>", lambda _event: close_signup_dialog())

    header_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
    header_frame.pack(fill="x", pady=(12, 26))

    ctk.CTkLabel(
        header_frame,
        text="Hesap Oluştur",
        font=get_inter_font(24, "bold"),
        text_color="#424242"
    ).pack()

    ctk.CTkLabel(
        header_frame,
        text="Bomaksan hesabınızı oluşturun",
        font=get_inter_font(13),
        text_color="#777777"
    ).pack(pady=(8, 0))

    info_box = ctk.CTkFrame(inner_container, fg_color="#f8f9fa", corner_radius=14)
    info_box.pack(fill="x", pady=(0, 18))

    ctk.CTkLabel(
        info_box,
        text="Sadece @bomaksan.com uzantılı e-posta adresleri kabul edilir.\nE-posta doğrulaması tamamlanmadan giriş yapamazsınız.",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=520,
        justify="left",
        anchor="w"
    ).pack(fill="x", padx=24, pady=16)

    status_box = ctk.CTkFrame(inner_container, fg_color="transparent", height=28)
    status_box.pack(fill="x", pady=(0, 12))
    status_box.pack_propagate(False)

    status_label = ctk.CTkLabel(
        status_box,
        text="",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=620,
        justify="left",
        anchor="w"
    )
    status_label.pack(fill="both")

    def set_status(message, is_error=False, is_success=False):
        color = "#666666"
        if is_error:
            color = "#b71c1c"
        elif is_success:
            color = "#1b5e20"
        status_label.configure(text=message, text_color=color)

    form_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
    form_frame.pack(fill="x", pady=(0, 18))

    def create_input_row(parent, icon_text, placeholder_text, show=None, right_text=None, right_command=None):
        field_frame = ctk.CTkFrame(parent, fg_color="#f8f9fa", corner_radius=12, height=52)
        field_frame.pack(fill="x", pady=(0, 14))
        field_frame.pack_propagate(False)

        icon_label = ctk.CTkLabel(
            field_frame,
            text=icon_text,
            font=get_inter_font(16, "bold"),
            text_color="#424242",
            width=30
        )
        icon_label.pack(side="left", padx=(16, 10))

        entry = ctk.CTkEntry(
            field_frame,
            placeholder_text=placeholder_text,
            font=get_inter_font(14),
            fg_color="transparent",
            border_width=0,
            show=show,
            text_color="#424242",
            placeholder_text_color="#8a8a8a"
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 12))

        if right_text and right_command:
            action_label = ctk.CTkLabel(
                field_frame,
                text=right_text,
                font=get_inter_font(12),
                text_color="#424242",
                cursor="hand2"
            )
            action_label.pack(side="right", padx=(0, 16))
            action_label.bind("<Button-1>", lambda _event: right_command())
        return entry

    username_entry = create_input_row(form_frame, "K", "Kullanıcı Adı")
    email_entry = create_input_row(form_frame, "@", "E-posta Adresi (@bomaksan.com)")

    password_visible = {"value": False}
    password_toggle_label = {"widget": None}

    def toggle_signup_password():
        password_visible["value"] = not password_visible["value"]
        password_entry.configure(show="" if password_visible["value"] else "*")
        if password_toggle_label["widget"] is not None:
            password_toggle_label["widget"].configure(text="Gizle" if password_visible["value"] else "Goster")

    password_entry = create_input_row(
        form_frame,
        "*",
        "Şifre",
        show="*",
        right_text="Goster",
        right_command=toggle_signup_password,
    )

    for child in form_frame.winfo_children():
        labels = [grand for grand in child.winfo_children() if isinstance(grand, ctk.CTkLabel) and grand.cget("cursor") == "hand2"]
        if labels:
            password_toggle_label["widget"] = labels[0]

    helper_row = ctk.CTkFrame(inner_container, fg_color="transparent")
    helper_row.pack(fill="x", pady=(0, 22))

    ctk.CTkLabel(
        helper_row,
        text="Kullanıcı adı, kurumsal e-posta ve en az 8 karakterli bir şifre belirleyin.",
        font=get_inter_font(11),
        text_color="#8a8a8a",
        wraplength=560,
        justify="left",
        anchor="w"
    ).pack(fill="x", anchor="w")

    def register_account():
        username = username_entry.get().strip()
        email = email_entry.get().strip().lower()
        password = password_entry.get()

        if not username:
            set_status("Kullanıcı adını girin.", is_error=True)
            return
        if not email:
            set_status("E-posta adresini girin.", is_error=True)
            return
        if not email.endswith("@bomaksan.com"):
            set_status("Sadece @bomaksan.com uzantılı e-posta adresleri ile kayıt olabilirsiniz.", is_error=True)
            return
        if not password:
            set_status("Şifreyi girin.", is_error=True)
            return

        try:
            result = app_signup(username, email, password) or {}
            entry_kullanici_adi.delete(0, "end")
            entry_kullanici_adi.insert(0, username)
            entry_sifre.delete(0, "end")
            entry_sifre.insert(0, password)
            remember_var.set(False)
            set_status(result.get("message", "Hesabınız oluşturuldu."), is_success=True)
            root.after(700, close_signup_dialog)
            root.after(750, lambda: show_email_verification_dialog(default_email=email))
        except Exception as e:
            set_status(str(e), is_error=True)

    ctk.CTkButton(
        inner_container,
        text="Hesap Oluştur",
        font=get_inter_font(14, "bold"),
        fg_color="#d32f2f",
        hover_color="#c62828",
        corner_radius=12,
        height=50,
        command=register_account,
    ).pack(fill="x", pady=(0, 14))

    footer_actions = ctk.CTkFrame(inner_container, fg_color="transparent")
    footer_actions.pack(fill="x", pady=(8, 0))

    ctk.CTkLabel(
        footer_actions,
        text="Sorun yaşıyorsanız destek ile iletişime geçin",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=560,
        justify="center"
    ).pack(fill="x", pady=(4, 6))

    support_action = ctk.CTkLabel(
        footer_actions,
        text="Destek ile İletişime Geçin",
        font=get_inter_font(12),
        text_color="#d32f2f",
        cursor="hand2"
    )
    support_action.pack()
    support_action.bind("<Button-1>", lambda _event: (close_signup_dialog(), show_support_dialog()))

    close_action = ctk.CTkLabel(
        footer_actions,
        text="Vazgeç",
        font=get_inter_font(12),
        text_color="#888888",
        cursor="hand2"
    )
    close_action.pack(pady=(12, 0))
    close_action.bind("<Button-1>", lambda _event: close_signup_dialog())

    username_entry.focus()
    signup_overlay.bind("<Escape>", lambda _event: close_signup_dialog())
    signup_overlay.bind("<Return>", lambda _event: register_account())

# Loading durumu için değişkenler
is_loading = False
original_button_text = "Giriş Yap"

# Giriş fonksiyonu
def giris_yap():
    global is_loading
    
    if is_loading:
        return
    
    kadi = entry_kullanici_adi.get().strip()
    sifre = entry_sifre.get().strip()
    
    if not kadi or not sifre:
        messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre alanları boş bırakılamaz.")
        return
    
    # Loading durumunu başlat
    is_loading = True
    giris_button.configure(
        text="Giriş Yapılıyor...",
        state="disabled",
        fg_color="#9e9e9e"
    )
    entry_kullanici_adi.configure(state="disabled")
    entry_sifre.configure(state="disabled")
    
    # Giriş işlemini ayrı thread'de yap - sadece kullanıcı doğrulaması
    def login_thread():
        try:
            # Sadece kullanıcı doğrulaması yap, veritabanı hazırlık işlemleri ana menüde yapılacak
            kullanici_adi, rol = kullanici_giris_yap(kadi, sifre)
            root.after(0, lambda: handle_login_result(kullanici_adi, rol, kadi, sifre))
        except LoginError as e:
            root.after(0, lambda msg=str(e): handle_login_error(msg))
        except Exception as e:
            root.after(0, lambda: handle_login_error(str(e)))
    
    threading.Thread(target=login_thread, daemon=True).start()

def handle_login_result(kullanici_adi, rol, kadi, sifre):
    global is_loading
    
    if rol:
        # Oturumda kullanicinin ekrana yazdigi deger yerine backend'in dogruladigi
        # kanonik kullanici adini sakla; yukleme akisinda ayni bilgi tekrar kullaniliyor.
        session_username = (kullanici_adi or kadi or "").strip()
        set_session(kullanici_adi=session_username, sifre=sifre, rol=rol, admin_token="")
        # Başarılı giriş - "Beni Hatırla" seçeneği işaretliyse bilgileri kaydet
        if remember_var.get():
            save_credentials(session_username, sifre)
        else:
            # İşaretli değilse kaydedilmiş bilgileri temizle
            clear_saved_credentials()
        
        # Ana menüyü aç (veritabanı hazırlık işlemleri orada başlayacak)
        root.withdraw()
        try:
            # Kapatıldığında tamamen çıkılabilmesi için kökü geçir
            ana_menu_ac(kullanici_adi, rol, parent_root=root)
        except Exception as e:
            print("Ana menu acilis hatasi:")
            traceback.print_exc()
            try:
                root.deiconify()
                root.lift()
                root.focus_force()
            except Exception:
                pass
            messagebox.showerror("Ana Menü Hatası", f"Ana menü açılırken hata oluştu:\n{e}")
            reset_login_form()
    else:
        # Başarısız giriş
        clear_session()
        messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı.")
        reset_login_form()

def handle_login_error(error_msg):
    global is_loading
    clear_session()
    messagebox.showerror("Sistem Hatası", f"Giriş sırasında bir hata oluştu:\n{error_msg}")
    reset_login_form()

def reset_login_form():
    global is_loading
    is_loading = False
    giris_button.configure(
        text=original_button_text,
        state="normal",
        fg_color="#d32f2f"
    )
    entry_kullanici_adi.configure(state="normal")
    entry_sifre.configure(state="normal")
    entry_sifre.delete(0, "end")
    entry_kullanici_adi.focus()

# Åifre gÃ¶ster/gizle fonksiyonu
def toggle_password():
    if entry_sifre.cget("show") == "*":
        entry_sifre.configure(show="")
        eye_icon.configure(text="Gizle")
    else:
        entry_sifre.configure(show="*")
        eye_icon.configure(text="Goster")

# Åifremi unuttum fonksiyonu
def show_forgot_password_dialog():
    """Åifremi unuttum dialog penceresini gÃ¶ster"""
    
    # Dialog penceresi oluştur
    dialog = ctk.CTkToplevel(root)
    dialog.title("Şifremi Unuttum")
    dialog.geometry("600x400")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#f5f5f5")
    
    # Pencereyi ortala
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    # Modal pencere yap
    dialog.transient(root)
    dialog.grab_set()
    
    # Ana container
    main_container = ctk.CTkFrame(dialog, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=30, pady=30)
    
    # Beyaz kart container
    card_container = ctk.CTkFrame(main_container, fg_color="#ffffff", corner_radius=15)
    card_container.pack(expand=True, fill="both", padx=20, pady=20)
    
    # İç container
    inner_container = ctk.CTkFrame(card_container, fg_color="transparent")
    inner_container.pack(expand=True, fill="both", padx=40, pady=40)
    
    # Başlık
    title_label = ctk.CTkLabel(
        inner_container,
        text="Şifremi Unuttum",
        font=get_inter_font(20, "bold"),
        text_color="#424242"
    )
    title_label.pack(pady=(0, 20))
    
    # Açıklama
    description_label = ctk.CTkLabel(
        inner_container,
        text="Şifrenizi sıfırlamak için aşağıdaki seçeneklerden birini kullanabilirsiniz:",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=400
    )
    description_label.pack(pady=(0, 30))
    
    # Seçenekler frame
    options_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
    options_frame.pack(fill="x", pady=(0, 30))
    
    # Seçenek 1: Yönetici ile iletişim
    option1_frame = ctk.CTkFrame(options_frame, fg_color="#f8f9fa", corner_radius=10, height=80)
    option1_frame.pack(fill="x", pady=(0, 15))
    
    option1_icon = ctk.CTkLabel(option1_frame, text="1", font=get_inter_font(20, "bold"), text_color="#d32f2f")
    option1_icon.pack(side="left", padx=(20, 15))
    
    option1_text_frame = ctk.CTkFrame(option1_frame, fg_color="transparent")
    option1_text_frame.pack(side="left", fill="x", expand=True, padx=(0, 20))
    
    option1_title = ctk.CTkLabel(
        option1_text_frame,
        text="Yönetici ile İletişim",
        font=get_inter_font(14, "bold"),
        text_color="#424242"
    )
    option1_title.pack(anchor="w")
    
    option1_desc = ctk.CTkLabel(
        option1_text_frame,
        text="K. Burak Boysan ile iletişime geçerek şifrenizi sıfırlatın",
        font=get_inter_font(11),
        text_color="#666666"
    )
    option1_desc.pack(anchor="w")
    
    # Seçenek 2: E-posta ile sıfırlama
    option2_frame = ctk.CTkFrame(options_frame, fg_color="#f8f9fa", corner_radius=10, height=80)
    option2_frame.pack(fill="x", pady=(0, 15))
    
    option2_icon = ctk.CTkLabel(option2_frame, text="2", font=get_inter_font(20, "bold"), text_color="#d32f2f")
    option2_icon.pack(side="left", padx=(20, 15))
    
    option2_text_frame = ctk.CTkFrame(option2_frame, fg_color="transparent")
    option2_text_frame.pack(side="left", fill="x", expand=True, padx=(0, 20))
    
    option2_title = ctk.CTkLabel(
        option2_text_frame,
        text="E-posta ile Sıfırlama",
        font=get_inter_font(14, "bold"),
        text_color="#424242"
    )
    option2_title.pack(anchor="w")
    
    option2_desc = ctk.CTkLabel(
        option2_text_frame,
        text="Kayıtlı e-posta adresinize sıfırlama linki gönderin",
        font=get_inter_font(11),
        text_color="#666666"
    )
    option2_desc.pack(anchor="w")
    
    # Seçenek 3: Güvenlik soruları
    option3_frame = ctk.CTkFrame(options_frame, fg_color="#f8f9fa", corner_radius=10, height=80)
    option3_frame.pack(fill="x")
    
    option3_icon = ctk.CTkLabel(option3_frame, text="3", font=get_inter_font(20, "bold"), text_color="#d32f2f")
    option3_icon.pack(side="left", padx=(20, 15))
    
    option3_text_frame = ctk.CTkFrame(option3_frame, fg_color="transparent")
    option3_text_frame.pack(side="left", fill="x", expand=True, padx=(0, 20))
    
    option3_title = ctk.CTkLabel(
        option3_text_frame,
        text="Güvenlik Soruları",
        font=get_inter_font(14, "bold"),
        text_color="#424242"
    )
    option3_title.pack(anchor="w")
    
    option3_desc = ctk.CTkLabel(
        option3_text_frame,
        text="Güvenlik sorularınızı yanıtlayarak şifrenizi sıfırlayın",
        font=get_inter_font(11),
        text_color="#666666"
    )
    option3_desc.pack(anchor="w")
    
    # Butonlar frame
    buttons_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
    buttons_frame.pack(side="bottom", fill="x", pady=(30, 0))
    
    # Kapat butonu
    close_button = ctk.CTkButton(
        buttons_frame,
        text="Kapat",
        font=get_inter_font(12),
        fg_color="#9e9e9e",
        hover_color="#757575",
        corner_radius=8,
        height=35,
        command=dialog.destroy
    )
    close_button.pack(side="right")
    
    # Seçenek tıklama fonksiyonları
    def contact_admin():
        dialog.destroy()
        show_admin_contact_dialog()
    
    def email_reset():
        dialog.destroy()
        show_email_reset_dialog()
    
    def security_questions():
        dialog.destroy()
        show_security_questions_dialog()
    
    # Seçeneklere tıklama olayları ekle
    option1_frame.bind("<Button-1>", lambda e: contact_admin())
    option1_icon.bind("<Button-1>", lambda e: contact_admin())
    option1_text_frame.bind("<Button-1>", lambda e: contact_admin())
    
    option2_frame.bind("<Button-1>", lambda e: email_reset())
    option2_icon.bind("<Button-1>", lambda e: email_reset())
    option2_text_frame.bind("<Button-1>", lambda e: email_reset())
    
    option3_frame.bind("<Button-1>", lambda e: security_questions())
    option3_icon.bind("<Button-1>", lambda e: security_questions())
    option3_text_frame.bind("<Button-1>", lambda e: security_questions())

def show_admin_contact_dialog():
    """Yönetici ile iletişim dialog penceresi"""
    dialog = ctk.CTkToplevel(root)
    dialog.title("Yönetici ile İletişim")
    dialog.geometry("450x300")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#f5f5f5")
    
    # Pencereyi ortala
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.transient(root)
    dialog.grab_set()
    
    # Ana container
    main_container = ctk.CTkFrame(dialog, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=30, pady=30)
    
    # Beyaz kart container
    card_container = ctk.CTkFrame(main_container, fg_color="#ffffff", corner_radius=15)
    card_container.pack(expand=True, fill="both", padx=20, pady=20)
    
    # İç container
    inner_container = ctk.CTkFrame(card_container, fg_color="transparent")
    inner_container.pack(expand=True, fill="both", padx=40, pady=40)
    
    # Başlık
    title_label = ctk.CTkLabel(
        inner_container,
        text="Yönetici ile İletişim",
        font=get_inter_font(18, "bold"),
        text_color="#424242"
    )
    title_label.pack(pady=(0, 20))
    
    # Açıklama
    description_label = ctk.CTkLabel(
        inner_container,
        text="Şifrenizi sıfırlamak için sistem yöneticisi ile iletişime geçin:",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=350
    )
    description_label.pack(pady=(0, 25))
    
    # İletişim bilgileri
    contact_info = [
        ("E-posta:", "admin@bomaksan.com"),
        ("Telefon:", "+90 212 555 0123"),
        ("Adres:", "Bomaksan Teknoloji A.Ş."),
        ("Konum:", "İstanbul, Türkiye")
    ]
    
    for label_text, value_text in contact_info:
        info_frame = ctk.CTkFrame(inner_container, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 10))
        
        label = ctk.CTkLabel(
            info_frame,
            text=label_text,
            font=get_inter_font(12, "bold"),
            text_color="#424242"
        )
        label.pack(side="left")
        
        value = ctk.CTkLabel(
            info_frame,
            text=value_text,
            font=get_inter_font(12),
            text_color="#666666"
        )
        value.pack(side="right")
    
    # Kapat butonu
    close_button = ctk.CTkButton(
        inner_container,
        text="Kapat",
        font=get_inter_font(12),
        fg_color="#d32f2f",
        hover_color="#c62828",
        corner_radius=8,
        height=35,
        command=dialog.destroy
    )
    close_button.pack(side="bottom", pady=(20, 0))

def show_email_reset_dialog():
    """Sifre sifirlama dialog penceresi"""
    dialog = ctk.CTkToplevel(root)
    dialog.title("Şifremi Unuttum")
    dialog.geometry("620x560")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#f5f5f5")
    
    # Pencereyi ortala
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.transient(root)
    dialog.grab_set()
    
    # Ana container
    main_container = ctk.CTkFrame(dialog, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=30, pady=30)
    
    # Beyaz kart container
    card_container = ctk.CTkFrame(main_container, fg_color="#ffffff", corner_radius=15)
    card_container.pack(expand=True, fill="both", padx=20, pady=20)
    
    # İç container
    inner_container = ctk.CTkScrollableFrame(card_container, fg_color="transparent")
    inner_container.pack(expand=True, fill="both", padx=30, pady=30)
    
    # Başlık
    title_label = ctk.CTkLabel(
        inner_container,
        text="Şifre Sıfırlama",
        font=get_inter_font(18, "bold"),
        text_color="#424242"
    )
    title_label.pack(pady=(0, 20))
    
    description_label = ctk.CTkLabel(
        inner_container,
        text="Kullanıcı adınızı veya e-posta adresinizi girin. Mailinize gelen kod ile yeni şifrenizi belirleyin.",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=350
    )
    description_label.pack(pady=(0, 20))

    def create_dialog_entry(placeholder_text, show=None):
        return ctk.CTkEntry(
            inner_container,
            placeholder_text=placeholder_text,
            show=show,
            width=300,
            fg_color="#ffffff",
            text_color="#222222",
            placeholder_text_color="#777777",
            border_color="#d9d9d9",
        )

    status_label = ctk.CTkLabel(
        inner_container,
        text="",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=420,
        justify="left",
    )
    status_label.pack(pady=(0, 15), anchor="w")

    def set_status(message, is_error=False, is_success=False):
        color = "#666666"
        if is_error:
            color = "#b71c1c"
        elif is_success:
            color = "#1b5e20"
        status_label.configure(text=message, text_color=color)

    identifier_entry = create_dialog_entry("Kullanıcı adı veya e-posta")
    identifier_entry.pack(pady=(0, 10))

    code_entry = create_dialog_entry("6 haneli sıfırlama kodu")
    code_entry.pack(pady=(0, 10))

    new_password_entry = create_dialog_entry("Yeni şifre", show="*")
    new_password_entry.pack(pady=(0, 10))

    confirm_password_entry = create_dialog_entry("Yeni şifre (tekrar)", show="*")
    confirm_password_entry.pack(pady=(0, 20))

    def send_code():
        identifier = identifier_entry.get().strip()
        if not identifier:
            set_status("Lutfen kullanici adi veya e-posta adresi girin.", is_error=True)
            return
        try:
            result = send_password_reset_code(identifier)
            set_status(result["message"], is_success=True)
        except Exception as e:
            set_status(str(e), is_error=True)

    def reset_password():
        identifier = identifier_entry.get().strip()
        reset_code = code_entry.get().strip()
        new_password = new_password_entry.get()
        confirm_password = confirm_password_entry.get()
        if not identifier:
            set_status("Lutfen kullanici adi veya e-posta adresi girin.", is_error=True)
            return
        if not reset_code:
            set_status("Lutfen sifirlama kodunu girin.", is_error=True)
            return
        if new_password != confirm_password:
            set_status("Yeni sifreler eslesmiyor.", is_error=True)
            return
        try:
            result = reset_password_with_code(
                identifier,
                reset_code,
                new_password,
            )
            login_identifier = result.get("username") or identifier
            entry_kullanici_adi.delete(0, "end")
            entry_kullanici_adi.insert(0, login_identifier)
            entry_sifre.delete(0, "end")
            entry_sifre.insert(0, new_password)
            set_status(result["message"] + " Giris ekrani yeni sifrenizle dolduruldu.", is_success=True)
        except Exception as e:
            set_status(str(e), is_error=True)

    ctk.CTkButton(
        inner_container,
        text="Kodu Gönder",
        font=get_inter_font(12),
        fg_color="#ffffff",
        hover_color="#d32f2f",
        text_color="#d32f2f",
        border_width=1,
        border_color="#d32f2f",
        corner_radius=8,
        height=35,
        command=send_code
    ).pack(fill="x", pady=(0, 10))

    ctk.CTkButton(
        inner_container,
        text="Şifreyi Sıfırla",
        font=get_inter_font(12),
        fg_color="#d32f2f",
        hover_color="#c62828",
        corner_radius=8,
        height=35,
        command=reset_password
    ).pack(fill="x", pady=(0, 10))

    close_button = ctk.CTkButton(
        inner_container,
        text="Kapat",
        font=get_inter_font(12),
        fg_color="gray",
        hover_color="#666666",
        corner_radius=8,
        height=35,
        command=dialog.destroy
    )
    close_button.pack(fill="x")


def show_email_verification_dialog(default_email=""):
    dialog = ctk.CTkToplevel(root)
    dialog.title("E-posta Doğrula")
    dialog.geometry("620x560")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#f5f5f5")

    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    dialog.transient(root)
    dialog.grab_set()

    main_container = ctk.CTkFrame(dialog, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=30, pady=30)

    card_container = ctk.CTkFrame(main_container, fg_color="#ffffff", corner_radius=15)
    card_container.pack(expand=True, fill="both", padx=20, pady=20)

    inner_container = ctk.CTkScrollableFrame(card_container, fg_color="transparent")
    inner_container.pack(expand=True, fill="both", padx=30, pady=24)

    ctk.CTkLabel(
        inner_container,
        text="E-posta Doğrulama",
        font=get_inter_font(18, "bold"),
        text_color="#424242"
    ).pack(pady=(0, 10))

    ctk.CTkLabel(
        inner_container,
        text="E-posta adresinize gelen 6 haneli kodu girerek hesabınızı aktif hale getirin.",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=440,
        justify="left",
    ).pack(pady=(0, 20))

    status_label = ctk.CTkLabel(
        inner_container,
        text="",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=460,
        justify="left",
    )
    status_label.pack(fill="x", pady=(0, 16))

    def set_status(message, is_error=False, is_success=False):
        color = "#666666"
        if is_error:
            color = "#b71c1c"
        elif is_success:
            color = "#1b5e20"
        status_label.configure(text=message, text_color=color)

    email_entry = ctk.CTkEntry(inner_container, placeholder_text="E-posta adresi", width=420, height=40)
    email_entry.pack(fill="x", pady=(0, 12))
    if default_email:
        email_entry.insert(0, default_email)

    code_entry = ctk.CTkEntry(inner_container, placeholder_text="Doğrulama kodu", width=420, height=40)
    code_entry.pack(fill="x", pady=(0, 20))

    def resend_code():
        try:
            result = send_verification_email_for_email(email_entry.get().strip())
            set_status(result["message"], is_success=True)
        except Exception as e:
            set_status(str(e), is_error=True)

    def verify_code():
        try:
            result = verify_email_code(email_entry.get().strip(), code_entry.get().strip())
            set_status(result["message"], is_success=True)
            dialog.destroy()
        except Exception as e:
            set_status(str(e), is_error=True)

    ctk.CTkButton(inner_container, text="Kodu Doğrula", height=38, command=verify_code).pack(fill="x", pady=(0, 10))
    ctk.CTkButton(
        inner_container,
        text="Kodu Yeniden Gönder",
        command=resend_code,
        height=38,
        fg_color="#ffffff",
        hover_color="#d32f2f",
        text_color="#d32f2f",
        border_width=1,
        border_color="#d32f2f"
    ).pack(fill="x", pady=(0, 10))
    ctk.CTkButton(inner_container, text="Kapat", height=38, command=dialog.destroy, fg_color="gray").pack(fill="x", pady=(0, 4))

def show_security_questions_dialog():
    """Güvenlik soruları dialog penceresi"""
    dialog = ctk.CTkToplevel(root)
    dialog.title("Güvenlik Soruları")
    dialog.geometry("450x250")
    dialog.resizable(False, False)
    dialog.configure(fg_color="#f5f5f5")
    
    # Pencereyi ortala
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.transient(root)
    dialog.grab_set()
    
    # Ana container
    main_container = ctk.CTkFrame(dialog, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=30, pady=30)
    
    # Beyaz kart container
    card_container = ctk.CTkFrame(main_container, fg_color="#ffffff", corner_radius=15)
    card_container.pack(expand=True, fill="both", padx=20, pady=20)
    
    # İç container
    inner_container = ctk.CTkFrame(card_container, fg_color="transparent")
    inner_container.pack(expand=True, fill="both", padx=40, pady=40)
    
    # Başlık
    title_label = ctk.CTkLabel(
        inner_container,
        text="Güvenlik Soruları",
        font=get_inter_font(18, "bold"),
        text_color="#424242"
    )
    title_label.pack(pady=(0, 20))
    
    # Açıklama
    description_label = ctk.CTkLabel(
        inner_container,
        text="Bu özellik henüz aktif değildir. Lütfen yönetici ile iletişime geçin.",
        font=get_inter_font(12),
        text_color="#666666",
        wraplength=350
    )
    description_label.pack(pady=(0, 25))
    
    # Kapat butonu
    close_button = ctk.CTkButton(
        inner_container,
        text="Kapat",
        font=get_inter_font(12),
        fg_color="#d32f2f",
        hover_color="#c62828",
        corner_radius=8,
        height=35,
        command=dialog.destroy
    )
    close_button.pack(side="bottom", pady=(20, 0))

# Buton komutlarını ayarla
giris_button.configure(command=giris_yap)
eye_icon.bind("<Button-1>", lambda event: toggle_password())
forgot_password_label.bind("<Button-1>", lambda event: show_email_reset_dialog())
verify_email_label.bind("<Button-1>", lambda event: show_email_verification_dialog())
support_label.bind("<Button-1>", lambda event: show_signup_dialog())

# Enter tuşu
root.bind("<Return>", lambda event: giris_yap())

# Kaydedilmiş bilgileri yükle
def load_saved_credentials():
    username, password = load_credentials()
    if username and password:
        entry_kullanici_adi.insert(0, username)
        entry_sifre.insert(0, password)
        remember_var.set(True)  # Checkbox'ı işaretle
        return True
    return False

# Form alanlarına odaklan ve (bayrağa göre) kaydedilmiş bilgileri yükle
if ENABLE_LOGIN_PREFILL:
    root.after(100, lambda: load_saved_credentials() or entry_kullanici_adi.focus())
else:
    root.after(100, lambda: entry_kullanici_adi.focus())

root.after(1500, lambda: check_for_updates_in_background(root))

def main():
    # Pencere kapatılınca uygulamayı tamamen sonlandır
    import sys
    def _on_root_close():
        try:
            root.destroy()
        except Exception:
            pass
        try:
            sys.exit(0)
        except SystemExit:
            pass
    root.protocol("WM_DELETE_WINDOW", _on_root_close)
    root.mainloop()

if __name__ == "__main__":
    main()
