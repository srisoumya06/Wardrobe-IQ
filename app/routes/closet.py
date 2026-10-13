import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, WardrobeItem, WornHistory
from app.services.ai_vision import analyze_clothing_image
from app.services.points_service import award_points

closet_bp = Blueprint("closet", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
CATEGORIES = ["Tops", "Bottoms", "Dresses / One-piece", "Footwear", "Accessories"]

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@closet_bp.route("/closet")
@login_required
def index():
    # Filtering & Sorting
    category = request.args.get("category", "").strip()
    color = request.args.get("color", "").strip()
    style = request.args.get("style", "").strip()
    search = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "newest")

    query = WardrobeItem.query.filter_by(user_id=current_user.id)

    if category and category != "All":
        query = query.filter(WardrobeItem.category == category)
    if color:
        query = query.filter(WardrobeItem.color.ilike(f"%{color}%"))
    if style:
        query = query.filter(WardrobeItem.style == style)
    if search:
        query = query.filter(
            (WardrobeItem.name.ilike(f"%{search}%")) |
            (WardrobeItem.brand.ilike(f"%{search}%")) |
            (WardrobeItem.subcategory.ilike(f"%{search}%"))
        )

    # Sorting
    if sort_by == "oldest":
        query = query.order_by(WardrobeItem.created_at.asc())
    elif sort_by == "price_high":
        query = query.order_by(WardrobeItem.purchase_price.desc())
    elif sort_by == "price_low":
        query = query.order_by(WardrobeItem.purchase_price.asc())
    elif sort_by == "name":
        query = query.order_by(WardrobeItem.name.asc())
    else: # newest
        query = query.order_by(WardrobeItem.created_at.desc())

    items = query.all()

    # Category counts for tabs
    all_user_items = WardrobeItem.query.filter_by(user_id=current_user.id).all()
    counts = {
        "All": len(all_user_items),
        "Tops": sum(1 for i in all_user_items if i.category == "Tops"),
        "Bottoms": sum(1 for i in all_user_items if i.category == "Bottoms"),
        "Dresses / One-piece": sum(1 for i in all_user_items if i.category == "Dresses / One-piece"),
        "Footwear": sum(1 for i in all_user_items if i.category == "Footwear"),
        "Accessories": sum(1 for i in all_user_items if i.category == "Accessories"),
    }

    return render_template(
        "closet/index.html",
        items=items,
        counts=counts,
        active_category=category or "All",
        active_sort=sort_by,
        categories=CATEGORIES
    )


@closet_bp.route("/closet/add", methods=["GET", "POST"])
@login_required
def add_item():
    if request.method == "POST":
        file = request.files.get("clothing_image")
        entry_mode = request.form.get("entry_mode", "upload") # upload, camera, manual
        
        saved_filename = "defaults/top_oxford_shirt.jpg"
        
        if file and file.filename and allowed_file(file.filename):
            orig_name = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"user_{current_user.id}_{timestamp}_{orig_name}"
            upload_path = os.path.join(closet_bp.root_path, "..", "static", "uploads", unique_filename)
            upload_path = os.path.abspath(upload_path)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            saved_filename = f"uploads/{unique_filename}"
            
            # Analyze image using AI vision service
            ai_data = analyze_clothing_image(upload_path)
        else:
            # Manual entry without custom image: use default clean placeholder
            ai_data = {
                "category": request.form.get("category", "Tops"),
                "subcategory": "Wardrobe Essential",
                "color": "Warm Ivory",
                "color_hex": "#F4EFE7",
                "pattern": "Solid",
                "style": "Casual",
                "season": "All-Season",
                "occasions": "College, Casual",
                "suggested_name": "New Wardrobe Piece",
                "is_ai_recognized": False,
                "service_note": "Manual entry mode selected."
            }
            if request.form.get("default_image"):
                saved_filename = f"defaults/{request.form.get('default_image')}"

        # Present editable confirmation screen
        return render_template(
            "closet/confirm_item.html",
            image_path=saved_filename,
            ai_data=ai_data,
            categories=CATEGORIES
        )

    return render_template("closet/add_modal.html", categories=CATEGORIES)


@closet_bp.route("/closet/save", methods=["POST"])
@login_required
def save_confirmed_item():
    name = request.form.get("name", "").strip() or "Untitled Wardrobe Piece"
    category = request.form.get("category", "Tops")
    subcategory = request.form.get("subcategory", "").strip()
    color = request.form.get("color", "Muted Taupe").strip()
    color_hex = request.form.get("color_hex", "#8B806E").strip()
    pattern = request.form.get("pattern", "Solid")
    style = request.form.get("style", "Casual")
    season = request.form.get("season", "All-Season")
    occasions = request.form.get("occasions", "Casual")
    brand = request.form.get("brand", "").strip()
    size = request.form.get("size", "").strip()
    fabric = request.form.get("fabric", "").strip()
    image_path = request.form.get("image_path", "defaults/top_oxford_shirt.jpg")
    notes = request.form.get("notes", "").strip()
    
    price_val = None
    if request.form.get("purchase_price"):
        try:
            price_val = float(request.form.get("purchase_price"))
        except ValueError:
            price_val = None

    item = WardrobeItem(
        user_id=current_user.id,
        name=name,
        category=category,
        subcategory=subcategory,
        color=color,
        color_hex=color_hex,
        pattern=pattern,
        style=style,
        season=season,
        occasions=occasions,
        brand=brand,
        size=size,
        fabric=fabric,
        purchase_price=price_val,
        image_path=image_path,
        notes=notes,
        availability_status="Available"
    )
    db.session.add(item)
    db.session.commit()

    # Award +15 fashion points with anti-abuse idempotency
    award_points(
        user_id=current_user.id,
        activity_type="ADD_ITEM",
        points=15,
        description=f"Added '{name}' to your digital closet",
        reference_id=f"item_{item.id}"
    )

    flash(f"'{name}' was successfully catalogued into your {category} collection!", "success")
    return redirect(url_for("closet.index", category=category))


@closet_bp.route("/closet/item/<int:item_id>")
@login_required
def item_detail(item_id):
    item = WardrobeItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    
    # Calculate wear count from actual confirmed worn history
    user_worn = WornHistory.query.filter_by(user_id=current_user.id).all()
    wear_count = 0
    recent_wears = []
    for entry in user_worn:
        if item.id in entry.item_ids:
            wear_count += 1
            recent_wears.append(entry)

    return render_template(
        "closet/item_detail.html",
        item=item,
        wear_count=wear_count,
        recent_wears=recent_wears[:5]
    )


@closet_bp.route("/closet/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    item = WardrobeItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    
    if request.method == "POST":
        item.name = request.form.get("name", item.name).strip()
        item.category = request.form.get("category", item.category)
        item.subcategory = request.form.get("subcategory", item.subcategory).strip()
        item.color = request.form.get("color", item.color).strip()
        item.color_hex = request.form.get("color_hex", item.color_hex).strip()
        item.pattern = request.form.get("pattern", item.pattern)
        item.style = request.form.get("style", item.style)
        item.season = request.form.get("season", item.season)
        item.occasions = request.form.get("occasions", item.occasions)
        item.brand = request.form.get("brand", "").strip()
        item.size = request.form.get("size", "").strip()
        item.fabric = request.form.get("fabric", "").strip()
        item.notes = request.form.get("notes", "").strip()
        
        if request.form.get("purchase_price"):
            try:
                item.purchase_price = float(request.form.get("purchase_price"))
            except ValueError:
                item.purchase_price = None

        file = request.files.get("clothing_image")
        if file and file.filename and allowed_file(file.filename):
            orig_name = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"user_{current_user.id}_{timestamp}_{orig_name}"
            upload_path = os.path.join(closet_bp.root_path, "..", "static", "uploads", unique_filename)
            upload_path = os.path.abspath(upload_path)
            file.save(upload_path)
            item.image_path = f"uploads/{unique_filename}"

        db.session.commit()
        flash(f"Updated details for '{item.name}'.", "success")
        return redirect(url_for("closet.item_detail", item_id=item.id))

    return render_template("closet/edit_item.html", item=item, categories=CATEGORIES)


@closet_bp.route("/closet/item/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    item = WardrobeItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item_name = item.name
    
    # Safely delete: cascade removes OutfitItem entries, while WornHistory preserves item_ids_json
    db.session.delete(item)
    db.session.commit()
    
    flash(f"'{item_name}' was removed from your closet. Historical wear records remain preserved.", "info")
    return redirect(url_for("closet.index"))


@closet_bp.route("/closet/seed-starter-capsule", methods=["POST"])
@login_required
def seed_starter_capsule():
    """Seeds a curated starter capsule wardrobe for student testing and demonstration."""
    starter_items = [
        # Tops
        {"name": "Crisp White Oxford Shirt", "cat": "Tops", "sub": "Button-down Shirt", "col": "White", "hex": "#FFFFFF", "pat": "Solid", "sty": "Smart Casual", "sea": "All-Season", "occ": "College, Work/Office, Smart Casual", "img": "defaults/top_oxford_shirt.jpg", "price": 2499.0},
        {"name": "Sand Linen Relaxed Tee", "cat": "Tops", "sub": "T-Shirt", "col": "Soft Beige", "hex": "#E8DFD3", "pat": "Solid", "sty": "Casual", "sea": "Summer", "occ": "Casual, College, Weekend", "img": "defaults/top_linen_tee.jpg", "price": 1299.0},
        {"name": "Forest Green Merino Knit", "cat": "Tops", "sub": "Sweater", "col": "Deep Forest Green", "hex": "#34483B", "pat": "Solid", "sty": "Minimalist", "sea": "Autumn", "occ": "College, Evening, Casual", "img": "defaults/top_forest_sweater.jpg", "price": 3499.0},
        {"name": "Charcoal Tailored Blazer", "cat": "Tops", "sub": "Blazer", "col": "Charcoal", "hex": "#292B28", "pat": "Solid", "sty": "Formal", "sea": "All-Season", "occ": "Work/Office, Formal, College", "img": "defaults/top_charcoal_blazer.jpg", "price": 7999.0},
        
        # Bottoms
        {"name": "Olive Tailored Chinos", "cat": "Bottoms", "sub": "Chinos", "col": "Olive Green", "hex": "#4F6F52", "pat": "Solid", "sty": "Smart Casual", "sea": "All-Season", "occ": "College, Smart Casual", "img": "defaults/bottom_chinos.jpg", "price": 2999.0},
        {"name": "Dark Raw Selvedge Denim", "cat": "Bottoms", "sub": "Jeans", "col": "Navy Blue", "hex": "#1E2D4A", "pat": "Solid", "sty": "Casual", "sea": "All-Season", "occ": "Casual, Weekend", "img": "defaults/bottom_jeans.jpg", "price": 3999.0},
        {"name": "Muted Taupe Wool Trousers", "cat": "Bottoms", "sub": "Trousers", "col": "Muted Taupe", "hex": "#8B806E", "pat": "Solid", "sty": "Formal", "sea": "Winter", "occ": "Formal, Smart Casual", "img": "defaults/bottom_trousers.jpg", "price": 4499.0},
        
        # Dresses
        {"name": "Ivory Tiered Linen Dress", "cat": "Dresses / One-piece", "sub": "Shirt Dress", "col": "Warm Ivory", "hex": "#F4EFE7", "pat": "Solid", "sty": "Minimalist", "sea": "Summer", "occ": "Casual, Weekend, Brunch", "img": "defaults/dress_linen.jpg", "price": 4999.0},
        {"name": "Sage Silk Slip Midi Dress", "cat": "Dresses / One-piece", "sub": "Slip Dress", "col": "Sage Green", "hex": "#A9B4A1", "pat": "Solid", "sty": "Elegant", "sea": "Spring", "occ": "Evening, Dinner, Party", "img": "defaults/dress_slip.jpg", "price": 5999.0},
        
        # Footwear
        {"name": "Minimalist White Leather Lows", "cat": "Footwear", "sub": "Sneakers", "col": "White", "hex": "#F7F7F7", "pat": "Solid", "sty": "Casual", "sea": "All-Season", "occ": "College, Casual", "img": "defaults/shoes_sneakers.jpg", "price": 3999.0},
        {"name": "Espresso Penny Loafers", "cat": "Footwear", "sub": "Loafers", "col": "Espresso Brown", "hex": "#3D2B1F", "pat": "Solid", "sty": "Smart Casual", "sea": "All-Season", "occ": "Smart Casual, Work/Office", "img": "defaults/shoes_loafers.jpg", "price": 5999.0},
        {"name": "Suede Chelsea Boots", "cat": "Footwear", "sub": "Boots", "col": "Camel / Tan", "hex": "#9E846A", "pat": "Solid", "sty": "Smart Casual", "sea": "Autumn", "occ": "College, Evening", "img": "defaults/shoes_boots.jpg", "price": 6999.0},
        
        # Accessories
        {"name": "Vintage Minimalist Field Watch", "cat": "Accessories", "sub": "Watch", "col": "Muted Taupe", "hex": "#C9BBA7", "pat": "Solid", "sty": "Minimalist", "sea": "All-Season", "occ": "Daily Wear", "img": "defaults/acc_watch.jpg", "price": 3499.0},
        {"name": "Woven Saddle Leather Belt", "cat": "Accessories", "sub": "Belt", "col": "Brown", "hex": "#5C3E21", "pat": "Woven", "sty": "Smart Casual", "sea": "All-Season", "occ": "Smart Casual, Formal", "img": "defaults/acc_belt.jpg", "price": 1499.0},
        {"name": "Canvas & Leather Weekender", "cat": "Accessories", "sub": "Bag", "col": "Soft Beige", "hex": "#D8CBBB", "pat": "Solid", "sty": "Casual", "sea": "All-Season", "occ": "Travel, College", "img": "defaults/acc_tote.jpg", "price": 3999.0},
    ]

    added_count = 0
    for data in starter_items:
        exists = WardrobeItem.query.filter_by(user_id=current_user.id, name=data["name"]).first()
        if not exists:
            item = WardrobeItem(
                user_id=current_user.id,
                name=data["name"],
                category=data["cat"],
                subcategory=data["sub"],
                color=data["col"],
                color_hex=data["hex"],
                pattern=data["pat"],
                style=data["sty"],
                season=data["sea"],
                occasions=data["occ"],
                image_path=data["img"],
                purchase_price=data["price"],
                availability_status="Available"
            )
            db.session.add(item)
            added_count += 1
            
    db.session.commit()
    award_points(
        user_id=current_user.id,
        activity_type="SEED_CAPSULE",
        points=30,
        description="Seeded curated capsule wardrobe collection",
        reference_id=f"capsule_seed_{current_user.id}"
    )

    flash(f"Successfully curated {added_count} capsule wardrobe essentials for your closet!", "success")
    return redirect(url_for("closet.index"))
