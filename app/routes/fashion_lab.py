import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, UserPreference, WardrobeItem
from app.services.ai_vision import analyze_outfit_photo
from app.services.gap_analyzer import perform_wardrobe_gap_analysis
from app.services.points_service import award_points

fashion_lab_bp = Blueprint("fashion_lab", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@fashion_lab_bp.route("/fashion-lab", methods=["GET"])
@login_required
def index():
    user_id = current_user.id
    
    # 1. Personal Style Guide Preferences
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = UserPreference(user_id=user_id)
        db.session.add(pref)
        db.session.commit()

    # 2. Wardrobe Intelligence & Gap Analysis
    intelligence = perform_wardrobe_gap_analysis(user_id)

    return render_template(
        "fashion_lab/index.html",
        pref=pref,
        intelligence=intelligence,
        analysis=None
    )


@fashion_lab_bp.route("/fashion-lab/analyze-outfit", methods=["POST"])
@login_required
def analyze_outfit():
    user_id = current_user.id
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json"
    file = request.files.get("outfit_photo")
    
    if not file or not file.filename or not allowed_file(file.filename):
        err_msg = "Please upload a valid image file (JPG, PNG, WEBP)."
        if is_ajax:
            return jsonify({"success": False, "error": err_msg}), 400
        flash(err_msg, "danger")
        return redirect(url_for("fashion_lab.index"))

    try:
        orig_name = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"outfit_eval_{user_id}_{timestamp}_{orig_name}"
        
        upload_dir = os.path.join(fashion_lab_bp.root_path, "..", "static", "uploads")
        upload_dir = os.path.abspath(upload_dir)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Perform outfit evaluation
        user_items = WardrobeItem.query.filter_by(user_id=user_id).all()
        analysis_result = analyze_outfit_photo(file_path, user_items)
        analysis_result["image_url"] = f"uploads/{filename}"

        # Award points for styling evaluation (+20 Fashion Points)
        award_points(
            user_id=user_id,
            activity_type="ANALYZE_OUTFIT",
            points=20,
            description="Analyzed outfit photo in AI Fashion Lab",
            reference_id=f"eval_{timestamp}"
        )

        if is_ajax:
            return jsonify({"success": True, "analysis": analysis_result})

        pref = UserPreference.query.filter_by(user_id=user_id).first()
        intelligence = perform_wardrobe_gap_analysis(user_id)

        flash("Outfit evaluation complete! Style score and improvement suggestions generated.", "success")
        return render_template(
            "fashion_lab/index.html",
            pref=pref,
            intelligence=intelligence,
            analysis=analysis_result
        )
    except Exception as e:
        err_msg = f"Failed to analyze outfit image: {str(e)}"
        if is_ajax:
            return jsonify({"success": False, "error": err_msg}), 500
        flash(err_msg, "danger")
        return redirect(url_for("fashion_lab.index"))


@fashion_lab_bp.route("/fashion-lab/update-preferences", methods=["POST"])
@login_required
def update_preferences():
    user_id = current_user.id
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = UserPreference(user_id=user_id)
        db.session.add(pref)

    pref.preferred_styles = request.form.get("preferred_styles", pref.preferred_styles).strip()
    pref.favourite_colors = request.form.get("favourite_colors", pref.favourite_colors).strip()
    pref.preferred_fits = request.form.get("preferred_fits", pref.preferred_fits).strip()
    pref.common_occasions = request.form.get("common_occasions", pref.common_occasions).strip()
    pref.comfort_preference = request.form.get("comfort_preference", pref.comfort_preference).strip()
    if "gender_preference" in request.form:
        g_val = request.form.get("gender_preference", "").strip().lower()
        pref.gender_preference = g_val if g_val in ["womens", "mens", "unisex"] else None
    
    db.session.commit()
    flash("Personal style preferences updated successfully!", "success")
    return redirect(url_for("fashion_lab.index"))
