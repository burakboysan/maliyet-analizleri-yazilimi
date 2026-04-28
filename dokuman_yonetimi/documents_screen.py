import os
import threading
import traceback
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core.document_service import (
    ALLOWED_DOCUMENT_TYPES,
    DOCUMENT_LANGUAGE_OPTIONS,
    DOCUMENT_SERIES_OPTIONS,
    DocumentServiceError,
    delete_document,
    get_document_upload_log_path,
    list_documents,
    upload_document,
    _write_debug_log,
)
from core.roles import has_master_admin_capabilities
from core.utils import apply_bomaksan_table_style, apply_zebra_striping


DOCUMENT_TYPE_OPTIONS = [
    ("brosur", "Broşür"),
    ("teknik_foy", "Teknik Bilgi Föyü"),
    ("kullanim_kilavuzu", "Kullanım Kılavuzu"),
]
DOCUMENT_LANGUAGE_FILTER_OPTIONS = [("all", "Tüm Diller")] + list(DOCUMENT_LANGUAGE_OPTIONS.items())


def dokumanlar_ekrani(kullanici_rolu, parent=None):
    pencere = ctk.CTkToplevel(parent) if parent is not None else ctk.CTkToplevel()
    pencere.title("Dokümanlar")
    pencere.geometry("1180x760")
    pencere.minsize(980, 620)
    pencere.configure(fg_color="#f5f5f5")

    try:
        pencere.state("zoomed")
    except Exception:
        pass

    try:
        pencere.lift()
        pencere.focus_force()
        pencere.attributes("-topmost", True)
        pencere.after(250, lambda: pencere.attributes("-topmost", False))
    except Exception:
        pass

    state = {
        "documents": [],
        "selected_file": None,
    }

    main_container = ctk.CTkFrame(pencere, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=20, pady=20)

    header_frame = ctk.CTkFrame(main_container, fg_color=("#ffffff", "#2d2d2d"), corner_radius=16)
    header_frame.pack(fill="x", pady=(0, 16))

    header_left = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_left.pack(side="left", fill="both", expand=True, padx=24, pady=20)

    ctk.CTkLabel(
        header_left,
        text="Doküman Yönetimi",
        font=ctk.CTkFont(size=26, weight="bold"),
        text_color=("#1a1a1a", "#ffffff"),
    ).pack(anchor="w")

    ctk.CTkLabel(
        header_left,
        text="Merkezi doküman listesini görüntüleyin ve yetkiniz varsa PDF yükleyin.",
        font=ctk.CTkFont(size=14),
        text_color=("#666666", "#cccccc"),
    ).pack(anchor="w", pady=(6, 0))

    header_right = ctk.CTkFrame(header_frame, fg_color="transparent")
    header_right.pack(side="right", padx=24, pady=20)

    status_label = ctk.CTkLabel(
        header_right,
        text="Hazır",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=("#d32f2f", "#f44336"),
    )
    status_label.pack(anchor="e")

    body_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    body_frame.pack(fill="both", expand=True)
    body_frame.grid_columnconfigure(0, weight=2)
    body_frame.grid_columnconfigure(1, weight=1)
    body_frame.grid_rowconfigure(0, weight=1)

    list_card = ctk.CTkFrame(body_frame, fg_color="#ffffff", corner_radius=16)
    list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    list_header = ctk.CTkFrame(list_card, fg_color="transparent")
    list_header.pack(fill="x", padx=20, pady=(16, 8))

    ctk.CTkLabel(
        list_header,
        text="Yayınlanan Dokümanlar",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#212121",
    ).pack(side="left")

    filtre_var = ctk.StringVar(value="Tümü")
    seri_filtre_var = ctk.StringVar(value="Tüm Seriler")
    dil_filtre_var = ctk.StringVar(value="Tüm Diller")

    filtre_combo = ctk.CTkComboBox(
        list_header,
        values=["Tümü", "Broşür", "Teknik Bilgi Föyü", "Kullanım Kılavuzu"],
        variable=filtre_var,
        width=170,
    )
    filtre_combo.pack(side="right")

    dil_filtre_combo = ctk.CTkComboBox(
        list_header,
        values=[label for _, label in DOCUMENT_LANGUAGE_FILTER_OPTIONS],
        variable=dil_filtre_var,
        width=140,
    )
    dil_filtre_combo.pack(side="right", padx=(0, 10))

    seri_filtre_combo = ctk.CTkComboBox(
        list_header,
        values=["Tüm Seriler"] + [label for _, label in DOCUMENT_SERIES_OPTIONS],
        variable=seri_filtre_var,
        width=170,
    )
    seri_filtre_combo.pack(side="right", padx=(0, 10))

    table_frame = ctk.CTkFrame(list_card, fg_color="transparent")
    table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
    tree_scroll_y.pack(side="right", fill="y")
    tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
    tree_scroll_x.pack(side="bottom", fill="x")

    tree = ttk.Treeview(
        table_frame,
        columns=("series_key", "title", "type", "language", "description", "updated_at"),
        show="headings",
        yscrollcommand=tree_scroll_y.set,
        xscrollcommand=tree_scroll_x.set,
        selectmode="extended",
    )
    tree_scroll_y.config(command=tree.yview)
    tree_scroll_x.config(command=tree.xview)
    apply_bomaksan_table_style(tree)
    tree.pack(side="left", fill="both", expand=True)

    tree.heading("series_key", text="Seri")
    tree.heading("title", text="Başlık")
    tree.heading("type", text="Tip")
    tree.heading("language", text="Dil")
    tree.heading("description", text="Açıklama")
    tree.heading("updated_at", text="Güncelleme")

    tree.column("series_key", width=140, minwidth=120, anchor="w")
    tree.column("title", width=240, minwidth=180, anchor="w")
    tree.column("type", width=160, minwidth=140, anchor="w")
    tree.column("language", width=110, minwidth=90, anchor="w")
    tree.column("description", width=380, minwidth=240, anchor="w")
    tree.column("updated_at", width=160, minwidth=140, anchor="w")

    right_card = ctk.CTkFrame(body_frame, fg_color="#ffffff", corner_radius=16)
    right_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    ctk.CTkLabel(
        right_card,
        text="PDF Yükle",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w", padx=20, pady=(18, 10))

    form_frame = ctk.CTkFrame(right_card, fg_color="transparent")
    form_frame.pack(fill="x", padx=20)

    title_var = ctk.StringVar()
    description_var = ctk.StringVar()
    type_var = ctk.StringVar(value="Broşür")
    language_var = ctk.StringVar(value=DOCUMENT_LANGUAGE_OPTIONS["tr"])
    series_var = ctk.StringVar(value=DOCUMENT_SERIES_OPTIONS[0][1])
    file_name_var = ctk.StringVar(value="Henüz dosya seçilmedi")

    ctk.CTkLabel(form_frame, text="Seri", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
    series_combo = ctk.CTkComboBox(
        form_frame,
        values=[label for _, label in DOCUMENT_SERIES_OPTIONS],
        variable=series_var,
        height=38,
    )
    series_combo.pack(fill="x", pady=(6, 12))

    ctk.CTkLabel(form_frame, text="Başlık", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
    title_entry = ctk.CTkEntry(form_frame, textvariable=title_var, height=38)
    title_entry.pack(fill="x", pady=(6, 12))

    ctk.CTkLabel(form_frame, text="Açıklama", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
    description_entry = ctk.CTkEntry(form_frame, textvariable=description_var, height=38)
    description_entry.pack(fill="x", pady=(6, 12))

    ctk.CTkLabel(form_frame, text="Doküman Tipi", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
    type_combo = ctk.CTkComboBox(
        form_frame,
        values=[label for _, label in DOCUMENT_TYPE_OPTIONS],
        variable=type_var,
        height=38,
    )
    type_combo.pack(fill="x", pady=(6, 12))

    ctk.CTkLabel(form_frame, text="Doküman Dili", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
    language_combo = ctk.CTkComboBox(
        form_frame,
        values=[label for _, label in DOCUMENT_LANGUAGE_OPTIONS.items()],
        variable=language_var,
        height=38,
    )
    language_combo.pack(fill="x", pady=(6, 12))

    ctk.CTkLabel(form_frame, text="Seçilen Dosya", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
    file_label = ctk.CTkLabel(
        form_frame,
        textvariable=file_name_var,
        wraplength=260,
        justify="left",
        text_color="#666666",
    )
    file_label.pack(anchor="w", pady=(6, 12))

    def set_status(message):
        status_label.configure(text=message)

    def selected_type_key():
        for key, label in DOCUMENT_TYPE_OPTIONS:
            if label == type_var.get():
                return key
        return "brosur"

    def selected_language_key():
        for key, label in DOCUMENT_LANGUAGE_OPTIONS.items():
            if label == language_var.get():
                return key
        return "tr"

    def selected_series_key():
        for key, label in DOCUMENT_SERIES_OPTIONS:
            if label == series_var.get():
                return key
        return ""

    def current_filter_key():
        selected = filtre_var.get()
        if selected == "Tümü":
            return None
        for key, label in DOCUMENT_TYPE_OPTIONS:
            if label == selected:
                return key
        return None

    def current_series_filter_key():
        selected = seri_filtre_var.get()
        if selected == "Tüm Seriler":
            return None
        for key, label in DOCUMENT_SERIES_OPTIONS:
            if label == selected:
                return key
        return None

    def current_language_filter_key():
        selected = dil_filtre_var.get()
        if selected == "Tüm Diller":
            return None
        for key, label in DOCUMENT_LANGUAGE_OPTIONS.items():
            if label == selected:
                return key
        return None

    def display_series_label(series_key):
        normalized_series_key = str(series_key or "").strip().upper()
        for key, label in DOCUMENT_SERIES_OPTIONS:
            if key == normalized_series_key:
                return label
        return normalized_series_key

    def fill_tree(documents):
        state["documents"] = documents
        for item in tree.get_children():
            tree.delete(item)

        item_ids = []
        for doc in documents:
            item_id = tree.insert(
                "",
                "end",
                values=(
                    display_series_label(doc.get("series_key")),
                    doc.get("title", ""),
                    ALLOWED_DOCUMENT_TYPES.get(doc.get("document_type", ""), doc.get("document_type", "")),
                    DOCUMENT_LANGUAGE_OPTIONS.get(doc.get("language", "tr"), doc.get("language", "tr")),
                    doc.get("description", "") or "",
                    (doc.get("updated_at") or doc.get("created_at") or "")[:19].replace("T", " "),
                ),
            )
            tree.set(item_id, "title", doc.get("title", ""))
            item_ids.append(item_id)

        if item_ids:
            apply_zebra_striping(tree, item_ids)

    def load_documents_async():
        set_status("Dokümanlar yükleniyor...")

        def worker():
            try:
                documents = list_documents(
                    current_series_filter_key(),
                    current_filter_key(),
                    current_language_filter_key(),
                )
                pencere.after(0, lambda: fill_tree(documents))
                pencere.after(0, lambda: set_status(f"{len(documents)} doküman listelendi"))
            except DocumentServiceError as exc:
                pencere.after(0, lambda: messagebox.showerror("Dokümanlar", str(exc), parent=pencere))
                pencere.after(0, lambda: set_status("Listeleme hatası"))
            except Exception as exc:
                _write_debug_log(f"Listeleme beklenmeyen hata: {exc}\n{traceback.format_exc()}")
                pencere.after(0, lambda: messagebox.showerror("Dokümanlar", str(exc), parent=pencere))
                pencere.after(0, lambda: set_status("Listeleme hatası"))

        threading.Thread(target=worker, daemon=True).start()

    def choose_file():
        selected_path = filedialog.askopenfilename(
            parent=pencere,
            title="PDF seç",
            filetypes=[("PDF Dosyaları", "*.pdf")],
        )
        if not selected_path:
            return

        state["selected_file"] = selected_path
        file_name_var.set(os.path.basename(selected_path))
        if not title_var.get().strip():
            title_var.set(os.path.splitext(os.path.basename(selected_path))[0])

    def upload_selected_pdf():
        if not has_master_admin_capabilities(kullanici_rolu):
            messagebox.showwarning("Yetki", "PDF yüklemek için Owner veya Master Admin yetkisi gereklidir.", parent=pencere)
            return

        if not state["selected_file"]:
            messagebox.showwarning("Dosya", "Lütfen bir PDF dosyası seçin.", parent=pencere)
            return

        title = title_var.get().strip()
        if not title:
            messagebox.showwarning("Başlık", "Lütfen doküman başlığını girin.", parent=pencere)
            return

        series_key = selected_series_key()
        if not series_key:
            messagebox.showwarning("Seri", "Lütfen bir seri seçin.", parent=pencere)
            return

        set_status("PDF yükleniyor...")
        upload_button.configure(state="disabled", text="Yükleniyor...")

        def worker():
            try:
                upload_document(
                    series_key=series_key,
                    title=title,
                    document_type=selected_type_key(),
                    language=selected_language_key(),
                    description=description_var.get().strip(),
                    file_path=state["selected_file"],
                )

                def on_success():
                    upload_button.configure(state="normal", text="PDF Yükle")
                    title_var.set("")
                    description_var.set("")
                    type_var.set("Broşür")
                    language_var.set(DOCUMENT_LANGUAGE_OPTIONS["tr"])
                    series_var.set(DOCUMENT_SERIES_OPTIONS[0][1])
                    state["selected_file"] = None
                    file_name_var.set("Henüz dosya seçilmedi")
                    set_status("PDF başarıyla yüklendi")
                    messagebox.showinfo("Başarılı", "PDF başarıyla yüklendi.", parent=pencere)
                    load_documents_async()

                pencere.after(0, on_success)
            except DocumentServiceError as exc:
                error_message = str(exc)
                pencere.after(
                    0,
                    lambda msg=error_message: (
                        upload_button.configure(state="normal", text="PDF Yükle"),
                        set_status("Yükleme hatası"),
                        messagebox.showerror(
                            "Yükleme Hatası",
                            f"{msg}\n\nDetay logu: logs/document_upload_debug.log",
                            parent=pencere,
                        ),
                    ),
                )
            except Exception as exc:
                _write_debug_log(f"Ekran upload beklenmeyen hata: {exc}\n{traceback.format_exc()}")
                error_message = str(exc)
                pencere.after(
                    0,
                    lambda msg=error_message: (
                        upload_button.configure(state="normal", text="PDF Yükle"),
                        set_status("Yükleme hatası"),
                        messagebox.showerror(
                            "Yükleme Hatası",
                            f"{msg}\n\nDetay logu: logs/document_upload_debug.log",
                            parent=pencere,
                        ),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def get_selected_document():
        selection = tree.selection()
        if not selection:
            return None
        index = tree.index(selection[0])
        if index >= len(state["documents"]):
            return None
        return state["documents"][index]

    def get_selected_documents():
        documents = []
        for item_id in tree.selection():
            index = tree.index(item_id)
            if 0 <= index < len(state["documents"]):
                documents.append(state["documents"][index])
        return documents

    def open_selected_document():
        document = get_selected_document()
        if not document:
            messagebox.showwarning("Seçim", "Lütfen açmak için bir doküman seçin.", parent=pencere)
            return

        file_url = document.get("file_url")
        if not file_url:
            messagebox.showwarning("Doküman", "Seçilen kaydın dosya bağlantısı bulunamadı.", parent=pencere)
            return

        try:
            webbrowser.open(file_url)
            set_status("Doküman tarayıcıda açıldı")
        except Exception as exc:
            messagebox.showerror("Doküman", f"Doküman açılamadı:\n{exc}", parent=pencere)

    def delete_selected_documents():
        if not has_master_admin_capabilities(kullanici_rolu):
            messagebox.showwarning("Yetki", "Silme işlemi için Owner veya Master Admin yetkisi gereklidir.", parent=pencere)
            return

        selected_documents = get_selected_documents()
        if not selected_documents:
            messagebox.showwarning("Seçim", "Lütfen silmek için en az bir doküman seçin.", parent=pencere)
            return

        titles = [doc.get("title", "Doküman") for doc in selected_documents]
        if len(selected_documents) == 1:
            prompt = f"'{titles[0]}' dokümanı silinsin mi?"
        else:
            prompt = f"{len(selected_documents)} doküman silinsin mi?\n\n" + "\n".join(f"- {title}" for title in titles[:10])
            if len(selected_documents) > 10:
                prompt += f"\n... ve {len(selected_documents) - 10} doküman daha"

        if not messagebox.askyesno("Silme Onayı", prompt, parent=pencere):
            return

        set_status("Doküman(lar) siliniyor...")
        delete_button.configure(state="disabled", text="Siliniyor...")

        def worker():
            deleted_count = 0
            try:
                for document in selected_documents:
                    delete_document(document.get("id"))
                    deleted_count += 1

                def on_success():
                    delete_button.configure(state="normal", text="Seçilenleri Sil")
                    set_status(f"{deleted_count} doküman silindi")
                    messagebox.showinfo("Başarılı", f"{deleted_count} doküman silindi.", parent=pencere)
                    load_documents_async()

                pencere.after(0, on_success)
            except DocumentServiceError as exc:
                error_message = str(exc)
                pencere.after(
                    0,
                    lambda msg=error_message: (
                        delete_button.configure(state="normal", text="Seçilenleri Sil"),
                        set_status("Silme hatası"),
                        messagebox.showerror(
                            "Silme Hatası",
                            f"{msg}\n\nDetay logu: logs/document_upload_debug.log",
                            parent=pencere,
                        ),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    choose_button = ctk.CTkButton(
        form_frame,
        text="PDF Seç",
        height=38,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#1976d2", "#64b5f6"),
        border_width=1,
        border_color="#1976d2",
        command=choose_file,
    )
    choose_button.pack(fill="x", pady=(4, 10))

    upload_button = ctk.CTkButton(
        form_frame,
        text="PDF Yükle",
        height=40,
        fg_color="#d32f2f",
        hover_color="#c62828",
        command=upload_selected_pdf,
    )
    upload_button.pack(fill="x")

    if not has_master_admin_capabilities(kullanici_rolu):
        upload_button.configure(state="disabled")
        choose_button.configure(state="disabled")
        title_entry.configure(state="disabled")
        description_entry.configure(state="disabled")
        type_combo.configure(state="disabled")
        language_combo.configure(state="disabled")
        series_combo.configure(state="disabled")

    info_card = ctk.CTkFrame(right_card, fg_color="#f8f9fa", corner_radius=12)
    info_card.pack(fill="x", padx=20, pady=(18, 12))

    ctk.CTkLabel(
        info_card,
        text="Not",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w", padx=14, pady=(12, 4))

    info_text = (
        "PDF yükleme yalnızca Owner veya Master Admin kullanıcıları için aktiftir.\n"
        "Yüklenen dosyalar seçilen dil etiketiyle merkezi doküman havuzuna eklenir."
    )
    ctk.CTkLabel(
        info_card,
        text=info_text,
        justify="left",
        wraplength=260,
        text_color="#666666",
    ).pack(anchor="w", padx=14, pady=(0, 12))

    actions_frame = ctk.CTkFrame(main_container, fg_color="transparent")
    actions_frame.pack(fill="x", pady=(14, 0))

    ctk.CTkButton(
        actions_frame,
        text="Yenile",
        width=130,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#1976d2", "#64b5f6"),
        border_width=1,
        border_color="#1976d2",
        command=load_documents_async,
    ).pack(side="left")

    ctk.CTkButton(
        actions_frame,
        text="Dokümanı Aç",
        width=150,
        fg_color="#2e7d32",
        hover_color="#1b5e20",
        command=open_selected_document,
    ).pack(side="left", padx=10)

    delete_button = ctk.CTkButton(
        actions_frame,
        text="Seçilenleri Sil",
        width=150,
        fg_color="#ffffff",
        hover_color="#d32f2f",
        text_color="#d32f2f",
        border_width=1,
        border_color="#d32f2f",
        command=delete_selected_documents,
    )
    delete_button.pack(side="left", padx=10)

    if not has_master_admin_capabilities(kullanici_rolu):
        delete_button.configure(state="disabled")

    ctk.CTkButton(
        actions_frame,
        text="Kapat",
        width=130,
        fg_color=("#ffffff", "#2d2d2d"),
        text_color=("#424242", "#ffffff"),
        border_width=1,
        border_color="#bdbdbd",
        command=pencere.destroy,
    ).pack(side="right")

    filtre_combo.configure(command=lambda _value: load_documents_async())
    dil_filtre_combo.configure(command=lambda _value: load_documents_async())
    seri_filtre_combo.configure(command=lambda _value: load_documents_async())
    tree.bind("<Double-1>", lambda _event: open_selected_document())

    load_documents_async()
    return pencere
