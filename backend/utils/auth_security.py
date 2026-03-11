import hashlib
import re
import uuid
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from email_validator import EmailNotValidError, validate_email
from flask import current_app, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import Session, db


def token_fingerprint(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email):
    return (email or "").strip().lower()


def validate_email_address(email):
    try:
        normalized = validate_email(email, check_deliverability=False).normalized
        return True, normalized, None
    except EmailNotValidError as exc:
        return False, None, str(exc)


def validate_password_policy(password):
    if not password or len(password) < 10:
        return False, "Password must be at least 10 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must include at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must include at least one number."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must include at least one special character."
    return True, None


def _get_serializer():
    secret = current_app.config["OAUTH_STATE_SECRET"]
    return URLSafeTimedSerializer(secret_key=secret, salt="oauth-state-v1")


def sanitize_frontend_url(candidate):
    default_url = current_app.config["FRONTEND_URL"]
    if not candidate:
        return default_url

    try:
        parsed = urlparse(candidate)
        origin = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return default_url

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return default_url

    allowed_origins = set(current_app.config.get("FRONTEND_ALLOWED_ORIGINS", []))
    if origin not in allowed_origins:
        return default_url

    return candidate


def build_url_with_query(url, params):
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({k: v for k, v in params.items() if v is not None})
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query),
            parsed.fragment,
        )
    )


def create_oauth_state(provider, mode, user_id=None, redirect_url=None):
    payload = {
        "nonce": str(uuid.uuid4()),
        "provider": provider,
        "mode": mode,
        "issued_at": int(datetime.utcnow().timestamp()),
    }
    if user_id:
        payload["user_id"] = user_id
    if redirect_url:
        payload["redirect_url"] = sanitize_frontend_url(redirect_url)

    return _get_serializer().dumps(payload)


def verify_oauth_state(state_token, expected_provider=None, expected_mode=None):
    if not state_token:
        return None, "Missing OAuth state."

    max_age = current_app.config.get("OAUTH_STATE_MAX_AGE_SECONDS", 600)

    try:
        payload = _get_serializer().loads(state_token, max_age=max_age)
    except SignatureExpired:
        return None, "OAuth state expired."
    except BadSignature:
        return None, "Invalid OAuth state."

    if expected_provider and payload.get("provider") != expected_provider:
        return None, "OAuth state provider mismatch."
    if expected_mode and payload.get("mode") != expected_mode:
        return None, "OAuth state mode mismatch."

    return payload, None


def cleanup_expired_sessions():
    deleted = Session.query.filter(Session.expires_at < datetime.utcnow()).delete(synchronize_session=False)
    return deleted


def create_user_session(user_id, access_token, expires_at):
    cleanup_expired_sessions()
    fingerprint = token_fingerprint(access_token)
    raw_ip = request.headers.get("X-Forwarded-For", request.remote_addr) or ""
    client_ip = raw_ip.split(",")[0].strip()
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token=fingerprint,
        user_agent=(request.headers.get("User-Agent") or "")[:500],
        ip_address=client_ip[:50],
        expires_at=expires_at,
    )
    db.session.add(session)
    return session


def extract_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    return token or None


def extract_access_token_from_request():
    token = extract_bearer_token()
    if token:
        return token
    cookie_name = current_app.config.get("JWT_ACCESS_COOKIE_NAME", "access_token_cookie")
    return request.cookies.get(cookie_name)


def is_session_active(raw_token):
    if not raw_token:
        return False
    fingerprint = token_fingerprint(raw_token)
    active = Session.query.filter(
        Session.token == fingerprint, Session.expires_at > datetime.utcnow()
    ).first()
    return active is not None


def revoke_session(raw_token):
    if not raw_token:
        return 0
    fingerprint = token_fingerprint(raw_token)
    deleted = Session.query.filter_by(token=fingerprint).delete(synchronize_session=False)
    return deleted
