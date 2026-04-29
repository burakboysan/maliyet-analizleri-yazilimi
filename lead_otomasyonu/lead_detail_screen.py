import threading
from tkinter import messagebox
from urllib.parse import quote
import webbrowser

import customtkinter as ctk

from core.api_client import ApiClientError, deep_research_ai_lead, generate_ai_email_sequence, get_ai_lead_detail, update_ai_lead_segment, update_ai_lead_status
from core.session import get_app_token
from lead_otomasyonu.strategy_constants import PRODUCT_CATEGORIES, PRIORITY_OPTIONS, SALES_CHANNELS, STATUS_OPTIONS, priority_for_segment


def lead_detay_ekrani(parent, lead, on_update=None):
    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title(f"Lead Detay - {lead.get('company_name', '')}")
    win.geometry("1120x780")
    win.minsize(940, 680)
    win.configure(fg_color="#f5f5f5")

    try:
        win.lift()
        win.focus_force()
        win.attributes("-topmost", True)
        win.after(300, lambda: win.attributes("-topmost", False))
    except Exception:
        pass

    state = {"detail": dict(lead), "drafts": []}
    company_name_var = ctk.StringVar(value=lead.get("company_name") or "Lead Detay")
    status_var = ctk.StringVar(value=lead.get("ai_status") or lead.get("status") or "New")
    status_note_var = ctk.StringVar()
    country_var = ctk.StringVar(value=lead.get("country") or "")
    website_var = ctk.StringVar(value=lead.get("website") or "")
    segment_sales_channel_var = ctk.StringVar(value=lead.get("sales_channel") or SALES_CHANNELS[0])
    segment_product_var = ctk.StringVar(value=lead.get("product_category") or PRODUCT_CATEGORIES[0])
    segment_priority_var = ctk.StringVar(
        value=lead.get("priority") or priority_for_segment(lead.get("product_category"), lead.get("sales_channel"))
    )
    info_vars = {}
    textboxes = {}

    root = ctk.CTkFrame(win, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=18, pady=18)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    header = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    header.grid_columnconfigure(0, weight=1)
    _selectable_header_entry(header, company_name_var).grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 2))
    ctk.CTkLabel(
        header,
        text="Lead bilgileri, araştırma sonucu, email uygunluğu ve operasyonel durum tek ekrandan yönetilir.",
        text_color="#64748b",
    ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

    status_bar = ctk.CTkFrame(header, fg_color="transparent")
    status_bar.grid(row=0, column=1, rowspan=2, sticky="e", padx=18, pady=14)
    ctk.CTkLabel(status_bar, text="Durum", text_color="#475569").grid(row=0, column=0, sticky="w", padx=(0, 8))
    ctk.CTkComboBox(status_bar, values=STATUS_OPTIONS, variable=status_var, width=190).grid(row=1, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkEntry(status_bar, textvariable=status_note_var, width=260, placeholder_text="Durum notu").grid(row=1, column=1, sticky="ew", padx=8)

    tabs = ctk.CTkTabview(root, fg_color="#ffffff")
    tabs.grid(row=1, column=0, sticky="nsew")
    for tab_name in ["Firma Bilgileri", "Kişiler", "Segmentasyon", "Kişiselleştirme", "Bilgi"]:
        tabs.add(tab_name)

    company_tab = _tab_content(tabs.tab("Firma Bilgileri"))
    people_tab = _tab_content(tabs.tab("Kişiler"))
    segmentation_tab = _tab_content(tabs.tab("Segmentasyon"))
    personalization_tab = _tab_content(tabs.tab("Kişiselleştirme"))
    info_tab = _tab_content(tabs.tab("Bilgi"))

    company_panel = _panel(company_tab)
    company_panel.pack(fill="x", pady=(0, 12))
    _section_title(company_panel, "Firma Bilgileri")
    for key, label in [
        ("company_name", "Firma"),
        ("source", "Kaynak"),
    ]:
        info_vars[key] = _kv_var(company_panel, label)
    _editable_kv_var(company_panel, "Ülke", country_var, "Lead ülkesini manuel düzeltebilirsiniz.")
    _editable_action_kv_var(company_panel, "Web", website_var, lambda: open_website(), "Lead web sitesini manuel düzeltebilirsiniz.", "Aç")
    info_vars["detected_activity"] = _kv_var(company_panel, "Aktivite")

    research_panel = _panel(company_tab)
    research_panel.pack(fill="x", pady=(0, 12))
    _section_title(research_panel, "Firma Araştırması")
    research_cards_frame = ctk.CTkFrame(research_panel, fg_color="transparent")
    research_cards_frame.pack(fill="x", padx=18, pady=(4, 14))

    email_panel = _panel(people_tab)
    email_panel.pack(fill="x", pady=(0, 12))
    _section_title(email_panel, "Kişi ve Email")
    for key, label in [
        ("contact_name", "Kişi"),
        ("contact_title", "Unvan"),
    ]:
        info_vars[key] = _kv_var(email_panel, label)
    info_vars["contact_email"] = _clickable_kv_var(email_panel, "Email", lambda: compose_email(), button_text="Mail")
    info_vars["email_status"] = _kv_var(email_panel, "Email Durumu")
    textboxes["email_explanation"] = _readonly_box(email_panel, height=130)

    contacts_panel = _panel(people_tab)
    contacts_panel.pack(fill="x", pady=(0, 12))
    _section_title(contacts_panel, "Lead İçindeki Kişiler")
    contacts_cards_frame = ctk.CTkFrame(contacts_panel, fg_color="transparent")
    contacts_cards_frame.pack(fill="x", padx=18, pady=(4, 14))

    status_panel = _panel(company_tab)
    status_panel.pack(fill="x", pady=(0, 12))
    _section_title(status_panel, "Operasyon Durumu")
    for key, label in [
        ("last_action", "Son Aksiyon"),
        ("ai_status", "Lead Durumu"),
        ("approval_status", "Onay / Hazırlık"),
        ("sequence_eligibility", "Sekans Uygunluğu"),
    ]:
        info_vars[key] = _kv_var(status_panel, label)

    segmentation_panel = _panel(segmentation_tab)
    segmentation_panel.pack(fill="x", pady=(0, 12))
    _section_title(segmentation_panel, "Segmentasyon")
    for key, label in [
        ("sales_channel", "Satış Kanalı"),
        ("product_category", "Ürün / Hizmet"),
        ("segment_name", "Segment"),
        ("priority", "Öncelik"),
        ("suggested_sequence", "Sekans"),
    ]:
        info_vars[key] = _kv_var(segmentation_panel, label)
    segment_editor = ctk.CTkFrame(segmentation_panel, fg_color="#f8fafc", corner_radius=8)
    segment_editor.pack(fill="x", padx=18, pady=(10, 8))
    ctk.CTkLabel(segment_editor, text="Manuel Etiket", text_color="#334155", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))
    ctk.CTkLabel(segment_editor, text="Satış Kanalı", text_color="#64748b").grid(row=1, column=0, sticky="w", padx=12, pady=6)
    ctk.CTkComboBox(segment_editor, values=SALES_CHANNELS, variable=segment_sales_channel_var, width=240).grid(row=1, column=1, sticky="ew", padx=12, pady=6)
    ctk.CTkLabel(segment_editor, text="Ürün / Hizmet", text_color="#64748b").grid(row=2, column=0, sticky="w", padx=12, pady=6)
    ctk.CTkComboBox(segment_editor, values=PRODUCT_CATEGORIES, variable=segment_product_var, width=240).grid(row=2, column=1, sticky="ew", padx=12, pady=6)
    ctk.CTkLabel(segment_editor, text="Öncelik", text_color="#64748b").grid(row=3, column=0, sticky="w", padx=12, pady=6)
    ctk.CTkComboBox(segment_editor, values=PRIORITY_OPTIONS, variable=segment_priority_var, width=240).grid(row=3, column=1, sticky="ew", padx=12, pady=(6, 12))
    segment_editor.grid_columnconfigure(1, weight=1)
    textboxes["segmentation_source"] = _readonly_box(segmentation_panel, height=120)

    apollo_source_panel = _panel(info_tab)
    apollo_source_panel.pack(fill="x", pady=(0, 12))
    _section_title(apollo_source_panel, "Arama Kaynağı")
    textboxes["apollo_source"] = _readonly_box(apollo_source_panel, height=170)

    personalization_panel = _panel(personalization_tab)
    personalization_panel.pack(fill="x", pady=(0, 12))
    _section_title(personalization_panel, "Kişiselleştirme Açısı")
    textboxes["personalization"] = _readonly_box(personalization_panel, height=150)

    drafts_panel = _panel(personalization_tab)
    drafts_panel.pack(fill="x", pady=(0, 12))
    _section_title(drafts_panel, "Email Sekansı")
    textboxes["drafts"] = _readonly_box(drafts_panel, height=250)

    actions = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    actions.grid_columnconfigure(0, weight=1)
    action_buttons = ctk.CTkFrame(actions, fg_color="transparent")
    action_buttons.pack(fill="x")
    progress_frame = ctk.CTkFrame(actions, fg_color="transparent")
    progress_frame.pack(fill="x", padx=12, pady=(0, 10))
    research_progress = ctk.CTkProgressBar(progress_frame, mode="indeterminate")
    research_progress.pack(fill="x", padx=4, pady=(2, 4))
    research_progress.set(0)
    research_status_var = ctk.StringVar(value="")
    research_status_label = ctk.CTkLabel(progress_frame, textvariable=research_status_var, text_color="#64748b")
    research_status_label.pack(anchor="w", padx=4)
    progress_frame.pack_forget()
    research_state = {"running": False, "message_index": 0}
    research_messages = [
        "AI araştırıyor, web sitesi kapıları çalınıyor...",
        "About us ve ürün sayfaları koklanıyor...",
        "Firma adı ve faaliyet sinyalleri ayıklanıyor...",
        "OpenAI notları toparlıyor, birazdan dökülecek...",
    ]

    def detail():
        return state["detail"]

    def open_website():
        website = str(website_var.get() or detail().get("website") or "").strip()
        if not website or website == "-":
            return
        if not website.lower().startswith(("http://", "https://")):
            website = f"https://{website}"
        webbrowser.open(website)

    def compose_email():
        email = str(detail().get("contact_email") or "").strip()
        if not email or email == "-":
            return
        webbrowser.open(f"mailto:{quote(email)}")

    def update_textbox(key, value):
        box = textboxes[key]
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", str(value or "-"))
        box.configure(state="disabled")

    def current_research():
        items = detail().get("research") or []
        return items[0] if items else None

    def sequence_eligibility_text():
        email = detail().get("contact_email")
        status = str(detail().get("email_status") or "").casefold()
        if not email:
            return "Uygun değil: email yok. Önce Email Enrich veya manuel email girişi gerekli."
        if status in {"verified", "user managed"}:
            return "Uygun: email verified veya kullanıcı tarafından doğrulanmış."
        if status == "extrapolated":
            return "Uygun değil: Apollo bu emaili tahmini/çıkarımsal verdi. Verified olmadığı için sekans engelleniyor."
        return f"Uygun değil: email durumu '{detail().get('email_status') or 'boş'}'."

    def email_explanation_text():
        status = str(detail().get("email_status") or "").strip()
        note = detail().get("enrichment_note") or ""
        explanations = {
            "verified": "Apollo bu email adresini doğrulanmış olarak döndürdü. Sekans oluşturmak için uygundur.",
            "user managed": "Email kullanıcı tarafından girildi veya yönetiliyor. Sekans oluşturmak için uygundur.",
            "extrapolated": "Apollo bu email adresini doğrulanmış veri olarak değil, isim/domain patterninden tahmini olarak üretmiş olabilir. Bu yüzden otomatik sekans başlatmıyoruz.",
            "guessed": "Email tahmini olabilir. Doğrulanmadan otomatik sekans için uygun kabul edilmez.",
            "unverified": "Email var ama doğrulanmamış. Bounce riski nedeniyle sekans engellenir.",
            "unavailable": "Apollo bu kişi için email döndürmedi.",
            "missing": "Bu lead için email bilgisi yok.",
        }
        explanation = explanations.get(status.casefold(), "Email durumu Apollo'dan geldiği şekliyle gösteriliyor; verified değilse otomatik sekans için uygun kabul edilmez.")
        return f"Status: {status or '-'}\n\n{explanation}\n\nEnrichment notu:\n{note or '-'}"

    def contacts_text():
        contacts = detail().get("contacts") or []
        if not contacts:
            return "Bu lead altında kayıtlı kişi yok. SerpAPI firma/domain bulur; Apollo Email Enrich çalışınca karar vericiler bu alana eklenir."
        lines = []
        for index, contact in enumerate(contacts, start=1):
            name = " ".join(
                part
                for part in [
                    str(contact.get("first_name") or "").strip(),
                    str(contact.get("last_name") or "").strip(),
                ]
                if part
            ) or str(contact.get("name") or "").strip() or "-"
            lines.append(f"{index}. {name}")
            lines.append(f"   Ünvan: {contact.get('title') or '-'}")
            lines.append(f"   Email: {contact.get('email') or '-'}")
            lines.append(f"   Email Durumu: {contact.get('email_status') or '-'}")
            if contact.get("linkedin_url"):
                lines.append(f"   LinkedIn: {contact.get('linkedin_url')}")
            lines.append("")
        return "\n".join(lines).strip()

    def render_contact_cards():
        for child in contacts_cards_frame.winfo_children():
            child.destroy()

        contacts = detail().get("contacts") or []
        if not contacts:
            empty = ctk.CTkFrame(contacts_cards_frame, fg_color="#f8fafc", corner_radius=10)
            empty.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                empty,
                text="Bu lead altında kayıtlı kişi yok. Apollo Email Enrich çalışınca karar vericiler burada kart olarak görünür.",
                text_color="#64748b",
                wraplength=760,
                justify="left",
            ).pack(anchor="w", padx=14, pady=14)
            return

        for index, contact in enumerate(contacts, start=1):
            name = " ".join(
                part
                for part in [
                    str(contact.get("first_name") or "").strip(),
                    str(contact.get("last_name") or "").strip(),
                ]
                if part
            ) or str(contact.get("name") or "").strip() or f"Kişi {index}"
            card = ctk.CTkFrame(contacts_cards_frame, fg_color="#f8fafc", corner_radius=10)
            card.pack(fill="x", pady=(0, 10))
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                card,
                text=name,
                font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
                text_color="#111827",
            ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))
            _contact_card_row(card, 1, "Ünvan", contact.get("title"))
            _contact_card_row(card, 2, "Email", contact.get("email"))
            _contact_card_row(card, 3, "Email Durumu", contact.get("email_status"))
            if contact.get("linkedin_url"):
                _contact_card_row(card, 4, "LinkedIn", contact.get("linkedin_url"))

    def segmentation_source_text():
        reason = detail().get("short_reasoning") or ""
        if reason.startswith("Segment Search recipe matched"):
            return (
                "Bu bölüm LLM analizi değildir.\n\n"
                "Segment, 'Segmentten Lead Bul' ekranında seçilen Apollo Search Recipe üzerinden atanmış. "
                "Yani lead bu reçeteyle bulunduğu için satış kanalı/ürün/öncelik otomatik olarak reçeteden geldi.\n\n"
                f"Sistem notu: {reason}"
            )
        if reason:
            return f"Segmentasyon gerekçesi:\n{reason}"
        return "Henüz segmentasyon gerekçesi yok."

    def apollo_source_text():
        if not any(
            detail().get(key)
            for key in [
                "apollo_search_recipe",
                "apollo_search_attempt",
                "apollo_search_keyword",
                "apollo_search_run_id",
                "apollo_fit_filter_status",
            ]
        ):
            return "Bu lead eski kayıt olabilir veya manuel eklenmiş olabilir; arama kaynağı metadata'sı yok."
        lines = [
            f"Run ID: {detail().get('apollo_search_run_id') or '-'}",
            f"Reçete: {detail().get('apollo_search_recipe') or '-'}",
            f"Arama denemesi: {detail().get('apollo_search_attempt') or '-'}",
            f"Keyword: {detail().get('apollo_search_keyword') or '-'}",
            f"Ülke parametresi: {detail().get('apollo_search_country') or '-'}",
            "",
            f"Fit filtre durumu: {detail().get('apollo_fit_filter_status') or '-'}",
            f"Fit filtre notu: {detail().get('apollo_fit_filter_reason') or '-'}",
        ]
        return "\n".join(lines)

    def personalization_text():
        research = current_research() or {}
        lines = []
        if detail().get("personalization_angle"):
            lines.append("Segmentasyon açısı:")
            lines.append(str(detail().get("personalization_angle")))
        if research.get("personalization_angle"):
            lines.append("")
            lines.append("Firma araştırmasından gelen açı:")
            lines.append(str(research.get("personalization_angle")))
        if research.get("detected_signals"):
            lines.append("")
            lines.append(f"Kullanılabilecek sinyaller: {research.get('detected_signals')}")
        if not lines:
            lines.append("Henüz yeterli kişiselleştirme verisi yok. AI Araştır çalıştırıldığında bu bölüm zenginleşir.")
        return "\n".join(lines)

    def research_text():
        research = current_research()
        if not research:
            return "Henüz firma araştırması yapılmadı. AI Araştır butonu web sitesini ve lead bağlamını analiz eder."
        model = str(research.get("model_used") or "")
        method = "OpenAI / LLM destekli analiz" if model and model != "rule_based_research" else "Kural bazlı web sinyal analizi"
        links = "\n".join(f"- {link}" for link in (research.get("source_links") or [])) or "-"
        return "\n".join(
            [
                f"Yöntem: {method}",
                f"Model: {model or '-'}",
                f"Güven: {research.get('confidence_score') or 0}",
                "",
                f"Firma: {research.get('company_overview') or '-'}",
                f"Ürün / Çözüm: {research.get('products_services') or '-'}",
                f"Partner Fit: {research.get('partner_fit_reason') or '-'}",
                f"Bomaksan Eşleşmesi: {research.get('bomaksan_match') or '-'}",
                f"Sinyaller: {research.get('detected_signals') or '-'}",
                f"Sektörler: {research.get('served_industries') or '-'}",
                f"Risk: {research.get('risk_notes') or '-'}",
                "",
                "Kaynaklar:",
                links,
            ]
        )

    def render_research_card():
        for child in research_cards_frame.winfo_children():
            child.destroy()

        research = current_research()
        if not research:
            empty = ctk.CTkFrame(research_cards_frame, fg_color="#f8fafc", corner_radius=10)
            empty.pack(fill="x")
            ctk.CTkLabel(
                empty,
                text="Henüz firma araştırması yapılmadı. AI Araştır butonu web sitesini ve lead bağlamını analiz eder.",
                text_color="#64748b",
                wraplength=820,
                justify="left",
            ).pack(anchor="w", padx=14, pady=14)
            return

        raw_summary = research.get("raw_summary") or {}
        model = str(research.get("model_used") or "")
        openai_status = raw_summary.get("openai_status")
        openai_error = raw_summary.get("openai_error")
        method = "OpenAI / LLM destekli analiz" if model and model != "rule_based_research" else "Kural bazlı web sinyal analizi"
        status_text = "Tamamlandı" if openai_status == "completed" else "Kural bazlı fallback kullanıldı"
        if openai_error:
            status_text = f"{status_text}. Sebep: {openai_error}"
        links = research.get("source_links") or []

        summary_card = ctk.CTkFrame(research_cards_frame, fg_color="#f8fafc", corner_radius=10)
        summary_card.pack(fill="x", pady=(0, 10))
        summary_card.grid_columnconfigure(1, weight=1)
        _research_row(summary_card, 0, "Yöntem", method)
        _research_row(summary_card, 1, "OpenAI Durumu", status_text)
        _research_row(summary_card, 2, "Model", model or "-")
        _research_row(summary_card, 3, "Güven", research.get("confidence_score") or 0)
        _research_row(summary_card, 4, "Genel Merkez Ülkesi", raw_summary.get("headquarters_country") or "-")
        _research_row(summary_card, 5, "AI Firma Adı", raw_summary.get("detected_company_name") or "-")
        _research_row(summary_card, 6, "Ülke Kanıtı", raw_summary.get("headquarters_country_evidence") or "-")

        detail_card = ctk.CTkFrame(research_cards_frame, fg_color="#f8fafc", corner_radius=10)
        detail_card.pack(fill="x", pady=(0, 10))
        detail_card.grid_columnconfigure(1, weight=1)
        _research_row(detail_card, 0, "Firma", research.get("company_overview"))
        _research_row(detail_card, 1, "Ürün / Çözüm", research.get("products_services"))
        _research_row(detail_card, 2, "Partner Fit", research.get("partner_fit_reason"))
        _research_row(detail_card, 3, "Bomaksan Eşleşmesi", research.get("bomaksan_match"))
        _research_row(detail_card, 4, "Sinyaller", research.get("detected_signals"))
        _research_row(detail_card, 5, "Sektörler", research.get("served_industries"))
        _research_row(detail_card, 6, "Risk", research.get("risk_notes"))

        source_card = ctk.CTkFrame(research_cards_frame, fg_color="#f8fafc", corner_radius=10)
        source_card.pack(fill="x")
        source_card.grid_columnconfigure(1, weight=1)
        _research_row(source_card, 0, "Kaynaklar", "\n".join(f"- {link}" for link in links) or "-")

    def render_drafts(drafts=None):
        if drafts is not None:
            state["drafts"] = drafts
        drafts = state["drafts"] or []
        if not drafts:
            update_textbox("drafts", "Henüz email sekansı oluşturulmadı.")
            return
        lines = []
        for draft in drafts:
            lines.append(f"Email {draft.get('step_number')} | {draft.get('status')} | {draft.get('language')}")
            lines.append(f"Konu: {draft.get('subject') or '-'}")
            lines.append(str(draft.get("body") or "-"))
            lines.append("")
        update_textbox("drafts", "\n".join(lines).strip())

    def render_all():
        company_name = detail().get("company_name") or "Lead Detay"
        company_name_var.set(str(company_name))
        win.title(f"Lead Detay - {company_name}")
        for key, var in info_vars.items():
            if key == "sequence_eligibility":
                var.set(sequence_eligibility_text())
            else:
                var.set(str(detail().get(key) if detail().get(key) not in (None, "") else "-"))
        country_var.set(str(detail().get("country") or ""))
        website_var.set(str(detail().get("website") or ""))
        status_var.set(detail().get("ai_status") or detail().get("status") or status_var.get())
        if detail().get("sales_channel") in SALES_CHANNELS:
            segment_sales_channel_var.set(detail().get("sales_channel"))
        if detail().get("product_category") in PRODUCT_CATEGORIES:
            segment_product_var.set(detail().get("product_category"))
        if detail().get("priority") in PRIORITY_OPTIONS:
            segment_priority_var.set(detail().get("priority"))
        update_textbox("email_explanation", email_explanation_text())
        render_contact_cards()
        update_textbox("segmentation_source", segmentation_source_text())
        update_textbox("apollo_source", apollo_source_text())
        update_textbox("personalization", personalization_text())
        render_research_card()
        render_drafts(detail().get("email_drafts") or state["drafts"])

    def refresh_detail(show_message=False):
        token = get_app_token()
        if not token:
            messagebox.showerror("Lead Otomasyonu", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        def worker():
            try:
                response = get_ai_lead_detail(token, lead.get("id"))
                state["detail"] = response
                lead.update(response)
                win.after(0, render_all)
                if show_message:
                    win.after(0, lambda: messagebox.showinfo("Lead Detay", "Detay bilgileri yenilendi.", parent=win))
                if on_update:
                    win.after(0, on_update)
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Lead Detay", f"Detay alınamadı: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def run_research():
        token = get_app_token()
        if not token:
            messagebox.showerror("AI Araştır", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return
        research_state["running"] = True
        research_state["message_index"] = 0
        progress_frame.pack(fill="x", padx=12, pady=(0, 10))
        research_progress.start()
        research_status_var.set(research_messages[0])
        research_button.configure(state="disabled", text="Araştırılıyor...")

        def tick_research_progress():
            if not research_state["running"]:
                return
            research_status_var.set(research_messages[research_state["message_index"] % len(research_messages)])
            research_state["message_index"] += 1
            win.after(1600, tick_research_progress)

        def finish_research_progress():
            research_state["running"] = False
            research_progress.stop()
            progress_frame.pack_forget()
            research_status_var.set("")
            research_button.configure(state="normal", text="AI Araştır")

        tick_research_progress()

        def worker():
            try:
                result = deep_research_ai_lead(token, lead.get("id"))
                research = result.get("research") or {}
                refreshed_lead = result.get("lead") or {}
                if refreshed_lead:
                    state["detail"].update(refreshed_lead)
                state["detail"]["research"] = [research]
                state["detail"]["research_status"] = research.get("status") or "Completed"
                state["detail"]["research_summary"] = research.get("company_overview") or ""
                state["detail"]["last_action"] = "AI firma araştırması tamamlandı."
                lead.update(state["detail"])
                win.after(0, finish_research_progress)
                win.after(0, render_all)
                if on_update:
                    win.after(0, on_update)
                win.after(0, lambda: messagebox.showinfo("AI Araştır", "Firma araştırması tamamlandı.", parent=win))
            except ApiClientError as exc:
                win.after(0, finish_research_progress)
                win.after(0, lambda err=str(exc): messagebox.showerror("AI Araştır", err, parent=win))
            except Exception as exc:
                win.after(0, finish_research_progress)
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
                state["detail"]["email_drafts"] = drafts
                state["detail"]["draft_count"] = len(drafts)
                state["detail"]["ai_status"] = "Draft Generated"
                state["detail"]["approval_status"] = "Awaiting Approval"
                state["detail"]["last_action"] = "3 adımlı email sekansı taslakları oluşturuldu."
                lead.update(state["detail"])
                win.after(0, render_all)
                if on_update:
                    win.after(0, on_update)
                win.after(0, lambda: messagebox.showinfo("Email Sekansı", f"{len(drafts)} email taslağı oluşturuldu. Gönderim yapılmadı.", parent=win))
            except ApiClientError as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Email Sekansı", err, parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Email Sekansı", f"Sekans oluşturulamadı: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def save_segment():
        token = get_app_token()
        if not token:
            messagebox.showerror("Segment", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        payload = current_segment_payload()

        def worker():
            try:
                update_ai_lead_segment(token, lead.get("id"), payload)
                response = get_ai_lead_detail(token, lead.get("id"))
                state["detail"] = response
                lead.update(response)
                win.after(0, render_all)
                if on_update:
                    win.after(0, on_update)
                win.after(0, lambda: messagebox.showinfo("Segment", "Ülke, ürün x satış kanalı ve öncelik kaydedildi.", parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Segment", f"Segment kaydedilemedi: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def current_segment_payload():
        sales_channel = segment_sales_channel_var.get().strip()
        product_category = segment_product_var.get().strip()
        return {
            "sales_channel": sales_channel,
            "product_category": product_category,
            "priority": segment_priority_var.get().strip() or priority_for_segment(product_category, sales_channel),
            "country": country_var.get().strip(),
        }

    def save_status():
        token = get_app_token()
        if not token:
            messagebox.showerror("Durum", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return
        payload = current_segment_payload()

        def worker():
            try:
                update_ai_lead_segment(token, lead.get("id"), payload)
                update_ai_lead_status(token, lead.get("id"), status_var.get(), status_note_var.get(), website_var.get())
                response = get_ai_lead_detail(token, lead.get("id"))
                state["detail"] = response
                lead.update(response)
                win.after(0, render_all)
                if on_update:
                    win.after(0, on_update)
                win.after(0, lambda: messagebox.showinfo("Durum", "Lead durumu, ülke ve öncelik kaydedildi.", parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Durum", f"Durum kaydedilemedi: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    _ghost_button(action_buttons, "Detayı Yenile", lambda: refresh_detail(show_message=True), "#2563eb").pack(side="left", padx=10, pady=12)
    research_button = _ghost_button(action_buttons, "AI Araştır", run_research, "#7c3aed")
    research_button.pack(side="left", padx=8, pady=12)
    _primary_button(action_buttons, "Sekans Oluştur", create_sequence, "#0f766e").pack(side="left", padx=8, pady=12)
    _ghost_button(action_buttons, "Segmenti Kaydet", save_segment, "#7c3aed").pack(side="left", padx=8, pady=12)
    _ghost_button(action_buttons, "Durumu Kaydet", save_status, "#334155").pack(side="right", padx=8, pady=12)
    _ghost_button(action_buttons, "Kapat", win.destroy, "#64748b").pack(side="right", padx=10, pady=12)

    render_all()
    refresh_detail(show_message=False)


def _panel(parent):
    return ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")


def _tab_content(parent):
    frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    return frame


def _section_title(parent, text):
    ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w", padx=18, pady=(16, 8))


def _selectable_header_entry(parent, variable):
    entry = ctk.CTkEntry(
        parent,
        textvariable=variable,
        font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
        text_color="#212121",
        fg_color="#ffffff",
        border_width=0,
        height=34,
    )
    entry.configure(state="readonly")
    _bind_select_all(entry)
    return entry


def _kv_var(parent, label):
    var = ctk.StringVar(value="-")
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row, text=f"{label}:", width=130, anchor="w", text_color="#64748b").pack(side="left")
    value_entry = ctk.CTkEntry(
        row,
        textvariable=var,
        text_color="#111827",
        fg_color="#ffffff",
        border_width=0,
        height=26,
    )
    value_entry.pack(side="left", fill="x", expand=True)
    value_entry.configure(state="readonly")
    _bind_select_all(value_entry)
    return var


def _editable_kv_var(parent, label, variable, placeholder_text=""):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row, text=f"{label}:", width=130, anchor="w", text_color="#64748b").pack(side="left")
    value_entry = ctk.CTkEntry(
        row,
        textvariable=variable,
        text_color="#111827",
        fg_color="#ffffff",
        border_color="#cbd5e1",
        height=32,
        placeholder_text=placeholder_text,
    )
    value_entry.pack(side="left", fill="x", expand=True)
    return variable


def _editable_action_kv_var(parent, label, variable, command, placeholder_text="", button_text="Aç"):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row, text=f"{label}:", width=130, anchor="w", text_color="#64748b").pack(side="left")
    value_entry = ctk.CTkEntry(
        row,
        textvariable=variable,
        text_color="#111827",
        fg_color="#ffffff",
        border_color="#cbd5e1",
        height=32,
        placeholder_text=placeholder_text,
    )
    value_entry.pack(side="left", fill="x", expand=True)
    _inline_action_button(row, button_text, command).pack(side="left", padx=(8, 0))
    return variable


def _clickable_kv_var(parent, label, command, button_text="Aç"):
    var = ctk.StringVar(value="-")
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(row, text=f"{label}:", width=130, anchor="w", text_color="#64748b").pack(side="left")
    value_entry = ctk.CTkEntry(
        row,
        textvariable=var,
        text_color="#2563eb",
        fg_color="#ffffff",
        border_width=0,
        height=26,
    )
    value_entry.pack(side="left", fill="x", expand=True)
    value_entry.configure(state="readonly")
    _bind_select_all(value_entry)
    _inline_action_button(row, button_text, command).pack(side="left", padx=(8, 0))
    return var


def _contact_card_row(parent, row_index, label, value):
    ctk.CTkLabel(parent, text=f"{label}:", width=110, anchor="w", text_color="#64748b").grid(
        row=row_index,
        column=0,
        sticky="nw",
        padx=(14, 8),
        pady=(2, 8),
    )
    entry = ctk.CTkEntry(
        parent,
        text_color="#111827",
        fg_color="#ffffff",
        border_width=0,
        height=28,
    )
    entry.grid(row=row_index, column=1, sticky="ew", padx=(0, 14), pady=(2, 8))
    entry.insert(0, str(value or "-"))
    entry.configure(state="readonly")
    _bind_select_all(entry)


def _research_row(parent, row_index, label, value):
    ctk.CTkLabel(
        parent,
        text=f"{label}:",
        width=150,
        anchor="nw",
        text_color="#334155",
        font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
    ).grid(row=row_index, column=0, sticky="nw", padx=(14, 10), pady=(8, 8))
    ctk.CTkLabel(
        parent,
        text=str(value if value not in (None, "") else "-"),
        anchor="nw",
        justify="left",
        wraplength=760,
        text_color="#111827",
    ).grid(row=row_index, column=1, sticky="ew", padx=(0, 14), pady=(8, 8))


def _bind_select_all(widget):
    def select_all(_event):
        widget.select_range(0, "end")
        widget.icursor("end")
        return "break"

    widget.bind("<Control-a>", select_all)
    widget.bind("<Control-A>", select_all)


def _inline_action_button(parent, text, command):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color="#ffffff",
        hover_color="#f8fafc",
        text_color="#2563eb",
        border_width=1,
        border_color="#2563eb",
        width=54,
        height=26,
        corner_radius=7,
    )


def _readonly_box(parent, height=120):
    box = ctk.CTkTextbox(parent, height=height, fg_color="#fafafa", text_color="#212121", wrap="word")
    box.pack(fill="x", padx=18, pady=(4, 14))
    box.configure(state="disabled")
    return box


def _primary_button(parent, text, command, color):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=color,
        hover_color=color,
        text_color="white",
        width=130,
        height=38,
        corner_radius=8,
    )


def _ghost_button(parent, text, command, color):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color="#ffffff",
        hover_color="#f8fafc",
        text_color=color,
        border_width=1,
        border_color=color,
        width=120,
        height=38,
        corner_radius=8,
    )
