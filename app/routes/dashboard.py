from collections import Counter
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import db, WardrobeItem, WornHistory, Outfit

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def home():
    if current_user.is_authenticated:
        return dashboard()
    return render_template("auth/login.html")

@dashboard_bp.route("/dashboard")
@login_required
def index():
    return dashboard()

def dashboard():
    user_id = current_user.id
    items = WardrobeItem.query.filter_by(user_id=user_id).all()
    worn_records = WornHistory.query.filter_by(user_id=user_id).order_by(WornHistory.date_worn.desc()).all()

    # 1. FOUR SUMMARY CARDS
    total_items = len(items)
    available_items = sum(1 for i in items if i.availability_status == "Available")
    
    # Wardrobe Value (sum of purchase prices with valid non-null prices)
    wardrobe_value = sum(i.purchase_price for i in items if i.purchase_price is not None)

    # Outfit Repetition Rate:
    # Defined as: (Count of confirmed worn outfits that repeat a combination previously worn) / (Total confirmed worn outfits) * 100
    total_wears = len(worn_records)
    if total_wears > 1:
        combos = []
        for w in worn_records:
            combo_key = tuple(sorted(w.item_ids))
            if combo_key:
                combos.append(combo_key)
        
        counts = Counter(combos)
        repeated_wear_count = sum(c - 1 for c in counts.values() if c > 1)
        repetition_rate = round((repeated_wear_count / total_wears) * 100, 1)
    else:
        repetition_rate = 0.0

    # 2. WARDROBE AT A GLANCE (Category counts)
    category_counts = {
        "Tops": sum(1 for i in items if i.category == "Tops"),
        "Bottoms": sum(1 for i in items if i.category == "Bottoms"),
        "Dresses / One-piece": sum(1 for i in items if i.category == "Dresses / One-piece"),
        "Footwear": sum(1 for i in items if i.category == "Footwear"),
        "Accessories": sum(1 for i in items if i.category == "Accessories")
    }

    # 3. COLOUR ANALYSIS
    color_counts = Counter(i.color for i in items if i.color)
    color_hexes = {i.color: i.color_hex for i in items if i.color and i.color_hex}
    
    color_distribution = []
    most_common_color = None
    least_common_color = None
    color_variety_observation = "Your closet holds a balanced spectrum."

    if total_items > 0 and color_counts:
        sorted_colors = color_counts.most_common()
        for col, count in sorted_colors:
            pct = round((count / total_items) * 100, 1)
            color_distribution.append({
                "name": col,
                "hex": color_hexes.get(col, "#8B806E"),
                "count": count,
                "percentage": pct
            })
            
        most_common_color = sorted_colors[0][0]
        least_common_color = sorted_colors[-1][0] if len(sorted_colors) > 1 else sorted_colors[0][0]
        
        # Variety observation
        if len(color_counts) == 1:
            color_variety_observation = f"Your wardrobe is completely monochromatic around {most_common_color}. Adding subtle contrast neutrals would expand pairing versatility."
        elif len(color_counts) <= 3:
            color_variety_observation = f"Strong focus on {most_common_color}. Great for a streamlined capsule wardrobe; consider neutral accents to link outfits."
        else:
            color_variety_observation = f"Healthy variety across {len(color_counts)} distinct shades. Strong tonal anchor in {most_common_color}."
    else:
        color_variety_observation = "No garments logged yet. Upload or curate items to reveal your personal color analysis."

    # 4. WARDROBE INTELLIGENCE & INSIGHTS (Real Data Driven)
    insights = []
    
    # Insight A: Laundry protection alert
    in_laundry = sum(1 for i in items if i.availability_status in ["In Laundry", "Worn / Needs Washing"])
    if in_laundry > 0:
        insights.append({
            "type": "care",
            "title": f"{in_laundry} Garment{'s' if in_laundry > 1 else ''} Currently Awaiting Wash",
            "detail": "These items are safely excluded from outfit generation and trip packing. Visit Laundry & Availability once clean.",
            "action_text": "Manage Laundry",
            "action_url": "/laundry"
        })

    # Insight B: Most worn item or unworn items
    item_wears = Counter()
    for w in worn_records:
        for item_id in w.item_ids:
            item_wears[item_id] += 1

    never_worn_items = [i for i in items if item_wears[i.id] == 0]
    most_worn_item_id = item_wears.most_common(1)[0][0] if item_wears else None
    
    if most_worn_item_id:
        most_worn = next((i for i in items if i.id == most_worn_item_id), None)
        if most_worn:
            insights.append({
                "type": "usage",
                "title": f"Wardrobe Anchor: '{most_worn.name}'",
                "detail": f"Worn {item_wears[most_worn.id]} times. This is your most versatile everyday foundation piece.",
                "action_text": "View Item",
                "action_url": f"/closet/item/{most_worn.id}"
            })

    if never_worn_items and total_wears >= 2:
        unworn_sample = never_worn_items[0]
        insights.append({
            "type": "opportunity",
            "title": f"Unexplored Piece: '{unworn_sample.name}'",
            "detail": f"You haven't logged a wear for this {unworn_sample.category.lower()} yet. Style it in Smart Outfit Studio for your next occasion.",
            "action_text": "Style This Piece",
            "action_url": "/outfit-studio"
        })

    # Insight C: Category Balance Gap
    if category_counts["Tops"] > 0 and category_counts["Bottoms"] == 0:
        insights.append({
            "type": "gap",
            "title": "Wardrobe Balance Gap: Bottoms Needed",
            "detail": f"You have {category_counts['Tops']} tops recorded but no bottoms. Adding versatile trousers or denim will unlock numerous complete outfits.",
            "action_text": "Explore Shopping Advice",
            "action_url": "/shopping"
        })
    elif category_counts["Tops"] >= 4 and category_counts["Bottoms"] >= 2:
        potential_combos = category_counts["Tops"] * category_counts["Bottoms"]
        insights.append({
            "type": "opportunity",
            "title": f"Up to {potential_combos} Combinations Possible",
            "detail": f"Between your {category_counts['Tops']} tops and {category_counts['Bottoms']} bottoms, you have extensive styling versatility without buying new items.",
            "action_text": "Generate Outfits",
            "action_url": "/outfit-studio"
        })

    # Fallback insight if empty or early stage
    if not insights:
        insights.append({
            "type": "guide",
            "title": "Welcome to Your Wardrobe Intelligence",
            "detail": "As you log confirmed outfits and organize your clothes, Wardrobe IQ will uncover your wear frequencies, cost per wear, and combination gaps here.",
            "action_text": "Explore Digital Closet",
            "action_url": "/closet"
        })

    return render_template(
        "dashboard/index.html",
        total_items=total_items,
        available_items=available_items,
        wardrobe_value=wardrobe_value,
        repetition_rate=repetition_rate,
        total_wears=total_wears,
        category_counts=category_counts,
        color_distribution=color_distribution,
        most_common_color=most_common_color,
        least_common_color=least_common_color,
        color_variety_observation=color_variety_observation,
        insights=insights[:3]
    )
