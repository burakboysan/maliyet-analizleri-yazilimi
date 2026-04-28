import threading
from tkinter import messagebox

import customtkinter as ctk

from core.api_client import ApiClientError, approve_ai_email_draft, deep_research_ai_lead, generate_ai_email_sequence, get_ai_lead_detail
from core.session import get_app_token


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
    state = {"detail": dict(lead), "drafts": []}

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
    _kv(left, "Enrichment Notu", lead.get("enrichment_note"))

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

    _section_title(right, "Firma Araştırması")
    research_box = ctk.CTkTextbox(right, height=180, fg_color="#fafafa", text_color="#212121")
    research_box.pack(fill="x", padx=18, pady=(4, 12))

    _section_title(right, "Email Sekansı")
    drafts_box = ctk.CTkTextbox(right, height=150, fg_color="#fafafa", text_color="#212121")
    drafts_box.pack(fill="both", expand=True, padx=18, pady=(4, 12))

    def render_research(research=None):
        if research is None:
            research_items = state["detail"].get("research") or []
            research = research_items[0] if research_items else None
        research_box.configure(state="normal")
        research_box.delete("1.0", "end")
        if not research:
            research_box.insert("1.0", "Henüz firma araştırması yapılmadı.")
        else:
            lines = [
                f"Durum: {research.get('status') or '-'}",
                "",
                f"Firma: {research.get('company_overview') or '-'}",
                f"Ürün / Çözüm: {research.get('products_services') or '-'}",
                f"Partner Fit: {research.get('partner_fit_reason') or '-'}",
                f"Bomaksan Eşleşmesi: {research.get('bomaksan_match') or '-'}",
                f"Sinyaller: {research.get('detected_signals') or '-'}",
                f"Sektörler: {research.get('served_industries') or '-'}",
                f"Email Açısı: {research.get('personalization_angle') or '-'}",
                f"Risk: {research.get('risk_notes') or '-'}",
                "",
                "Kaynaklar:",
            ]
            lines.extend(f"- {link}" for link in (research.get("source_links") or []))
            research_box.insert("1.0", "\n".join(lines).strip())
        research_box.configure(state="disabled")

    def render_drafts(drafts=None):
        if drafts is not None:
            state["drafts"] = drafts
        drafts_box.configure(state="normal")
        drafts_box.delete("1.0", "end")
        if not state["drafts"]:
            drafts_box.insert("1.0", "Henüz email sekansı oluşturulmadı.")
        else:
            lines = []
            for draft in state["drafts"]:
                lines.append(f"Email {draft.get('step_number')} | {draft.get('status')} | {draft.get('language')}")
                lines.append(f"Konu: {draft.get('subject') or '-'}")
                lines.append(str(draft.get("body") or "-"))
                lines.append("")
            drafts_box.insert("1.0", "\n".join(lines).strip())
        drafts_box.configure(state="disabled")

    render_drafts()
    render_research()

    actions = ctk.CTkFrame(root, fg_color="transparent")
    actions.grid(row=2, column=0, columnspan=2, sticky="e", pady=(16, 0))

    def refresh_detail(show_message=False):
        token = get_app_token()
        if not token:
            messagebox.showerror("Lead Otomasyonu", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        def worker():
            try:
                detail = get_ai_lead_detail(token, lead.get("id"))
                state["detail"] = detail
                lead.update(detail)
                win.after(0, lambda: render_drafts(detail.get("email_drafts") or []))
                win.after(0, lambda: render_research())
                if show_message:
                    win.after(0, lambda: messagebox.showinfo("Email Sekansı", "Taslaklar güncellendi.", parent=win))
                if on_update:
                    win.after(0, on_update)
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Email Sekansı", f"Taslaklar alınamadı: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def run_research():
        token = get_app_token()
        if not token:
            messagebox.showerror("AI Araştır", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        def worker():
            try:
                result = deep_research_ai_lead(token, lead.get("id"))
                research = result.get("research") or {}
                lead["research_status"] = research.get("status") or "Completed"
                lead["research_summary"] = research.get("company_overview") or ""
                lead["last_action"] = "AI firma araştırması tamamlandı."
                state["detail"]["research"] = [research]
                win.after(0, lambda: render_research(research))
                if on_update:
                    win.after(0, on_update)
                win.after(0, lambda: messagebox.showinfo("AI Araştır", "Firma araştırması tamamlandı.", parent=win))
            except ApiClientError as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("AI Araştır", err, parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("AI Araştır", f"Araştırma tamamlanamadı: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def create_sequence():
        token = get_app_token()
        if not token:
            messagebox.showerror("Email Sekansı", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        def worker():
            try:
                result = generate_ai_email_sequence(token, lead.get("id"))
                drafts = result.get("drafts") or []
                lead["draft_count"] = len(drafts)
                lead["ai_status"] = "Draft Generated"
                lead["approval_status"] = "Awaiting Approval"
                lead["last_action"] = "3 adımlı email sekansı taslakları oluşturuldu."
                win.after(0, lambda: render_drafts(drafts))
                if on_update:
                    win.after(0, on_update)
                win.after(0, lambda: messagebox.showinfo("Email Sekansı", f"{len(drafts)} email taslağı oluşturuldu. Gönderim yapılmadı; onay bekliyor.", parent=win))
            except ApiClientError as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Email Sekansı", err, parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Email Sekansı", f"Sekans oluşturulamadı: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def approve_drafts():
        token = get_app_token()
        drafts = state.get("drafts") or []
        if not token:
            messagebox.showerror("Email Sekansı", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return
        if not drafts:
            messagebox.showwarning("Email Sekansı", "Onaylanacak email taslağı yok.", parent=win)
            return

        def worker():
            try:
                approved = 0
                for draft in drafts:
                    if draft.get("status") != "Approved":
                        approve_ai_email_draft(token, draft.get("id"))
                        approved += 1
                lead["approval_status"] = "Approved"
                lead["ai_status"] = "Approved"
                lead["last_action"] = f"{approved} email taslağı onaylandı."
                win.after(0, lambda: refresh_detail(show_message=False))
                win.after(0, lambda: messagebox.showinfo("Email Sekansı", f"{approved} email taslağı onaylandı.", parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Email Sekansı", f"Onay başarısız: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

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

    _action_button(actions, "Sekans Oluştur", create_sequence, "#0f766e").pack(side="left", padx=(0, 8))
    _action_button(actions, "AI Araştır", run_research, "#7c3aed").pack(side="left", padx=8)
    _action_button(actions, "Taslakları Yenile", lambda: refresh_detail(show_message=True), "#2563eb").pack(side="left", padx=8)
    _action_button(actions, "Taslakları Onayla", approve_drafts, "#15803d").pack(side="left", padx=8)
    _action_button(actions, "Review'a Al", mark_review, "#b45309").pack(side="left", padx=8)
    _action_button(actions, "Exclude Et", exclude, "#dc2626").pack(side="left", padx=8)
    _action_button(actions, "Onayla", approve, "#16a34a").pack(side="left", padx=8)
    _action_button(actions, "Kapat", win.destroy, "#475569").pack(side="left", padx=(8, 0))
    refresh_detail(show_message=False)


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
