from collections import Counter
import re
from app.models import WardrobeItem, WornHistory, UserPreference

WOMENS_KEYWORDS = {
    "dress", "dresses", "gown", "gowns", "frock", "frocks", "lehenga", "lehengas",
    "chudidar", "churidar", "saree", "sari", "saris", "skirt", "skirts", "blouse",
    "blouses", "crop top", "camisole", "slip dress", "heels", "pumps", "stiletto",
    "stilettos", "earrings", "earring", "anarkali", "kurti", "kurtis", "dupatta",
    "palazzo", "bra", "lingerie", "tights", "corset", "romper"
}

MENS_KEYWORDS = {
    "necktie", "tie", "ties", "bow tie", "cufflinks", "cufflink", "tuxedo",
    "kurta pajama", "dhoti", "boxer", "boxers", "sherwani", "waistcoat", "briefs"
}

def perform_wardrobe_gap_analysis(user_id):
    """
    Analyzes actual user wardrobe records to detect:
    - Gender / Department profile ('womens', 'mens', 'mixed', or 'ambiguous')
    - Underrepresented categories tailored to wardrobe orientation
    - Imbalances in style / formality
    - Seldom-worn items
    - Duplicate purchase risks
    """
    items = WardrobeItem.query.filter_by(user_id=user_id).all()
    wears = WornHistory.query.filter_by(user_id=user_id).all()
    pref = UserPreference.query.filter_by(user_id=user_id).first()

    total_items = len(items)

    # 1. Wardrobe Gender / Department Classification
    womens_count = 0
    mens_count = 0

    for i in items:
        text = f"{i.name} {i.subcategory or ''} {i.notes or ''}".lower()
        words = set(re.findall(r"\b[a-z'-]+\b", text))

        is_w = False
        is_m = False

        if i.category == "Dresses / One-piece":
            is_w = True
        elif words.intersection(WOMENS_KEYWORDS) or any(kw in text for kw in ["crop top", "slip dress", "bow tie"]):
            is_w = True

        if words.intersection(MENS_KEYWORDS):
            is_m = True

        if is_w and not is_m:
            womens_count += 1
        elif is_m and not is_w:
            mens_count += 1
        elif is_w and is_m:
            womens_count += 1
            mens_count += 1

    # Determine detected orientation
    if womens_count > 0 and mens_count == 0:
        detected = "womens"
        detected_label = "Women's / Girls'"
        is_mixed = False
        is_ambiguous = False
    elif mens_count > 0 and womens_count == 0:
        detected = "mens"
        detected_label = "Men's / Boys'"
        is_mixed = False
        is_ambiguous = False
    elif womens_count > 0 and mens_count > 0:
        detected = "mixed"
        detected_label = "Mixed Wardrobe (Women's & Men's)"
        is_mixed = True
        is_ambiguous = False
    else:
        detected = "unisex"
        detected_label = "Neutral / Unspecified"
        is_mixed = False
        is_ambiguous = True

    # Check wardrobe items first, fallback to user preference if ambiguous/empty
    saved_pref = (pref.gender_preference or "").strip().lower() if pref else ""
    if not is_ambiguous:
        effective_department = detected
        department_source = f"Auto-detected from {total_items} closet pieces"
    elif saved_pref in ["womens", "mens", "unisex", "mixed"]:
        effective_department = "all" if saved_pref == "mixed" else saved_pref
        department_source = "Saved Style Preference"
    else:
        effective_department = "unisex"
        department_source = "Neutral / Unspecified"

    if total_items == 0:
        return {
            "gaps": ["Your wardrobe is empty. Start by logging your foundational tops and bottoms."],
            "duplicates": [],
            "underrepresented": ["Tops", "Bottoms", "Footwear"],
            "rarely_worn": [],
            "versatility_ratio": 0.0,
            "detected_department": detected,
            "department_label": detected_label,
            "effective_department": effective_department,
            "department_source": department_source,
            "is_mixed": is_mixed,
            "is_ambiguous": True,
            "womens_score": 0,
            "mens_score": 0,
            "total_items": 0
        }

    cat_counts = Counter(i.category for i in items)

    # 2. Category gaps
    gaps = []
    underrepresented = []

    if cat_counts["Bottoms"] == 0:
        if effective_department == "womens":
            gaps.append("Missing Bottoms: You have no recorded bottoms. A versatile pair of tailored trousers, dark denim, or an A-line skirt would immediately unlock multiple complete looks.")
        else:
            gaps.append("Missing Bottoms: You have no recorded bottoms. A pair of tailored neutral chinos or dark denim would immediately unlock multiple complete looks.")
        underrepresented.append("Bottoms")
    elif cat_counts["Tops"] > 0 and (cat_counts["Tops"] / max(1, cat_counts["Bottoms"])) > 3.0:
        gaps.append(f"Top-to-Bottom Imbalance: You have {cat_counts['Tops']} tops for only {cat_counts['Bottoms']} bottoms. Investing in 1 versatile bottom will multiply your outfit combinations significantly.")
        underrepresented.append("Bottoms")

    if cat_counts["Footwear"] == 0:
        gaps.append("Grounded Anchor Needed: No footwear recorded in your closet. Logging your primary casual or smart shoes will complete your outfits.")
        underrepresented.append("Footwear")

    if cat_counts["Tops"] == 0 and cat_counts["Dresses / One-piece"] == 0:
        gaps.append("Foundational Tops Needed: No shirts or tops recorded yet.")
        underrepresented.append("Tops")

    if effective_department == "womens" and cat_counts["Dresses / One-piece"] == 0 and total_items >= 4:
        gaps.append("Effortless One-Piece: You have no dresses logged. Adding a classic slip or linen wrap dress provides an effortless single-garment ensemble.")
        underrepresented.append("Dresses / One-piece")

    if cat_counts["Accessories"] == 0 and total_items >= 4:
        gaps.append("Finishing Touches Needed: You have no accessories recorded. Adding a classic timepiece, belt, or everyday bag will elevate your outfits.")
        underrepresented.append("Accessories")

    # 3. Formality balance
    formal_count = sum(1 for i in items if i.style in ["Formal", "Smart Casual"])
    if total_items >= 4 and formal_count == 0:
        gaps.append("Formality Gap: Your collection is predominantly casual. Consider one structured blazer or tailored trousers for presentations or formal events.")

    # 4. Duplicate items detection (same category, color, and pattern)
    duplicates = []
    seen = {}
    for i in items:
        key = (i.category, i.color.lower(), i.pattern.lower())
        if key in seen:
            duplicates.append({
                "item_a": seen[key],
                "item_b": i,
                "reason": f"Both are {i.color} {i.category} in {i.pattern} pattern."
            })
        else:
            seen[key] = i

    # 5. Seldom or never worn items
    item_wears = Counter()
    for w in wears:
        for itm_id in w.item_ids:
            item_wears[itm_id] += 1

    rarely_worn = [i for i in items if item_wears[i.id] == 0 and len(wears) >= 2]

    return {
        "gaps": gaps if gaps else ["Your wardrobe has a healthy category balance."],
        "duplicates": duplicates,
        "underrepresented": underrepresented,
        "rarely_worn": rarely_worn[:4],
        "versatility_ratio": round((cat_counts['Tops'] * cat_counts['Bottoms']) / max(1, total_items), 1) if total_items > 0 else 0,
        "detected_department": detected,
        "department_label": detected_label,
        "effective_department": effective_department,
        "department_source": department_source,
        "is_mixed": is_mixed,
        "is_ambiguous": is_ambiguous,
        "womens_score": womens_count,
        "mens_score": mens_count,
        "total_items": total_items
    }
