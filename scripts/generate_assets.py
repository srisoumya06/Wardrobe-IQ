import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULTS_DIR = os.path.join(BASE_DIR, "app", "static", "images", "defaults")
os.makedirs(DEFAULTS_DIR, exist_ok=True)

ITEMS = [
    # Tops
    ("top_oxford_shirt.jpg", "White Oxford Shirt", "Tops", "#FFFFFF", "#34483B", "👔"),
    ("top_linen_tee.jpg", "Sand Linen T-Shirt", "Tops", "#E8DFD3", "#8B806E", "👕"),
    ("top_forest_sweater.jpg", "Forest Merino Sweater", "Tops", "#34483B", "#F4EFE7", "🧶"),
    ("top_charcoal_blazer.jpg", "Charcoal Tailored Blazer", "Tops", "#292B28", "#D8CBBB", "🧥"),
    
    # Bottoms
    ("bottom_chinos.jpg", "Olive Tailored Chinos", "Bottoms", "#4B5648", "#F4EFE7", "👖"),
    ("bottom_jeans.jpg", "Selvedge Denim Jeans", "Bottoms", "#243342", "#F4EFE7", "👖"),
    ("bottom_trousers.jpg", "Taupe Wool Trousers", "Bottoms", "#8B806E", "#FFFFFF", "👖"),
    
    # Dresses / One-piece
    ("dress_linen.jpg", "Ivory Tiered Shirt Dress", "Dresses / One-piece", "#F4EFE7", "#34483B", "👗"),
    ("dress_slip.jpg", "Sage Silk Slip Dress", "Dresses / One-piece", "#A9B4A1", "#292B28", "👗"),
    
    # Footwear
    ("shoes_sneakers.jpg", "Minimalist White Sneakers", "Footwear", "#F7F7F7", "#292B28", "👟"),
    ("shoes_loafers.jpg", "Espresso Leather Loafers", "Footwear", "#3D2B1F", "#F4EFE7", "👞"),
    ("shoes_boots.jpg", "Desert Suede Chelsea Boots", "Footwear", "#9E846A", "#FFFFFF", "🥾"),
    
    # Accessories
    ("acc_watch.jpg", "Vintage Minimalist Watch", "Accessories", "#C9BBA7", "#292B28", "⌚"),
    ("acc_belt.jpg", "Woven Saddle Leather Belt", "Accessories", "#5C3E21", "#F4EFE7", "🏷️"),
    ("acc_tote.jpg", "Canvas & Leather Weekender", "Accessories", "#D8CBBB", "#34483B", "👜"),

    # AI Model try-on avatars
    ("model_pose_studio.jpg", "Model Alex — Studio Neutral", "Model", "#FAF6F0", "#34483B", "👤"),
    ("model_pose_editorial.jpg", "Model Jordan — Editorial 3/4", "Model", "#F4EFE7", "#34483B", "👤"),
    ("model_pose_relaxed.jpg", "Model Taylor — Relaxed Stance", "Model", "#EDE6DC", "#34483B", "👤"),
]

for filename, title, cat, bg_color, text_color, icon in ITEMS:
    path = os.path.join(DEFAULTS_DIR, filename)
    img = Image.new("RGB", (600, 700), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Subtle border
    draw.rectangle([15, 15, 585, 685], outline="#D8CBBB", width=2)
    draw.rectangle([25, 25, 575, 675], outline="#FAF7F2", width=1)
    
    # Center placeholder artistic card
    draw.ellipse([230, 240, 370, 380], fill="#FFFFFF", outline="#D8CBBB", width=2)
    
    # Text metadata
    draw.text((300, 430), cat.upper(), fill=text_color, anchor="mm")
    draw.text((300, 480), title, fill=text_color, anchor="mm")
    draw.text((300, 520), "WARDROBE IQ ESSENTIALS", fill="#8B806E", anchor="mm")
    
    img.save(path, quality=92)

print(f"Generated {len(ITEMS)} default clothing and model assets.")
