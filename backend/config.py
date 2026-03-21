import os
from datetime import timedelta


def _get_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_csv(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config:
    """Base configuration"""
    ENV_NAME = os.environ.get("FLASK_ENV", "development")
    DEBUG = False
    TESTING = False

    SERVERLESS_MODE = _get_bool("SERVERLESS_MODE", False)
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    ADMIN_SECRET_CODE = os.environ.get("ADMIN_SECRET_CODE", "SuperSecret123!")  # Added for admin panel access
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or ("sqlite:////tmp/creatoros.db" if SERVERLESS_MODE else "sqlite:///creatorOS.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "dev-jwt-secret-key-change-in-production"
    AUTH_ACCESS_TOKEN_DAYS = _get_int("AUTH_ACCESS_TOKEN_DAYS", 30)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=AUTH_ACCESS_TOKEN_DAYS)
    JWT_TOKEN_LOCATION = _get_csv("JWT_TOKEN_LOCATION", "headers")
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_ACCESS_COOKIE_NAME = os.environ.get("JWT_ACCESS_COOKIE_NAME", "access_token_cookie")
    JWT_COOKIE_SECURE = _get_bool("JWT_COOKIE_SECURE", False)
    JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = _get_bool("JWT_COOKIE_CSRF_PROTECT", True)
    AUTH_EXPOSE_ACCESS_TOKEN = _get_bool("AUTH_EXPOSE_ACCESS_TOKEN", True)
    AUTH_SESSION_CHECK = _get_bool("AUTH_SESSION_CHECK", not SERVERLESS_MODE)

    # Database engine options
    DB_POOL_SIZE = _get_int("DB_POOL_SIZE", 5)
    DB_MAX_OVERFLOW = _get_int("DB_MAX_OVERFLOW", 10)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": DB_POOL_SIZE,
        "max_overflow": DB_MAX_OVERFLOW,
    }
    DB_AUTO_CREATE = _get_bool("DB_AUTO_CREATE", True)

    # Request limits and rate limiting
    MAX_CONTENT_LENGTH = _get_int("MAX_CONTENT_LENGTH", 25 * 1024 * 1024)  # 25MB
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per day;50 per hour")
    RATELIMIT_AUTH = os.environ.get("RATELIMIT_AUTH", "10 per minute")
    RATELIMIT_AI = os.environ.get("RATELIMIT_AI", "30 per hour")
    RATELIMIT_POSTS = os.environ.get("RATELIMIT_POSTS", "60 per hour")
    RATELIMIT_UPLOAD = os.environ.get("RATELIMIT_UPLOAD", "20 per hour")
    RATELIMIT_FEEDBACK = os.environ.get("RATELIMIT_FEEDBACK", "10 per hour")
    RATELIMIT_ADMIN = os.environ.get("RATELIMIT_ADMIN", "60 per minute")
    RATELIMIT_NOTIFICATIONS = os.environ.get("RATELIMIT_NOTIFICATIONS", "120 per minute")
    RATELIMIT_SYNC = os.environ.get("RATELIMIT_SYNC", "10 per hour")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = _get_bool("RATELIMIT_HEADERS_ENABLED", True)

    # API / CORS
    API_REQUEST_TIMEOUT_SECONDS = _get_int("API_REQUEST_TIMEOUT_SECONDS", 15)
    CORS_ALLOWED_ORIGINS = _get_csv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
    )

    # Frontend redirects for OAuth callbacks
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8000")
    FRONTEND_ALLOWED_ORIGINS = _get_csv("FRONTEND_ALLOWED_ORIGINS", FRONTEND_URL)

    # OAuth state signing
    OAUTH_STATE_SECRET = os.environ.get("OAUTH_STATE_SECRET") or JWT_SECRET_KEY
    OAUTH_STATE_MAX_AGE_SECONDS = _get_int("OAUTH_STATE_MAX_AGE_SECONDS", 600)

    # OAuth Credentials
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    TIKTOK_CLIENT_ID = os.environ.get("TIKTOK_CLIENT_ID", "")
    TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")

    INSTAGRAM_CLIENT_ID = os.environ.get("INSTAGRAM_CLIENT_ID", "")
    INSTAGRAM_CLIENT_SECRET = os.environ.get("INSTAGRAM_CLIENT_SECRET", "")
    INSTAGRAM_TEST_MODE = _get_bool("INSTAGRAM_TEST_MODE", False)

    TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
    TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
    TWITTER_CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID") or TWITTER_API_KEY
    TWITTER_CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET") or TWITTER_API_SECRET
    TWITTER_SCOPES = os.environ.get("TWITTER_SCOPES", "tweet.read users.read offline.access")

    LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_SCOPES = os.environ.get("LINKEDIN_SCOPES", "openid profile email")

    # AI generation (OpenAI-compatible)
    AI_ENABLED = _get_bool("AI_ENABLED", True)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_TIMEOUT_SECONDS = _get_int("OPENAI_TIMEOUT_SECONDS", 30)

    # Observability
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "text")
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

    # Cache
    REDIS_URL = os.environ.get("REDIS_URL", "")

    # Storage
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "")
    STORAGE_TEMP_DIR = os.environ.get("STORAGE_TEMP_DIR", "")
    S3_BUCKET = os.environ.get("S3_BUCKET", "")
    S3_REGION = os.environ.get("S3_REGION", "")
    S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "")
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")

    # Callback URLs
    GOOGLE_CALLBACK_URL = os.environ.get("GOOGLE_CALLBACK_URL") or "http://localhost:5000/api/auth/google/callback"
    GOOGLE_PLATFORM_CALLBACK_URL = os.environ.get("GOOGLE_PLATFORM_CALLBACK_URL") or "http://localhost:5000/api/platforms/youtube/callback"
    TIKTOK_CALLBACK_URL = os.environ.get("TIKTOK_CALLBACK_URL") or "http://localhost:5000/api/auth/tiktok/callback"
    TIKTOK_PLATFORM_CALLBACK_URL = os.environ.get("TIKTOK_PLATFORM_CALLBACK_URL") or "http://localhost:5000/api/platforms/tiktok/callback"
    INSTAGRAM_CALLBACK_URL = os.environ.get("INSTAGRAM_CALLBACK_URL") or "http://localhost:5000/api/platforms/instagram/callback"
    TWITTER_CALLBACK_URL = os.environ.get("TWITTER_CALLBACK_URL") or "http://localhost:5000/api/platforms/twitter/callback"
    LINKEDIN_CALLBACK_URL = os.environ.get("LINKEDIN_CALLBACK_URL") or "http://localhost:5000/api/platforms/linkedin/callback"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    JWT_COOKIE_SECURE = True
    AUTH_EXPOSE_ACCESS_TOKEN = _get_bool("AUTH_EXPOSE_ACCESS_TOKEN", False)


def validate_production_config(app):
    """Fail fast if required auth settings are missing in production."""
    if app.config.get("ENV_NAME") != "production":
        return
    if app.config.get("SERVERLESS_MODE"):
        return

    missing = []
    insecure_defaults = []

    def _is_placeholder(value):
        return str(value or "").strip().lower() in {
            "change-me",
            "changeme",
            "replace-me",
            "placeholder",
            "password",
        }

    required = [
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "OAUTH_STATE_SECRET",
        "ADMIN_SECRET_CODE",
        "FRONTEND_URL",
        "CORS_ALLOWED_ORIGINS",
        "FRONTEND_ALLOWED_ORIGINS",
    ]

    for key in required:
        value = app.config.get(key)
        if not value:
            missing.append(key)

    if app.config.get("SECRET_KEY", "").startswith("dev-secret-key"):
        insecure_defaults.append("SECRET_KEY")
    if app.config.get("JWT_SECRET_KEY", "").startswith("dev-jwt-secret-key"):
        insecure_defaults.append("JWT_SECRET_KEY")
    if app.config.get("ADMIN_SECRET_CODE", "") == "SuperSecret123!":
        insecure_defaults.append("ADMIN_SECRET_CODE")
    if _is_placeholder(app.config.get("SECRET_KEY")) or len(str(app.config.get("SECRET_KEY") or "")) < 32:
        insecure_defaults.append("SECRET_KEY")
    if _is_placeholder(app.config.get("JWT_SECRET_KEY")) or len(str(app.config.get("JWT_SECRET_KEY") or "")) < 32:
        insecure_defaults.append("JWT_SECRET_KEY")
    if _is_placeholder(app.config.get("OAUTH_STATE_SECRET")) or len(str(app.config.get("OAUTH_STATE_SECRET") or "")) < 32:
        insecure_defaults.append("OAUTH_STATE_SECRET")
    if _is_placeholder(app.config.get("ADMIN_SECRET_CODE")) or len(str(app.config.get("ADMIN_SECRET_CODE") or "")) < 12:
        insecure_defaults.append("ADMIN_SECRET_CODE")
    if "*" in (app.config.get("CORS_ALLOWED_ORIGINS") or []):
        insecure_defaults.append("CORS_ALLOWED_ORIGINS=*")
    if "cookies" in (app.config.get("JWT_TOKEN_LOCATION") or []) and not app.config.get("JWT_COOKIE_SECURE"):
        insecure_defaults.append("JWT_COOKIE_SECURE=false")
    db_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if db_uri.startswith("sqlite"):
        insecure_defaults.append("DATABASE_URL=sqlite")
    frontend_url = str(app.config.get("FRONTEND_URL") or "")
    if frontend_url.startswith("http://"):
        insecure_defaults.append("FRONTEND_URL=http")
    for origin in (app.config.get("CORS_ALLOWED_ORIGINS") or []):
        if str(origin).startswith("http://"):
            insecure_defaults.append("CORS_ALLOWED_ORIGINS=http")
            break
    if str(app.config.get("RATELIMIT_STORAGE_URI") or "").startswith("memory://"):
        insecure_defaults.append("RATELIMIT_STORAGE_URI=memory")
    if str(app.config.get("CELERY_BROKER_URL") or "").strip() == "":
        insecure_defaults.append("CELERY_BROKER_URL")
    if str(app.config.get("CELERY_RESULT_BACKEND") or "").strip() == "":
        insecure_defaults.append("CELERY_RESULT_BACKEND")
    if (app.config.get("STORAGE_BACKEND") or "local").lower() == "local":
        upload_dir = str(app.config.get("UPLOAD_DIR") or "")
        if not upload_dir:
            insecure_defaults.append("UPLOAD_DIR")

    if missing or insecure_defaults:
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if insecure_defaults:
            details.append(f"insecure_defaults={','.join(insecure_defaults)}")
        raise RuntimeError("Invalid production auth configuration: " + " ".join(details))


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
