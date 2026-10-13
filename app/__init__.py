import os
from flask import Flask, render_template
from flask_login import LoginManager
from app.config import Config
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access your Wardrobe IQ closet."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config, config_override=None):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if config_override:
        app.config.update(config_override)
    
    # Ensure instance and upload directories exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.closet import closet_bp
    from app.routes.laundry import laundry_bp
    from app.routes.outfit_studio import studio_bp
    from app.routes.fashion_lab import fashion_lab_bp
    from app.routes.chatbot import chatbot_bp
    from app.routes.shopping import shopping_bp
    from app.routes.trends import trends_bp
    from app.routes.packing import packing_bp
    from app.routes.points import points_bp
    from app.routes.weekly_planner import weekly_planner_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(closet_bp)
    app.register_blueprint(laundry_bp)
    app.register_blueprint(studio_bp)
    app.register_blueprint(fashion_lab_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(shopping_bp)
    app.register_blueprint(trends_bp)
    app.register_blueprint(packing_bp)
    app.register_blueprint(points_bp)
    app.register_blueprint(weekly_planner_bp)

    with app.app_context():
        db.create_all()
    
    # Currency filters and context
    from app.services.currency import format_inr, convert_usd_to_inr, get_usd_to_inr_rate_info

    @app.template_filter("inr")
    def inr_filter(value):
        return format_inr(value)

    @app.template_filter("usd_to_inr")
    def usd_to_inr_filter(value):
        return convert_usd_to_inr(value)

    # Global context processor
    @app.context_processor
    def inject_global_vars():
        from flask_login import current_user
        rate, is_live, rate_source = get_usd_to_inr_rate_info()
        context = {
            "app_name": "Wardrobe IQ",
            "tagline": "Your Closet, Smarter Everyday",
            "currency_rate_info": {
                "rate": rate,
                "is_live": is_live,
                "source": rate_source
            }
        }
        if current_user.is_authenticated:
            context["user_points"] = current_user.total_points
            context["user_level"] = current_user.current_level_info
        return context

    # Custom Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def file_too_large(e):
        return render_template("errors/413.html"), 413

    with app.app_context():
        db.create_all()

    return app
