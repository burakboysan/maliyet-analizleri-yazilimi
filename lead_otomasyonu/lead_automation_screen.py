import csv
import threading
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.api_client import ApiClientError, enrich_ai_lead_from_apollo, generate_ai_email_sequence, list_ai_leads, search_apollo_ai_leads, search_apollo_segment_leads
from core.session import get_app_token
from core.utils import apply_bomaksan_table_style, apply_zebra_striping
from lead_otomasyonu.lead_detail_screen import lead_detay_ekrani
from lead_otomasyonu.strategy_constants import (
    MOCK_LEADS,
    HIGH_PRIORITY_SEGMENT_NAMES,
    PRIORITY_OPTIONS,
    PRODUCT_CATEGORIES,
    SALES_CHANNELS,
    TARGET_COUNTRIES,
    build_segment_name,
    get_sequence_code,
    priority_for_segment,
)


def lead_otomasyonu_ekrani(parent=None, kullanici_rolu=None):
    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title("Lead Otomasyonu")
    win.geometry("1440x860")
    win.minsize(1120, 720)
    win.configure(fg_color="#f5f5f5")

    try:
        win.state("zoomed")
        win.lift()
        win.focus_force()
        win.attributes("-topmost", True)
        win.after(350, lambda: win.attributes("-topmost", False))
    except Exception:
        pass

    state = {
        "leads": [dict(item) for item in MOCK_LEADS],
        "filtered": [],
        "api_mode": False,
    }

    root = ctk.CTkFrame(win, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=20, pady=20)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(3, weight=1)

    header = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=16, border_width=1, border_color="#e5e7eb")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
    header.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        header,
        text="Lead Otomasyonu",
        font=ctk.CTkFont(family="Inter", size=28, weight="bold"),
        text_color="#212121",
    ).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 4))
    status_var = ctk.StringVar(value="MVP iskeleti mock veriyle hazır. API bağlandığında aynı ekran canlı veriyi kullanacak.")
    ctk.CTkLabel(
        header,
        textvariable=status_var,
        font=ctk.CTkFont(size=13),
        text_color="#64748b",
    ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 18))

    actions = ctk.CTkFrame(header, fg_color="transparent")
    actions.grid(row=0, column=1, rowspan=2, sticky="e", padx=22, pady=18)

    summary = ctk.CTkFrame(root, fg_color="transparent")
    summary.grid(row=1, column=0, sticky="ew", pady=(0, 14))
    summary.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
    metric_vars = {
        "total": ctk.StringVar(value="0"),
        "pending": ctk.StringVar(value="0"),
        "high": ctk.StringVar(value="0"),
        "excluded": ctk.StringVar(value="0"),
        "drafts": ctk.StringVar(value="0"),
        "approval": ctk.StringVar(value="0"),
    }
    metric_defs = [
        ("Toplam Lead", "total", "#2563eb"),
        ("AI Bekleyen", "pending", "#7c3aed"),
        ("High / Very High", "high", "#15803d"),
        ("Excluded", "excluded", "#dc2626"),
        ("Taslak", "drafts", "#b45309"),
        ("Onay Bekleyen", "approval", "#0f766e"),
    ]
    for index, (title, key, color) in enumerate(metric_defs):
        _metric_card(summary, index, title, metric_vars[key], color)

    filters = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    filters.grid(row=2, column=0, sticky="ew", pady=(0, 14))
    filters.grid_columnconfigure(7, weight=1)

    search_var = ctk.StringVar()
    channel_var = ctk.StringVar(value="Tüm Kanallar")
    product_var = ctk.StringVar(value="Tüm Ürünler")
    priority_var = ctk.StringVar(value="Tüm Öncelikler")

    _filter_label(filters, "Arama", 0)
    search_entry = ctk.CTkEntry(filters, textvariable=search_var, width=220, placeholder_text="Firma, ülke veya segment")
    search_entry.grid(row=1, column=0, padx=(16, 8), pady=(0, 14), sticky="ew")

    _filter_label(filters, "Satış Kanalı", 1)
    channel_combo = ctk.CTkComboBox(filters, values=["Tüm Kanallar"] + SALES_CHANNELS, variable=channel_var, width=220)
    channel_combo.grid(row=1, column=1, padx=8, pady=(0, 14), sticky="ew")

    _filter_label(filters, "Ürün / Hizmet", 2)
    product_combo = ctk.CTkComboBox(filters, values=["Tüm Ürünler"] + PRODUCT_CATEGORIES, variable=product_var, width=200)
    product_combo.grid(row=1, column=2, padx=8, pady=(0, 14), sticky="ew")

    _filter_label(filters, "Öncelik", 3)
    priority_combo = ctk.CTkComboBox(filters, values=["Tüm Öncelikler"] + PRIORITY_OPTIONS, variable=priority_var, width=170)
    priority_combo.grid(row=1, column=3, padx=8, pady=(0, 14), sticky="ew")

    table_card = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    table_card.grid(row=3, column=0, sticky="nsew")
    table_card.grid_rowconfigure(0, weight=1)
    table_card.grid_columnconfigure(0, weight=1)

    table_wrap = ctk.CTkFrame(table_card, fg_color="transparent")
    table_wrap.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    table_wrap.grid_rowconfigure(0, weight=1)
    table_wrap.grid_columnconfigure(0, weight=1)

    y_scroll = ttk.Scrollbar(table_wrap, orient="vertical")
    x_scroll = ttk.Scrollbar(table_wrap, orient="horizontal")
    columns = (
        "company_name",
        "contact_email",
        "email_status",
        "enrichment_note",
        "country",
        "local_language",
        "source",
        "sales_channel",
        "product_category",
        "priority",
        "ai_score",
        "suggested_sequence",
        "draft_count",
        "ai_status",
        "approval_status",
        "last_action",
    )
    tree = ttk.Treeview(
        table_wrap,
        columns=columns,
        show="headings",
        yscrollcommand=y_scroll.set,
        xscrollcommand=x_scroll.set,
        selectmode="browse",
    )
    y_scroll.config(command=tree.yview)
    x_scroll.config(command=tree.xview)
    apply_bomaksan_table_style(tree)

    headings = {
        "company_name": "Firma",
        "contact_email": "Email",
        "email_status": "Email Durumu",
        "enrichment_note": "Enrichment Notu",
        "country": "Ülke",
        "local_language": "Dil",
        "source": "Kaynak",
        "sales_channel": "Satış Kanalı",
        "product_category": "Ürün / Hizmet",
        "priority": "Öncelik",
        "ai_score": "AI Skor",
        "suggested_sequence": "Sekans",
        "draft_count": "Taslak",
        "ai_status": "AI Durumu",
        "approval_status": "Onay",
        "last_action": "Son Aksiyon",
    }
    widths = {
        "company_name": 230,
        "contact_email": 210,
        "email_status": 120,
        "enrichment_note": 320,
        "country": 120,
        "local_language": 110,
        "source": 90,
        "sales_channel": 230,
        "product_category": 160,
        "priority": 110,
        "ai_score": 80,
        "suggested_sequence": 110,
        "draft_count": 80,
        "ai_status": 150,
        "approval_status": 150,
        "last_action": 260,
    }
    for col in columns:
        tree.heading(col, text=headings[col])
        tree.column(col, width=widths[col], minwidth=70, anchor="w")

    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")

    def refresh_metrics():
        leads = state["leads"]
        metric_vars["total"].set(str(len(leads)))
        metric_vars["pending"].set(str(sum(1 for item in leads if item.get("ai_status") in {"New", "Pending AI Analysis"})))
        metric_vars["high"].set(str(sum(1 for item in leads if item.get("priority") in {"High", "Very High"})))
        metric_vars["excluded"].set(str(sum(1 for item in leads if item.get("priority") == "Excluded" or item.get("ai_status") == "Excluded")))
        metric_vars["drafts"].set(str(sum(1 for item in leads if item.get("ai_status") == "Draft Generated")))
        metric_vars["approval"].set(str(sum(1 for item in leads if item.get("approval_status") in {"Awaiting Approval", "Review Needed"})))

    def apply_filters(*_args):
        query = search_var.get().strip().casefold()
        channel = channel_var.get()
        product = product_var.get()
        priority = priority_var.get()
        filtered = []
        for item in state["leads"]:
            haystack = " ".join(str(item.get(key, "")) for key in ("company_name", "contact_email", "email_status", "enrichment_note", "country", "segment_name", "sales_channel", "product_category")).casefold()
            if query and query not in haystack:
                continue
            if channel != "Tüm Kanallar" and item.get("sales_channel") != channel:
                continue
            if product != "Tüm Ürünler" and item.get("product_category") != product:
                continue
            if priority != "Tüm Öncelikler" and item.get("priority") != priority:
                continue
            filtered.append(item)
        state["filtered"] = filtered
        render_table()

    def render_table():
        children = tree.get_children()
        if children:
            tree.delete(*children)
        for item in state["filtered"]:
            values = [item.get(col, "") for col in columns]
            tree.insert("", "end", iid=str(item.get("id")), values=values)
        apply_zebra_striping(tree, tree.get_children())
        refresh_metrics()

    def selected_lead():
        selection = tree.selection()
        if not selection:
            return None
        lead_id = str(selection[0])
        for item in state["leads"]:
            if str(item.get("id")) == lead_id:
                return item
        return None

    def open_detail(_event=None):
        lead = selected_lead()
        if not lead:
            messagebox.showwarning("Lead Otomasyonu", "Lütfen bir lead seçin.", parent=win)
            return
        lead_detay_ekrani(win, lead, on_update=apply_filters)

    def add_manual_lead():
        dialog = ctk.CTkToplevel(win)
        dialog.title("Manuel Lead Ekle")
        dialog.geometry("560x660")
        dialog.configure(fg_color="#f5f5f5")
        dialog.transient(win)
        dialog.grab_set()

        form = ctk.CTkFrame(dialog, fg_color="#ffffff", corner_radius=14)
        form.pack(fill="both", expand=True, padx=18, pady=18)
        vars_ = {
            "company_name": ctk.StringVar(),
            "contact_name": ctk.StringVar(),
            "contact_title": ctk.StringVar(),
            "contact_email": ctk.StringVar(),
            "country": ctk.StringVar(),
            "local_language": ctk.StringVar(value="English"),
            "sales_channel": ctk.StringVar(value="White Label / Resellers"),
            "product_category": ctk.StringVar(value="Dust Collection"),
            "detected_activity": ctk.StringVar(),
        }
        _form_entry(form, "Firma", vars_["company_name"], 0)
        _form_entry(form, "Kişi", vars_["contact_name"], 1)
        _form_entry(form, "Unvan", vars_["contact_title"], 2)
        _form_entry(form, "Email", vars_["contact_email"], 3)
        _form_entry(form, "Ülke", vars_["country"], 4)
        _form_entry(form, "Dil", vars_["local_language"], 5)
        _form_combo(form, "Satış Kanalı", vars_["sales_channel"], SALES_CHANNELS, 6)
        _form_combo(form, "Ürün / Hizmet", vars_["product_category"], PRODUCT_CATEGORIES, 7)
        _form_entry(form, "Aktivite", vars_["detected_activity"], 8)

        def save():
            company = vars_["company_name"].get().strip()
            if not company:
                messagebox.showwarning("Eksik Bilgi", "Firma adı zorunludur.", parent=dialog)
                return
            product = vars_["product_category"].get()
            channel = vars_["sales_channel"].get()
            priority = priority_for_segment(product, channel)
            lead = {
                "id": _next_id(state["leads"]),
                "company_name": company,
                "contact_name": vars_["contact_name"].get().strip(),
                "contact_title": vars_["contact_title"].get().strip(),
                "contact_email": vars_["contact_email"].get().strip(),
                "email_status": "user managed" if vars_["contact_email"].get().strip() else "missing",
                "country": vars_["country"].get().strip(),
                "local_language": vars_["local_language"].get().strip(),
                "source": "Manual",
                "sales_channel": channel,
                "product_category": product,
                "segment_name": build_segment_name(product, channel),
                "priority": priority,
                "ai_score": 65 if priority in {"High", "Very High"} else 45,
                "suggested_sequence": get_sequence_code(channel),
                "ai_status": "Segmented",
                "approval_status": "Awaiting Approval",
                "last_action": "Manuel lead eklendi ve segment önerildi",
                "website": "",
                "detected_activity": vars_["detected_activity"].get().strip(),
                "short_reasoning": "MVP kural setiyle otomatik segment önerisi oluşturuldu.",
                "personalization_angle": "Partner adayının faaliyet alanına göre kısa kişiselleştirme.",
            }
            state["leads"].append(lead)
            dialog.destroy()
            apply_filters()

        ctk.CTkButton(form, text="Kaydet", command=save, fg_color="#d32f2f", hover_color="#b91c1c").grid(row=9, column=1, sticky="e", padx=16, pady=18)

    def import_csv():
        path = filedialog.askopenfilename(
            parent=win,
            title="Apollo CSV Seç",
            filetypes=[("CSV Dosyası", "*.csv"), ("Tüm Dosyalar", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as file:
                rows = list(csv.DictReader(file))
            added = 0
            for row in rows:
                company = _first_value(row, ["company_name", "Company", "Company Name", "company", "Firma"])
                if not company:
                    continue
                country = _first_value(row, ["country", "Country", "Ülke"])
                email = _first_value(row, ["email", "Email", "Email Address", "person_email", "contact_email"])
                email_status = _first_value(row, ["email_status", "Email Status", "contact_email_status"]) or ("user managed" if email else "missing")
                first_name = _first_value(row, ["first_name", "First Name"])
                last_name = _first_value(row, ["last_name", "Last Name"])
                contact_name = _first_value(row, ["name", "Name", "Person Name"]) or " ".join(part for part in [first_name, last_name] if part)
                activity = _first_value(row, ["description", "Company Description", "industry", "Industry", "Açıklama"])
                partner_reason = _first_value(row, ["partner_fit_reason", "Partner Fit Reason"])
                value_proposition = _first_value(row, ["value_proposition", "Value Proposition"])
                recommended_campaign = _first_value(row, ["recommended_campaign", "Recommended Campaign"])
                segment_hint = _first_value(row, ["segment", "Segment"])
                combined_signal = " ".join(item for item in [activity, partner_reason, value_proposition, recommended_campaign, segment_hint] if item)
                channel = _channel_from_apollo_row(row, combined_signal)
                product = _product_from_apollo_row(row, combined_signal)
                priority = _priority_from_icp(row) or priority_for_segment(product, channel)
                score = _score_from_icp(row, priority)
                state["leads"].append(
                    {
                        "id": _next_id(state["leads"]),
                        "company_name": company,
                        "contact_name": contact_name,
                        "contact_title": _first_value(row, ["title", "Title", "Job Title"]),
                        "contact_email": email,
                        "email_status": email_status,
                        "country": country,
                        "local_language": _guess_language(country),
                        "source": "CSV",
                        "sales_channel": channel,
                        "product_category": product,
                        "segment_name": build_segment_name(product, channel),
                        "priority": priority,
                        "ai_score": score,
                        "suggested_sequence": _sequence_from_campaign(recommended_campaign, channel),
                        "ai_status": "Segmented",
                        "approval_status": "Awaiting Approval",
                        "last_action": "CSV import ile eklendi",
                        "website": _first_value(row, ["website", "Website"]),
                        "detected_activity": combined_signal or activity,
                        "short_reasoning": partner_reason or "Apollo import sonrası ICP ve segment sinyalleriyle öneri oluşturuldu.",
                        "personalization_angle": _first_value(row, ["personalized_opener", "Personalized Opener"]) or value_proposition or combined_signal,
                        "value_proposition": value_proposition,
                        "icp_tier": _first_value(row, ["icp_tier", "ICP Tier"]),
                        "recommended_campaign": recommended_campaign,
                    }
                )
                added += 1
            apply_filters()
            messagebox.showinfo("CSV Import", f"{added} lead eklendi.", parent=win)
        except Exception as exc:
            messagebox.showerror("CSV Import", f"CSV okunamadı: {exc}", parent=win)

    def load_from_api():
        token = get_app_token()
        if not token:
            status_var.set("API oturumu bulunamadı; mock veri gösteriliyor.")
            return

        def worker():
            try:
                leads = list_ai_leads(token)
                if leads:
                    state["leads"] = leads
                    state["api_mode"] = True
                    win.after(0, lambda: status_var.set("Canlı API verisi yüklendi."))
                    win.after(0, apply_filters)
            except ApiClientError as exc:
                message = f"API hazır değil veya erişilemiyor; mock veri kullanılıyor. Detay: {exc}"
                win.after(0, lambda msg=message: status_var.set(msg))
            except Exception as exc:
                message = f"Lead verisi yüklenemedi; mock veri kullanılıyor. Detay: {exc}"
                win.after(0, lambda msg=message: status_var.set(msg))

        threading.Thread(target=worker, daemon=True).start()

    def apollo_search():
        token = get_app_token()
        if not token:
            messagebox.showerror("Apollo", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        dialog = ctk.CTkToplevel(win)
        dialog.title("Apollo Search")
        dialog.geometry("560x460")
        dialog.configure(fg_color="#f5f5f5")
        dialog.transient(win)
        dialog.grab_set()

        form = ctk.CTkFrame(dialog, fg_color="#ffffff", corner_radius=14)
        form.pack(fill="both", expand=True, padx=18, pady=18)
        vars_ = {
            "country": ctk.StringVar(value="Germany"),
            "titles": ctk.StringVar(value="Business Development Manager, Sales Manager, Managing Director"),
            "keywords": ctk.StringVar(value="industrial ventilation, dust collection, fume extraction"),
            "per_page": ctk.StringVar(value="25"),
        }
        _form_entry(form, "Ülke", vars_["country"], 0)
        _form_entry(form, "Unvanlar", vars_["titles"], 1)
        _form_entry(form, "Anahtar Kelimeler", vars_["keywords"], 2)
        _form_entry(form, "Limit", vars_["per_page"], 3)
        note = ctk.CTkLabel(
            form,
            text="Not: Apollo People Search email döndürmez. Email için enrichment çalıştırılır ve ai_lead_contacts.email alanına yazılır.",
            text_color="#64748b",
            wraplength=460,
            justify="left",
        )
        note.grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 4))

        def run_search():
            payload = {
                "country": vars_["country"].get().strip(),
                "person_titles": [item.strip() for item in vars_["titles"].get().split(",") if item.strip()],
                "keywords": [item.strip() for item in vars_["keywords"].get().split(",") if item.strip()],
                "per_page": int(vars_["per_page"].get() or 25),
            }

            def worker():
                try:
                    result = search_apollo_ai_leads(token, payload)
                    created = int(result.get("created") or 0)
                    win.after(0, lambda: messagebox.showinfo("Apollo", f"{created} lead eklendi. Email için enrichment çalıştırın.", parent=win))
                    win.after(0, load_from_api)
                    win.after(0, dialog.destroy)
                except Exception as exc:
                    win.after(0, lambda err=str(exc): messagebox.showerror("Apollo", f"Apollo search başarısız: {err}", parent=dialog))

            threading.Thread(target=worker, daemon=True).start()

        ctk.CTkButton(form, text="Apollo'dan Lead Çek", command=run_search, fg_color="#d32f2f", hover_color="#b91c1c").grid(row=5, column=1, sticky="e", padx=16, pady=18)

    def segment_search():
        token = get_app_token()
        if not token:
            messagebox.showerror("Segmentten Lead Bul", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        dialog = ctk.CTkToplevel(win)
        dialog.title("Segmentten Lead Bul")
        dialog.geometry("600x500")
        dialog.configure(fg_color="#f5f5f5")
        dialog.transient(win)
        dialog.grab_set()

        form = ctk.CTkFrame(dialog, fg_color="#ffffff", corner_radius=14)
        form.pack(fill="both", expand=True, padx=18, pady=18)

        vars_ = {
            "segment_name": ctk.StringVar(value=HIGH_PRIORITY_SEGMENT_NAMES[0] if HIGH_PRIORITY_SEGMENT_NAMES else ""),
            "country": ctk.StringVar(value="Germany"),
            "limit": ctk.StringVar(value="25"),
            "enrich": ctk.StringVar(value="Evet"),
        }
        _form_combo(form, "Segment", vars_["segment_name"], HIGH_PRIORITY_SEGMENT_NAMES, 0)
        _form_combo(form, "Ülke", vars_["country"], TARGET_COUNTRIES, 1)
        _form_entry(form, "Lead Limiti", vars_["limit"], 2)
        _form_combo(form, "Email Enrichment", vars_["enrich"], ["Evet", "Hayır"], 3)

        note = ctk.CTkLabel(
            form,
            text="Bu ekran manuel keyword veya unvan istemez. Seçilen segmentin Apollo Search Recipe bilgisi backend'den çalıştırılır, sonuçlar enrich + score edilip Onay Bekliyor durumunda dashboard'a eklenir.",
            text_color="#64748b",
            wraplength=500,
            justify="left",
        )
        note.grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 4))

        def run_segment_search():
            segment_name = vars_["segment_name"].get().strip()
            if not segment_name:
                messagebox.showwarning("Eksik Bilgi", "Lütfen bir segment seçin.", parent=dialog)
                return
            try:
                limit = max(1, min(int(vars_["limit"].get() or 25), 100))
            except Exception:
                messagebox.showwarning("Eksik Bilgi", "Lead limiti sayı olmalı.", parent=dialog)
                return

            payload = {
                "segment_name": segment_name,
                "country": vars_["country"].get().strip(),
                "limit": limit,
                "enrich": vars_["enrich"].get() == "Evet",
            }

            def worker():
                try:
                    result = search_apollo_segment_leads(token, payload)
                    created = int(result.get("created") or 0)
                    skipped = int(result.get("skipped_duplicates") or 0)
                    win.after(0, lambda: messagebox.showinfo("Segmentten Lead Bul", f"{created} lead eklendi. {skipped} tekrar kayıt atlandı.", parent=win))
                    win.after(0, load_from_api)
                    win.after(0, dialog.destroy)
                except Exception as exc:
                    win.after(0, lambda err=str(exc): messagebox.showerror("Segmentten Lead Bul", f"Arama başarısız: {err}", parent=dialog))

            threading.Thread(target=worker, daemon=True).start()

        ctk.CTkButton(
            form,
            text="Segmentten Lead Bul",
            command=run_segment_search,
            fg_color="#d32f2f",
            hover_color="#b91c1c",
        ).grid(row=5, column=1, sticky="e", padx=16, pady=18)

    def enrich_selected():
        token = get_app_token()
        lead = selected_lead()
        if not token:
            messagebox.showerror("Apollo", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return
        if not lead:
            messagebox.showwarning("Apollo", "Lütfen enrichment yapılacak lead'i seçin.", parent=win)
            return

        def worker():
            try:
                result = enrich_ai_lead_from_apollo(token, lead.get("id"))
                contact = result.get("contact") or {}
                if contact:
                    lead["contact_email"] = contact.get("email") or lead.get("contact_email") or ""
                    lead["email_status"] = contact.get("email_status") or lead.get("email_status") or "enriched"
                    lead["enrichment_note"] = contact.get("enrichment_note") or lead.get("enrichment_note") or ""
                    lead["contact_name"] = contact.get("name") or lead.get("contact_name") or ""
                    lead["contact_title"] = contact.get("title") or lead.get("contact_title") or ""
                note = lead.get("enrichment_note") or "Apollo enrichment tamamlandı."
                lead["last_action"] = note
                win.after(0, apply_filters)
                win.after(0, lambda msg=note: messagebox.showinfo("Apollo", msg, parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Apollo", f"Apollo enrichment başarısız: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def create_sequence_for_selected():
        token = get_app_token()
        lead = selected_lead()
        if not token:
            messagebox.showerror("Email Sekansı", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return
        if not lead:
            messagebox.showwarning("Email Sekansı", "Lütfen sekans oluşturulacak lead'i seçin.", parent=win)
            return

        def worker():
            try:
                result = generate_ai_email_sequence(token, lead.get("id"))
                drafts = result.get("drafts") or []
                lead["draft_count"] = len(drafts)
                lead["ai_status"] = "Draft Generated"
                lead["approval_status"] = "Awaiting Approval"
                lead["last_action"] = "3 adımlı email sekansı taslakları oluşturuldu."
                win.after(0, apply_filters)
                win.after(0, lambda: messagebox.showinfo("Email Sekansı", f"{len(drafts)} email taslağı oluşturuldu. Gönderim yapılmadı; detay ekranından kontrol edip onaylayabilirsiniz.", parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Email Sekansı", f"Sekans oluşturulamadı: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    ctk.CTkButton(actions, text="Yenile", width=110, command=load_from_api, fg_color="#ffffff", text_color="#d32f2f", border_width=1, border_color="#d32f2f").pack(side="left", padx=(0, 8))
    ctk.CTkButton(actions, text="CSV Import", width=120, command=import_csv, fg_color="#ffffff", text_color="#2563eb", border_width=1, border_color="#2563eb").pack(side="left", padx=8)
    ctk.CTkButton(actions, text="Segmentten Lead Bul", width=165, command=segment_search, fg_color="#d32f2f", hover_color="#b91c1c").pack(side="left", padx=8)
    ctk.CTkButton(actions, text="Apollo Search", width=130, command=apollo_search, fg_color="#ffffff", text_color="#7c3aed", border_width=1, border_color="#7c3aed").pack(side="left", padx=8)
    ctk.CTkButton(actions, text="Email Enrich", width=120, command=enrich_selected, fg_color="#ffffff", text_color="#0f766e", border_width=1, border_color="#0f766e").pack(side="left", padx=8)
    ctk.CTkButton(actions, text="Sekans Oluştur", width=145, command=create_sequence_for_selected, fg_color="#ffffff", text_color="#0f766e", border_width=1, border_color="#0f766e").pack(side="left", padx=8)
    ctk.CTkButton(actions, text="Manuel Lead", width=130, command=add_manual_lead, fg_color="#d32f2f", hover_color="#b91c1c").pack(side="left", padx=(8, 0))

    search_var.trace_add("write", apply_filters)
    channel_var.trace_add("write", apply_filters)
    product_var.trace_add("write", apply_filters)
    priority_var.trace_add("write", apply_filters)
    tree.bind("<Double-1>", open_detail)

    apply_filters()
    load_from_api()


def _metric_card(parent, column, title, value_var, color):
    card = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    card.grid(row=0, column=column, sticky="ew", padx=6)
    ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#64748b").pack(anchor="w", padx=14, pady=(12, 2))
    ctk.CTkLabel(card, textvariable=value_var, font=ctk.CTkFont(size=24, weight="bold"), text_color=color).pack(anchor="w", padx=14, pady=(0, 12))


def _filter_label(parent, text, column):
    ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12, weight="bold"), text_color="#475569").grid(row=0, column=column, sticky="w", padx=(16 if column == 0 else 8, 8), pady=(14, 5))


def _form_entry(parent, label, variable, row):
    ctk.CTkLabel(parent, text=label, text_color="#475569").grid(row=row, column=0, sticky="w", padx=16, pady=8)
    ctk.CTkEntry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=16, pady=8)
    parent.grid_columnconfigure(1, weight=1)


def _form_combo(parent, label, variable, values, row):
    ctk.CTkLabel(parent, text=label, text_color="#475569").grid(row=row, column=0, sticky="w", padx=16, pady=8)
    ctk.CTkComboBox(parent, values=values, variable=variable).grid(row=row, column=1, sticky="ew", padx=16, pady=8)
    parent.grid_columnconfigure(1, weight=1)


def _next_id(leads):
    return max([int(item.get("id") or 0) for item in leads] or [0]) + 1


def _first_value(row, keys):
    for key in keys:
        value = row.get(key)
        if value:
            return str(value).strip()
    return ""


def _guess_channel(text):
    haystack = str(text or "").casefold()
    if any(word in haystack for word in ["integrator", "integration", "epc", "engineering", "automation"]):
        return "System Integration Solution Partner"
    if any(word in haystack for word in ["hvac", "ventilation", "indoor air", "clean air"]):
        return "Clean Air Solution Partner"
    if any(word in haystack for word in ["reseller", "distributor", "supplier"]):
        return "White Label / Resellers"
    if any(word in haystack for word in ["manufacturer", "machine builder", "oem"]):
        return "OEM"
    return "White Label / Resellers"


def _channel_from_apollo_row(row, text):
    segment = _first_value(row, ["segment", "Segment"]).casefold()
    campaign = _first_value(row, ["recommended_campaign", "Recommended Campaign"]).casefold()
    haystack = f"{segment} {campaign} {text}".casefold()
    if any(word in haystack for word in ["system integrator", "integration", "integrator", "epc", "turnkey"]):
        return "System Integration Solution Partner"
    if any(word in haystack for word in ["hvac", "clean air", "ventilation", "industrial_hvac"]):
        return "Clean Air Solution Partner"
    if any(word in haystack for word in ["distributor", "reseller", "dealer", "supplier"]):
        return "White Label / Resellers"
    if any(word in haystack for word in ["oem", "manufacturer", "machine builder"]):
        return "OEM"
    return _guess_channel(text)


def _guess_product(text):
    haystack = str(text or "").casefold()
    if any(word in haystack for word in ["oil mist", "cnc", "machining", "die casting"]):
        return "Oil Mist Filtration"
    if any(word in haystack for word in ["dust", "bulk", "foundry", "smelter", "powder"]):
        return "Dust Collection"
    if any(word in haystack for word in ["fume", "welding", "laser", "plasma", "cutting"]):
        return "Fume Extraction"
    if any(word in haystack for word in ["turnkey", "epc", "plant"]):
        return "Turnkey Solutions"
    return "Hall Ventilation"


def _product_from_apollo_row(row, text):
    campaign = _first_value(row, ["recommended_campaign", "Recommended Campaign"]).casefold()
    haystack = f"{campaign} {text}".casefold()
    if any(word in haystack for word in ["oil_mist", "oil mist", "cnc", "machining"]):
        return "Oil Mist Filtration"
    if any(word in haystack for word in ["dust", "atex", "bulk", "foundry", "powder"]):
        return "Dust Collection"
    if any(word in haystack for word in ["fume", "welding", "cutting", "grinding"]):
        return "Fume Extraction"
    if any(word in haystack for word in ["turnkey", "epc", "plant"]):
        return "Turnkey Solutions"
    if any(word in haystack for word in ["hvac", "ventilation", "clean air"]):
        return "Hall Ventilation"
    return _guess_product(text)


def _priority_from_icp(row):
    tier = _first_value(row, ["icp_tier", "ICP Tier"])
    if tier == "A+ Partner Target":
        return "Very High"
    if tier == "A Partner Target":
        return "High"
    if tier == "B Partner Target":
        return "Medium"
    if tier:
        return "Low"
    return ""


def _score_from_icp(row, priority):
    raw = _first_value(row, ["icp_score", "ICP Score"])
    try:
        return max(0, min(int(float(raw)), 100))
    except Exception:
        return 82 if priority == "Very High" else 70 if priority == "High" else 50 if priority == "Medium" else 30


def _sequence_from_campaign(campaign, channel):
    normalized = str(campaign or "").casefold()
    if "hvac" in normalized or "clean" in normalized:
        return "CASP"
    if "integr" in normalized or "turnkey" in normalized:
        return "SISP"
    if "oem" in normalized:
        return "OEM"
    if "reseller" in normalized or "distributor" in normalized:
        return "WL_RESELLER"
    return get_sequence_code(channel)


def _guess_language(country):
    mapping = {
        "Germany": "German",
        "Austria": "German",
        "France": "French",
        "Spain": "Spanish",
        "Italy": "Italian",
        "Netherlands": "Dutch",
        "Belgium": "French/Dutch",
        "Turkey": "Turkish",
    }
    return mapping.get(str(country or "").strip(), "English")
