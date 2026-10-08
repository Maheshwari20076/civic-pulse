"""Application configuration. All secrets come from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    # --- Database --------------------------------------------------------
    # "mysql" is the deployment target (XAMPP). "sqlite" needs no DB server.
    DB_DRIVER = os.getenv("DB_DRIVER", "mysql").lower()
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "civicpulse")
    SQLITE_PATH = os.path.join(BASE_DIR, "database", "civicpulse.sqlite3")

    # --- AI --------------------------------------------------------------
    # Optional: without a key the app runs on the deterministic fallback engine.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # --- Uploads ---------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "webp", "gif"})
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB per upload

    # --- Clustering / priority tuning -------------------------------------
    CLUSTER_RADIUS_M = int(os.getenv("CLUSTER_RADIUS_M", "120"))
    CLUSTER_WINDOW_DAYS = int(os.getenv("CLUSTER_WINDOW_DAYS", "30"))
    CLUSTER_MIN_SCORE = float(os.getenv("CLUSTER_MIN_SCORE", "0.55"))
    ESCALATION_HOURS = int(os.getenv("ESCALATION_HOURS", "48"))
    SIGNAL_RADIUS_M = int(os.getenv("SIGNAL_RADIUS_M", "900"))
    SIGNAL_WINDOW_HOURS = int(os.getenv("SIGNAL_WINDOW_HOURS", "168"))
