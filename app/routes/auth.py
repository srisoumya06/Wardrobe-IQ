from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, UserPreference, PointTransaction

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Validation
        if not username or len(username) < 3:
            flash("Username must be at least 3 characters long.", "danger")
            return render_template("auth/register.html")
            
        if not email or "@" not in email:
            flash("Please enter a valid email address.", "danger")
            return render_template("auth/register.html")
            
        if not password or len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html")
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")
            
        # Check existing user
        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "danger")
            return render_template("auth/register.html")
            
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html")
            
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Create default preferences
        pref = UserPreference(user_id=user.id)
        db.session.add(pref)
        
        # Award Welcome Fashion Points
        welcome_points = PointTransaction(
            user_id=user.id,
            points=50,
            activity_type="WELCOME_BONUS",
            reference_id=f"welcome_{user.id}",
            description="Welcome to Wardrobe IQ! Starting style points."
        )
        db.session.add(welcome_points)
        db.session.commit()
        
        login_user(user)
        flash("Welcome to Wardrobe IQ! Your digital wardrobe is ready.", "success")
        return redirect(url_for("dashboard.index"))
        
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
        
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        remember = True if request.form.get("remember") else False
        
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()
        
        if not user or not user.check_password(password):
            flash("Invalid username/email or password.", "danger")
            return render_template("auth/login.html")
            
        login_user(user, remember=remember)
        flash(f"Welcome back, {user.username}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))
        
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out. See you soon!", "info")
    return redirect(url_for("auth.login"))
