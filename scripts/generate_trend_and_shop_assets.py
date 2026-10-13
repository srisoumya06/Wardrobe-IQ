import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
DEFAULTS_DIR = os.path.join(STATIC_DIR, "defaults")
IMAGES_DEFAULTS_DIR = os.path.join(STATIC_DIR, "images", "defaults")

os.makedirs(DEFAULTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DEFAULTS_DIR, exist_ok=True)

# 1. Dedicated Live Fashion Trends Cards
TRENDS = [
    (
        "trend_quiet_luxury.jpg",
        "QUIET LUXURY & TAILORING",
        "Autumn / Winter 2026",
        "#292B28", # Charcoal bg
        "#F4EFE7", # Ivory text
        "#D8CBBB", # Accent
        "🧥",
        ["Charcoal", "Warm Ivory", "Soft Beige", "Espresso"]
    ),
    (
        "trend_utilitarian.jpg",
        "EARTHY UTILITARIAN",
        "Spring / Autumn 2026",
        "#34483B", # Forest green bg
        "#F4EFE7",
        "#A9B4A1",
        "🏕️",
        ["Olive Green", "Forest Green", "Camel", "Soft Beige"]
    ),
    (
        "trend_collegiate.jpg",
        "COLLEGIATE & KNITWEAR",
        "Year-Round 2026",
        "#1E2D4A", # Navy bg
        "#FFFFFF",
        "#D8CBBB",
        "👔",
        ["Navy Blue", "Crisp White", "Forest Green", "Taupe"]
    ),
    (
        "trend_linen_resort.jpg",
        "FLUID RESORT LINEN",
        "Spring / Summer 2026",
        "#EAE3D6", # Linen sand bg
        "#292B28",
        "#8B806E",
        "👗",
        ["Warm Ivory", "Sage Green", "Soft Sand"]
    ),
]

# 2. Dedicated Shopping Companion Product Cards
PRODUCTS = [
    ("shop_uniqlo_chinos.jpg", "Uniqlo Relaxed Chinos", "Bottoms", "₹4,250", "#4B5648", "#F4EFE7", "👖"),
    ("shop_cos_trousers.jpg", "COS Pleated Wool Trousers", "Bottoms", "₹10,800", "#3E3B36", "#FFFFFF", "👖"),
    ("shop_everlane_tee.jpg", "Everlane Organic Heavyweight Tee", "Tops", "₹2,750", "#E8DFD3", "#292B28", "👕"),
    ("shop_arket_oxford.jpg", "Arket Premium Oxford Shirt", "Tops", "₹5,950", "#F8F9FA", "#1E2D4A", "👔"),
    ("shop_veja_sneakers.jpg", "Veja Campo Leather Lows", "Footwear", "₹12,100", "#F5F5F5", "#292B28", "👟"),
    ("shop_massimo_loafers.jpg", "Massimo Dutti Suede Loafers", "Footwear", "₹14,600", "#3D2B1F", "#F4EFE7", "👞"),
    ("shop_reformation_dress.jpg", "Reformation Tiered Slip Dress", "Dresses / One-piece", "₹15,400", "#F4EFE7", "#34483B", "👗"),
    ("shop_nordgreen_watch.jpg", "Nordgreen Minimalist Field Watch", "Accessories", "₹15,550", "#C9BBA7", "#292B28", "⌚"),
]

def render_fashion_card(filename, title, subtitle, bg_color, text_color, border_color, icon, swatches=None):
    img = Image.new("RGB", (680, 800), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Architectural double border
    draw.rectangle([18, 18, 662, 782], outline=border_color, width=2)
    draw.rectangle([30, 30, 650, 770], outline=border_color, width=1)

    # Stylized central medallion
    draw.ellipse([260, 240, 420, 400], fill=border_color)
    draw.ellipse([275, 255, 405, 385], fill=bg_color)

    # Central typography
    draw.text((340, 450), title, fill=text_color, anchor="mm")
    draw.text((340, 490), subtitle, fill=text_color, anchor="mm")
    draw.text((340, 530), "WARDROBE IQ • EDITORIAL FORECAST", fill=border_color, anchor="mm")

    # Swatch dots if provided
    if swatches:
        x_start = 340 - ((len(swatches) * 36) // 2)
        swatch_colors = {
            "Charcoal": "#292B28", "Warm Ivory": "#F4EFE7", "Soft Beige": "#D8CBBB",
            "Espresso": "#3D2B1F", "Olive Green": "#4B5648", "Forest Green": "#34483B",
            "Camel": "#9E846A", "Navy Blue": "#1E2D4A", "Crisp White": "#FFFFFF",
            "Taupe": "#8B806E", "Sage Green": "#A9B4A1", "Soft Sand": "#E8DFD3"
        }
        for i, sw in enumerate(swatches):
            c_hex = swatch_colors.get(sw, "#8B806E")
            cx = x_start + (i * 36) + 18
            draw.ellipse([cx - 10, 600, cx + 10, 620], fill=c_hex, outline=border_color, width=1)

    for target_dir in [DEFAULTS_DIR, IMAGES_DEFAULTS_DIR]:
        path = os.path.join(target_dir, filename)
        img.save(path, quality=94)

for fn, tit, sub, bg, txt, bdr, ico, sws in TRENDS:
    render_fashion_card(fn, tit, sub, bg, txt, bdr, ico, sws)

for fn, tit, cat, price, bg, txt, ico in PRODUCTS:
    render_fashion_card(fn, tit.upper(), f"{cat} • {price}", bg, txt, "#D8CBBB", ico)

print(f"Rendered {len(TRENDS)} trend assets and {len(PRODUCTS)} product assets in both directories.")
