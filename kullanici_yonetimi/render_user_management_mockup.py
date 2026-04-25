"""Kullanici yonetimi modern mockup gorselini uretir.

Bu script canli uygulamaya baglanmaz; yalnizca tasarim onizlemesi icin
statik PNG render eder.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "user_management_modern_mockup.png"

W, H = 1600, 980
BG = "#eef2f6"
PANEL = "#ffffff"
SURFACE = "#f8fafc"
BORDER = "#d8e0ea"
SOFT = "#e5ebf2"
TEXT = "#1f2937"
MUTED = "#64748b"
ACCENT = "#c62828"
ACCENT_DARK = "#a91f1f"
BLUE = "#2563eb"
GREEN = "#15803d"
GREEN_BG = "#ecfdf3"
AMBER = "#b45309"
AMBER_BG = "#fffbeb"
DANGER = "#dc2626"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


F_TITLE = font(30, True)
F_H2 = font(21, True)
F_H3 = font(15, True)
F_BODY = font(13)
F_BODY_B = font(13, True)
F_SMALL = font(12)
F_SMALL_B = font(12, True)
F_STAT = font(24, True)


def rr(draw: ImageDraw.ImageDraw, box, radius=8, fill=PANEL, outline=BORDER, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy, value, fnt=F_BODY, fill=TEXT, anchor=None):
    draw.text(xy, value, font=fnt, fill=fill, anchor=anchor)


def pill(draw: ImageDraw.ImageDraw, box, value, fg, bg, fnt=F_SMALL_B):
    rr(draw, box, radius=7, fill=bg, outline=bg)
    cx = (box[0] + box[2]) // 2
    cy = (box[1] + box[3]) // 2
    text(draw, (cx, cy), value, fnt, fg, anchor="mm")


def metric_card(draw: ImageDraw.ImageDraw, box, value, label, fg, bg):
    rr(draw, box, radius=7, fill=bg, outline=bg)
    text(draw, (box[0] + 22, box[1] + 26), value, F_STAT, fg, anchor="lm")
    text(draw, (box[0] + 22, box[1] + 53), label, F_SMALL, MUTED, anchor="lm")


def input_box(draw: ImageDraw.ImageDraw, box, placeholder):
    rr(draw, box, radius=8, fill="#ffffff", outline="#cbd5e1")
    text(draw, (box[0] + 12, box[1] + 13), placeholder, F_SMALL, "#64748b")


def button(draw: ImageDraw.ImageDraw, box, label, fill, fg="#ffffff", outline=None):
    rr(draw, box, radius=8, fill=fill, outline=outline or fill)
    text(draw, ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2), label, F_BODY_B, fg, anchor="mm")


def stat_card(draw: ImageDraw.ImageDraw, x, label, value, bg, fg):
    rr(draw, (x, 26, x + 118, 88), radius=8, fill=bg, outline=SOFT)
    text(draw, (x + 59, 45), value, F_STAT, fg, anchor="mm")
    text(draw, (x + 59, 72), label, F_SMALL, MUTED, anchor="mm")


def render() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    text(draw, (24, 34), "Kullanıcı Yönetim Paneli", F_TITLE)
    text(
        draw,
        (24, 76),
        "Kullanıcı hesapları, e-posta doğrulama, rol atamaları ve izin bakiyeleri tek ekranda.",
        F_BODY,
        MUTED,
    )

    stat_card(draw, 1020, "Toplam", "8", SURFACE, TEXT)
    stat_card(draw, 1150, "Aktif", "7", GREEN_BG, GREEN)
    stat_card(draw, 1280, "Doğrulanmamış", "1", AMBER_BG, AMBER)
    button(draw, (1438, 31, 1576, 70), "Listeyi Yenile", "#ffffff", TEXT, "#cbd5e1")

    left = (24, 120, 1082, 940)
    right = (1122, 120, 1576, 940)
    rr(draw, left, radius=10)
    rr(draw, right, radius=10)

    text(draw, (46, 156), "Kullanıcılar", F_H2)
    input_box(draw, (590, 140, 902, 180), "Ara: kullanıcı adı, e-posta veya rol")
    input_box(draw, (918, 140, 1060, 180), "Tüm Roller")

    form = (42, 194, 1063, 312)
    rr(draw, form, radius=8, fill=SURFACE, outline=SOFT)
    text(draw, (58, 226), "Yeni Kullanıcı Oluştur", F_H3)
    x = 58
    widths = [150, 190, 154, 154, 154]
    labels = ["Kullanıcı Adı", "Email Adresi", "Şifre Belirleme", "Şifre Doğrulama", "Rol Seç"]
    for w, label in zip(widths, labels):
        input_box(draw, (x, 248, x + w, 288), label)
        x += w + 10
    button(draw, (900, 248, 1048, 288), "Kullanıcı Ekle", ACCENT)

    header_y = 330
    rr(draw, (42, header_y, 1063, header_y + 42), radius=6, fill="#f1f5f9", outline="#f1f5f9")
    columns = [
        (56, "ID"),
        (118, "Kullanıcı Adı"),
        (336, "E-posta"),
        (628, "Rol"),
        (770, "E-posta"),
        (895, "Aktif"),
        (982, "Kalan İzin"),
    ]
    for x, label in columns:
        text(draw, (x, header_y + 16), label, F_SMALL_B)

    rows = [
        ("22", "Beyzanur Güç", "beyzanurapaydin@bomaksan.com", "Master Admin", "Doğrulandı", "Aktif", "14 gün", True),
        ("26", "Bora Boysan", "boraboysan@bomaksan.com", "Kullanıcı", "Doğrulandı", "Aktif", "6 gün", False),
        ("24", "Burak Boysan", "burakboysan@bomaksan.com", "Owner", "Doğrulandı", "Aktif", "18 gün", False),
        ("29", "Erinç Çelik", "erincelik@bomaksan.com", "Kullanıcı", "Bekliyor", "Pasif", "1 gün", False),
        ("27", "Hakan Çaresiz", "hakancaresiz@bomaksan.com", "Kullanıcı", "Doğrulandı", "Aktif", "10 gün", False),
        ("21", "Samet Bor", "sametbor@bomaksan.com", "Master Admin", "Doğrulandı", "Aktif", "15 gün", False),
        ("28", "Serhat Kara", "serhatkara@bomaksan.com", "Kullanıcı", "Doğrulandı", "Aktif", "4 gün", False),
        ("8", "Zafer Deliömeroğlu", "zaferdeliomeroglu@bomaksan.com", "Master Admin", "Doğrulandı", "Aktif", "13 gün", False),
    ]
    y = 380
    for i, row in enumerate(rows):
        selected = row[-1]
        fill = "#fff7ed" if selected else ("#ffffff" if i % 2 == 0 else SURFACE)
        outline = "#fed7aa" if selected else SOFT
        rr(draw, (42, y, 1063, y + 50), radius=6, fill=fill, outline=outline)
        values = row[:-1]
        for (x, _), value in zip(columns, values):
            color = MUTED if "@" in value else TEXT
            if value in ("Doğrulandı", "Aktif"):
                color = GREEN
            if value in ("Bekliyor",):
                color = AMBER
            if value == "Pasif":
                color = DANGER
            if "gün" in value:
                color = BLUE
            text(draw, (x, y + 18), value, F_SMALL, color)
        y += 58

    text(draw, (1144, 156), "Seçili Kullanıcı: Beyzanur Güç", F_H2)
    tab_y = 184
    button(draw, (1144, tab_y, 1270, tab_y + 38), "Profil", ACCENT)
    button(draw, (1278, tab_y, 1406, tab_y + 38), "Güvenlik", "#e2e8f0", TEXT, "#e2e8f0")
    button(draw, (1414, tab_y, 1542, tab_y + 38), "İzin Yönetimi", "#e2e8f0", TEXT, "#e2e8f0")

    rr(draw, (1144, 238, 1554, 326), radius=8, fill=SURFACE, outline=SOFT)
    draw.ellipse((1162, 252, 1221, 311), fill=ACCENT_DARK)
    text(draw, (1191, 282), "BG", F_BODY_B, "#ffffff", anchor="mm")
    text(draw, (1238, 272), "Beyzanur Güç", F_H2)
    text(draw, (1238, 302), "Master Admin · ID 22", F_SMALL, MUTED)

    rr(draw, (1144, 342, 1554, 624), radius=8, fill=SURFACE, outline=SOFT)
    text(draw, (1162, 378), "E-posta Güncelle", F_SMALL_B, MUTED)
    input_box(draw, (1162, 391, 1538, 431), "beyzanurapaydin@bomaksan.com")
    text(draw, (1162, 463), "Rol Seçme", F_SMALL_B, MUTED)
    input_box(draw, (1162, 476, 1538, 516), "Master Admin")
    button(draw, (1162, 547, 1344, 586), "E-postayı Güncelle", BLUE)
    button(draw, (1358, 547, 1538, 586), "Seçili Kullanıcıyı Sil", DANGER)

    rr(draw, (1144, 646, 1554, 916), radius=8, fill="#ffffff", outline=SOFT)
    text(draw, (1162, 682), "İzin Yönetimi sekmesi önizlemesi", F_H3)
    metric_card(draw, (1162, 700, 1278, 771), "18 gün", "Yıllık Hak", BLUE, "#eff6ff")
    metric_card(draw, (1288, 700, 1404, 771), "4 gün", "Kullanılan", AMBER, AMBER_BG)
    metric_card(draw, (1414, 700, 1538, 771), "14 gün", "Kalan Bakiye", GREEN, GREEN_BG)
    text(draw, (1162, 816), "Yönetici Ataması", F_SMALL_B, MUTED)
    input_box(draw, (1162, 829, 1538, 869), "Burak Boysan")
    button(draw, (1162, 880, 1538, 918), "İzin Bilgilerini Kaydet", ACCENT)

    img.save(OUT)


if __name__ == "__main__":
    render()
    print(OUT)
