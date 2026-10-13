from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, PackingTrip, PackingItem, WardrobeItem
from app.services.packing_service import generate_trip_packing_plan
from app.services.points_service import award_points

packing_bp = Blueprint("packing", __name__)

@packing_bp.route("/packing")
@login_required
def index():
    user_id = current_user.id
    trips = PackingTrip.query.filter_by(user_id=user_id).order_by(PackingTrip.created_at.desc()).all()
    active_trip_id = request.args.get("trip_id")
    
    if active_trip_id:
        active_trip = PackingTrip.query.filter_by(id=active_trip_id, user_id=user_id).first()
    else:
        active_trip = trips[0] if trips else None

    # Group items by category for checklist display
    grouped_items = {}
    if active_trip:
        for pi in active_trip.items:
            cat = pi.category
            if cat not in grouped_items:
                grouped_items[cat] = []
            grouped_items[cat].append(pi)

    # Defaults for form
    today = date.today()
    default_end = today + timedelta(days=3)

    return render_template(
        "packing/index.html",
        trips=trips,
        active_trip=active_trip,
        grouped_items=grouped_items,
        default_start=today.strftime("%Y-%m-%d"),
        default_end=default_end.strftime("%Y-%m-%d")
    )


@packing_bp.route("/packing/create-trip", methods=["POST"])
@login_required
def create_trip():
    user_id = current_user.id
    destination = request.form.get("destination", "").strip() or "Weekend Getaway"
    start_str = request.form.get("start_date") or date.today().strftime("%Y-%m-%d")
    end_str = request.form.get("end_date") or (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
    trip_purpose = request.form.get("trip_purpose", "Leisure / Sightseeing")
    activities = request.form.get("activities", "Casual walking, dining")
    laundry_access = True if request.form.get("laundry_access") == "yes" else False
    
    try:
        limit_kg = float(request.form.get("luggage_limit_kg", 15.0))
    except ValueError:
        limit_kg = 15.0

    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    except ValueError:
        start_date = date.today()
        end_date = date.today() + timedelta(days=3)

    trip = PackingTrip(
        user_id=user_id,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        trip_purpose=trip_purpose,
        activities=activities,
        luggage_limit_kg=limit_kg,
        laundry_access=laundry_access
    )
    db.session.add(trip)
    db.session.flush()

    # Generate packing items from available wardrobe
    plan_items = generate_trip_packing_plan(
        user_id=user_id,
        days=trip.duration_days,
        purpose=trip_purpose,
        activities=activities,
        laundry_access=laundry_access
    )

    for p in plan_items:
        pi = PackingItem(
            trip_id=trip.id,
            wardrobe_item_id=p["wardrobe_item_id"],
            custom_name=p["custom_name"],
            category=p["category"],
            is_packed=False,
            weight_grams=p["weight_grams"]
        )
        db.session.add(pi)

    db.session.commit()
    flash(f"Packing list created for '{destination}' ({trip.duration_days} days).", "success")
    return redirect(url_for("packing.index", trip_id=trip.id))


@packing_bp.route("/packing/toggle-item/<int:item_id>", methods=["POST"])
@login_required
def toggle_item(item_id):
    pi = PackingItem.query.get_or_404(item_id)
    if pi.trip.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    pi.is_packed = not pi.is_packed
    db.session.commit()

    all_packed = pi.trip.packed_count == pi.trip.total_count

    return jsonify({
        "success": True,
        "is_packed": pi.is_packed,
        "packed_count": pi.trip.packed_count,
        "total_count": pi.trip.total_count,
        "all_packed": all_packed
    })


@packing_bp.route("/packing/add-custom-item", methods=["POST"])
@login_required
def add_custom_item():
    trip_id = request.form.get("trip_id")
    trip = PackingTrip.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    
    item_name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "Essentials")
    
    if item_name:
        pi = PackingItem(
            trip_id=trip.id,
            custom_name=item_name,
            category=category,
            is_packed=False,
            weight_grams=200.0
        )
        db.session.add(pi)
        db.session.commit()
        flash(f"Added '{item_name}' to packing list.", "success")

    return redirect(url_for("packing.index", trip_id=trip.id))


@packing_bp.route("/packing/delete-item/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    pi = PackingItem.query.get_or_404(item_id)
    trip_id = pi.trip_id
    if pi.trip.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("packing.index"))

    db.session.delete(pi)
    db.session.commit()
    return redirect(url_for("packing.index", trip_id=trip_id))


@packing_bp.route("/packing/complete-trip/<int:trip_id>", methods=["POST"])
@login_required
def complete_trip(trip_id):
    trip = PackingTrip.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    
    # Mark all items as packed
    for itm in trip.items:
        itm.is_packed = True
    db.session.commit()

    # Award points (+35 Fashion Points for completing packing list)
    award_points(
        user_id=current_user.id,
        activity_type="COMPLETE_PACKING",
        points=35,
        description=f"Completed travel packing for '{trip.destination}'",
        reference_id=f"trip_{trip.id}"
    )

    flash(f"Suitcase fully packed for {trip.destination}! +35 Fashion Points earned.", "success")
    return redirect(url_for("packing.index", trip_id=trip.id))


@packing_bp.route("/packing/delete-trip/<int:trip_id>", methods=["POST"])
@login_required
def delete_trip(trip_id):
    trip = PackingTrip.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    db.session.delete(trip)
    db.session.commit()
    flash("Trip and packing checklist removed.", "info")
    return redirect(url_for("packing.index"))
