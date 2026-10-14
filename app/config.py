import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "wardrobe-iq-dev-secret-key-2026-editorial-v1")
    
    # Ensure absolute sqlite path with forward slashes
    default_db = (INSTANCE_DIR / "wardrobe_iq.db").as_posix()
    raw_db_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_db_url or "instance" in raw_db_url:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{default_db}"
    else:
        # Render / Heroku compatibility: SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
        if raw_db_url.startswith("postgres://"):
            raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = raw_db_url
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = (BASE_DIR / "app" / "static" / "uploads").as_posix()
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    
    # Optional external AI & service configurations
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
    VIRTUAL_TRYON_API_KEY = os.getenv("VIRTUAL_TRYON_API_KEY", "")
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    SHOPPING_API_KEY = os.getenv("SHOPPING_API_KEY", "")
