import json
from datetime import date, datetime, timedelta
from app.models import WardrobeItem, WornHistory, UserPreference

COMPATIBLE_COLOR_PAIRS = {
    "White": ["Navy Blue", "Olive Green", "Charcoal", "Deep Forest Green", "Muted Taupe", "Soft Beige", "Black"],
    "Warm Ivory": ["Deep Forest Green", "Olive Green", "Charcoal", "Soft Beige", "Muted Taupe", "Navy Blue", "Espresso Brown"],
    "Soft Beige": ["Deep Forest Green", "White", "Navy Blue", "Muted Taupe", "Charcoal", "Olive Green"],
    "Deep Forest Green": ["Warm Ivory", "White", "Soft Beige", "Muted Taupe", "Camel / Tan", "Charcoal"],
    "Navy Blue": ["White", "Warm Ivory", "Soft Beige", "Muted Taupe", "Olive Green", "Charcoal", "Camel / Tan"],
    "Charcoal": ["White", "Warm Ivory", "Soft Beige", "Sage Green", "Muted Taupe", "Black", "Deep Forest Green"],
    "Olive Green": ["White", "Warm Ivory", "Soft Beige", "Charcoal", "Navy Blue", "Camel / Tan"],
    "Sage Green": ["White", "Warm Ivory", "Charcoal", "Soft Beige", "Deep Forest Green", "Muted Taupe"],
    "Muted Taupe": ["White", "Warm Ivory", "Deep Forest Green", "Charcoal", "Navy Blue", "Sage Green"],
    "Black": ["White", "Charcoal", "Warm Ivory", "Muted Taupe", "Soft Beige", "Sage Green", "Navy Blue"],
    "Espresso Brown": ["Warm Ivory", "Soft Beige", "Muted Taupe", "White", "Navy Blue", "Deep Forest Green"],
    "Camel / Tan": ["Navy Blue", "Deep Forest Green", "White", "Charcoal", "Soft Beige", "Warm Ivory"]
}

OCCASION_RULES = {
    "placement_interview": {
        "name": "Placement / Job Interview",
        "dress_code": "Business Formal",
        "description": "Formal corporate recruitment, campus placement, or technical interview.",
        "top_preferred": ["oxford shirt", "formal shirt", "dress shirt", "button-down", "blazer", "tailored blazer", "suit jacket"],
        "top_avoid": ["t-shirt", "tee", "crop", "graphic", "hoodie", "tank", "sweatshirt", "sweater", "knit", "cardigan"],
        "bottom_preferred": ["trouser", "formal trousers", "dress pants", "wool trousers", "pleated", "tailored chinos", "chinos"],
        "bottom_avoid": ["jeans", "denim", "shorts", "sweatpants", "joggers", "cargo", "distressed"],
        "shoe_preferred": ["loafer", "oxford", "brogue", "dress shoe", "leather shoe", "monk", "derby"],
        "shoe_avoid": ["sneaker", "running", "sandal", "flip-flop", "slipper", "canvas"],
        "acc_preferred": ["watch", "belt", "leather", "minimalist"],
        "target_style": "Formal"
    },
    "presentation": {
        "name": "Presentation / Conference",
        "dress_code": "Smart Formal / Business Casual",
        "description": "Seminar presentation, project defense, conference, or client pitch.",
        "top_preferred": ["blazer", "oxford shirt", "button-down", "knit sweater", "shirt", "merino"],
        "top_avoid": ["graphic", "tank", "hoodie", "distressed"],
        "bottom_preferred": ["chinos", "trousers", "tailored", "dark raw denim", "wool"],
        "bottom_avoid": ["sweatpants", "shorts", "gym"],
        "shoe_preferred": ["loafer", "chelsea boot", "derby", "oxford", "leather low"],
        "shoe_avoid": ["running", "flip-flop", "sandal"],
        "acc_preferred": ["watch", "belt", "tote"],
        "target_style": "Smart Casual"
    },
    "college": {
        "name": "College / Campus",
        "dress_code": "Casual / Smart Casual",
        "description": "Campus lectures, laboratory sessions, study groups, and library days.",
        "top_preferred": ["tee", "t-shirt", "linen tee", "oxford shirt", "polo", "sweater", "knit", "casual shirt"],
        "top_avoid": ["tuxedo", "suit jacket"],
        "bottom_preferred": ["chinos", "jeans", "denim", "casual pants", "cotton"],
        "bottom_avoid": ["tuxedo trousers"],
        "shoe_preferred": ["sneaker", "chelsea boot", "leather lows", "casual loafer"],
        "shoe_avoid": ["formal patent"],
        "acc_preferred": ["tote", "bag", "backpack", "watch"],
        "target_style": "Casual"
    },
    "casual": {
        "name": "Casual Outing / Weekend",
        "dress_code": "Relaxed Casual",
        "description": "Brunch, coffee meetup, weekend errands, and relaxed downtime.",
        "top_preferred": ["tee", "t-shirt", "linen", "polo", "shirt", "sweater"],
        "top_avoid": ["blazer", "suit"],
        "bottom_preferred": ["jeans", "denim", "chinos", "shorts", "relaxed trousers"],
        "bottom_avoid": ["formal wool trousers"],
        "shoe_preferred": ["sneaker", "boot", "slip-on", "casual", "loafer"],
        "shoe_avoid": ["formal oxford"],
        "acc_preferred": ["watch", "tote", "belt"],
        "target_style": "Casual"
    },
    "party": {
        "name": "Party / Evening Celebration",
        "dress_code": "Chic / Cocktail / Evening Glam",
        "description": "Social gathering, evening dinner date, cocktail event, or celebration.",
        "top_preferred": ["slip dress", "silk", "blazer", "dark shirt", "satin", "merino knit", "tailored"],
        "top_avoid": ["gym", "hoodie", "faded tee"],
        "bottom_preferred": ["tailored trousers", "dark denim", "chinos", "wool trousers"],
        "bottom_avoid": ["sweatpants", "cargo shorts"],
        "shoe_preferred": ["loafer", "chelsea boot", "dress shoe", "leather shoe", "heels"],
        "shoe_avoid": ["running sneakers", "flip-flops"],
        "acc_preferred": ["watch", "belt", "necklace"],
        "target_style": "Elegant"
    },
    "wedding": {
        "name": "Wedding / Reception",
        "dress_code": "Festive / Elegant Formal",
        "description": "Traditional wedding ceremony, banquet reception, or festive sangeet.",
        "top_preferred": ["kurta", "sherwani", "silk", "blazer", "formal suit", "festive dress", "shirt dress"],
        "top_avoid": ["t-shirt", "casual tee", "faded jeans"],
        "bottom_preferred": ["churidar", "dhoti", "trousers", "silk trousers", "wool trousers"],
        "bottom_avoid": ["denim", "jeans", "shorts"],
        "shoe_preferred": ["jutti", "moj", "loafer", "dress shoe", "leather loafers"],
        "shoe_avoid": ["sneaker", "athletic", "running"],
        "acc_preferred": ["watch", "belt", "stole"],
        "target_style": "Formal"
    },
    "festival": {
        "name": "Festival / Cultural Celebration",
        "dress_code": "Traditional / Festive",
        "description": "Cultural festival, puja, ethnic celebration, or holiday gathering.",
        "top_preferred": ["kurta", "ethnic", "nehru", "traditional", "silk dress", "festive"],
        "top_avoid": ["graphic tee", "athletic", "gym"],
        "bottom_preferred": ["churidar", "dhoti", "pyjama", "trousers", "linen pants"],
        "bottom_avoid": ["shorts", "track pants"],
        "shoe_preferred": ["jutti", "moj", "loafer", "leather sandal"],
        "shoe_avoid": ["running", "gym sneakers"],
        "acc_preferred": ["watch", "stole"],
        "target_style": "Traditional"
    },
    "travel": {
        "name": "Travel / Transit",
        "dress_code": "Comfortable Layered Casual",
        "description": "Airport transit, train journey, road trip, or destination walking.",
        "top_preferred": ["tee", "t-shirt", "sweater", "cardigan", "linen shirt", "merino"],
        "top_avoid": ["stiff formal suit", "dry-clean only heavy"],
        "bottom_preferred": ["stretch chinos", "relaxed jeans", "joggers", "breathable", "chinos"],
        "bottom_avoid": ["tight wool trousers"],
        "shoe_preferred": ["sneaker", "slip-on", "walking shoe", "chelsea boot"],
        "shoe_avoid": ["stiff heels", "pinch dress shoes"],
        "acc_preferred": ["tote", "bag", "weekender", "watch"],
        "target_style": "Casual"
    }
}

def get_item_display_name(item):
    """Formats clean, elegant display names, normalizing generic placeholders."""
    if not item:
        return ""
    name = (item.name or "").strip()
    if not name or "wardrobe piece" in name.lower():
        color_str = (item.color or "").title()
        subcat = (item.subcategory or item.category or "Piece").title()
        return f"{color_str} {subcat}".strip()
    return name

def parse_prompt_preferences(prompt):
    """
    Extracts styling intent, occasion key, outfit type, and weather conditions from prompt.
    """
    p = prompt.lower()
    occasion_key = "casual"
    outfit_type = "any"
    weather = "all"

    # 1. Weather Intent
    if any(k in p for k in ["rain", "rainy", "monsoon", "wet", "shower", "umbrella"]):
        weather = "rainy"
    elif any(k in p for k in ["hot", "summer", "sunny", "warm", "humid", "heat"]):
        weather = "hot"
    elif any(k in p for k in ["cold", "winter", "chilly", "freezing", "snow", "sweater weather", "cool"]):
        weather = "cold"
    elif any(k in p for k in ["mild", "spring", "breezy", "autumn", "fall"]):
        weather = "mild"

    # 2. Occasion Intent
    if any(k in p for k in ["interview", "placement", "job interview", "campus interview", "recruitment", "hiring"]):
        occasion_key = "placement_interview"
    elif any(k in p for k in ["presentation", "conference", "seminar", "defense", "defend", "pitch", "board meeting", "speech"]):
        occasion_key = "presentation"
    elif any(k in p for k in ["wedding", "marriage", "reception", "sangeet", "shaadi", "nikah", "ceremony"]):
        occasion_key = "wedding"
    elif any(k in p for k in ["festival", "festive", "diwali", "eid", "puja", "holi", "navratri", "ethnic", "traditional"]):
        occasion_key = "festival"
    elif any(k in p for k in ["party", "night out", "club", "cocktail", "dinner date", "drinks", "celebration", "evening"]):
        occasion_key = "party"
    elif any(k in p for k in ["college", "campus", "class", "lecture", "university", "school", "library", "exam"]):
        occasion_key = "college"
    elif any(k in p for k in ["travel", "flight", "trip", "airport", "vacation", "journey", "transit", "road trip"]):
        occasion_key = "travel"
    elif any(k in p for k in ["casual", "brunch", "day out", "weekend", "coffee", "hangout", "relax", "chill", "errand"]):
        occasion_key = "casual"

    # 3. Outfit type preference
    if any(k in p for k in ["dress", "one-piece", "jumpsuit"]):
        outfit_type = "dress"
    elif any(k in p for k in ["shirt", "t-shirt", "tee", "top", "pant", "trousers", "chinos", "jeans"]):
        outfit_type = "top_bottom"

    rule = OCCASION_RULES.get(occasion_key, OCCASION_RULES["casual"])
    return occasion_key, rule["name"], rule["target_style"], outfit_type, weather

def score_item_for_occasion(item, occasion_key, target_style):
    """
    Evaluates individual garment dress code suitability (0 to 35 points scale).
    """
    if not item:
        return 20.0
    rule = OCCASION_RULES.get(occasion_key, OCCASION_RULES["casual"])
    item_text = f"{item.name} {item.category} {item.subcategory or ''} {item.style or ''} {item.occasions or ''} {item.fabric or ''}".lower()

    score = 22.0 # Baseline suitability

    pref_kw = []
    avoid_kw = []
    if item.category in ["Tops", "Dresses / One-piece"]:
        pref_kw = rule.get("top_preferred", [])
        avoid_kw = rule.get("top_avoid", [])
    elif item.category == "Bottoms":
        pref_kw = rule.get("bottom_preferred", [])
        avoid_kw = rule.get("bottom_avoid", [])
    elif item.category == "Footwear":
        pref_kw = rule.get("shoe_preferred", [])
        avoid_kw = rule.get("shoe_avoid", [])
    elif item.category == "Accessories":
        pref_kw = rule.get("acc_preferred", [])
        avoid_kw = []

    # Preferred keyword boost
    for kw in pref_kw:
        if kw in item_text:
            score += 9.0
            break

    # Avoid penalty
    for kw in avoid_kw:
        if kw in item_text:
            score -= 14.0
            break

    # Style matching
    item_style = (item.style or "").lower()
    if rule["dress_code"].lower() in item_style or item_style in rule["dress_code"].lower():
        score += 3.5
    elif target_style.lower() in item_style:
        score += 2.5

    # Declared occasions match
    if any(w in (item.occasions or "").lower() for w in rule["name"].lower().split()):
        score += 2.0

    return max(2.0, min(35.0, score))

def score_weather_suitability(top_or_dress, bottom, footwear, weather):
    """
    Evaluates weather and seasonal appropriateness (0 to 15 points scale).
    """
    if weather == "all":
        return 13.0 # Balanced all-season baseline

    items = [i for i in [top_or_dress, bottom, footwear] if i]
    score = 10.0

    for itm in items:
        text = f"{itm.name} {itm.subcategory or ''} {itm.fabric or ''} {itm.season or ''} {itm.color or ''}".lower()
        if weather == "rainy":
            if any(k in text for k in ["boot", "leather", "dark", "navy", "charcoal", "black"]):
                score += 1.8
            if any(k in text for k in ["white pant", "sandals", "flip-flop", "suede"]):
                score -= 2.5
        elif weather == "hot":
            if any(k in text for k in ["linen", "cotton", "tee", "light", "white", "ivory", "beige", "summer"]):
                score += 1.8
            if any(k in text for k in ["wool", "knit", "sweater", "heavy", "leather jacket", "turtleneck"]):
                score -= 3.0
        elif weather == "cold":
            if any(k in text for k in ["wool", "knit", "sweater", "merino", "blazer", "boot", "winter"]):
                score += 1.8
            if any(k in text for k in ["linen tee", "shorts", "sleeveless", "tank"]):
                score -= 3.0
        elif weather == "mild":
            if any(k in text for k in ["chinos", "oxford", "cardigan", "all-season", "knit"]):
                score += 1.5

    return max(4.0, min(15.0, round(score, 1)))

def score_color_harmony(c1, c2, fav_colors=None):
    """
    Evaluates color coordination and tonal palette balance (0 to 25 points scale).
    """
    if not c1 or not c2:
        return 22.0

    c1_title = c1.title()
    c2_title = c2.title()

    c1_compat = COMPATIBLE_COLOR_PAIRS.get(c1_title, [])
    c2_compat = COMPATIBLE_COLOR_PAIRS.get(c2_title, [])

    score = 15.0 # Baseline neutral

    if c2_title in c1_compat or c1_title in c2_compat:
        score = 23.5 # Proven harmonious editorial pairing
    elif c1_title.lower() == c2_title.lower():
        score = 22.0 # Monochromatic harmony
    elif any(n in c1_title.lower() for n in ["white", "ivory", "beige", "black", "grey", "charcoal"]) and \
         any(n in c2_title.lower() for n in ["white", "ivory", "beige", "black", "grey", "charcoal"]):
        score = 20.5 # Neutral on neutral

    if fav_colors:
        if c1_title.lower() in fav_colors or c2_title.lower() in fav_colors:
            score = min(25.0, score + 1.5)

    return max(8.0, min(25.0, round(score, 1)))

def score_style_preference(top_or_dress, bottom, footwear, user_style_prefs, filter_style):
    """
    Evaluates aesthetic style alignment (0 to 15 points scale).
    """
    score = 10.0
    items = [i for i in [top_or_dress, bottom, footwear] if i]
    target = (filter_style or "").lower()

    for itm in items:
        style_val = (itm.style or "").lower()
        if target and target in style_val:
            score += 1.8
        elif any(p in style_val for p in user_style_prefs):
            score += 1.2

    return max(6.0, min(15.0, round(score, 1)))

def score_wardrobe_freshness(items, recent_wears_map):
    """
    Rewards items that have not been worn recently, cycling closet inventory (0 to 10 points scale).
    recent_wears_map: dict of item_id -> days_since_worn
    """
    score = 10.0
    for itm in items:
        if not itm:
            continue
        days = recent_wears_map.get(itm.id)
        if days is not None:
            if days <= 2:
                score -= 2.5
            elif days <= 5:
                score -= 1.2
            elif days <= 7:
                score -= 0.5
    return max(3.0, min(10.0, round(score, 1)))

def check_wardrobe_gaps(available_items, occasion_key):
    """
    Identifies specific wardrobe gaps when available items cannot fulfill the dress code.
    Prevents fabricating unavailable items and guides the user transparently.
    """
    gaps = []
    rule = OCCASION_RULES.get(occasion_key)
    if not rule:
        return gaps

    if occasion_key == "placement_interview":
        formal_tops = [i for i in available_items if i.category in ["Tops", "Dresses / One-piece"] and any(k in f"{i.name} {i.subcategory} {i.style}".lower() for k in ["oxford", "shirt", "blazer", "formal", "suit"])]
        if not formal_tops:
            gaps.append("Formal Shirt or Tailored Blazer (e.g., crisp white Oxford or navy/charcoal blazer)")

        formal_btms = [i for i in available_items if i.category == "Bottoms" and any(k in f"{i.name} {i.subcategory} {i.style}".lower() for k in ["trouser", "dress pant", "wool", "formal", "chinos", "pleated"])]
        if not formal_btms:
            gaps.append("Formal Dress Trousers or Pressed Chinos")

        formal_shoes = [i for i in available_items if i.category == "Footwear" and any(k in f"{i.name} {i.subcategory} {i.style}".lower() for k in ["loafer", "oxford", "brogue", "leather", "dress", "monk"])]
        if not formal_shoes:
            gaps.append("Formal Leather Dress Shoes or Loafers")

    elif occasion_key in ["wedding", "festival"]:
        ethnic_items = [i for i in available_items if any(k in f"{i.name} {i.subcategory} {i.style} {i.occasions}".lower() for k in ["kurta", "ethnic", "traditional", "sherwani", "festive", "silk", "anarkali", "saree"])]
        if not ethnic_items:
            gaps.append("Traditional / Festive Attire (e.g., Kurta, Festive Silk Dress, or Nehru Jacket)")

    elif occasion_key == "presentation":
        smart_tops = [i for i in available_items if i.category in ["Tops", "Dresses / One-piece"] and any(k in f"{i.name} {i.subcategory} {i.style}".lower() for k in ["blazer", "oxford", "shirt", "knit", "formal"])]
        if not smart_tops:
            gaps.append("Structured Presentation Layer (e.g., Tailored Blazer or Crisp Oxford Shirt)")

    return gaps

def build_styling_explanation(top_or_dress, bottom, footwear, accessory, occasion_key, score, weather="all"):
    """Generates an occasion-tailored rationale explaining why this specific combination works."""
    reasons = []

    top_title = get_item_display_name(top_or_dress)
    btm_title = get_item_display_name(bottom) if bottom else None
    shoe_title = get_item_display_name(footwear) if footwear else "selected footwear"

    c1 = top_or_dress.color
    c2 = bottom.color if bottom else None

    # 1. Color pairing explanation
    if c2:
        if c1.lower() == c2.lower():
            reasons.append(f"Monochromatic harmony anchored in refined {c1}.")
        elif c2.title() in COMPATIBLE_COLOR_PAIRS.get(c1.title(), []) or c1.title() in COMPATIBLE_COLOR_PAIRS.get(c2.title(), []):
            reasons.append(f"Clean tonal balance pairing {c1} with {c2}.")
        else:
            reasons.append(f"Modern contrast between {c1} and {c2}.")
    else:
        reasons.append(f"Refined one-piece silhouette centered in {c1}.")

    # 2. Occasion & Dress Code Rationale
    if occasion_key == "placement_interview":
        btm_phrase = f" and {btm_title}" if btm_title else ""
        reasons.append(f"Strictly meets corporate interview standards: {top_title}{btm_phrase} deliver structured poise, while {shoe_title} grounds the look in professional confidence.")
    elif occasion_key == "presentation":
        reasons.append(f"Authoritative tailoring: {top_title} creates clean, stage-ready visual lines paired with comfortable mobility.")
    elif occasion_key == "college":
        btm_phrase = f" with {btm_title}" if btm_title else ""
        reasons.append(f"Effortless campus versatility: {top_title}{btm_phrase} balances casual lecture comfort with intentional styling.")
    elif occasion_key == "wedding":
        reasons.append(f"Celebratory ceremonial grace: rich styling and elegant drape suited for wedding festivities.")
    elif occasion_key == "festival":
        reasons.append(f"Festive cultural resonance: refined ethnic aesthetic that honors traditional celebrations.")
    elif occasion_key == "party":
        reasons.append(f"Elevated evening charm: balanced textures and chic silhouette designed for social vibrancy.")
    elif occasion_key == "travel":
        reasons.append(f"Transit-ready comfort: breathable, versatile layers tailored for airport mobility and long hours.")
    else:
        reasons.append(f"Effortless off-duty pairing delivering relaxed comfort with smart silhouette control.")

    # 3. Weather context
    if weather == "rainy":
        reasons.append("Tonal depth and practical footwear selected for wet-weather resilience.")
    elif weather == "hot":
        reasons.append("Breathable fabrics and light palette maximize hot-weather airflow.")
    elif weather == "cold":
        reasons.append("Structured thermal layering keeps you warm without bulk.")

    if footwear and occasion_key != "placement_interview":
        reasons.append(f"{shoe_title} completes the ensemble.")

    return " ".join(reasons)

def generate_outfits(user_id, prompt="Suggest a look", filters=None, return_gaps=False):
    """
    Intelligent occasion-aware styling engine.
    Strictly uses user's available closet pieces, respects dress codes, prioritizes formal items for interviews,
    accounts for weather and user preferences, provides explainable multi-factor scoring, and selects
    2 to 3 distinct, high-quality combinations.
    """
    filters = filters or {}
    parsed_occ_key, def_occ_name, def_style, req_type, weather = parse_prompt_preferences(prompt)

    # Allow explicit filters to override prompt intent
    occ_key = parsed_occ_key
    if filters.get("occasion"):
        filt_occ = filters["occasion"].lower().strip()
        if filt_occ in OCCASION_RULES:
            occ_key = filt_occ
        elif "interview" in filt_occ or "placement" in filt_occ:
            occ_key = "placement_interview"
        elif "presentation" in filt_occ:
            occ_key = "presentation"
        elif "college" in filt_occ or "campus" in filt_occ:
            occ_key = "college"
        elif "wedding" in filt_occ:
            occ_key = "wedding"
        elif "festival" in filt_occ:
            occ_key = "festival"
        elif "travel" in filt_occ:
            occ_key = "travel"
        elif "evening" in filt_occ or "party" in filt_occ:
            occ_key = "party"
        elif "casual" in filt_occ:
            occ_key = "casual"

    req_style = filters.get("style") or def_style
    if filters.get("outfit_type"):
        req_type = filters["outfit_type"]

    rule = OCCASION_RULES.get(occ_key, OCCASION_RULES["casual"])

    # Load User Preferences & Worn History
    user_pref = UserPreference.query.filter_by(user_id=user_id).first()
    user_style_prefs = [s.strip().lower() for s in (user_pref.preferred_styles or "").split(",") if s.strip()] if user_pref else []
    fav_colors = [c.strip().lower() for c in (user_pref.favourite_colors or "").split(",") if c.strip()] if user_pref else []

    recent_wears = WornHistory.query.filter_by(user_id=user_id).order_by(WornHistory.date_worn.desc()).limit(30).all()
    today = date.today()
    recent_wears_map = {}
    for rw in recent_wears:
        days_ago = (today - rw.date_worn).days if rw.date_worn else 99
        item_ids = rw.item_ids
        for i_id in item_ids:
            if i_id not in recent_wears_map or days_ago < recent_wears_map[i_id]:
                recent_wears_map[i_id] = days_ago

    # Strictly fetch only items marked as 'Available'
    available_items = WardrobeItem.query.filter_by(
        user_id=user_id,
        availability_status="Available"
    ).all()

    # Identify wardrobe gaps
    wardrobe_gaps = check_wardrobe_gaps(available_items, occ_key)

    tops = [i for i in available_items if i.category == "Tops"]
    bottoms = [i for i in available_items if i.category == "Bottoms"]
    dresses = [i for i in available_items if i.category == "Dresses / One-piece"]
    shoes = [i for i in available_items if i.category == "Footwear"]
    accs = [i for i in available_items if i.category == "Accessories"]

    outfit_candidates = []

    # Rank individual items by occasion appropriateness
    scored_tops = sorted(tops, key=lambda t: score_item_for_occasion(t, occ_key, req_style), reverse=True)
    scored_bottoms = sorted(bottoms, key=lambda b: score_item_for_occasion(b, occ_key, req_style), reverse=True)
    scored_shoes = sorted(shoes, key=lambda s: score_item_for_occasion(s, occ_key, req_style), reverse=True)
    scored_dresses = sorted(dresses, key=lambda d: score_item_for_occasion(d, occ_key, req_style), reverse=True)
    scored_accs = sorted(accs, key=lambda a: score_item_for_occasion(a, occ_key, req_style), reverse=True)

    # Strategy 1: Top + Bottom combinations
    if req_type != "dress" and scored_tops and scored_bottoms:
        # Evaluate up to 5 tops and 5 bottoms
        for top in scored_tops[:5]:
            top_occ_score = score_item_for_occasion(top, occ_key, req_style)
            for btm in scored_bottoms[:5]:
                btm_occ_score = score_item_for_occasion(btm, occ_key, req_style)

                # Pair with best matching shoe for this specific pair
                best_shoe = None
                best_shoe_score = -1.0
                for sh in scored_shoes[:4]:
                    sh_occ = score_item_for_occasion(sh, occ_key, req_style)
                    sh_col = score_color_harmony(top.color, sh.color, fav_colors)
                    sh_total = (sh_occ * 0.6) + (sh_col * 0.4)
                    if sh_total > best_shoe_score:
                        best_shoe_score = sh_total
                        best_shoe = sh

                if not best_shoe and scored_shoes:
                    best_shoe = scored_shoes[0]

                best_acc = scored_accs[0] if scored_accs else None

                # Compute 5-factor explainable score:
                # 1. Occasion suitability (0 - 35)
                shoe_occ = score_item_for_occasion(best_shoe, occ_key, req_style) if best_shoe else 20.0
                occ_factor = (top_occ_score * 0.45) + (btm_occ_score * 0.35) + (shoe_occ * 0.20)

                # 2. Color harmony (0 - 25)
                color_factor = score_color_harmony(top.color, btm.color, fav_colors)

                # 3. Style preference alignment (0 - 15)
                style_factor = score_style_preference(top, btm, best_shoe, user_style_prefs, req_style)

                # 4. Weather appropriateness (0 - 15)
                weather_factor = score_weather_suitability(top, btm, best_shoe, weather)

                # 5. Wardrobe rotation bonus (0 - 10)
                rotation_factor = score_wardrobe_freshness([top, btm, best_shoe], recent_wears_map)

                composite_score = occ_factor + color_factor + style_factor + weather_factor + rotation_factor
                final_score = round(min(98.8, max(52.0, composite_score)), 1)

                top_dname = get_item_display_name(top)
                btm_dname = get_item_display_name(btm)
                why = build_styling_explanation(top, btm, best_shoe, best_acc, occ_key, final_score, weather)

                outfit_candidates.append({
                    "title": f"The {top.color.title()} & {btm.color.title()} Ensemble",
                    "occasion": rule["name"],
                    "style": rule["dress_code"],
                    "score": final_score,
                    "why": why,
                    "slots": {
                        "top": top,
                        "bottom": btm,
                        "dress": None,
                        "footwear": best_shoe,
                        "accessory": best_acc
                    },
                    "wardrobe_gaps": wardrobe_gaps
                })

    # Strategy 2: Dress / One-Piece combinations
    if (req_type in ["dress", "any"] or not outfit_candidates) and scored_dresses:
        for drs in scored_dresses[:4]:
            drs_occ = score_item_for_occasion(drs, occ_key, req_style)
            shoe = scored_shoes[0] if scored_shoes else None
            shoe_occ = score_item_for_occasion(shoe, occ_key, req_style) if shoe else 20.0
            acc = scored_accs[0] if scored_accs else None

            # 5-factor scoring for dress:
            occ_factor = (drs_occ * 0.70) + (shoe_occ * 0.30)
            color_factor = score_color_harmony(drs.color, shoe.color if shoe else None, fav_colors)
            style_factor = score_style_preference(drs, None, shoe, user_style_prefs, req_style)
            weather_factor = score_weather_suitability(drs, None, shoe, weather)
            rotation_factor = score_wardrobe_freshness([drs, shoe], recent_wears_map)

            composite_score = occ_factor + color_factor + style_factor + weather_factor + rotation_factor
            final_score = round(min(98.5, max(55.0, composite_score)), 1)

            drs_dname = get_item_display_name(drs)
            why = build_styling_explanation(drs, None, shoe, acc, occ_key, final_score, weather)

            outfit_candidates.append({
                "title": f"The {drs_dname} Statement",
                "occasion": rule["name"],
                "style": rule["dress_code"],
                "score": final_score,
                "why": why,
                "slots": {
                    "top": None,
                    "bottom": None,
                    "dress": drs,
                    "footwear": shoe,
                    "accessory": acc
                },
                "wardrobe_gaps": wardrobe_gaps
            })

    # Sort strictly descending by composite score
    outfit_candidates.sort(key=lambda x: x["score"], reverse=True)

    # Select 2 to 3 distinct combinations across pieces and silhouettes
    selected = []
    used_top_ids = set()
    used_bottom_ids = set()
    used_combos = set()

    # Pass 1: Select best overall combinations ensuring variety across tops/silhouettes
    for cand in outfit_candidates:
        top_id = cand["slots"]["top"].id if cand["slots"]["top"] else 0
        btm_id = cand["slots"]["bottom"].id if cand["slots"]["bottom"] else 0
        drs_id = cand["slots"]["dress"].id if cand["slots"]["dress"] else 0
        combo_key = (top_id, btm_id, drs_id)

        if combo_key in used_combos:
            continue

        # If we have multiple tops available, prefer distinct primary tops for looks 1, 2, 3
        if len(selected) > 0 and top_id and top_id in used_top_ids and len(tops) > len(selected):
            continue

        used_combos.add(combo_key)
        if top_id: used_top_ids.add(top_id)
        if btm_id: used_bottom_ids.add(btm_id)
        selected.append(cand)
        if len(selected) >= 3:
            break

    # Pass 2: If we still have fewer than 2-3 outfits, backfill with remaining best distinct combos
    if len(selected) < 3:
        for cand in outfit_candidates:
            combo_key = (
                cand["slots"]["top"].id if cand["slots"]["top"] else 0,
                cand["slots"]["bottom"].id if cand["slots"]["bottom"] else 0,
                cand["slots"]["dress"].id if cand["slots"]["dress"] else 0
            )
            if combo_key not in used_combos:
                used_combos.add(combo_key)
                selected.append(cand)
                if len(selected) >= 3:
                    break

    if return_gaps:
        return selected, wardrobe_gaps
    return selected
