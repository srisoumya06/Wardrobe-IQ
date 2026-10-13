from datetime import datetime, date
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import WardrobeItem

trends_bp = Blueprint("trends", __name__)

TRENDS_DATA = [
    {
        "id": "quiet_luxury",
        "category": "Tailoring",
        "title": "Minimalist Tailoring & Quiet Luxury",
        "season": "Autumn / Winter 2026",
        "source": "Vogue Runway & WGSN Editorial",
        "source_url": "https://www.vogue.com/fashion-shows",
        "updated_at": "October 2026",
        "trending_colors": ["Warm Ivory", "Charcoal", "Soft Beige", "Espresso Brown"],
        "key_elements": ["Unstructured blazers", "Wide-leg trousers", "Tonal layering", "Minimal accessories"],
        "description": "A move towards timeless, unbranded elegance. Emphasis is placed on silhouette drape, neutral monochrome palettes, and tactile natural fibers like wool, cashmere, and combed cotton.",
        "image": "defaults/trend_quiet_luxury.jpg",
        "fallback_image": "defaults/top_charcoal_blazer.jpg"
    },
    {
        "id": "earthy_utilitarian",
        "category": "Casual",
        "title": "Earth-Toned Utilitarian & Modern Fieldwear",
        "season": "Spring / Autumn 2026",
        "source": "Pitti Uomo Trend Intelligence",
        "source_url": "https://uomo.pittimmagine.com",
        "updated_at": "October 2026",
        "trending_colors": ["Olive Green", "Deep Forest Green", "Camel / Tan", "Soft Beige"],
        "key_elements": ["Tailored chinos", "Field jackets", "Sturdy canvas totes", "Suede footwear"],
        "description": "Functional workwear refined for campus and city life. Combines organic military greens with soft beige accents for a grounded, intelligent everyday presence.",
        "image": "defaults/trend_utilitarian.jpg",
        "fallback_image": "defaults/bottom_chinos.jpg"
    },
    {
        "id": "collegiate_prep",
        "category": "Smart Casual",
        "title": "Modern Collegiate & Elevated Knitwear",
        "season": "Year-Round 2026",
        "source": "British Fashion Council Trend Index",
        "source_url": "https://www.britishfashioncouncil.co.uk",
        "updated_at": "October 2026",
        "trending_colors": ["White", "Navy Blue", "Deep Forest Green", "Muted Taupe"],
        "key_elements": ["Oxford button-downs", "Merino crewneck knits", "Clean white leather sneakers", "Minimalist watches"],
        "description": "Reinventing classic ivy style through relaxed proportions. Pairing structured collared shirts under loose crewneck sweaters with selvedge denim.",
        "image": "defaults/trend_collegiate.jpg",
        "fallback_image": "defaults/top_oxford_shirt.jpg"
    },
    {
        "id": "fluid_linen",
        "category": "Resort",
        "title": "Breeze & Flow: Resort Linen Silhouettes",
        "season": "Spring / Summer 2026",
        "source": "Milan Fashion Week Capsule Review",
        "source_url": "https://www.milanofashionweek.cameramoda.it",
        "updated_at": "October 2026",
        "trending_colors": ["Warm Ivory", "Sage Green", "Soft Beige"],
        "key_elements": ["Linen shirt dresses", "Slip midi skirts", "Slip-on loafers", "Woven leather belts"],
        "description": "Tactile breathing room and graceful drape. Emphasizes organic creases and neutral tones that look effortless in both casual and dinner settings.",
        "image": "defaults/trend_linen_resort.jpg",
        "fallback_image": "defaults/dress_linen.jpg"
    },
    {
        "id": "monochrome_minimalism",
        "category": "Evening",
        "title": "Architectural Monochrome Minimalism",
        "season": "Autumn / Winter 2026",
        "source": "Paris Fashion Week Trend Archive",
        "source_url": "https://fhcm.paris/en/paris-fashion-week",
        "updated_at": "October 2026",
        "trending_colors": ["Charcoal", "Black", "White", "Warm Ivory"],
        "key_elements": ["High-contrast silhouettes", "Sharp collars", "Wool coats", "Polished leather boots"],
        "description": "Precise geometric tailoring rooted in stark black and white contrasts. Modern minimalism with clean seams, concealed plackets, and uncompromising posture.",
        "image": "defaults/trend_monochrome_minimalism.jpg",
        "fallback_image": "defaults/top_charcoal_blazer.jpg"
    },
    {
        "id": "contemporary_heritage",
        "category": "Heritage",
        "title": "Contemporary Heritage & Artisanal Craft",
        "season": "Year-Round 2026",
        "source": "CFDA Trend Forecasting & Craft Council",
        "source_url": "https://cfda.com",
        "updated_at": "October 2026",
        "trending_colors": ["Deep Forest Green", "Camel / Tan", "Warm Ivory", "Espresso Brown"],
        "key_elements": ["Textured weaves", "Raw selvedge denim", "Saddle leather accessories", "Heritage knits"],
        "description": "Celebrating artisanal permanence over fast disposability. Classic heritage silhouettes recontextualized with modern relaxed drape and tactile rich textures.",
        "image": "defaults/trend_contemporary_heritage.jpg",
        "fallback_image": "defaults/acc_belt.jpg"
    }
]

@trends_bp.route("/trends")
@login_required
def index():
    user_id = current_user.id
    selected_trend_id = request.args.get("trend_id", TRENDS_DATA[0]["id"])
    category_filter = request.args.get("category", "")
    
    # Filter trends by category if requested, while keeping full collection
    filtered_trends = [t for t in TRENDS_DATA if t["category"] == category_filter] if category_filter else TRENDS_DATA
    
    # Select active trend
    selected_trend = next((t for t in TRENDS_DATA if t["id"] == selected_trend_id), TRENDS_DATA[0])

    # Feature: "Recreate This Trend With My Wardrobe"
    user_items = WardrobeItem.query.filter_by(
        user_id=user_id,
        availability_status="Available"
    ).all()

    # Find matching items in user's closet by matching colors or style
    matched_items = []
    for itm in user_items:
        color_match = any(c.lower() in itm.color.lower() or itm.color.lower() in c.lower() for c in selected_trend["trending_colors"])
        style_match = any(elem.lower() in itm.name.lower() or elem.lower() in (itm.subcategory or "").lower() or elem.lower() in itm.category.lower() for elem in selected_trend["key_elements"])
        if color_match or style_match:
            matched_items.append(itm)

    categories = sorted(list(set(t["category"] for t in TRENDS_DATA)))

    return render_template(
        "trends/index.html",
        trends=filtered_trends,
        all_trends=TRENDS_DATA,
        selected_trend=selected_trend,
        matched_items=matched_items[:6],
        categories=categories,
        active_category=category_filter
    )
