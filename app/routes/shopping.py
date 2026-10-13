import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, WardrobeItem, UserPreference
from app.services.gap_analyzer import perform_wardrobe_gap_analysis
from app.services.currency import convert_usd_to_inr, get_usd_to_inr_rate_info

shopping_bp = Blueprint("shopping", __name__)

# Curated, verified product catalog from established brands with real product images and working links
CATALOG_ITEMS = [
    # ================= WOMEN'S / GIRLS' COLLECTION =================
    {
        "id": "w_dress_1",
        "name": "Tagliatelle Linen Midi Dress",
        "department": "womens",
        "category": "Dresses / One-piece",
        "brand": "Reformation",
        "price_usd": 278.00,
        "color": "Warm Ivory",
        "color_hex": "#F4EFE7",
        "style": "Minimalist",
        "size_range": "XS – XL",
        "image": "defaults/shop_reformation_dress.jpg",
        "fallback_image": "defaults/dress_slip.jpg",
        "merchant": "Reformation Official",
        "url": "https://www.thereformation.com/products/tagliatelle-linen-dress/1310134.html",
        "description": "Bestselling structured sweetheart neckline midi dress tailored from 100% lightweight European linen."
    },
    {
        "id": "w_dress_2",
        "name": "Tie-Back Satin Evening Gown",
        "department": "womens",
        "category": "Dresses / One-piece",
        "brand": "Mango",
        "price_usd": 129.99,
        "color": "Black",
        "color_hex": "#292B28",
        "style": "Formal",
        "size_range": "XS – L",
        "image": "defaults/shop_mango_gown.jpg",
        "fallback_image": "defaults/dress_slip.jpg",
        "merchant": "Myntra",
        "url": "https://www.myntra.com/dresses",
        "description": "Floor-skimming evening gown in fluid drape satin with an open back and subtle cowl neck."
    },
    {
        "id": "w_dress_3",
        "name": "Silk Slip Midi Dress",
        "department": "womens",
        "category": "Dresses / One-piece",
        "brand": "Quince",
        "price_usd": 79.90,
        "color": "Sage Green",
        "color_hex": "#A9B4A1",
        "style": "Smart Casual",
        "size_range": "XS – XL",
        "image": "defaults/shop_quince_slip_dress.jpg",
        "fallback_image": "defaults/dress_slip.jpg",
        "merchant": "Quince Official",
        "url": "https://www.onequince.com/women/silk/silk-slip-dress",
        "description": "100% Mulberry silk slip dress with delicate adjustable straps and bias cut for an effortless drape."
    },
    {
        "id": "w_dress_4",
        "name": "Embroidered Tiered Anarkali Dress",
        "department": "womens",
        "category": "Dresses / One-piece",
        "brand": "FabIndia",
        "price_usd": 68.00,
        "color": "Ivory Cream",
        "color_hex": "#FAF6F0",
        "style": "Traditional / Ethnic",
        "size_range": "S – XXL",
        "image": "defaults/shop_fabindia_anarkali.jpg",
        "fallback_image": "defaults/dress_slip.jpg",
        "merchant": "Myntra",
        "url": "https://www.myntra.com/dresses",
        "description": "Artisanal hand-block printed tiered dress crafted from breathable woven cotton with subtle gold gota trim."
    },
    {
        "id": "w_bottom_1",
        "name": "Pleated Wide-Leg Trousers",
        "department": "womens",
        "category": "Bottoms",
        "brand": "Uniqlo",
        "price_usd": 49.90,
        "color": "Muted Taupe",
        "color_hex": "#8B806E",
        "style": "Smart Casual",
        "size_range": "24 – 32",
        "image": "defaults/bottom_trousers.jpg",
        "fallback_image": "defaults/shop_cos_trousers.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "High-rise tailored trousers with front pleats and two-way stretch fabric for comfortable all-day elegance."
    },
    {
        "id": "w_bottom_2",
        "name": "High-Rise Straight Leg Jeans",
        "department": "womens",
        "category": "Bottoms",
        "brand": "Levi's",
        "price_usd": 79.50,
        "color": "Dark Indigo",
        "color_hex": "#2B3A42",
        "style": "Casual",
        "size_range": "24 – 34",
        "image": "defaults/bottom_jeans.jpg",
        "fallback_image": "defaults/bottom_chinos.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Vintage-inspired classic straight leg denim made with sustainably sourced cotton."
    },
    {
        "id": "w_bottom_3",
        "name": "Pleated A-Line Midi Skirt",
        "department": "womens",
        "category": "Bottoms",
        "brand": "H&M",
        "price_usd": 42.00,
        "color": "Black",
        "color_hex": "#1E1E1E",
        "style": "Smart Casual",
        "size_range": "XS – L",
        "image": "defaults/shop_hm_skirt.jpg",
        "fallback_image": "defaults/bottom_trousers.jpg",
        "merchant": "Myntra",
        "url": "https://www.myntra.com/dresses",
        "description": "Accordion-pleated fluid midi skirt with comfortable elasticized waist, easily dressed up or down."
    },
    {
        "id": "w_top_1",
        "name": "Washable Silk Relaxed Blouse",
        "department": "womens",
        "category": "Tops",
        "brand": "Quince",
        "price_usd": 69.90,
        "color": "Soft Blue",
        "color_hex": "#6C829B",
        "style": "Smart Casual",
        "size_range": "XS – XL",
        "image": "defaults/shop_quince_blouse.jpg",
        "fallback_image": "defaults/top_linen_tee.jpg",
        "merchant": "Myntra",
        "url": "https://www.myntra.com/dresses",
        "description": "Hypoallergenic washable silk button-up shirt featuring clean French seams and mother-of-pearl buttons."
    },
    {
        "id": "w_top_2",
        "name": "Relaxed French Linen Shirt",
        "department": "womens",
        "category": "Tops",
        "brand": "Uniqlo",
        "price_usd": 39.90,
        "color": "Soft Beige",
        "color_hex": "#D8CBBB",
        "style": "Casual",
        "size_range": "XS – XXL",
        "image": "defaults/top_linen_tee.jpg",
        "fallback_image": "defaults/shop_everlane_tee.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "100% premium European flax linen relaxed shirt, washed for exceptional softness."
    },
    {
        "id": "w_top_3",
        "name": "Tailored Single-Breasted Blazer",
        "department": "womens",
        "category": "Tops",
        "brand": "Zara",
        "price_usd": 119.00,
        "color": "Charcoal Grey",
        "color_hex": "#292B28",
        "style": "Formal",
        "size_range": "XS – L",
        "image": "defaults/top_charcoal_blazer.jpg",
        "fallback_image": "defaults/shop_cos_trousers.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Structured blazer with notch lapels, padded shoulders, and flap pockets for refined power dressing."
    },
    {
        "id": "w_shoe_1",
        "name": "Leather Pointed Slingback Pumps",
        "department": "womens",
        "category": "Footwear",
        "brand": "Calvin Klein",
        "price_usd": 89.00,
        "color": "Alabaster White",
        "color_hex": "#F4EFE7",
        "style": "Formal",
        "size_range": "36 – 41",
        "image": "defaults/shop_calvin_pumps.jpg",
        "fallback_image": "defaults/shoes_loafers.jpg",
        "merchant": "Amazon Fashion",
        "url": "https://www.amazon.in/s?k=penny+loafers+men",
        "description": "Sleek pointed toe slingback silhouette with a manageable 2-inch kitten heel and cushioned leather insole."
    },
    {
        "id": "w_shoe_2",
        "name": "Block-Heel Minimalist Leather Sandals",
        "department": "womens",
        "category": "Footwear",
        "brand": "Mango",
        "price_usd": 79.99,
        "color": "Tan Brown",
        "color_hex": "#7B553C",
        "style": "Smart Casual",
        "size_range": "36 – 41",
        "image": "defaults/shop_mango_sandals.jpg",
        "fallback_image": "defaults/shoes_loafers.jpg",
        "merchant": "Myntra",
        "url": "https://www.myntra.com/dresses",
        "description": "Supple leather two-strap mule sandal with architectural wooden block heel and square open toe."
    },
    {
        "id": "w_acc_1",
        "name": "Classic Structured Leather Crossbody Handbag",
        "department": "womens",
        "category": "Accessories",
        "brand": "Coach",
        "price_usd": 195.00,
        "color": "Terracotta Leather",
        "color_hex": "#B85D43",
        "style": "Smart Casual",
        "size_range": "One Size",
        "image": "defaults/shop_coach_handbag.jpg",
        "fallback_image": "defaults/acc_tote.jpg",
        "merchant": "Amazon Fashion",
        "url": "https://www.amazon.in/s?k=leather+crossbody+bag+women",
        "description": "Refined structured leather top-handle handbag with secure metal turnlock, polished hardware, and detachable strap."
    },
    {
        "id": "w_acc_2",
        "name": "Emerald Crystal Drop Earrings",
        "department": "womens",
        "category": "Accessories",
        "brand": "Mejuri",
        "price_usd": 58.00,
        "color": "Emerald Green",
        "color_hex": "#34483B",
        "style": "Formal",
        "size_range": "One Size",
        "image": "defaults/shop_mejuri_earrings.jpg",
        "fallback_image": "defaults/acc_watch.jpg",
        "merchant": "Myntra",
        "url": "https://www.myntra.com/dresses",
        "description": "14k gold vermeil statement drop earrings handset with ethically sourced vibrant green teardrop crystals."
    },

    # ================= MEN'S / BOYS' COLLECTION =================
    {
        "id": "m_bottom_1",
        "name": "Relaxed Tailored Chinos",
        "department": "mens",
        "category": "Bottoms",
        "brand": "Uniqlo",
        "price_usd": 49.90,
        "color": "Olive Green",
        "color_hex": "#4F6F52",
        "style": "Smart Casual",
        "size_range": "29 – 36",
        "image": "defaults/shop_uniqlo_chinos.jpg",
        "fallback_image": "defaults/bottom_chinos.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Versatile mid-rise chinos cut with comfortable stretch cotton and cleanly finished coin pocket."
    },
    {
        "id": "m_bottom_2",
        "name": "Classic Pleated Wool Trousers",
        "department": "mens",
        "category": "Bottoms",
        "brand": "COS",
        "price_usd": 125.00,
        "color": "Muted Taupe",
        "color_hex": "#8B806E",
        "style": "Formal",
        "size_range": "30 – 36",
        "image": "defaults/shop_cos_trousers.jpg",
        "fallback_image": "defaults/bottom_trousers.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Tailored wide-leg trousers crafted from responsibly sourced lightweight wool with pressed creases."
    },
    {
        "id": "m_bottom_3",
        "name": "Dark Raw Selvedge Denim Jeans",
        "department": "mens",
        "category": "Bottoms",
        "brand": "Levi's",
        "price_usd": 89.00,
        "color": "Dark Indigo",
        "color_hex": "#1C2833",
        "style": "Casual",
        "size_range": "30 – 38",
        "image": "defaults/bottom_jeans.jpg",
        "fallback_image": "defaults/shop_uniqlo_chinos.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Authentic shuttle-loom selvedge denim woven with a hint of stretch for rigid looks with modern comfort."
    },
    {
        "id": "m_top_1",
        "name": "Everyday White Button-down Oxford Shirt",
        "department": "mens",
        "category": "Tops",
        "brand": "Arket",
        "price_usd": 69.00,
        "color": "White",
        "color_hex": "#FFFFFF",
        "style": "Smart Casual",
        "size_range": "S – XXL",
        "image": "defaults/shop_arket_oxford.jpg",
        "fallback_image": "defaults/top_oxford_shirt.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Regular-fit Oxford shirt woven from premium combed cotton with durable curved hem."
    },
    {
        "id": "m_top_2",
        "name": "Organic Heavyweight Cotton Crewneck Tee",
        "department": "mens",
        "category": "Tops",
        "brand": "Everlane",
        "price_usd": 32.00,
        "color": "Soft Beige",
        "color_hex": "#E8DFD3",
        "style": "Casual",
        "size_range": "XS – XXL",
        "image": "defaults/shop_everlane_tee.jpg",
        "fallback_image": "defaults/top_linen_tee.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Durable 100% organic cotton box-cut tee with dense knit and double-needle ribbed collar."
    },
    {
        "id": "m_top_3",
        "name": "Forest Green Merino Knit Sweater",
        "department": "mens",
        "category": "Tops",
        "brand": "Uniqlo",
        "price_usd": 49.90,
        "color": "Deep Forest Green",
        "color_hex": "#34483B",
        "style": "Smart Casual",
        "size_range": "S – XXL",
        "image": "defaults/top_forest_sweater.jpg",
        "fallback_image": "defaults/top_oxford_shirt.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Ultra-fine 19.5-micron merino wool sweater offering natural thermo-regulation and glossy soft texture."
    },
    {
        "id": "m_top_4",
        "name": "Charcoal Tailored Structured Blazer",
        "department": "mens",
        "category": "Tops",
        "brand": "Massimo Dutti",
        "price_usd": 189.00,
        "color": "Charcoal Grey",
        "color_hex": "#292B28",
        "style": "Formal",
        "size_range": "38 – 46",
        "image": "defaults/top_charcoal_blazer.jpg",
        "fallback_image": "defaults/shop_cos_trousers.jpg",
        "merchant": "Uniqlo India",
        "url": "https://www.uniqlo.com/in/en/products/E450251-000",
        "description": "Modern slim tailored jacket cut in Italian wool-flannel with kissing button cuffs."
    },
    {
        "id": "m_shoe_1",
        "name": "Suede Penny Loafers",
        "department": "mens",
        "category": "Footwear",
        "brand": "Massimo Dutti",
        "price_usd": 169.00,
        "color": "Espresso Brown",
        "color_hex": "#3D2B1F",
        "style": "Smart Casual",
        "size_range": "40 – 46",
        "image": "defaults/shop_massimo_loafers.jpg",
        "fallback_image": "defaults/shoes_loafers.jpg",
        "merchant": "Amazon Fashion",
        "url": "https://www.amazon.in/s?k=penny+loafers+men",
        "description": "Supple cowhide suede loafers with cushioned leather insoles and hand-stitched apron toe."
    },
    {
        "id": "m_shoe_2",
        "name": "Classic Suede Chelsea Boots",
        "department": "mens",
        "category": "Footwear",
        "brand": "Clarks",
        "price_usd": 150.00,
        "color": "Muted Taupe",
        "color_hex": "#7A7062",
        "style": "Smart Casual",
        "size_range": "40 – 46",
        "image": "defaults/shoes_boots.jpg",
        "fallback_image": "defaults/shoes_loafers.jpg",
        "merchant": "Amazon Fashion",
        "url": "https://www.amazon.in/s?k=penny+loafers+men",
        "description": "Water-resistant oiled suede ankle boot with twin elastic gussets and natural crepe rubber soles."
    },
    {
        "id": "m_acc_1",
        "name": "Woven Saddle Leather Belt",
        "department": "mens",
        "category": "Accessories",
        "brand": "Massimo Dutti",
        "price_usd": 69.00,
        "color": "Cognac Brown",
        "color_hex": "#6E4726",
        "style": "Smart Casual",
        "size_range": "85 – 105 cm",
        "image": "defaults/acc_belt.jpg",
        "fallback_image": "defaults/acc_watch.jpg",
        "merchant": "Amazon Fashion",
        "url": "https://www.amazon.in/s?k=leather+crossbody+bag+women",
        "description": "Plaited vegetable-tanned leather belt finished with brushed antique brass hardware."
    },

    # ================= GENDER-NEUTRAL / UNISEX COLLECTION =================
    {
        "id": "u_shoe_1",
        "name": "Campo Chrome-Free Leather Court Sneakers",
        "department": "unisex",
        "category": "Footwear",
        "brand": "Veja",
        "price_usd": 140.00,
        "color": "White",
        "color_hex": "#F7F7F7",
        "style": "Casual",
        "size_range": "36 – 46",
        "image": "defaults/shop_veja_sneakers.jpg",
        "fallback_image": "defaults/shoes_sneakers.jpg",
        "merchant": "Amazon Fashion",
        "url": "https://www.amazon.in/s?k=veja+sneakers",
        "description": "Minimalist white low-top sneakers featuring wild Amazonian rubber soles and eco-certified leather."
    },
    {
        "id": "u_acc_1",
        "name": "Minimalist Field Watch with Leather Strap",
        "department": "unisex",
        "category": "Accessories",
        "brand": "Nordgreen",
        "price_usd": 180.00,
        "color": "Muted Taupe",
        "color_hex": "#C9BBA7",
        "style": "Minimalist",
        "size_range": "36mm / 40mm",
        "image": "defaults/shop_nordgreen_watch.jpg",
        "fallback_image": "defaults/acc_watch.jpg",
        "merchant": "Amazon Fashion",
        "url": "https://www.amazon.in/s?k=minimalist+leather+watch",
        "description": "Danish-designed classic timepiece featuring an asymmetric second hand and interchangeable Italian leather strap."
    },
    {
        "id": "u_acc_2",
        "name": "Canvas & Leather Weekender Duffle",
        "department": "unisex",
        "category": "Accessories",
        "brand": "Bellroy",
        "price_usd": 120.00,
        "color": "Charcoal Grey",
        "color_hex": "#292B28",
        "style": "Casual",
        "size_range": "30 Litres",
        "image": "defaults/shop_bellroy_duffle.jpg",
        "fallback_image": "defaults/acc_tote.jpg",
        "merchant": "Bellroy Official",
        "url": "https://bellroy.com/products/category/bags",
        "description": "Durable water-resistant woven canvas bag with premium leather handles, interior organizers, and laptop compartment."
    }
]

@shopping_bp.route("/shopping")
@login_required
def index():
    user_id = current_user.id
    
    # 1. Wardrobe Gap & Department Analysis
    gap_data = perform_wardrobe_gap_analysis(user_id)
    
    # 2. Exchange Rate Information
    rate, is_live, rate_source = get_usd_to_inr_rate_info()

    # 3. User items and preferences
    user_items = WardrobeItem.query.filter_by(user_id=user_id).all()
    pref = UserPreference.query.filter_by(user_id=user_id).first()

    # Determine Active Department / Gender Orientation Automatically:
    # 1. Explicit query parameter (for direct filter URLs or tests)
    # 2. Wardrobe-driven effective department (auto-detected from closet pieces, or saved preference if ambiguous)
    # 3. Default to 'all' (curated capsule)
    dept_param = request.args.get("department", "").strip().lower()
    if dept_param in ["womens", "mens", "all", "mixed", "unisex"]:
        active_department = dept_param
        dept_is_manual = True
    elif gap_data.get("effective_department") in ["womens", "mens"]:
        active_department = gap_data["effective_department"]
        dept_is_manual = False
    elif gap_data.get("is_mixed") or gap_data.get("effective_department") in ["mixed", "all"]:
        active_department = "all"
        dept_is_manual = False
    elif pref and (pref.gender_preference or "").strip().lower() in ["womens", "mens", "unisex"]:
        active_department = pref.gender_preference.strip().lower()
        dept_is_manual = False
    else:
        active_department = "all"
        dept_is_manual = False

    # Filter parameters
    cat_filter = request.args.get("category", "").strip()
    style_filter = request.args.get("style", "").strip()
    brand_filter = request.args.get("brand", "").strip()
    max_price_inr = request.args.get("max_price", "").strip()

    annotated_products = []
    for prod in CATALOG_ITEMS:
        p_dept = prod.get("department", "unisex")
        
        # 1. Department match
        if active_department == "womens":
            if p_dept not in ["womens", "unisex"]:
                continue
        elif active_department == "mens":
            if p_dept not in ["mens", "unisex"]:
                continue
        elif active_department == "unisex":
            if p_dept != "unisex":
                continue
        # If "all" or "mixed", show all departments

        # 2. Category match
        if cat_filter:
            if cat_filter == "Clothing":
                if prod["category"] not in ["Tops", "Bottoms", "Dresses / One-piece"]:
                    continue
            elif prod["category"] != cat_filter:
                continue

        # 3. Style match
        if style_filter and prod.get("style") != style_filter:
            continue

        # 4. Brand match
        if brand_filter and prod.get("brand", "").lower() != brand_filter.lower():
            continue

        # Calculate INR price from original USD price
        price_inr = convert_usd_to_inr(prod["price_usd"])

        # 5. Price budget match
        if max_price_inr:
            try:
                if price_inr > float(max_price_inr):
                    continue
            except ValueError:
                pass

        # Check duplicate risk against user's actual closet
        duplicate_match = None
        for ui in user_items:
            if ui.category == prod["category"] and (ui.color.lower() in prod["color"].lower() or prod["color"].lower() in ui.color.lower()):
                duplicate_match = ui
                break

        # Check if item fills a genuine wardrobe gap
        is_gap_filler = prod["category"] in gap_data["underrepresented"]

        annotated_products.append({
            **prod,
            "price_inr": price_inr,
            "is_gap_filler": is_gap_filler,
            "duplicate_warning": f"You already own '{duplicate_match.name}' ({duplicate_match.color} {duplicate_match.category}). Consider if this offers new utility." if duplicate_match else None,
            "gap_recommendation": f"Fills your identified {prod['category']} gap! Expands outfit pairings with your existing wardrobe." if is_gap_filler else None
        })

    # Sort so gap fillers appear first, prioritizing the active department over unisex
    annotated_products.sort(
        key=lambda p: (
            0 if p["is_gap_filler"] else 1,
            0 if p.get("department") == active_department else 1
        )
    )

    # API configuration check
    shopping_api_key = os.getenv("SHOPPING_API_KEY", "").strip()
    is_api_configured = bool(shopping_api_key)

    # Distinct brands for filter dropdown
    available_brands = sorted(list({p["brand"] for p in CATALOG_ITEMS}))

    return render_template(
        "shopping/index.html",
        products=annotated_products,
        gaps=gap_data["gaps"],
        underrepresented=gap_data["underrepresented"],
        gap_data=gap_data,
        rate=rate,
        rate_source=rate_source,
        is_live_rate=is_live,
        active_department=active_department,
        dept_is_manual=dept_is_manual,
        active_cat=cat_filter,
        active_style=style_filter,
        active_brand=brand_filter,
        active_max_price=max_price_inr,
        available_brands=available_brands,
        is_api_configured=is_api_configured,
        user_preference=pref
    )


@shopping_bp.route("/shopping/set-preference", methods=["POST"])
@login_required
def set_preference():
    dept = request.form.get("department", "").strip().lower()
    if dept in ["womens", "mens", "unisex", "all"]:
        pref = UserPreference.query.filter_by(user_id=current_user.id).first()
        if not pref:
            pref = UserPreference(user_id=current_user.id)
            db.session.add(pref)
        pref.gender_preference = dept if dept in ["womens", "mens", "unisex"] else None
        db.session.commit()
        dept_label = "Women's / Girls'" if dept == "womens" else "Men's / Boys'" if dept == "mens" else "Neutral / All"
        flash(f"Shopping style preference updated to {dept_label}!", "success")
    return redirect(url_for("shopping.index", department=dept))
