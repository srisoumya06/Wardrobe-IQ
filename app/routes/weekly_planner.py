import json
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, WardrobeItem, WeeklyPlan, PlannedOutfit

weekly_planner_bp = Blueprint("weekly_planner", __name__)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_monday_of_week(target_date):
    """Returns the Monday date for any given date."""
    return target_date - timedelta(days=target_date.weekday())


@weekly_planner_bp.route("/weekly-planner")
@login_required
def index():
    today = date.today()
    default_monday = get_monday_of_week(today)

    week_param = request.args.get("week")
    try:
        if week_param:
            parsed_date = datetime.strptime(week_param, "%Y-%m-%d").date()
            monday = get_monday_of_week(parsed_date)
        else:
            monday = default_monday
    except (ValueError, TypeError):
        monday = default_monday

    prev_week_monday = monday - timedelta(days=7)
    next_week_monday = monday + timedelta(days=7)
    sunday = monday + timedelta(days=6)
    is_current_week = (monday == default_monday)

    # Week heading formatted for fashion-editorial aesthetic
    week_heading = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')}"

    # Query persistent plan for current user and this specific week
    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, week_start_date=monday).first()

    # Build 7-day data structure
    days_data = []
    for i in range(7):
        day_date = monday + timedelta(days=i)
        outfits = plan.get_outfits_for_day(i) if plan else []
        days_data.append({
            "day_index": i,
            "name": DAY_NAMES[i],
            "date": day_date,
            "date_str": day_date.strftime("%Y-%m-%d"),
            "date_formatted": day_date.strftime("%a, %b %d"),
            "date_full": day_date.strftime("%A, %B %d, %Y"),
            "is_today": (day_date == today),
            "outfits": outfits,
            "outfit_count": len(outfits),
            "is_full": len(outfits) >= 3,
            "can_add": len(outfits) < 3
        })

    # Summary statistics
    days_planned_count = sum(1 for d in days_data if d["outfit_count"] > 0)
    total_outfits_count = sum(d["outfit_count"] for d in days_data)
    completion_pct = round((days_planned_count / 7.0) * 100)

    # Day selection (default to today if in current week, else Monday 0)
    try:
        selected_day_arg = request.args.get("day")
        if selected_day_arg is not None:
            selected_day_idx = int(selected_day_arg)
        else:
            selected_day_idx = today.weekday() if is_current_week else 0
        if selected_day_idx < 0 or selected_day_idx > 6:
            selected_day_idx = 0
    except (ValueError, TypeError):
        selected_day_idx = 0

    # User's Digital Closet items (strictly scoped to current_user.id)
    user_items = WardrobeItem.query.filter_by(user_id=current_user.id).order_by(
        WardrobeItem.category, WardrobeItem.name
    ).all()

    closet_by_category = {
        "Tops": [i for i in user_items if i.category == "Tops"],
        "Bottoms": [i for i in user_items if i.category == "Bottoms"],
        "Dresses / One-piece": [i for i in user_items if i.category == "Dresses / One-piece"],
        "Footwear": [i for i in user_items if i.category == "Footwear"],
        "Accessories": [i for i in user_items if i.category == "Accessories"]
    }

    return render_template(
        "weekly_planner/index.html",
        monday=monday,
        sunday=sunday,
        week_str=monday.strftime("%Y-%m-%d"),
        prev_week_str=prev_week_monday.strftime("%Y-%m-%d"),
        next_week_str=next_week_monday.strftime("%Y-%m-%d"),
        current_week_str=default_monday.strftime("%Y-%m-%d"),
        is_current_week=is_current_week,
        week_heading=week_heading,
        days_data=days_data,
        selected_day_idx=selected_day_idx,
        selected_day=days_data[selected_day_idx],
        days_planned_count=days_planned_count,
        total_outfits_count=total_outfits_count,
        completion_pct=completion_pct,
        user_items=user_items,
        closet_by_category=closet_by_category,
        total_items_count=len(user_items)
    )


@weekly_planner_bp.route("/weekly-planner/save-outfit", methods=["POST"])
@login_required
def save_outfit():
    week_str = request.form.get("week")
    today = date.today()
    default_monday = get_monday_of_week(today)

    try:
        parsed_date = datetime.strptime(week_str, "%Y-%m-%d").date() if week_str else default_monday
        monday = get_monday_of_week(parsed_date)
    except (ValueError, TypeError):
        monday = default_monday

    try:
        day_of_week = int(request.form.get("day_of_week", 0))
        if day_of_week < 0 or day_of_week > 6:
            day_of_week = 0
    except (ValueError, TypeError):
        day_of_week = 0

    outfit_id = request.form.get("outfit_id", type=int)
    title = (request.form.get("title") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    # Extract chosen item IDs
    item_ids = request.form.getlist("item_ids", type=int)
    if not item_ids:
        # Also check for comma-separated string if sent via hidden field
        raw_ids = request.form.get("selected_item_ids_str", "")
        if raw_ids:
            try:
                item_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]
            except Exception:
                item_ids = []

    day_name = DAY_NAMES[day_of_week]

    if not item_ids:
        flash(f"Please select at least one wardrobe item or accessory for your outfit on {day_name}.", "warning")
        return redirect(url_for("weekly_planner.index", week=monday.strftime("%Y-%m-%d"), day=day_of_week))

    # Strict user ownership verification: all items must belong to current_user
    selected_items = WardrobeItem.query.filter(
        WardrobeItem.id.in_(item_ids),
        WardrobeItem.user_id == current_user.id
    ).all()

    if len(selected_items) != len(set(item_ids)):
        flash("One or more selected items could not be validated in your closet.", "danger")
        return redirect(url_for("weekly_planner.index", week=monday.strftime("%Y-%m-%d"), day=day_of_week))

    # Retrieve or create WeeklyPlan for current_user & week_start_date
    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, week_start_date=monday).first()
    if not plan:
        plan = WeeklyPlan(user_id=current_user.id, week_start_date=monday)
        db.session.add(plan)
        db.session.flush()

    if outfit_id:
        # EDITING existing outfit
        outfit = PlannedOutfit.query.filter_by(
            id=outfit_id,
            weekly_plan_id=plan.id,
            user_id=current_user.id
        ).first()

        if not outfit:
            flash("The outfit set you attempted to edit could not be found.", "danger")
            return redirect(url_for("weekly_planner.index", week=monday.strftime("%Y-%m-%d"), day=day_of_week))

        outfit.title = title or outfit.title or f"Look {outfit.slot_index}"
        outfit.notes = notes
        outfit.items = selected_items
        db.session.commit()
        flash(f"Updated '{outfit.title}' for {day_name} successfully!", "success")

    else:
        # CREATING new outfit set - strictly enforce maximum of 3 per day
        existing_count = PlannedOutfit.query.filter_by(
            weekly_plan_id=plan.id,
            day_of_week=day_of_week
        ).count()

        if existing_count >= 3:
            flash(f"Daily limit reached: You can plan a maximum of 3 outfit sets for {day_name}.", "warning")
            return redirect(url_for("weekly_planner.index", week=monday.strftime("%Y-%m-%d"), day=day_of_week))

        slot_index = existing_count + 1
        default_title = f"Look {slot_index}"
        new_outfit = PlannedOutfit(
            weekly_plan_id=plan.id,
            user_id=current_user.id,
            day_of_week=day_of_week,
            slot_index=slot_index,
            title=title or default_title,
            notes=notes
        )
        new_outfit.items = selected_items
        db.session.add(new_outfit)
        db.session.commit()
        flash(f"Added '{new_outfit.title}' to your plan for {day_name}!", "success")

    return redirect(url_for("weekly_planner.index", week=monday.strftime("%Y-%m-%d"), day=day_of_week))


@weekly_planner_bp.route("/weekly-planner/delete-outfit/<int:outfit_id>", methods=["POST"])
@login_required
def delete_outfit(outfit_id):
    outfit = PlannedOutfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    week_str = outfit.weekly_plan.week_start_date.strftime("%Y-%m-%d")
    day_idx = outfit.day_of_week
    outfit_title = outfit.title

    db.session.delete(outfit)
    db.session.commit()

    flash(f"Removed '{outfit_title}' from your weekly plan.", "info")
    return redirect(url_for("weekly_planner.index", week=week_str, day=day_idx))


@weekly_planner_bp.route("/weekly-planner/clear-week", methods=["POST"])
@login_required
def clear_week():
    week_str = request.form.get("week")
    today = date.today()
    default_monday = get_monday_of_week(today)

    try:
        parsed_date = datetime.strptime(week_str, "%Y-%m-%d").date() if week_str else default_monday
        monday = get_monday_of_week(parsed_date)
    except (ValueError, TypeError):
        monday = default_monday

    plan = WeeklyPlan.query.filter_by(user_id=current_user.id, week_start_date=monday).first()
    if plan:
        db.session.delete(plan)
        db.session.commit()
        flash(f"Cleared the outfit plan for the week of {monday.strftime('%B %d, %Y')}. Your Digital Closet, wear history, and other weeks remain unchanged.", "info")
    else:
        flash("No active plan was found for this week.", "info")

    return redirect(url_for("weekly_planner.index", week=monday.strftime("%Y-%m-%d")))


@weekly_planner_bp.route("/weekly-planner/outfit/<int:outfit_id>", methods=["GET"])
@login_required
def get_outfit_json(outfit_id):
    outfit = PlannedOutfit.query.filter_by(id=outfit_id, user_id=current_user.id).first_or_404()
    return jsonify({
        "success": True,
        "id": outfit.id,
        "title": outfit.title,
        "notes": outfit.notes or "",
        "day_of_week": outfit.day_of_week,
        "slot_index": outfit.slot_index,
        "item_ids": [i.id for i in outfit.items]
    })
