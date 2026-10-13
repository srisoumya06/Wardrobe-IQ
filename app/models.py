from datetime import datetime, date
import json
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    preference = db.relationship("UserPreference", backref="user", uselist=False, cascade="all, delete-orphan")
    items = db.relationship("WardrobeItem", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    outfits = db.relationship("Outfit", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    worn_history = db.relationship("WornHistory", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    point_transactions = db.relationship("PointTransaction", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    packing_trips = db.relationship("PackingTrip", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    weekly_plans = db.relationship("WeeklyPlan", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def total_points(self):
        result = db.session.query(db.func.sum(PointTransaction.points)).filter(PointTransaction.user_id == self.id).scalar()
        return result or 0

    @property
    def current_level_info(self):
        pts = self.total_points
        levels = [
            ("Styling Novice", 0, 100),
            ("Wardrobe Curator", 100, 300),
            ("Chic Strategist", 300, 600),
            ("Capsule Connoisseur", 600, 1000),
            ("Fashion Maestro", 1000, 2000),
            ("Couture Icon", 2000, 5000),
        ]
        for name, min_p, max_p in levels:
            if pts < max_p or max_p == 5000:
                progress = min(100, int(((pts - min_p) / max(1, (max_p - min_p))) * 100)) if pts >= min_p else 0
                return {
                    "level_name": name,
                    "points": pts,
                    "min_points": min_p,
                    "next_level_points": max_p,
                    "progress_pct": progress,
                    "points_to_next": max(0, max_p - pts)
                }
        return {
            "level_name": "Couture Icon",
            "points": pts,
            "min_points": 2000,
            "next_level_points": 5000,
            "progress_pct": 100,
            "points_to_next": 0
        }


class UserPreference(db.Model):
    __tablename__ = "user_preferences"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    preferred_styles = db.Column(db.String(256), default="Casual, Minimalist, Smart Casual")
    favourite_colors = db.Column(db.String(256), default="Warm Ivory, Deep Forest Green, Navy Blue, Charcoal")
    preferred_fits = db.Column(db.String(64), default="Balanced / Tailored")
    common_occasions = db.Column(db.String(256), default="College, Casual Outings, Smart Casual")
    comfort_preference = db.Column(db.String(64), default="Balanced Style & Comfort")
    gender_preference = db.Column(db.String(32), nullable=True) # "womens", "mens", "unisex", or None (auto-detect)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WardrobeItem(db.Model):
    __tablename__ = "wardrobe_items"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    image_path = db.Column(db.String(256), nullable=False)
    category = db.Column(db.String(64), nullable=False, index=True) # Tops, Bottoms, Dresses / One-piece, Footwear, Accessories
    subcategory = db.Column(db.String(64), nullable=True)
    color = db.Column(db.String(64), nullable=False)
    color_hex = db.Column(db.String(16), default="#8B806E")
    pattern = db.Column(db.String(64), default="Solid")
    style = db.Column(db.String(64), default="Casual")
    season = db.Column(db.String(64), default="All-Season")
    occasions = db.Column(db.String(256), default="Casual")
    brand = db.Column(db.String(64), nullable=True)
    size = db.Column(db.String(32), nullable=True)
    fabric = db.Column(db.String(64), nullable=True)
    purchase_price = db.Column(db.Float, nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    weight_grams = db.Column(db.Float, default=250.0) # Used for packing luggage calculation
    notes = db.Column(db.Text, nullable=True)
    availability_status = db.Column(db.String(32), default="Available", index=True) # Available, Worn / Needs Washing, In Laundry
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_available(self):
        return self.availability_status == "Available"


class Outfit(db.Model):
    __tablename__ = "outfits"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(128), default="Curated Look")
    occasion = db.Column(db.String(64), default="Casual")
    style = db.Column(db.String(64), default="Smart Casual")
    score = db.Column(db.Float, default=88.0)
    why_explanation = db.Column(db.Text, nullable=True)
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Items in this outfit
    outfit_items = db.relationship("OutfitItem", backref="outfit", cascade="all, delete-orphan")
    
    def get_item_by_slot(self, slot):
        for oi in self.outfit_items:
            if oi.slot == slot:
                return oi.item
        return None

    @property
    def items(self):
        return [oi.item for oi in self.outfit_items if oi.item is not None]


class OutfitItem(db.Model):
    __tablename__ = "outfit_items"
    
    id = db.Column(db.Integer, primary_key=True)
    outfit_id = db.Column(db.Integer, db.ForeignKey("outfits.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True)
    slot = db.Column(db.String(32), nullable=False) # top, bottom, dress, footwear, accessory
    
    item = db.relationship("WardrobeItem")


class WornHistory(db.Model):
    __tablename__ = "worn_history"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    outfit_id = db.Column(db.Integer, db.ForeignKey("outfits.id", ondelete="SET NULL"), nullable=True)
    item_ids_json = db.Column(db.Text, nullable=False) # JSON list e.g. "[1, 4, 8]" preserving history
    date_worn = db.Column(db.Date, nullable=False, default=date.today, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    outfit = db.relationship("Outfit")
    
    @property
    def item_ids(self):
        try:
            return json.loads(self.item_ids_json)
        except Exception:
            return []

    def get_items(self):
        ids = self.item_ids
        if not ids:
            return []
        return WardrobeItem.query.filter(WardrobeItem.id.in_(ids)).all()


class PointTransaction(db.Model):
    __tablename__ = "point_transactions"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)
    activity_type = db.Column(db.String(64), nullable=False, index=True)
    reference_id = db.Column(db.String(128), nullable=True) # Key to prevent duplicate points
    description = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PackingTrip(db.Model):
    __tablename__ = "packing_trips"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    destination = db.Column(db.String(128), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    trip_purpose = db.Column(db.String(128), default="Leisure / Vacation")
    activities = db.Column(db.Text, default="City walk, Casual dining, Sightseeing")
    luggage_limit_kg = db.Column(db.Float, default=15.0)
    laundry_access = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship("PackingItem", backref="trip", cascade="all, delete-orphan")
    
    @property
    def duration_days(self):
        if self.end_date and self.start_date:
            delta = (self.end_date - self.start_date).days + 1
            return max(1, delta)
        return 1

    @property
    def packed_count(self):
        return sum(1 for i in self.items if i.is_packed)

    @property
    def total_count(self):
        return len(self.items)

    @property
    def total_weight_kg(self):
        total_g = sum(i.weight_grams or 250.0 for i in self.items)
        return round(total_g / 1000.0, 2)


class PackingItem(db.Model):
    __tablename__ = "packing_items"
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("packing_trips.id"), nullable=False, index=True)
    wardrobe_item_id = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True)
    custom_name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    is_packed = db.Column(db.Boolean, default=False)
    weight_grams = db.Column(db.Float, default=250.0)
    
    wardrobe_item = db.relationship("WardrobeItem")


# Association table for PlannedOutfit and WardrobeItem (Many-to-Many)
planned_outfit_items = db.Table(
    "planned_outfit_items",
    db.Column("planned_outfit_id", db.Integer, db.ForeignKey("planned_outfits.id", ondelete="CASCADE"), primary_key=True),
    db.Column("item_id", db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="CASCADE"), primary_key=True)
)


class WeeklyPlan(db.Model):
    __tablename__ = "weekly_plans"
    __table_args__ = (
        db.UniqueConstraint("user_id", "week_start_date", name="uq_user_week"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start_date = db.Column(db.Date, nullable=False, index=True) # Monday of the week
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    outfits = db.relationship("PlannedOutfit", backref="weekly_plan", cascade="all, delete-orphan", order_by="PlannedOutfit.day_of_week, PlannedOutfit.slot_index")

    def get_outfits_for_day(self, day_index):
        """Returns outfits planned for day_index (0=Monday, 6=Sunday), max 3."""
        return [o for o in self.outfits if o.day_of_week == day_index]

    @property
    def total_outfits_count(self):
        return len(self.outfits)

    @property
    def days_planned_count(self):
        days_with_outfits = {o.day_of_week for o in self.outfits}
        return len(days_with_outfits)


class PlannedOutfit(db.Model):
    __tablename__ = "planned_outfits"

    id = db.Column(db.Integer, primary_key=True)
    weekly_plan_id = db.Column(db.Integer, db.ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False) # 0=Monday, 1=Tuesday, ..., 6=Sunday
    slot_index = db.Column(db.Integer, nullable=False, default=1) # 1, 2, or 3
    title = db.Column(db.String(128), default="Planned Look") # e.g. "Work Look", "Dinner Ensemble"
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Selected wardrobe items (many-to-many)
    items = db.relationship("WardrobeItem", secondary=planned_outfit_items, backref=db.backref("planned_outfits", lazy="dynamic"))

    @property
    def item_ids(self):
        return [i.id for i in self.items]

    def get_items_by_category(self):
        categorized = {
            "Tops": [],
            "Bottoms": [],
            "Dresses / One-piece": [],
            "Footwear": [],
            "Accessories": []
        }
        for item in self.items:
            cat = item.category
            if cat in categorized:
                categorized[cat].append(item)
            else:
                categorized["Accessories"].append(item)
        return categorized

