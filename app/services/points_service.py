from datetime import datetime, date
from app.models import db, PointTransaction

def award_points(user_id, activity_type, points, description, reference_id=None):
    """
    Awards fashion points to user with idempotency check against reference_id.
    Prevents duplicate points for the same action or page refresh.
    Returns (success: bool, points_awarded: int, message: str)
    """
    if reference_id:
        existing = PointTransaction.query.filter_by(
            user_id=user_id,
            activity_type=activity_type,
            reference_id=str(reference_id)
        ).first()
        if existing:
            return False, 0, "Points already earned for this activity."

    transaction = PointTransaction(
        user_id=user_id,
        points=points,
        activity_type=activity_type,
        reference_id=str(reference_id) if reference_id else None,
        description=description,
        created_at=datetime.utcnow()
    )
    db.session.add(transaction)
    db.session.commit()
    return True, points, f"+{points} Fashion Points: {description}"
