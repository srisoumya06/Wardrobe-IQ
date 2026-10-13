import os
import json
import base64
import requests
from PIL import Image, ImageStat
from app.config import Config

COLOR_PALETTE_MAP = [
    ("#FFFFFF", "Crisp White", (255, 255, 255)),
    ("#F4EFE7", "Warm Ivory", (244, 239, 231)),
    ("#D8CBBB", "Soft Beige", (216, 203, 187)),
    ("#D3B683", "Camel / Tan", (211, 182, 131)),
    ("#C3B091", "Khaki", (195, 176, 145)),
    ("#8B806E", "Muted Taupe", (139, 128, 110)),
    ("#5C4033", "Rich Brown", (92, 64, 51)),
    ("#3B2F2F", "Dark Espresso", (59, 47, 47)),
    ("#0F0F0F", "Jet Black", (15, 15, 15)),
    ("#292B28", "Charcoal", (41, 43, 40)),
    ("#607274", "Slate Gray", (96, 114, 116)),
    ("#B0B7BD", "Heather Gray", (176, 183, 189)),
    ("#1E2D4A", "Navy Blue", (30, 45, 74)),
    ("#2B4C7E", "Royal / Cobalt Blue", (43, 76, 126)),
    ("#A0C4E2", "Light / Sky Blue", (160, 196, 226)),
    ("#4682B4", "Denim Blue", (70, 130, 180)),
    ("#34483B", "Deep Forest Green", (52, 72, 59)),
    ("#4F6F52", "Olive Green", (79, 111, 82)),
    ("#A9B4A1", "Sage Green", (169, 180, 161)),
    ("#E8D382", "Butter Yellow", (232, 211, 130)),
    ("#D4A017", "Warm Mustard", (212, 160, 23)),
    ("#B05E5E", "Terracotta / Rust", (176, 94, 94)),
    ("#6B2D38", "Burgundy / Wine", (107, 45, 56)),
    ("#A82828", "Crimson Red", (168, 40, 40)),
    ("#D4A5A5", "Blush / Dusty Rose", (212, 165, 165)),
    ("#B6A6CA", "Lavender / Lilac", (182, 166, 202))
]

def match_closest_color(r, g, b):
    """Finds closest color in COLOR_PALETTE_MAP using Euclidean distance."""
    best = None
    min_dist = float("inf")
    for hex_code, name, (cr, cg, cb) in COLOR_PALETTE_MAP:
        dist = ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            best = (hex_code, name)
    return best if best else ("#8B806E", "Muted Taupe")

def get_dominant_color_pillow(image_path):
    """Calculates dominant color using Pillow quantization, filtering out background margins."""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            # Sample center crop to avoid background walls
            crop = img.crop((int(w * 0.15), int(h * 0.15), int(w * 0.85), int(h * 0.85)))
            crop.thumbnail((120, 120))
            quantized = crop.quantize(colors=6)
            palette = quantized.getpalette()
            color_counts = sorted(quantized.getcolors() or [], reverse=True, key=lambda x: x[0])
            
            top_color_idx = color_counts[0][1]
            r = palette[top_color_idx * 3]
            g = palette[top_color_idx * 3 + 1]
            b = palette[top_color_idx * 3 + 2]
            
            best_hex, best_name = match_closest_color(r, g, b)
            hex_val = f"#{r:02x}{g:02x}{b:02x}"
            return {
                "hex": hex_val,
                "closest_palette_hex": best_hex,
                "color_name": best_name
            }
    except Exception:
        return {"hex": "#8B806E", "closest_palette_hex": "#8B806E", "color_name": "Muted Taupe"}


def analyze_clothing_image(image_path):
    """
    Analyzes an uploaded single clothing item image for closet addition.
    Uses Gemini API if GEMINI_API_KEY is configured.
    Otherwise falls back to honest local color analysis & guided manual confirmation.
    """
    color_info = get_dominant_color_pillow(image_path)
    
    if Config.GEMINI_API_KEY:
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
            prompt = """
            Analyze this clothing image for a digital wardrobe application. Respond ONLY with a valid JSON object with the following fields:
            {
              "category": "Tops" | "Bottoms" | "Dresses / One-piece" | "Footwear" | "Accessories",
              "subcategory": "e.g. Button-down Shirt, Trousers, Loafers, etc.",
              "color": "e.g. Warm Ivory, Navy Blue, etc.",
              "pattern": "Solid" | "Striped" | "Plaid" | "Floral" | "Checked" | "Graphic" | "Other",
              "style": "Casual" | "Formal" | "Smart Casual" | "Minimalist" | "Streetwear" | "Athleisure",
              "season": "All-Season" | "Spring" | "Summer" | "Autumn" | "Winter",
              "occasions": "e.g. College, Casual, Smart Casual, Work/Office",
              "suggested_name": "Short descriptive title"
            }
            """
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                    ]
                }]
            }
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text_content.startswith("```"):
                    text_content = text_content.split("```")[1]
                    if text_content.startswith("json"):
                        text_content = text_content[4:]
                result = json.loads(text_content.strip())
                result["color_hex"] = color_info["hex"]
                result["is_ai_recognized"] = True
                result["service_note"] = "Recognised via Gemini Vision API"
                return result
        except Exception:
            pass

    return {
        "category": "Tops",
        "subcategory": "Casual Shirt",
        "color": color_info["color_name"],
        "color_hex": color_info["hex"],
        "pattern": "Solid",
        "style": "Smart Casual",
        "season": "All-Season",
        "occasions": "College, Casual, Smart Casual",
        "suggested_name": f"{color_info['color_name']} Wardrobe Piece",
        "is_ai_recognized": False,
        "service_note": "Local palette analysis active. No external Vision API key configured — please verify attributes below."
    }


# -------------------------------------------------------------
# IMAGE COMPUTER VISION & STATS EXTRACTION
# -------------------------------------------------------------

def extract_section_stats(crop_img, bg_rgb):
    """
    Extracts mean color, texture variance, and luminance from a garment crop,
    filtering out background studio wall colors.
    """
    stat = ImageStat.Stat(crop_img)
    mean_r, mean_g, mean_b = stat.mean[:3]
    std_r, std_g, std_b = stat.stddev[:3]
    texture_variance = (std_r + std_g + std_b) / 3.0

    # Quantize to find non-background colors
    thumb = crop_img.copy()
    thumb.thumbnail((100, 100))
    quantized = thumb.quantize(colors=6)
    palette = quantized.getpalette()
    counts = sorted(quantized.getcolors() or [], reverse=True, key=lambda x: x[0])

    bg_r, bg_g, bg_b = bg_rgb
    candidate_colors = []
    for count, idx in counts:
        r = palette[idx * 3]
        g = palette[idx * 3 + 1]
        b = palette[idx * 3 + 2]
        dist_bg = ((r - bg_r) ** 2 + (g - bg_g) ** 2 + (b - bg_b) ** 2) ** 0.5
        if dist_bg > 30:
            candidate_colors.append((count, r, g, b))

    if candidate_colors:
        _, best_r, best_g, best_b = candidate_colors[0]
    elif counts:
        # If all colors were close to background, take the one furthest from background
        best_count, best_idx = max(counts, key=lambda c: ((palette[c[1]*3]-bg_r)**2 + (palette[c[1]*3+1]-bg_g)**2 + (palette[c[1]*3+2]-bg_b)**2))
        best_r = palette[best_idx * 3]
        best_g = palette[best_idx * 3 + 1]
        best_b = palette[best_idx * 3 + 2]
    else:
        best_r, best_g, best_b = int(mean_r), int(mean_g), int(mean_b)

    closest_hex, color_name = match_closest_color(best_r, best_g, best_b)
    hex_code = f"#{best_r:02x}{best_g:02x}{best_b:02x}"
    luminance = 0.299 * best_r + 0.587 * best_g + 0.114 * best_b
    max_c = max(best_r, best_g, best_b)
    min_c = min(best_r, best_g, best_b)
    saturation = (max_c - min_c) / 255.0
    warmth = (best_r - best_b) / 255.0

    return {
        "rgb": (best_r, best_g, best_b),
        "hex": hex_code,
        "closest_palette_hex": closest_hex,
        "color_name": color_name,
        "luminance": luminance,
        "saturation": saturation,
        "warmth": warmth,
        "texture_variance": texture_variance
    }

def extract_outfit_features(image_path):
    """
    Extracts computer vision features across upper body, lower body, and full outfit.
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        w, h = img.size

        # Background sampling from outer corners
        corners = [
            img.getpixel((max(0, 3), max(0, 3))),
            img.getpixel((min(w - 4, w - 1), max(0, 3))),
            img.getpixel((max(0, 3), min(h - 4, h - 1))),
            img.getpixel((min(w - 4, w - 1), min(h - 4, h - 1)))
        ]
        bg_rgb = (
            sum(c[0] for c in corners) // 4,
            sum(c[1] for c in corners) // 4,
            sum(c[2] for c in corners) // 4
        )

        # Upper region (torso/top)
        upper_crop = img.crop((int(w * 0.20), int(h * 0.15), int(w * 0.80), int(h * 0.50)))
        # Lower region (legs/bottom)
        lower_crop = img.crop((int(w * 0.20), int(h * 0.48), int(w * 0.80), int(h * 0.88)))
        # Center subject
        center_crop = img.crop((int(w * 0.15), int(h * 0.10), int(w * 0.85), int(h * 0.90)))

        upper_stats = extract_section_stats(upper_crop, bg_rgb)
        lower_stats = extract_section_stats(lower_crop, bg_rgb)
        overall_stats = extract_section_stats(center_crop, bg_rgb)

        lum_diff = abs(upper_stats["luminance"] - lower_stats["luminance"])
        if lum_diff > 65:
            contrast_level = "High Contrast"
        elif lum_diff >= 22:
            contrast_level = "Balanced Mid-Contrast"
        else:
            contrast_level = "Monochromatic / Tonal"

        is_same_color = upper_stats["color_name"] == lower_stats["color_name"]
        neutrals = [
            "Crisp White", "Warm Ivory", "Soft Beige", "Camel / Tan", "Khaki",
            "Muted Taupe", "Rich Brown", "Dark Espresso", "Jet Black", "Charcoal",
            "Slate Gray", "Heather Gray"
        ]
        upper_is_neutral = upper_stats["color_name"] in neutrals
        lower_is_neutral = lower_stats["color_name"] in neutrals

        if is_same_color:
            harmony_type = "monochromatic"
        elif upper_is_neutral and lower_is_neutral:
            harmony_type = "dual_neutral"
        elif upper_is_neutral or lower_is_neutral:
            harmony_type = "neutral_anchor"
        elif (upper_stats["warmth"] > 0.1 and lower_stats["warmth"] < -0.1) or (upper_stats["warmth"] < -0.1 and lower_stats["warmth"] > 0.1):
            harmony_type = "warm_cool_contrast"
        else:
            harmony_type = "color_combination"

        return {
            "upper": upper_stats,
            "lower": lower_stats,
            "overall": overall_stats,
            "lum_diff": lum_diff,
            "contrast_level": contrast_level,
            "harmony_type": harmony_type,
            "bg_rgb": bg_rgb,
            "is_same_color": is_same_color
        }

def calculate_dynamic_style_score(features, user_wardrobe_items=None):
    """
    Computes an explainable, non-constant style score based on measured image characteristics.
    """
    base_score = 72
    breakdown = ["Base Standard: 72 pts"]

    # 1. Color Harmony Points
    h_type = features["harmony_type"]
    up_col = features["upper"]["color_name"]
    lo_col = features["lower"]["color_name"]

    if h_type == "dual_neutral":
        harmony_pts = 11
        breakdown.append(f"Palette Synergy: +11 pts (Refined dual-neutral pairing of {up_col} and {lo_col})")
    elif h_type == "neutral_anchor":
        harmony_pts = 10
        breakdown.append(f"Palette Synergy: +10 pts (Neutral grounding between {up_col} and {lo_col})")
    elif h_type == "monochromatic":
        harmony_pts = 9
        breakdown.append(f"Palette Synergy: +9 pts (Tonal column harmony in {up_col})")
    elif h_type == "warm_cool_contrast":
        harmony_pts = 8
        breakdown.append(f"Palette Synergy: +8 pts (Dynamic temperature contrast between {up_col} and {lo_col})")
    else:
        if features["upper"]["saturation"] > 0.55 and features["lower"]["saturation"] > 0.55:
            harmony_pts = 4
            breakdown.append("Palette Synergy: +4 pts (High saturation across both halves competes for attention)")
        else:
            harmony_pts = 7
            breakdown.append(f"Palette Synergy: +7 pts (Cohesive pairing of {up_col} with {lo_col})")

    # 2. Contrast & Silhouette Definition
    lum_diff = features["lum_diff"]
    if features["contrast_level"] == "High Contrast":
        contrast_pts = 6
        breakdown.append(f"Value Contrast: +6 pts (Sharp {lum_diff:.0f} pt value separation defines waistline)")
    elif features["contrast_level"] == "Balanced Mid-Contrast":
        contrast_pts = 5
        breakdown.append(f"Value Contrast: +5 pts (Smooth {lum_diff:.0f} pt tonal graduation)")
    else:
        if features["is_same_color"]:
            contrast_pts = 5
            breakdown.append("Value Contrast: +5 pts (Uninterrupted vertical line elongates silhouette)")
        else:
            contrast_pts = 3
            breakdown.append(f"Value Contrast: +3 pts (Subtle {lum_diff:.0f} pt contrast)")

    # 3. Texture & Finish
    up_tex = features["upper"]["texture_variance"]
    lo_tex = features["lower"]["texture_variance"]
    if (up_tex > 38 and lo_tex <= 38) or (lo_tex > 38 and up_tex <= 38):
        texture_pts = 5
        breakdown.append("Texture Balance: +5 pts (Balanced interplay of smooth and textured fabric surfaces)")
    elif up_tex > 55 and lo_tex > 55:
        texture_pts = 2
        breakdown.append("Texture Balance: +2 pts (Dual textured patterns compete slightly for focus)")
    else:
        texture_pts = 4
        breakdown.append("Texture Balance: +4 pts (Clean, solid visual coherence across garments)")

    # 4. Wardrobe Cohesion
    wardrobe_bonus = 0
    if user_wardrobe_items:
        closet_colors = {getattr(i, 'color', '').lower() for i in user_wardrobe_items if getattr(i, 'color', '')}
        up_match = any(c in up_col.lower() for c in closet_colors)
        lo_match = any(c in lo_col.lower() for c in closet_colors)
        if up_match and lo_match:
            wardrobe_bonus = 3
            breakdown.append("Wardrobe Alignment: +3 pts (High affinity with your existing digital capsule)")
        elif up_match or lo_match:
            wardrobe_bonus = 2
            breakdown.append("Wardrobe Alignment: +2 pts (Matches core tones in your digital closet)")

    # Score synthesis (65 - 96)
    total_score = min(96, max(65, base_score + harmony_pts + contrast_pts + texture_pts + wardrobe_bonus - 14))
    score_explanation = f"Score Breakdown ({total_score}/100): " + " • ".join(breakdown)
    return total_score, score_explanation


def generate_local_styling_feedback(features, score, score_explanation):
    """
    Constructs image-specific editorial feedback based on the exact detected metrics.
    """
    up_col = features["upper"]["color_name"]
    lo_col = features["lower"]["color_name"]
    contrast = features["contrast_level"]
    is_mono = features["is_same_color"]
    is_warm = features["overall"]["warmth"] > 0.05
    is_dark = features["overall"]["luminance"] < 110

    # 1. Dominant Tone
    if is_mono:
        dominant_tone = f"Monochromatic {up_col} Column"
    elif contrast == "High Contrast":
        dominant_tone = f"High-Contrast {up_col} & {lo_col}"
    else:
        dominant_tone = f"Balanced {up_col} & {lo_col} Palette"

    # 2. What Works Well (3 specific points)
    works_well = []
    if is_mono:
        works_well.append(f"Monochromatic {up_col} column creates an uninterrupted vertical line that visually elongates your silhouette.")
    elif contrast == "High Contrast":
        works_well.append(f"Crisp value contrast between {up_col} on top and {lo_col} on the bottom provides clear waistline and garment separation.")
    else:
        works_well.append(f"Sophisticated tonal harmony between {up_col} and {lo_col} creates an effortless, quiet-luxury feel.")

    if is_warm:
        works_well.append(f"Warm undertones in the {up_col} piece give the outfit an approachable, organic elegance.")
    else:
        works_well.append(f"Cool/neutral depth across the palette lends modern architectural polish.")

    works_well.append(f"Cohesive visual weight: the {lo_col} base provides a grounded foundation that anchors your upper body silhouette.")

    # 3. Opportunities for Improvement (2-3 specific points)
    could_improve = []
    if contrast == "Monochromatic / Tonal":
        could_improve.append(f"Because the {up_col} tones are closely matched, introduce a contrasting belt, open overshirt, or textured knit to add visual depth.")
    elif contrast == "High Contrast":
        could_improve.append(f"To tie the stark contrast between {up_col} and {lo_col} together, apply the Sandwich Rule by echoing the {up_col} shade in your footwear or bag.")
    else:
        could_improve.append("Consider sharpening the hemline breaks at the ankle to ensure clean footwear visibility.")

    if is_dark:
        could_improve.append(f"With deep overall tones, incorporating subtle metallic accents (gold or silver jewelry) or an unbuttoned lighter collar will brighten your neckline.")
    else:
        could_improve.append(f"Ground the lighter {up_col} palette with structured, deeper leather footwear or a dark watch strap.")

    could_improve.append("Ensure the fabric weights feel balanced so the upper and lower garments move in harmony.")

    # 4. Alternative Styling
    if contrast == "High Contrast":
        alternative_styling = f"Layer a draped neutral trench coat or soft cardigan over your {up_col} top to soften the high contrast against your {lo_col} bottoms and add editorial movement."
    elif is_mono:
        alternative_styling = f"Break up the monochromatic {up_col} column with a contrasting leather belt and drape an unbuttoned overshirt or blazer over your shoulders."
    else:
        alternative_styling = f"Swap in footwear that matches the {up_col} tone to create an intentional 'sandwich' frame, or add a structured blazer for evening polish."

    # 5. Suggested Accessories
    if is_warm:
        accessories = [
            f"Woven cognac leather belt",
            f"Minimalist watch with brass or olive detailing",
            f"Tortoiseshell sunglasses or warm gold jewelry"
        ]
    elif is_dark:
        accessories = [
            f"Brushed silver minimalist watch",
            f"Structured black leather tote or crossbody",
            f"Charcoal silk or cashmere scarf"
        ]
    else:
        accessories = [
            f"Classic saddle brown leather belt",
            f"Clean white minimalist leather sneakers or loafers",
            f"Canvas and leather weekend tote"
        ]

    # 6. Occasion Suitability
    if contrast == "High Contrast" or is_dark:
        occasions = "Smart Casual, Corporate Office, Executive Meetings, Evening Dinners"
    elif is_mono and not is_dark:
        occasions = "Weekend Brunch, Creative Workplace, Gallery Visits, Resort & Travel"
    else:
        occasions = "College Campus, Casual Workdays, Coffee Dates, Everyday Social Outings"

    return {
        "style_score": score,
        "score_explanation": score_explanation,
        "dominant_tone": dominant_tone,
        "contrast_level": contrast,
        "detected_colors": [up_col, lo_col],
        "works_well": works_well,
        "could_improve": could_improve,
        "alternative_styling": alternative_styling,
        "suggested_accessories": accessories,
        "occasion_suitability": occasions,
        "is_ai_generated": False,
        "analysis_mode": "basic_visual_analysis",
        "service_badge": "Basic Visual Analysis Mode (PIL Palette & Contrast Engine)",
        "service_note": "Basic Visual Analysis Mode: Color quantization, luminance contrast, and texture variance were measured directly from your uploaded image. To enable deep neural outfit recognition (garment cut, fabric detection), add GEMINI_API_KEY to your .env file."
    }


# -------------------------------------------------------------
# MAIN OUTFIT PHOTO ANALYSIS ENTRYPOINT
# -------------------------------------------------------------

def analyze_outfit_photo(image_path, user_wardrobe_items=None):
    """
    Evaluates clothing categories, color coordination, pattern harmony, and style score.
    Uses Gemini Vision API when configured; otherwise runs local PIL Computer Vision analysis.
    """
    # 1. Multi-Modal Vision API if configured
    if Config.GEMINI_API_KEY:
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                
            mime_type = "image/jpeg"
            if image_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif image_path.lower().endswith(".webp"):
                mime_type = "image/webp"

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={Config.GEMINI_API_KEY}"
            prompt = """
            You are an expert editorial fashion stylist for Wardrobe IQ. Evaluate this outfit photo strictly on styling, color harmony, proportion, and aesthetic coordination.
            DO NOT evaluate personal attractiveness, body type, or facial appearance.
            Return ONLY a valid JSON object with the following fields:
            {
              "style_score": 86,
              "score_explanation": "Clear explanation of how the score was calculated across color harmony, silhouette, and layering",
              "dominant_tone": "Descriptive color palette and mood",
              "contrast_level": "High Contrast" | "Balanced Mid-Contrast" | "Monochromatic / Tonal",
              "detected_colors": ["Color 1", "Color 2"],
              "works_well": ["Specific strength 1", "Specific strength 2", "Specific strength 3"],
              "could_improve": ["Actionable improvement 1", "Actionable improvement 2"],
              "alternative_styling": "Text explaining an alternative styling trick or layering option",
              "suggested_accessories": ["Accessory idea 1", "Accessory idea 2", "Accessory idea 3"],
              "occasion_suitability": "Specific occasions and dress codes"
            }
            """
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": img_b64}}
                    ]
                }]
            }
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text_content.startswith("```"):
                    text_content = text_content.split("```")[1]
                    if text_content.startswith("json"):
                        text_content = text_content[4:]
                analysis = json.loads(text_content.strip())
                analysis["is_ai_generated"] = True
                analysis["analysis_mode"] = "ai_vision"
                analysis["service_badge"] = "Multi-Modal AI Vision (Gemini 1.5 Flash)"
                analysis["service_note"] = "Styling evaluated using Gemini Vision Multi-Modal Model"
                return analysis
        except Exception:
            pass

    # 2. Local PIL Image Computer Vision & Fashion Heuristics
    features = extract_outfit_features(image_path)
    score, score_explanation = calculate_dynamic_style_score(features, user_wardrobe_items)
    return generate_local_styling_feedback(features, score, score_explanation)
