import os
import shutil
import urllib.request
from io import BytesIO
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
DEFAULTS_DIR = os.path.join(STATIC_DIR, "defaults")
IMAGES_DEFAULTS_DIR = os.path.join(STATIC_DIR, "images", "defaults")

os.makedirs(DEFAULTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DEFAULTS_DIR, exist_ok=True)

# 1. Download real human full-body models
MODELS_TO_FETCH = [
    ("model_pose_studio.jpg", "photo-1617137984095-74e4e5e3613f", (700, 1000)),
    ("model_pose_editorial.jpg", "photo-1515886657613-9f3515b0c78f", (700, 1000)),
    ("model_pose_relaxed.jpg", "photo-1509631179647-0177331693ae", (700, 1000)),
    ("top_charcoal_blazer.jpg", "photo-1594938298603-c8148c4dae35", (600, 750)),
    ("top_forest_sweater.jpg", "photo-1620799140408-edc6dcb6d633", (600, 750)),
    ("bottom_jeans.jpg", "photo-1541099649105-f69ad21f3246", (600, 750)),
    ("shoes_boots.jpg", "photo-1608256246200-53e635b5b65f", (600, 750)),
    ("acc_belt.jpg", "photo-1624222247344-550fb60583dc", (600, 750)),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def install():
    # A. Copy existing verified shop photography to closet defaults where applicable
    mappings = [
        ("shop_arket_oxford.jpg", "top_oxford_shirt.jpg"),
        ("shop_everlane_tee.jpg", "top_linen_tee.jpg"),
        ("shop_uniqlo_chinos.jpg", "bottom_chinos.jpg"),
        ("shop_cos_trousers.jpg", "bottom_trousers.jpg"),
        ("shop_reformation_dress.jpg", "dress_linen.jpg"),
        ("shop_massimo_loafers.jpg", "shoes_loafers.jpg"),
        ("shop_veja_sneakers.jpg", "shoes_sneakers.jpg"),
        ("shop_nordgreen_watch.jpg", "acc_watch.jpg"),
    ]
    for src_name, dst_name in mappings:
        src_path = os.path.join(DEFAULTS_DIR, src_name)
        if os.path.exists(src_path):
            for d in [DEFAULTS_DIR, IMAGES_DEFAULTS_DIR]:
                dst_path = os.path.join(d, dst_name)
                shutil.copyfile(src_path, dst_path)
            print(f"Copied real asset: {src_name} -> {dst_name}")

    # B. Fetch remote high-resolution photography for models and remaining items
    for filename, pid, size in MODELS_TO_FETCH:
        url = f"https://images.unsplash.com/{pid}?w={size[0] * 2}&auto=format&fit=crop&q=85"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                im = Image.open(BytesIO(data)).convert("RGB")
                im = im.resize(size, Image.Resampling.LANCZOS)
                for d in [DEFAULTS_DIR, IMAGES_DEFAULTS_DIR]:
                    im.save(os.path.join(d, filename), "JPEG", quality=92)
                print(f"Saved real photography for: {filename} ({size[0]}x{size[1]})")
        except Exception as e:
            print(f"Failed to fetch {filename}: {e}")

if __name__ == "__main__":
    install()
