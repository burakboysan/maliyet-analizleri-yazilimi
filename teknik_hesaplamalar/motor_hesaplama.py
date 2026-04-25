import os
from datetime import datetime
from math import pow
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox


KELVIN_OFFSET = 273.15
GAS_CONSTANT_DRY_AIR = 287.05
STANDARD_AIR_DENSITY = 1.20
SEA_LEVEL_DENSITY_0C = 1.293

STANDARD_MOTOR_POWERS_KW = [
    0.18,
    0.25,
    0.37,
    0.55,
    0.75,
    1.1,
    1.5,
    2.2,
    3.0,
    4.0,
    5.5,
    7.5,
    11.0,
    15.0,
    18.5,
    22.0,
    30.0,
    37.0,
    45.0,
    55.0,
    75.0,
    90.0,
    110.0,
    132.0,
    160.0,
    200.0,
    250.0,
    315.0,
]

DRIVE_TYPES = {
    "Direkt akuple": 1.00,
    "Kayis kasnak": 0.95,
}

VFD_OPTIONS = {
    "Var": True,
    "Yok": False,
}


def parse_number(input_text: str) -> float | None:
    trimmed = input_text.strip()
    if not trimmed:
        return None

    normalized = trimmed.replace(" ", "")
    if normalized.count(",") == 1 and "." not in normalized:
        normalized = normalized.replace(",", ".")
    else:
        normalized = normalized.replace(",", "")

    try:
        return float(normalized)
    except Exception:
        return None


def format_number(value: float) -> str:
    return f"{value:.2f}"


def format_decimal(value: float, digits: int = 2, grouped: bool = False) -> str:
    formatted = f"{value:,.{digits}f}" if grouped else f"{value:.{digits}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def calculate_atmospheric_pressure(altitude_m: float) -> float:
    return 101325.0 * pow(1.0 - 2.25577e-5 * altitude_m, 5.25588)


def calculate_air_density(temperature_c: float, altitude_m: float) -> tuple[float, float]:
    temperature_k = temperature_c + KELVIN_OFFSET
    atmospheric_pressure_pa = calculate_atmospheric_pressure(altitude_m)
    air_density = atmospheric_pressure_pa / (GAS_CONSTANT_DRY_AIR * temperature_k)
    return atmospheric_pressure_pa, air_density


def calculate_service_margin_suggestion(has_vfd: bool, drive_label: str) -> float:
    base_margin = 10.0 if has_vfd else 15.0
    drive_extra = 3.0 if drive_label == "Kayis kasnak" else 0.0
    return base_margin + drive_extra


def select_recommended_motor_kw(required_kw: float) -> float:
    for power in STANDARD_MOTOR_POWERS_KW:
        if power >= required_kw:
            return power
    return STANDARD_MOTOR_POWERS_KW[-1]


def get_expected_fan_efficiency_percent(motor_kw: float) -> int:
    if motor_kw <= 1.1:
        return 55
    if motor_kw < 5.5:
        return 60
    if motor_kw < 22.0:
        return 65
    if motor_kw < 75.0:
        return 70
    if motor_kw < 110.0:
        return 75
    return 80


def build_fan_efficiency_warning(motor_kw: float, fan_efficiency_percent: float) -> str:
    expected = get_expected_fan_efficiency_percent(motor_kw)
    if abs(fan_efficiency_percent - expected) < 0.0001:
        return ""
    return (
        f"Bu motor gucu araliginda fan verimi %{expected} olmalidir. "
        f"Girilen deger %{format_decimal(fan_efficiency_percent, 2)}."
    )


def build_selection_note(
    drive_label: str,
    has_vfd: bool,
    service_margin_percent: float,
    recommended_motor_kw: float,
) -> str:
    notes: list[str] = []
    suggested_margin = calculate_service_margin_suggestion(has_vfd, drive_label)

    if drive_label == "Direkt akuple":
        notes.append("Direkt akuple icin tahrik verimi 1.00 kabul edildi.")
    else:
        notes.append("Kayis kasnak icin tahrik verimi 0.95 ve ek %3 servis payi uygulandi.")

    if has_vfd:
        notes.append("VFD motor secimini dogrudan kucultmez; kalkis, kontrol ve kismi yuk isletmesinde avantaj saglar.")
    else:
        notes.append("VFD olmadigi icin servis payi %15 baz alinmistir.")

    if abs(service_margin_percent - suggested_margin) < 0.0001:
        notes.append(f"Onerilen servis payi %{format_number(service_margin_percent)} aynen kullanildi.")
    else:
        notes.append(
            f"Onerilen servis payi %{format_number(suggested_margin)} idi; kullanici girisi olarak %{format_number(service_margin_percent)} uygulandi."
        )

    notes.append(f"Motor secimi icin {format_number(recommended_motor_kw)} kW ust nominal motor onerildi.")
    return " ".join(notes)


def safe_pdf_text(value: str) -> str:
    return str(value).encode("cp1254", errors="replace").decode("cp1254")


def motor_hesaplama_ekrani_ac(
    parent: Optional[ctk.CTk] | Optional[ctk.CTkToplevel] = None,
) -> None:
    pencere = ctk.CTkToplevel(parent)
    pencere.title("Fan Guc Hesaplama")
    pencere.geometry("1100x820")
    pencere.minsize(980, 760)
    pencere.resizable(True, True)

    pencere.update_idletasks()
    x_pos = (pencere.winfo_screenwidth() // 2) - (1100 // 2)
    y_pos = (pencere.winfo_screenheight() // 2) - (820 // 2)
    pencere.geometry(f"1100x820+{x_pos}+{y_pos}")
    pencere.configure(fg_color="#f5f5f5")

    def _bring_to_front() -> None:
        try:
            pencere.lift()
            pencere.attributes("-topmost", True)
            pencere.after(250, lambda: pencere.attributes("-topmost", False))
            pencere.focus_force()
        except Exception:
            pass

    pencere.after(10, _bring_to_front)

    flow_rate_var = ctk.StringVar(value="10000")
    pressure_var = ctk.StringVar(value="2500")
    fan_efficiency_var = ctk.StringVar(value="65")
    temperature_var = ctk.StringVar(value="20")
    altitude_var = ctk.StringVar(value="1000")
    drive_type_var = ctk.StringVar(value="Direkt akuple")
    vfd_var = ctk.StringVar(value="Var")
    service_margin_var = ctk.StringVar(
        value=format_number(calculate_service_margin_suggestion(True, "Direkt akuple"))
    )
    last_suggested_margin = {"value": calculate_service_margin_suggestion(True, "Direkt akuple")}

    main_container = ctk.CTkFrame(pencere, fg_color="#f5f5f5")
    main_container.pack(fill="both", expand=True, padx=24, pady=20)

    header = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    header.pack(fill="x", pady=(0, 14))
    ctk.CTkLabel(
        header,
        text="Fan Guc Hesaplama",
        font=ctk.CTkFont(family="Inter", size=24, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="Yogunluk, hava gucu, mil gucu ve motor secimi hesabi.",
        font=ctk.CTkFont(family="Inter", size=13),
        text_color="#666666",
    ).pack(anchor="w")

    content = ctk.CTkScrollableFrame(main_container, fg_color="#f5f5f5")
    content.pack(fill="both", expand=True)
    content.grid_columnconfigure(0, weight=1)
    content.grid_columnconfigure(1, weight=1)

    intro = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=14)
    intro.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    ctk.CTkLabel(
        intro,
        text="Actual debi ve basinc ile fan gucu, mil gucu ve motor giris gucu hesabi.",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w", padx=16, pady=(16, 6))
    ctk.CTkLabel(
        intro,
        text="Mil gucu fan miline ulasan net gucu gosterir. Motor giris gucu ise yalnizca tahrik kayiplari dahil sebekeden cekilen guc ihtiyacidir.",
        font=ctk.CTkFont(size=13),
        text_color="#666666",
        wraplength=980,
        justify="left",
    ).pack(anchor="w", padx=16)
    ctk.CTkLabel(
        intro,
        text="Servis payi onerilen degerle gelir; istenirse kullanici tarafindan degistirilebilir.",
        font=ctk.CTkFont(size=13),
        text_color="#666666",
        wraplength=980,
        justify="left",
    ).pack(anchor="w", padx=16, pady=(6, 16))

    inputs_card = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=14)
    inputs_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    inputs_card.grid_columnconfigure(0, weight=1)
    inputs_card.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        inputs_card,
        text="Girdiler",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#212121",
    ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 12))

    def add_field(
        row: int,
        column: int,
        label: str,
        variable: ctk.StringVar,
        kind: str = "entry",
        values: list[str] | None = None,
    ):
        cell = ctk.CTkFrame(inputs_card, fg_color="#ffffff")
        cell.grid(row=row, column=column, sticky="ew", padx=16, pady=(0, 12))
        cell.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            cell,
            text=label,
            font=ctk.CTkFont(size=13),
            text_color="#555555",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        if kind == "menu":
            widget = ctk.CTkOptionMenu(
                cell,
                values=values or [],
                variable=variable,
                height=36,
                fg_color="#d32f2f",
                button_color="#b71c1c",
                button_hover_color="#8e0000",
                dropdown_fg_color="#ffffff",
                dropdown_hover_color="#ffebee",
                dropdown_text_color="#212121",
            )
        else:
            widget = ctk.CTkEntry(cell, textvariable=variable, height=36)
        widget.grid(row=1, column=0, sticky="ew")
        return widget

    watched_entries = [
        add_field(1, 0, "Debi actual (m3/h)", flow_rate_var),
        add_field(1, 1, "Basinc actual (Pa)", pressure_var),
        add_field(2, 0, "Fan verimi (%)", fan_efficiency_var),
        add_field(2, 1, "Servis payi (%)", service_margin_var),
        add_field(3, 0, "Calisma sicakligi (C)", temperature_var),
        add_field(3, 1, "Rakim (m)", altitude_var),
    ]
    add_field(4, 0, "Tahrik tipi", drive_type_var, kind="menu", values=list(DRIVE_TYPES.keys()))
    add_field(4, 1, "VFD", vfd_var, kind="menu", values=list(VFD_OPTIONS.keys()))

    error_card = ctk.CTkFrame(content, fg_color="#ffebee", corner_radius=14)
    error_card.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    ctk.CTkLabel(
        error_card,
        text="Giris hatalari",
        font=ctk.CTkFont(size=15, weight="bold"),
        text_color="#b71c1c",
    ).pack(anchor="w", padx=16, pady=(14, 6))
    error_text = ctk.CTkLabel(
        error_card,
        text="",
        font=ctk.CTkFont(size=13),
        text_color="#b71c1c",
        justify="left",
        wraplength=980,
    )
    error_text.pack(anchor="w", padx=16, pady=(0, 14))
    error_card.grid_remove()

    results_card = ctk.CTkFrame(content, fg_color="#ffffff", corner_radius=14)
    results_card.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    results_card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        results_card,
        text="Sonuclar",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#212121",
    ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 12))

    result_labels: dict[str, ctk.CTkLabel] = {}
    result_title_labels: dict[str, ctk.CTkLabel] = {}
    result_title_texts: dict[str, str] = {}

    def add_result(row: int, label: str, key: str, *, emphasized: bool = False) -> None:
        wrapper = ctk.CTkFrame(results_card, fg_color="#ffffff")
        wrapper.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 10))
        wrapper.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            wrapper,
            text=label,
            font=ctk.CTkFont(size=13 if not emphasized else 15, weight="bold" if emphasized else "normal"),
            text_color="#555555",
        )
        title_label.grid(row=0, column=0, sticky="w")

        value_label = ctk.CTkLabel(
            wrapper,
            text="-",
            font=ctk.CTkFont(size=13 if not emphasized else 18, weight="bold"),
            text_color="#212121" if not emphasized else "#d32f2f",
        )
        value_label.grid(row=0, column=1, sticky="e")

        result_labels[key] = value_label
        result_title_labels[key] = title_label
        result_title_texts[key] = label

    add_result(1, "1. Hava Debisi", "flow_rate_m3h")
    add_result(2, "2. Hava Yogunlugu (Deniz Seviyesi, 0 C)", "sea_level_density")
    add_result(3, "3. Hava Debisi", "flow_rate_m3s")
    add_result(4, "4. Giris/Atmosfer Basinci", "atmospheric_pressure")
    add_result(5, "5. Emilen Hava Sicakligi", "temperature_c")
    add_result(6, "6. Toplam Gercek Basinc Farki", "actual_pressure_diff")
    add_result(7, "7. Toplam Basinc Farki (@ 1,2 kg/m3 yogunlukta)", "pressure_diff_std_density")
    add_result(8, "8. Fan Verimi", "fan_efficiency")
    add_result(9, "9. Mil Gucu (Actual)", "shaft_power_actual")
    add_result(10, "10. Mil Gucu (@ 1,2 kg/m3 yogunlukta)", "shaft_power_std_density")
    add_result(11, "11. Servis Payi", "service_margin")
    add_result(12, "12. Onerilen Nominal Motor Gucu", "recommended_motor", emphasized=True)

    note_card = ctk.CTkFrame(content, fg_color="#f5f5f5", corner_radius=14)
    note_card.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 14))
    ctk.CTkLabel(
        note_card,
        text="Secim notu",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#212121",
    ).pack(anchor="w", padx=16, pady=(16, 8))
    note_text = ctk.CTkLabel(
        note_card,
        text="-",
        font=ctk.CTkFont(size=13),
        text_color="#555555",
        justify="left",
        wraplength=980,
    )
    note_text.pack(anchor="w", padx=16, pady=(0, 6))
    warning_text = ctk.CTkLabel(
        note_card,
        text="",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color="#d32f2f",
        justify="left",
        wraplength=980,
    )
    warning_text.pack(anchor="w", padx=16, pady=(0, 6))
    margin_text = ctk.CTkLabel(
        note_card,
        text="",
        font=ctk.CTkFont(size=13),
        text_color="#555555",
        justify="left",
        wraplength=980,
    )
    margin_text.pack(anchor="w", padx=16, pady=(0, 16))

    footer = ctk.CTkFrame(main_container, fg_color="#f5f5f5")
    footer.pack(fill="x", pady=(14, 0))
    export_state: dict[str, str] = {}

    def export_pdf() -> None:
        if not export_state:
            messagebox.showwarning("PDF Disa Aktarma", "Once gecerli bir hesaplama sonucu olusturun.", parent=pencere)
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            title="Fan Guc Hesabi PDF Kaydet",
            initialfile="fan_guc_hesabi_ozet.pdf",
        )
        if not path:
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.pdfgen import canvas
        except ImportError:
            messagebox.showerror(
                "PDF Disa Aktarma",
                "PDF olusturmak icin reportlab kutuphanesi bulunamadi.",
                parent=pencere,
            )
            return

        try:
            regular_font_name = "Helvetica"
            bold_font_name = "Helvetica-Bold"
            possible_font_pairs = [
                (
                    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
                    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf"),
                ),
                (
                    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "DejaVuSans.ttf"),
                    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "DejaVuSans-Bold.ttf"),
                ),
            ]
            for regular_path, bold_path in possible_font_pairs:
                if os.path.exists(regular_path) and os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("FanPowerPdfFont", regular_path))
                    pdfmetrics.registerFont(TTFont("FanPowerPdfFontBold", bold_path))
                    regular_font_name = "FanPowerPdfFont"
                    bold_font_name = "FanPowerPdfFontBold"
                    break

            pdf = canvas.Canvas(path, pagesize=A4)
            width, height = A4
            y_pos_pdf = height - 50

            def ensure_space(lines_needed: int = 2) -> None:
                nonlocal y_pos_pdf
                if y_pos_pdf < 60 + (lines_needed * 16):
                    pdf.showPage()
                    y_pos_pdf = height - 50

            pdf.setTitle(safe_pdf_text("Fan Guc Hesaplama Ozeti"))
            pdf.setFont(bold_font_name, 16)
            pdf.drawString(40, y_pos_pdf, safe_pdf_text("Fan Guc Hesaplama Ozeti"))
            y_pos_pdf -= 28

            pdf.setFont(regular_font_name, 11)
            pdf.drawString(
                40,
                y_pos_pdf,
                safe_pdf_text(f"Olusturma Zamani: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"),
            )
            y_pos_pdf -= 22

            pdf.setFont(bold_font_name, 12)
            pdf.drawString(40, y_pos_pdf, safe_pdf_text("Sonuclar"))
            y_pos_pdf -= 18

            rows = [
                ("Hava Debisi", export_state["flow_rate_m3h"]),
                ("Hava Yogunlugu (Deniz Seviyesi, 0 C)", export_state["sea_level_density"]),
                ("Hava Debisi", export_state["flow_rate_m3s"]),
                ("Giris/Atmosfer Basinci", export_state["atmospheric_pressure"]),
                ("Emilen Hava Sicakligi", export_state["temperature_c"]),
                ("Toplam Gercek Basinc Farki", export_state["actual_pressure_diff"]),
                ("Toplam Basinc Farki (@ 1,2 kg/m3 yogunlukta)", export_state["pressure_diff_std_density"]),
                ("Fan Verimi", export_state["fan_efficiency"]),
                ("Mil Gucu (Actual)", export_state["shaft_power_actual"]),
                ("Mil Gucu (@ 1,2 kg/m3 yogunlukta)", export_state["shaft_power_std_density"]),
                ("Servis Payi", export_state["service_margin"]),
                ("Onerilen Nominal Motor Gucu", export_state["recommended_motor"]),
            ]

            for label, value in rows:
                ensure_space(2)
                pdf.setFont(bold_font_name, 11)
                pdf.drawString(50, y_pos_pdf, safe_pdf_text(f"{label}:"))
                label_width = pdf.stringWidth(f"{label}:", bold_font_name, 11)
                if label == "Onerilen Nominal Motor Gucu":
                    pdf.setFillColorRGB(0.82, 0.18, 0.18)
                    pdf.setFont(bold_font_name, 12)
                    pdf.drawString(56 + label_width, y_pos_pdf, safe_pdf_text(value))
                    pdf.setFillColorRGB(0, 0, 0)
                else:
                    pdf.setFont(regular_font_name, 11)
                    pdf.drawString(56 + label_width, y_pos_pdf, safe_pdf_text(value))
                y_pos_pdf -= 15

            ensure_space(5)
            y_pos_pdf -= 8
            pdf.setFont(bold_font_name, 12)
            pdf.drawString(40, y_pos_pdf, safe_pdf_text("Secim Notu"))
            y_pos_pdf -= 18
            pdf.setFont(regular_font_name, 11)
            for line in export_state["selection_note"].split("\n"):
                ensure_space(2)
                pdf.drawString(50, y_pos_pdf, safe_pdf_text(line))
                y_pos_pdf -= 15
            if export_state.get("warning_note"):
                ensure_space(2)
                pdf.setFillColorRGB(0.82, 0.18, 0.18)
                pdf.setFont(bold_font_name, 11)
                pdf.drawString(50, y_pos_pdf, safe_pdf_text(export_state["warning_note"]))
                pdf.setFillColorRGB(0, 0, 0)
                pdf.setFont(regular_font_name, 11)
                y_pos_pdf -= 15
            for line in export_state["margin_note"].split("\n"):
                ensure_space(2)
                pdf.drawString(50, y_pos_pdf, safe_pdf_text(line))
                y_pos_pdf -= 15

            pdf.save()
            messagebox.showinfo("PDF Disa Aktarma", f"PDF olusturuldu:\n{path}", parent=pencere)
        except Exception as exc:
            messagebox.showerror("PDF Disa Aktarma", f"PDF olusturulurken hata olustu:\n{exc}", parent=pencere)

    ctk.CTkButton(
        footer,
        text="PDF Disa Aktar",
        width=130,
        fg_color="#d32f2f",
        hover_color="#c62828",
        text_color="white",
        command=export_pdf,
    ).pack(side="right", padx=(0, 10))
    ctk.CTkButton(
        footer,
        text="Kapat",
        width=100,
        fg_color="#9e9e9e",
        hover_color="#757575",
        text_color="white",
        command=pencere.destroy,
    ).pack(side="right", padx=(0, 12))

    def clear_results() -> None:
        for key, title_label in result_title_labels.items():
            title_label.configure(text=result_title_texts[key], text_color="#555555")
        for label in result_labels.values():
            label.configure(text="-")
        note_text.configure(text="-")
        warning_text.configure(text="")
        margin_text.configure(text="")
        export_state.clear()

    def show_errors(errors: list[str]) -> None:
        if errors:
            error_text.configure(text="\n".join(f"- {error}" for error in errors))
            error_card.grid()
        else:
            error_card.grid_remove()

    def maybe_refresh_service_margin(*_args) -> None:
        suggested = calculate_service_margin_suggestion(
            VFD_OPTIONS.get(vfd_var.get(), True),
            drive_type_var.get(),
        )
        current_margin = parse_number(service_margin_var.get())
        previous_suggested = last_suggested_margin["value"]
        if current_margin is None or abs(current_margin - previous_suggested) < 0.0001:
            service_margin_var.set(format_number(suggested))
        last_suggested_margin["value"] = suggested

    def recalculate(*_args) -> None:
        parsed_flow_rate = parse_number(flow_rate_var.get())
        parsed_pressure = parse_number(pressure_var.get())
        parsed_fan_efficiency = parse_number(fan_efficiency_var.get())
        parsed_temperature = parse_number(temperature_var.get())
        parsed_altitude = parse_number(altitude_var.get())
        parsed_service_margin = parse_number(service_margin_var.get())

        errors: list[str] = []
        if parsed_flow_rate is None:
            errors.append("Debi sayisal bir deger olmalidir.")
        if parsed_pressure is None:
            errors.append("Basinc sayisal bir deger olmalidir.")
        if parsed_fan_efficiency is None:
            errors.append("Fan verimi sayisal bir deger olmalidir.")
        if parsed_temperature is None:
            errors.append("Sicaklik sayisal bir deger olmalidir.")
        if parsed_altitude is None:
            errors.append("Rakim sayisal bir deger olmalidir.")
        if parsed_service_margin is None:
            errors.append("Servis payi sayisal bir deger olmalidir.")

        if errors:
            show_errors(errors)
            clear_results()
            return

        flow_rate_m3h = parsed_flow_rate or 0.0
        pressure_pa = parsed_pressure or 0.0
        fan_efficiency_percent = parsed_fan_efficiency or 0.0
        fan_efficiency = fan_efficiency_percent / 100.0
        temperature_c = parsed_temperature or 0.0
        altitude_m = parsed_altitude or 0.0
        service_margin_percent = parsed_service_margin or 0.0
        drive_label = drive_type_var.get()
        has_vfd = VFD_OPTIONS.get(vfd_var.get(), True)

        if flow_rate_m3h <= 0.0:
            errors.append("Debi 0'dan buyuk olmalidir.")
        if pressure_pa <= 0.0:
            errors.append("Basinc 0'dan buyuk olmalidir.")
        if fan_efficiency <= 0.0 or fan_efficiency > 1.0:
            errors.append("Fan verimi 0 ile 100 arasinda olmalidir.")
        if temperature_c <= -KELVIN_OFFSET:
            errors.append("Sicaklik mutlak sifirin ustunde olmalidir.")
        if altitude_m >= 44330.0:
            errors.append("Rakim 44.330 m altinda olmalidir.")
        if service_margin_percent < 0.0:
            errors.append("Servis payi 0 veya daha buyuk olmalidir.")

        if errors:
            show_errors(errors)
            clear_results()
            return

        show_errors([])

        atmospheric_pressure_pa, air_density_kg_m3 = calculate_air_density(temperature_c, altitude_m)
        flow_rate_m3s = flow_rate_m3h / 3600.0
        air_power_kw = (flow_rate_m3s * pressure_pa) / 1000.0
        shaft_power_kw = air_power_kw / fan_efficiency
        motor_input_kw = shaft_power_kw / DRIVE_TYPES.get(drive_label, 1.0)
        density_ratio = STANDARD_AIR_DENSITY / air_density_kg_m3 if air_density_kg_m3 > 0 else 0.0
        pressure_diff_std_density = pressure_pa * density_ratio
        shaft_power_std_density = shaft_power_kw * density_ratio
        sizing_basis_kw = motor_input_kw * (1.0 + service_margin_percent / 100.0)
        recommended_motor_kw = select_recommended_motor_kw(sizing_basis_kw)
        fan_efficiency_warning = build_fan_efficiency_warning(recommended_motor_kw, fan_efficiency_percent)

        result_labels["flow_rate_m3h"].configure(text=f"{format_decimal(flow_rate_m3h, 2, grouped=True)} m3/h")
        result_labels["sea_level_density"].configure(text=f"{format_decimal(SEA_LEVEL_DENSITY_0C, 3, grouped=True)} kg/m3")
        result_labels["flow_rate_m3s"].configure(text=f"{format_decimal(flow_rate_m3s, 3, grouped=True)} m3/s")
        result_labels["atmospheric_pressure"].configure(text=f"{format_decimal(atmospheric_pressure_pa, 0, grouped=True)} Pa")
        result_labels["temperature_c"].configure(text=f"{format_decimal(temperature_c, 1, grouped=True)} C")
        result_labels["actual_pressure_diff"].configure(text=f"{format_decimal(pressure_pa, 2, grouped=True)} Pa")
        result_labels["pressure_diff_std_density"].configure(text=f"{format_decimal(pressure_diff_std_density, 2, grouped=True)} Pa")
        result_labels["fan_efficiency"].configure(text=f"{format_decimal(fan_efficiency_percent, 2, grouped=True)}%")
        result_labels["shaft_power_actual"].configure(text=f"{format_decimal(shaft_power_kw, 2, grouped=True)} kW")
        result_labels["shaft_power_std_density"].configure(text=f"{format_decimal(shaft_power_std_density, 2, grouped=True)} kW")
        result_labels["service_margin"].configure(text=f"{format_decimal(service_margin_percent, 2, grouped=True)}%")
        result_labels["recommended_motor"].configure(text=f"{format_decimal(recommended_motor_kw, 2, grouped=True)} kW")

        if fan_efficiency_warning:
            result_title_labels["fan_efficiency"].configure(
                text=f"{result_title_texts['fan_efficiency']} ⚠",
                text_color="#d32f2f",
            )
        else:
            result_title_labels["fan_efficiency"].configure(
                text=result_title_texts["fan_efficiency"],
                text_color="#555555",
            )

        selection_note = build_selection_note(drive_label, has_vfd, service_margin_percent, recommended_motor_kw)
        margin_note = f"Hesaplanan motor giris gucune toplam %{format_number(service_margin_percent)} pay eklendi."
        if fan_efficiency_warning:
            warning_text.configure(text=f"⚠ DIKKAT! {fan_efficiency_warning}")
        else:
            warning_text.configure(text="")
        note_text.configure(text=selection_note)
        margin_text.configure(text=margin_note)

        export_state.clear()
        export_state.update(
            {
                "flow_rate_m3h": f"{format_decimal(flow_rate_m3h, 2, grouped=True)} m3/h",
                "sea_level_density": f"{format_decimal(SEA_LEVEL_DENSITY_0C, 3, grouped=True)} kg/m3",
                "flow_rate_m3s": f"{format_decimal(flow_rate_m3s, 3, grouped=True)} m3/s",
                "atmospheric_pressure": f"{format_decimal(atmospheric_pressure_pa, 0, grouped=True)} Pa",
                "temperature_c": f"{format_decimal(temperature_c, 1, grouped=True)} C",
                "actual_pressure_diff": f"{format_decimal(pressure_pa, 2, grouped=True)} Pa",
                "pressure_diff_std_density": f"{format_decimal(pressure_diff_std_density, 2, grouped=True)} Pa",
                "fan_efficiency": f"{format_decimal(fan_efficiency_percent, 2, grouped=True)}%",
                "shaft_power_actual": f"{format_decimal(shaft_power_kw, 2, grouped=True)} kW",
                "shaft_power_std_density": f"{format_decimal(shaft_power_std_density, 2, grouped=True)} kW",
                "service_margin": f"{format_decimal(service_margin_percent, 2, grouped=True)}%",
                "recommended_motor": f"{format_decimal(recommended_motor_kw, 2, grouped=True)} kW",
                "selection_note": selection_note,
                "margin_note": margin_note,
                "warning_note": f"⚠ DIKKAT! {fan_efficiency_warning}" if fan_efficiency_warning else "",
            }
        )

    for entry in watched_entries:
        entry.bind("<KeyRelease>", recalculate)

    drive_type_var.trace_add("write", maybe_refresh_service_margin)
    vfd_var.trace_add("write", maybe_refresh_service_margin)
    drive_type_var.trace_add("write", recalculate)
    vfd_var.trace_add("write", recalculate)
    recalculate()
