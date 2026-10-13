import os
import urllib.request
from io import BytesIO
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
DEFAULTS_DIR = os.path.join(STATIC_DIR, "defaults")
IMAGES_DEFAULTS_DIR = os.path.join(STATIC_DIR, "images", "defaults")

os.makedirs(DEFAULTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DEFAULTS_DIR, exist_ok=True)

ASSETS = [
    # 8 Shopping Products
    ("shop_uniqlo_chinos.jpg", "photo-1624378439575-d8705ad7ae80", (600, 750)),
    ("shop_cos_trousers.jpg", "photo-1594633312681-425c7b97ccd1", (600, 750)),
    ("shop_everlane_tee.jpg", "photo-1521572267360-ee0c2909d518", (600, 750)),
    ("shop_arket_oxford.jpg", "photo-1596755094514-f87e34085b2c", (600, 750)),
    ("shop_veja_sneakers.jpg", "photo-1560769629-975ec94e6a86", (600, 750)),
    ("shop_massimo_loafers.jpg", "photo-1614252369475-531eba835eb1", (600, 750)),
    ("shop_reformation_dress.jpg", "photo-1595777457583-95e059d581b8", (600, 750)),
    ("shop_nordgreen_watch.jpg", "photo-1524805444758-089113d48a6d", (600, 750)),

    # 6 Live Fashion Trends
    ("trend_quiet_luxury.jpg", "photo-1539109136881-3be0616acf4b", (640, 800)),
    ("trend_utilitarian.jpg", "photo-1515886657613-9f3515b0c78f", (640, 800)),
    ("trend_collegiate.jpg", "photo-1490481651871-ab68de25d43d", (640, 800)),
    ("trend_linen_resort.jpg", "photo-1469334031218-e382a71b716b", (640, 800)),
    ("trend_monochrome_minimalism.jpg", "photo-1483985988355-763728e1935b", (640, 800)),
    ("trend_contemporary_heritage.jpg", "photo-1509631179647-0177331693ae", (640, 800)),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def download_and_save():
    success_count = 0
    for filename, photo_id, target_size in ASSETS:
        url = f"https://images.unsplash.com/{photo_id}?w={target_size[0] * 2}&auto=format&fit=crop&q=85"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                img_data = response.read()
                im = Image.open(BytesIO(img_data)).convert("RGB")
                im = im.resize(target_size, Image.Resampling.LANCZOS)
                
                # Save to both defaults dirs
                p1 = os.path.join(DEFAULTS_DIR, filename)
                p2 = os.path.join(IMAGES_DEFAULTS_DIR, filename)
                im.save(p1, "JPEG", quality=90)
                im.save(p2, "JPEG", quality=90)
                print(f"Saved real photography for: {filename} ({target_size[0]}x{target_size[1]})")
                success_count += 1
        except Exception as e:
            print(f"Failed to fetch {filename} from {url}: {e}")

    print(f"\nCompleted: {success_count}/{len(ASSETS)} fashion photography assets installed.")

if __name__ == "__main__":
    download_and_save()
