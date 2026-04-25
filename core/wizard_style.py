WIZARD_BG = "#eef2f6"
PANEL_BG = "#ffffff"
SUMMARY_BG = "#ffffff"
SURFACE_BG = "#f8fafc"
RESULT_BG = "#fff7ed"
DOCUMENT_BG = "#eef6ff"
BORDER_COLOR = "#d8e0ea"
SOFT_BORDER_COLOR = "#e5ebf2"
ENTRY_BORDER_COLOR = "#cbd5e1"
ENTRY_FOCUS_BORDER_COLOR = "#94a3b8"
TEXT_COLOR = "#1f2937"
MUTED_TEXT_COLOR = "#64748b"
ACCENT_COLOR = "#c62828"
ACCENT_HOVER_COLOR = "#a91f1f"
PANEL_RADIUS = 10
CARD_RADIUS = 8


def configure_wizard_split(content_row, main_weight=4, summary_weight=6):
    content_row.grid_columnconfigure(0, weight=main_weight)
    content_row.grid_columnconfigure(1, weight=summary_weight)
    content_row.grid_rowconfigure(0, weight=1)


def entry_style():
    return {
        "height": 38,
        "corner_radius": 8,
        "border_width": 1,
        "border_color": ENTRY_BORDER_COLOR,
        "fg_color": "#f8fafc",
        "text_color": TEXT_COLOR,
    }
