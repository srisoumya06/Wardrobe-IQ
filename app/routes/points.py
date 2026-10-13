from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import PointTransaction

points_bp = Blueprint("points", __name__)

BADGES = [
    {
        "id": "welcome",
        "title": "Closet Pioneer",
        "description": "Created your digital wardrobe archive.",
        "icon": "✨",
        "min_pts": 50
    },
    {
        "id": "capsule",
        "title": "Capsule Curator",
        "description": "Organized and cataloged multiple garments.",
        "icon": "👔",
        "min_pts": 100
    },
    {
        "id": "stylist",
        "title": "Chic Strategist",
        "description": "Explored combinations and saved favorite looks.",
        "icon": "🎨",
        "min_pts": 200
    },
    {
        "id": "mindful_wearer",
        "title": "Mindful Wearer",
        "description": "Logged actual outfit wear history in calendar.",
        "icon": "📅",
        "min_pts": 350
    },
    {
        "id": "globetrotter",
        "title": "Globe Trotter",
        "description": "Packaged a capsule luggage list for travel.",
        "icon": "🧳",
        "min_pts": 500
    }
]

@points_bp.route("/points")
@login_required
def index():
    user_id = current_user.id
    transactions = PointTransaction.query.filter_by(user_id=user_id).order_by(PointTransaction.created_at.desc()).all()
    
    total_pts = current_user.total_points
    level_info = current_user.current_level_info

    # Calculate earned badges
    awarded_badges = []
    for b in BADGES:
        awarded_badges.append({
            **b,
            "is_unlocked": total_pts >= b["min_pts"]
        })

    return render_template(
        "points/index.html",
        total_pts=total_pts,
        level_info=level_info,
        transactions=transactions,
        badges=awarded_badges
    )
