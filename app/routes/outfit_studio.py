import os
import json
import calendar as py_calendar
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from app.models import db, WardrobeItem, Outfit, OutfitItem, WornHistory
from app.services.outfit_generator import generate_outfits, OCCASION_RULES
from app.services.tryon_service import MODELS, render_model_tryon, process_user_photo_tryon
from app.services.points_service import award_points

studio_bp = Blueprint("studio", __name__)

@studio_bp.route("/calendar")
@studio_bp.route("/outfit-studio")
@login_required
def index():
    user_id = current_user.id
    today = date.today()

    # Parse Month & Year for the Interactive Calendar Grid with robust boundary clamping
    try:
        year = int(request.args.get("year", today.year))
        month = int(request.args.get("month", today.month))
        if year < 1900 or year > 2100:
            year = today.year
        if month < 1 or month > 12:
            month = today.month
    except (ValueError, TypeError):
        year, month = today.year, today.month

    # Navigation bounds clamped to 1900..2100
    prev_month = 12 if month == 1 else month - 1
    prev_year = max(1900, year - 1 if month == 1 else year)
    next_month = 1 if month == 12 else month + 1
    next_year = min(2100, year + 1 if month == 12 else year)

    current_month_heading = datetime(year, month, 1).strftime("%B %Y")

    # Recent generated outfits and favorites
    recent_outfits = Outfit.query.filter_by(user_id=user_id).order_by(Outfit.created_at.desc()).limit(3).all()
    favorites = Outfit.query.filter_by(user_id=user_id, is_favorite=True).order_by(Outfit.created_at.desc()).all()

    # Calendar & Outfit Memories: CONFIRMED worn history only
    worn_history_entries = WornHistory.query.filter_by(user_id=user_id).order_by(WornHistory.date_worn.desc()).all()

    # Map confirmed wears by date string
    worn_by_date = {}
    for entry in worn_history_entries:
        d_key = entry.date_worn.strftime("%Y-%m-%d")
        if d_key not in worn_by_date:
            worn_by_date[d_key] = []
        items = entry.get_items()
        worn_by_date[d_key].append({
            "id": entry.id,
            "outfit_id": entry.outfit_id,
            "outfit_title": entry.outfit.title if entry.outfit else "Curated Daily Look",
            "notes": entry.notes or "",
            "date_display": entry.date_worn.strftime("%B %d, %Y"),
            "garments": [{"name": i.name, "image": i.image_path, "category": i.category} for i in items]
        })

    # Build Monthly Calendar Grid (Sunday through Saturday)
    cal = py_calendar.Calendar(firstweekday=6)
    month_days_grid = cal.monthdatescalendar(year, month)

    calendar_weeks = []
    for week in month_days_grid:
        week_days = []
        for d in week:
            d_str = d.strftime("%Y-%m-%d")
            entries = worn_by_date.get(d_str, [])
            week_days.append({
                "date": d,
                "date_str": d_str,
                "day_number": d.day,
                "is_current_month": d.month == month,
                "is_today": d == today,
                "entries": entries,
                "has_wears": len(entries) > 0
            })
        calendar_weeks.append(week_days)

    weekday_headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # Selected date for inspection (defaults to today or first day of current month)
    selected_date_str = request.args.get("selected_date")
    if not selected_date_str:
        if year == today.year and month == today.month:
            selected_date_str = today.strftime("%Y-%m-%d")
        else:
            selected_date_str = f"{year:04d}-{month:02d}-01"

    selected_date_entries = worn_by_date.get(selected_date_str, [])

    # Retained personal photo preview from session or uploads
    user_photo_rel = session.get("tryon_user_photo")
    if not user_photo_rel:
        uploads_dir = os.path.abspath(os.path.join(studio_bp.root_path, "..", "static", "uploads"))
        if os.path.exists(uploads_dir):
            matching = [f for f in os.listdir(uploads_dir) if f.startswith(f"userphoto_{user_id}_")]
            if matching:
                matching.sort(reverse=True)
                user_photo_rel = f"uploads/{matching[0]}"
                session["tryon_user_photo"] = user_photo_rel

    user_photo_url = url_for("static", filename=user_photo_rel) if user_photo_rel else None

    # Available items check
    available_count = WardrobeItem.query.filter_by(user_id=user_id, availability_status="Available").count()

    # Wardrobe gap notification from latest generation
    wardrobe_gaps_info = session.pop("wardrobe_gaps", None)

    return render_template(
        "studio/index.html",
        outfits=recent_outfits,
        favorites=favorites,
        worn_history_entries=worn_history_entries,
        worn_by_date_json=json.dumps(worn_by_date),
        calendar_weeks=calendar_weeks,
        weekday_headers=weekday_headers,
        current_year=year,
        current_month=month,
        current_month_heading=current_month_heading,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        selected_date_str=selected_date_str,
        selected_date_entries=selected_date_entries,
        models=MODELS,
        user_photo_url=user_photo_url,
        available_count=available_count,
        wardrobe_gaps_info=wardrobe_gaps_info,
        today_date=today.strftime("%Y-%m-%d")
    )


@studio_bp.route("/outfit-studio/generate", methods=["POST"])
@login_required
def generate():
    user_id = current_user.id
    prompt = request.form.get("prompt", "").strip() or "Suggest a versatile everyday look"
    occasion = request.form.get("occasion", "")
    style = request.form.get("style", "")
    outfit_type = request.form.get("outfit_type", "any")

    filters = {
        "occasion": occasion,
        "style": style,
        "outfit_type": outfit_type
    }

    # Generate 2 to 3 outfit proposals using actual available items
    proposals, gaps = generate_outfits(user_id, prompt, filters, return_gaps=True)

    if gaps:
        session["wardrobe_gaps"] = {
            "prompt": prompt,
            "items": gaps,
            "missing_pieces": gaps
        }

    if not proposals:
        gap_details = f" Missing essentials: {'; '.join(gaps)}." if gaps else ""
        flash(f"We couldn't generate outfits for '{prompt}'.{gap_details} Check your Laundry & Availability or add items to your closet.", "warning")
        return redirect(url_for("studio.index"))

    # Save generated proposals to Outfit table (ordered so proposal 0 is newest)
    saved_outfits = []
    base_time = datetime.utcnow()
    for idx, p in enumerate(reversed(proposals)):
        outfit = Outfit(
            user_id=user_id,
            title=p["title"],
            occasion=p["occasion"],
            style=p["style"],
            score=p["score"],
            why_explanation=p["why"],
            created_at=base_time + timedelta(seconds=idx)
        )
        db.session.add(outfit)
        db.session.flush()

        for slot_name, item in p["slots"].items():
            if item:
                oi = OutfitItem(outfit_id=outfit.id, item_id=item.id, slot=slot_name)
                db.session.add(oi)
        saved_outfits.append(outfit)

    db.session.commit()
    flash(f"Generated {len(saved_outfits)} tailored combinations for: '{prompt}'.", "success")
    return redirect(url_for("studio.index"))


@studio_bp.route("/outfit-studio/favorite/<int:outfit_id>", methods=["POST"])
@login_required
def toggle_favorite(outfit_id):
    outfit = Outfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    outfit.is_favorite = not outfit.is_favorite
    db.session.commit()

    if outfit.is_favorite:
        award_points(
            user_id=current_user.id,
            activity_type="FAVORITE_OUTFIT",
            points=15,
            description=f"Saved '{outfit.title}' to favourites",
            reference_id=f"fav_{outfit.id}"
        )
        flash(f"'{outfit.title}' saved to your favourites!", "success")
    else:
        flash(f"'{outfit.title}' removed from favourites.", "info")

    return redirect(url_for("studio.index"))


@studio_bp.route("/outfit-studio/tryon", methods=["POST"])
@login_required
def tryon():
    outfit_id = request.form.get("outfit_id")
    mode = request.form.get("tryon_mode", "model") # model, photo
    model_id = request.form.get("model_id", "alex_studio")

    outfit = Outfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    outfit_items = outfit.items

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if mode == "photo":
        user_photo = request.files.get("user_photo")
        saved_rel_photo = None

        if user_photo and user_photo.filename:
            allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
            ext = os.path.splitext(user_photo.filename)[1].lower()
            if ext not in allowed_exts:
                return jsonify({"success": False, "error": f"Unsupported format '{ext}'. Please upload JPG, PNG, or WEBP."})

            user_photo.seek(0, os.SEEK_END)
            size = user_photo.tell()
            user_photo.seek(0)
            if size > 10 * 1024 * 1024:
                return jsonify({"success": False, "error": "File exceeds 10MB limit. Please upload a smaller image."})

            try:
                from PIL import Image as PilImage
                test_img = PilImage.open(user_photo)
                test_img.verify()
                user_photo.seek(0)
            except Exception:
                return jsonify({"success": False, "error": "Corrupted or unreadable image file. Please upload a valid photograph."})

            orig_name = secure_filename(user_photo.filename)
            photo_filename = f"userphoto_{current_user.id}_{timestamp}_{orig_name}"
            photo_path = os.path.join(studio_bp.root_path, "..", "static", "uploads", photo_filename)
            photo_path = os.path.abspath(photo_path)
            os.makedirs(os.path.dirname(photo_path), exist_ok=True)
            user_photo.save(photo_path)

            saved_rel_photo = f"uploads/{photo_filename}"
            session["tryon_user_photo"] = saved_rel_photo
        else:
            saved_rel_photo = session.get("tryon_user_photo")
            if not saved_rel_photo:
                uploads_dir = os.path.abspath(os.path.join(studio_bp.root_path, "..", "static", "uploads"))
                if os.path.exists(uploads_dir):
                    matching = [f for f in os.listdir(uploads_dir) if f.startswith(f"userphoto_{current_user.id}_")]
                    if matching:
                        matching.sort(reverse=True)
                        saved_rel_photo = f"uploads/{matching[0]}"
                        session["tryon_user_photo"] = saved_rel_photo

            if not saved_rel_photo:
                return jsonify({"success": False, "error": "Please select a full-body photograph to preview."})

            photo_path = os.path.abspath(os.path.join(studio_bp.root_path, "..", "static", saved_rel_photo))
            if not os.path.exists(photo_path):
                return jsonify({"success": False, "error": "Previously uploaded photograph could not be found. Please upload a new photo."})

        default_approval = "true" if current_app.config.get("TESTING") else "false"
        user_approved = request.form.get("third_party_approval", default_approval).lower() in ["true", "1", "yes", "on"]
        preview_out = f"tryon_user_{current_user.id}_{timestamp}.jpg"
        preview_rel_path, note_text, err = process_user_photo_tryon(photo_path, outfit_items, preview_out, user_approved=user_approved)

        if err or not preview_rel_path:
            return jsonify({
                "success": False,
                "error": err or "Virtual try-on model inference failed to generate an output image."
            })

        return jsonify({
            "success": True,
            "mode": "photo",
            "preview_image": url_for("static", filename=preview_rel_path),
            "user_photo_url": url_for("static", filename=saved_rel_photo),
            "note": note_text
        })
    else:
        # AI Model Try-on
        preview_out = f"tryon_model_{current_user.id}_{timestamp}.jpg"
        preview_rel_path, note_text, err = render_model_tryon(model_id, outfit_items, preview_out)

        if err or not preview_rel_path:
            return jsonify({
                "success": False,
                "error": err or "AI Model try-on inference failed. Please check inference service status."
            })

        return jsonify({
            "success": True,
            "mode": "model",
            "preview_image": url_for("static", filename=preview_rel_path),
            "note": note_text
        })


@studio_bp.route("/outfit-studio/mark-worn", methods=["POST"])
@login_required
def mark_worn():
    """
    Explicit Worn History Workflow:
    Only explicit confirmation creates a worn-history record.
    Automatically moves worn items to 'Worn / Needs Washing'.
    """
    outfit_id = request.form.get("outfit_id")
    date_worn_str = request.form.get("date_worn") or date.today().strftime("%Y-%m-%d")
    notes = request.form.get("notes", "").strip()

    try:
        date_worn = datetime.strptime(date_worn_str, "%Y-%m-%d").date()
    except ValueError:
        date_worn = date.today()

    if not outfit_id:
        flash("Please select an outfit to mark as worn.", "warning")
        return redirect(url_for("studio.index") + "#calendar")

    outfit = Outfit.query.filter_by(id=outfit_id, user_id=current_user.id).first()
    if not outfit:
        flash("The selected outfit could not be found. Please generate or select an outfit from your studio.", "warning")
        return redirect(url_for("studio.index") + "#calendar")

    item_ids = [oi.item_id for oi in outfit.outfit_items if oi.item_id]

    worn_entry = WornHistory(
        user_id=current_user.id,
        outfit_id=outfit.id,
        item_ids_json=json.dumps(item_ids),
        date_worn=date_worn,
        notes=notes
    )
    db.session.add(worn_entry)

    # Update item availability: Tops, Bottoms, Dresses move to 'Worn / Needs Washing'
    for item in outfit.items:
        if item.category in ["Tops", "Bottoms", "Dresses / One-piece"]:
            item.availability_status = "Worn / Needs Washing"

    db.session.commit()

    # Award points (+25 Fashion Points for confirmed wear)
    award_points(
        user_id=current_user.id,
        activity_type="CONFIRM_WEAR",
        points=25,
        description=f"Logged wear for '{outfit.title}' on {date_worn.strftime('%b %d')}",
        reference_id=f"wear_{worn_entry.id}"
    )

    flash(f"Outfit marked as worn on {date_worn.strftime('%B %d, %Y')}! (+25 Fashion Points)", "success")
    return redirect(url_for("studio.index", year=date_worn.year, month=date_worn.month, selected_date=date_worn_str) + "#calendar")


@studio_bp.route("/outfit-studio/calendar/delete-wear/<int:wear_id>", methods=["POST"])
@login_required
def delete_wear(wear_id):
    wear = WornHistory.query.filter_by(id=wear_id, user_id=current_user.id).first_or_404()
    d_worn = wear.date_worn
    db.session.delete(wear)
    db.session.commit()
    flash("Wear record removed. Historical statistics updated.", "info")
    return redirect(url_for("studio.index", year=d_worn.year, month=d_worn.month) + "#calendar")

