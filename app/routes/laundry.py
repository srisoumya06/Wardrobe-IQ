from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, WardrobeItem
from app.services.points_service import award_points

laundry_bp = Blueprint("laundry", __name__)

LAUNDRY_CATEGORIES = ["Tops", "Bottoms", "Dresses / One-piece"]
VALID_STATUSES = ["Available", "Worn / Needs Washing", "In Laundry"]

@laundry_bp.route("/laundry")
@login_required
def index():
    status_filter = request.args.get("status", "All")
    cat_filter = request.args.get("category", "All")
    
    query = WardrobeItem.query.filter(
        WardrobeItem.user_id == current_user.id,
        WardrobeItem.category.in_(LAUNDRY_CATEGORIES)
    )

    if status_filter and status_filter != "All":
        query = query.filter(WardrobeItem.availability_status == status_filter)
    if cat_filter and cat_filter != "All":
        query = query.filter(WardrobeItem.category == cat_filter)

    items = query.order_by(WardrobeItem.category.asc(), WardrobeItem.name.asc()).all()
    
    # Counts
    all_laundry_items = WardrobeItem.query.filter(
        WardrobeItem.user_id == current_user.id,
        WardrobeItem.category.in_(LAUNDRY_CATEGORIES)
    ).all()

    counts = {
        "Available": sum(1 for i in all_laundry_items if i.availability_status == "Available"),
        "Worn": sum(1 for i in all_laundry_items if i.availability_status == "Worn / Needs Washing"),
        "In Laundry": sum(1 for i in all_laundry_items if i.availability_status == "In Laundry"),
        "Total": len(all_laundry_items)
    }

    return render_template(
        "laundry/index.html",
        items=items,
        counts=counts,
        active_status=status_filter,
        active_cat=cat_filter,
        valid_statuses=VALID_STATUSES
    )


@laundry_bp.route("/laundry/update-status", methods=["POST"])
@login_required
def update_status():
    item_id = request.form.get("item_id")
    new_status = request.form.get("status")

    if not item_id or new_status not in VALID_STATUSES:
        flash("Invalid status update request.", "danger")
        return redirect(url_for("laundry.index"))

    item = WardrobeItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    old_status = item.availability_status
    item.availability_status = new_status
    db.session.commit()

    # Award points if user moves clothes from laundry back to Available (promoting mindful wardrobe care)
    if old_status in ["In Laundry", "Worn / Needs Washing"] and new_status == "Available":
        award_points(
            user_id=current_user.id,
            activity_type="LAUNDRY_CARE",
            points=5,
            description=f"Freshly washed & ready: {item.name}",
            reference_id=f"clean_{item.id}_{db.func.current_date()}"
        )

    flash(f"Updated '{item.name}' status to '{new_status}'.", "success")
    return redirect(url_for("laundry.index"))


@laundry_bp.route("/laundry/batch-action", methods=["POST"])
@login_required
def batch_action():
    action = request.form.get("action")
    
    items = WardrobeItem.query.filter(
        WardrobeItem.user_id == current_user.id,
        WardrobeItem.category.in_(LAUNDRY_CATEGORIES)
    )

    if action == "clean_all":
        items.filter(WardrobeItem.availability_status.in_(["In Laundry", "Worn / Needs Washing"])).update(
            {"availability_status": "Available"}
        )
        db.session.commit()
        flash("All garments marked as Fresh & Available to wear!", "success")
    elif action == "wash_all_worn":
        items.filter(WardrobeItem.availability_status == "Worn / Needs Washing").update(
            {"availability_status": "In Laundry"}
        )
        db.session.commit()
        flash("All worn garments moved to In Laundry.", "info")

    return redirect(url_for("laundry.index"))
