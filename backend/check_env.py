import os
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH)

REQUIRED = [
    "FLASK_ENV",
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "OAUTH_STATE_SECRET",
    "ADMIN_SECRET_CODE",
    "DATABASE_URL",
    "FRONTEND_URL",
    "CORS_ALLOWED_ORIGINS",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
]

PLACEHOLDERS = {
    "change-me",
    "changeme",
    "replace-me",
    "placeholder",
    "password",
}

missing = [key for key in REQUIRED if not os.environ.get(key)]
placeholders = [
    key
    for key in REQUIRED
    if (os.environ.get(key) or "").strip().lower() in PLACEHOLDERS
]

def _has_placeholder_hostname(value):
    raw = (value or "").strip().lower()
    return any(token in raw for token in ["example.com", "host", "user:password"])


suspect = []
db_url = os.environ.get("DATABASE_URL", "")
if db_url and _has_placeholder_hostname(db_url):
    suspect.append("DATABASE_URL")
redis_url = os.environ.get("REDIS_URL", "")
if redis_url and _has_placeholder_hostname(redis_url):
    suspect.append("REDIS_URL")
frontend_url = os.environ.get("FRONTEND_URL", "")
if frontend_url and "example.com" in frontend_url.lower():
    suspect.append("FRONTEND_URL")
google_cb = os.environ.get("GOOGLE_CALLBACK_URL", "")
if google_cb and "example.com" in google_cb.lower():
    suspect.append("GOOGLE_CALLBACK_URL")

print("Loaded .env:", ENV_PATH)
print("FLASK_ENV:", os.environ.get("FLASK_ENV"))
print("FRONTEND_URL:", os.environ.get("FRONTEND_URL"))
print("FRONTEND_ALLOWED_ORIGINS:", os.environ.get("FRONTEND_ALLOWED_ORIGINS"))
print("CORS_ALLOWED_ORIGINS:", os.environ.get("CORS_ALLOWED_ORIGINS"))
print("GOOGLE_CALLBACK_URL:", os.environ.get("GOOGLE_CALLBACK_URL"))
print("GOOGLE_PLATFORM_CALLBACK_URL:", os.environ.get("GOOGLE_PLATFORM_CALLBACK_URL"))

if missing:
    print("Missing required values:", ", ".join(missing))
if placeholders:
    print("Placeholder values detected:", ", ".join(placeholders))
if suspect:
    print("Potentially non-production values:", ", ".join(sorted(set(suspect))))
if not missing and not placeholders:
    print("All required values are present.")
