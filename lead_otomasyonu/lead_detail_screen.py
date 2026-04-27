from tkinter import messagebox

import customtkinter as ctk


def lead_detay_ekrani(parent, lead, on_update=None):
    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title(f"Lead Detay - {lead.get('company_name', '')}")
    win.geometry("1040x720")
    win.minsize(900, 620)
    win.configure(fg_color="#f5f5f5")

    try:
        win.lift()
        win.focus_force()
        win.attributes("-topmost", True)
        win.after(300, lambda: win.attributes("-topmost", False))
    except Exception:
        pass

    root = ctk.CTkFrame(win, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=20, pady=20)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(1, weight=1)

    title = ctk.CTkLabel(
        root,
        text=lead.get("company_name") or "Lead Detay",
        font=ctk.CTkFont(family="Inter", size=26, weight="bold"),
        text_color="#212121",
    )
    title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

    left = _panel(root)
    left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
    right = _panel(root)
    right.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

    _section_title(left, "Firma Bilgileri")
    _kv(left, "Ülke", lead.get("country"))
    _kv(left, "Dil", lead.get("local_language"))
    _kv(left, "Kaynak", lead.get("source"))
    _kv(left, "Web", lead.get("website"))
    _kv(left, "Aktivite", lead.get("detected_activity"))

    _section_title(left, "Kişi ve Email")
    _kv(left, "Kişi", lead.get("contact_name"))
    _kv(left, "Unvan", lead.get("contact_title"))
    _kv(left, "Email", lead.get("contact_email"))
    _kv(left, "Email Durumu", lead.get("email_status"))

    _section_title(left, "AI Aksiyonları")
    _kv(left, "Son Aksiyon", lead.get("last_action"))
    _kv(left, "AI Durumu", lead.get("ai_status"))
    _kv(left, "Onay Durumu", lead.get("approval_status"))

    _section_title(right, "Segmentasyon")
    _kv(right, "Satış Kanalı", lead.get("sales_channel"))
    _kv(right, "Ürün / Hizmet", lead.get("product_category"))
    _kv(right, "Segment", lead.get("segment_name"))
    _kv(right, "Öncelik", lead.get("priority"))
    _kv(right, "AI Skor", lead.get("ai_score"))
    _kv(right, "Sekans", lead.get("suggested_sequence"))

    _section_title(right, "AI Gerekçesi")
    reason = ctk.CTkTextbox(right, height=120, fg_color="#fafafa", text_color="#212121")
    reason.pack(fill="x", padx=18, pady=(4, 12))
    reason.insert("1.0", lead.get("short_reasoning") or "Henüz AI gerekçesi yok.")
    reason.configure(state="disabled")

    _section_title(right, "Kişiselleştirme Açısı")
    angle = ctk.CTkTextbox(right, height=110, fg_color="#fafafa", text_color="#212121")
    angle.pack(fill="x", padx=18, pady=(4, 12))
    angle.insert("1.0", lead.get("personalization_angle") or "Henüz kişiselleştirme açısı yok.")
    angle.configure(state="disabled")

    actions = ctk.CTkFrame(root, fg_color="transparent")
    actions.grid(row=2, column=0, columnspan=2, sticky="e", pady=(16, 0))

    def mark_review():
        lead["approval_status"] = "Review Needed"
        lead["last_action"] = "Kullanıcı review'a aldı"
        if on_update:
            on_update()
        messagebox.showinfo("Lead Otomasyonu", "Lead review durumuna alındı.", parent=win)

    def approve():
        lead["approval_status"] = "Approved"
        lead["last_action"] = "Kullanıcı segment ve taslağı onayladı"
        if on_update:
            on_update()
        messagebox.showinfo("Lead Otomasyonu", "Lead onaylandı.", parent=win)

    def exclude():
        lead["priority"] = "Excluded"
        lead["ai_status"] = "Excluded"
        lead["approval_status"] = "Not Required"
        lead["last_action"] = "Kullanıcı hariç tuttu"
        if on_update:
            on_update()
        messagebox.showinfo("Lead Otomasyonu", "Lead hariç tutuldu.", parent=win)

    _action_button(actions, "Review'a Al", mark_review, "#b45309").pack(side="left", padx=(0, 8))
    _action_button(actions, "Exclude Et", exclude, "#dc2626").pack(side="left", padx=8)
    _action_button(actions, "Onayla", approve, "#15803d").pack(side="left", padx=8)
    _action_button(actions, "Kapat", win.destroy, "#475569").pack(side="left", padx=(8, 0))


def _panel(parent):
    panel = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    return panel


def _section_title(parent, text):
    ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(family="Inter", size=17, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w", padx=18, pady=(18, 8))


def _kv(parent, label, value):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row, text=f"{label}:", width=120, anchor="w", text_color="#64748b").pack(side="left")
    ctk.CTkLabel(
        row,
        text=str(value if value not in (None, "") else "-"),
        anchor="w",
        text_color="#111827",
        wraplength=340,
        justify="left",
    ).pack(side="left", fill="x", expand=True)


def _action_button(parent, text, command, color):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=color,
        hover_color=color,
        text_color="white",
        height=38,
        corner_radius=10,
    )
