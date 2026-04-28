import threading
from tkinter import messagebox, ttk

import customtkinter as ctk

from core.api_client import ApiClientError, list_ai_search_recipes, update_ai_search_recipe
from core.session import get_app_token
from core.utils import apply_bomaksan_table_style, apply_zebra_striping
from lead_otomasyonu.strategy_constants import PRIORITY_OPTIONS, PRODUCT_CATEGORIES, SALES_CHANNELS, build_segment_name


def segment_ayarlari_ekrani(parent=None, on_update=None):
    win = ctk.CTkToplevel(parent) if parent else ctk.CTkToplevel()
    win.title("Segment Ayarları")
    win.geometry("1180x760")
    win.minsize(1040, 680)
    win.configure(fg_color="#f5f5f5")
    win.transient(parent)

    try:
        win.lift()
        win.focus_force()
    except Exception:
        pass

    state = {"recipes": [], "selected_id": None}

    root = ctk.CTkFrame(win, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=18, pady=18)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=2)
    root.grid_rowconfigure(1, weight=1)

    header = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        header,
        text="Segment Ayarları",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#212121",
    ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))
    status_var = ctk.StringVar(value="Segment tanımı, hedefleme notu ve Apollo arama reçeteleri burada düzenlenir.")
    ctk.CTkLabel(header, textvariable=status_var, text_color="#64748b").grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

    list_panel = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    list_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
    list_panel.grid_rowconfigure(1, weight=1)
    list_panel.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        list_panel,
        text="Apollo Search Recipe",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color="#334155",
    ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))

    tree_wrap = ctk.CTkFrame(list_panel, fg_color="transparent")
    tree_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
    tree_wrap.grid_rowconfigure(0, weight=1)
    tree_wrap.grid_columnconfigure(0, weight=1)

    y_scroll = ttk.Scrollbar(tree_wrap, orient="vertical")
    columns = ("segment_name", "priority", "is_active")
    tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", yscrollcommand=y_scroll.set, selectmode="browse")
    y_scroll.config(command=tree.yview)
    apply_bomaksan_table_style(tree)
    tree.heading("segment_name", text="Segment")
    tree.heading("priority", text="Öncelik")
    tree.heading("is_active", text="Aktif")
    tree.column("segment_name", width=300, minwidth=220, anchor="w")
    tree.column("priority", width=90, minwidth=80, anchor="w")
    tree.column("is_active", width=60, minwidth=55, anchor="center")
    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")

    editor = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e5e7eb")
    editor.grid(row=1, column=1, sticky="nsew")
    editor.grid_columnconfigure(1, weight=1)
    editor.grid_columnconfigure(3, weight=1)
    editor.grid_rowconfigure(4, weight=1)
    editor.grid_rowconfigure(6, weight=1)
    editor.grid_rowconfigure(8, weight=1)

    vars_ = {
        "segment_name": ctk.StringVar(),
        "sales_channel": ctk.StringVar(value=SALES_CHANNELS[0]),
        "product_category": ctk.StringVar(value=PRODUCT_CATEGORIES[0]),
        "priority": ctk.StringVar(value="High"),
        "is_active": ctk.BooleanVar(value=True),
    }
    textboxes = {}

    _form_entry(editor, "Segment Adı", vars_["segment_name"], 0, 0, colspan=3)
    _form_combo(editor, "Satış Kanalı", vars_["sales_channel"], SALES_CHANNELS, 1, 0)
    _form_combo(editor, "Ürün / Hizmet", vars_["product_category"], PRODUCT_CATEGORIES, 1, 2)
    _form_combo(editor, "Öncelik", vars_["priority"], PRIORITY_OPTIONS, 2, 0)
    ctk.CTkCheckBox(editor, text="Aktif", variable=vars_["is_active"], text_color="#334155").grid(row=2, column=2, columnspan=2, sticky="w", padx=14, pady=8)

    textboxes["target_definition"] = _textbox(editor, "Hedef Segment Tanımı", 3, 0, height=88)
    textboxes["targeting_notes"] = _textbox(editor, "Hedefleme Notları", 3, 2, height=88)
    textboxes["company_keywords"] = _textbox(editor, "Apollo Firma Keywordleri", 5, 0, height=120)
    textboxes["person_titles"] = _textbox(editor, "Hedef Ünvanlar", 5, 2, height=120)
    textboxes["positive_signals"] = _textbox(editor, "Pozitif Sinyaller", 7, 0, height=120)
    textboxes["negative_signals"] = _textbox(editor, "Negatif Sinyaller", 7, 2, height=120)

    button_bar = ctk.CTkFrame(editor, fg_color="transparent")
    button_bar.grid(row=9, column=0, columnspan=4, sticky="ew", padx=14, pady=(8, 14))
    button_bar.grid_columnconfigure(0, weight=1)

    def set_text(key, value):
        box = textboxes[key]
        box.delete("1.0", "end")
        if isinstance(value, list):
            box.insert("1.0", "\n".join(str(item) for item in value if str(item).strip()))
        else:
            box.insert("1.0", str(value or ""))

    def get_text(key):
        return textboxes[key].get("1.0", "end").strip()

    def get_lines(key):
        return [line.strip() for line in get_text(key).splitlines() if line.strip()]

    def selected_recipe():
        selected = tree.selection()
        if not selected:
            return None
        recipe_id = str(selected[0])
        for recipe in state["recipes"]:
            if str(recipe.get("id")) == recipe_id:
                return recipe
        return None

    def fill_form(recipe):
        state["selected_id"] = recipe.get("id")
        vars_["segment_name"].set(recipe.get("segment_name") or "")
        vars_["sales_channel"].set(recipe.get("sales_channel") or SALES_CHANNELS[0])
        vars_["product_category"].set(recipe.get("product_category") or PRODUCT_CATEGORIES[0])
        vars_["priority"].set(recipe.get("priority") or "High")
        vars_["is_active"].set(bool(recipe.get("is_active")))
        for key in textboxes:
            set_text(key, recipe.get(key))
        status_var.set("Seçili segment düzenlenebilir. Kaydettiğiniz hedefleme Segmentten Lead Bul aramasında kullanılır.")

    def render():
        children = tree.get_children()
        if children:
            tree.delete(*children)
        for recipe in state["recipes"]:
            tree.insert(
                "",
                "end",
                iid=str(recipe.get("id")),
                values=(
                    recipe.get("segment_name") or "",
                    recipe.get("priority") or "",
                    "Evet" if recipe.get("is_active") else "Hayır",
                ),
            )
        apply_zebra_striping(tree, tree.get_children())
        if state["recipes"]:
            first_id = str(state["recipes"][0].get("id"))
            tree.selection_set(first_id)
            tree.focus(first_id)
            fill_form(state["recipes"][0])

    def load_recipes():
        token = get_app_token()
        if not token:
            messagebox.showerror("Segment Ayarları", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return

        def worker():
            try:
                recipes = list_ai_search_recipes(token)
                state["recipes"] = recipes
                win.after(0, render)
            except ApiClientError as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Segment Ayarları", err, parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Segment Ayarları", f"Segmentler yüklenemedi: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def save_recipe():
        token = get_app_token()
        recipe = selected_recipe()
        if not token:
            messagebox.showerror("Segment Ayarları", "API oturumu bulunamadı. Lütfen yeniden giriş yapın.", parent=win)
            return
        if not recipe:
            messagebox.showwarning("Segment Ayarları", "Lütfen düzenlenecek segmenti seçin.", parent=win)
            return

        sales_channel = vars_["sales_channel"].get().strip()
        product_category = vars_["product_category"].get().strip()
        segment_name = vars_["segment_name"].get().strip() or build_segment_name(product_category, sales_channel)
        payload = {
            "segment_name": segment_name,
            "sales_channel": sales_channel,
            "product_category": product_category,
            "priority": vars_["priority"].get().strip(),
            "target_definition": get_text("target_definition"),
            "targeting_notes": get_text("targeting_notes"),
            "company_keywords": get_lines("company_keywords"),
            "person_titles": get_lines("person_titles"),
            "positive_signals": get_lines("positive_signals"),
            "negative_signals": get_lines("negative_signals"),
            "is_active": bool(vars_["is_active"].get()),
        }

        def worker():
            try:
                updated = update_ai_search_recipe(token, recipe.get("id"), payload)
                for index, item in enumerate(state["recipes"]):
                    if str(item.get("id")) == str(updated.get("id")):
                        state["recipes"][index] = updated
                        break
                win.after(0, render)
                win.after(0, lambda item=updated: (tree.selection_set(str(item.get("id"))), tree.focus(str(item.get("id"))), fill_form(item)))
                win.after(0, lambda: status_var.set("Segment ayarları kaydedildi."))
                if on_update:
                    win.after(0, on_update)
            except ApiClientError as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Segment Ayarları", err, parent=win))
            except Exception as exc:
                win.after(0, lambda err=str(exc): messagebox.showerror("Segment Ayarları", f"Kaydedilemedi: {err}", parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def on_select(_event=None):
        recipe = selected_recipe()
        if recipe:
            fill_form(recipe)

    def rebuild_name():
        vars_["segment_name"].set(build_segment_name(vars_["product_category"].get(), vars_["sales_channel"].get()))

    ctk.CTkButton(button_bar, text="Segment Adını Yenile", width=150, command=rebuild_name, fg_color="#ffffff", text_color="#2563eb", border_width=1, border_color="#2563eb").grid(row=0, column=1, padx=8, sticky="e")
    ctk.CTkButton(button_bar, text="Kaydet", width=120, command=save_recipe, fg_color="#d32f2f", hover_color="#b91c1c").grid(row=0, column=2, padx=(8, 0), sticky="e")

    tree.bind("<<TreeviewSelect>>", on_select)
    load_recipes()


def _form_entry(parent, label, variable, row, column, colspan=1):
    ctk.CTkLabel(parent, text=label, text_color="#475569").grid(row=row, column=column, sticky="w", padx=14, pady=(12, 4))
    ctk.CTkEntry(parent, textvariable=variable).grid(row=row, column=column + 1, columnspan=colspan, sticky="ew", padx=14, pady=(12, 4))


def _form_combo(parent, label, variable, values, row, column):
    ctk.CTkLabel(parent, text=label, text_color="#475569").grid(row=row, column=column, sticky="w", padx=14, pady=8)
    ctk.CTkComboBox(parent, values=values, variable=variable).grid(row=row, column=column + 1, sticky="ew", padx=14, pady=8)


def _textbox(parent, label, row, column, height=100):
    ctk.CTkLabel(parent, text=label, text_color="#475569").grid(row=row, column=column, columnspan=2, sticky="w", padx=14, pady=(12, 4))
    box = ctk.CTkTextbox(parent, height=height, wrap="word")
    box.grid(row=row + 1, column=column, columnspan=2, sticky="nsew", padx=14, pady=(0, 4))
    return box
