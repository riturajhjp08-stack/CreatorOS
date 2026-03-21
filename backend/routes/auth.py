from datetime import datetime, timedelta
import logging
import uuid

import requests
from flask import Blueprint, current_app, redirect, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
    set_access_cookies,
    unset_jwt_cookies,
)
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import limiter
from models import OAuthAccount, User, db
from utils.auth_security import (
    build_url_with_query,
    create_oauth_state,
    create_user_session,
    extract_access_token_from_request,
    is_session_active,
    normalize_email,
    revoke_session,
    sanitize_frontend_url,
    validate_email_address,
    validate_password_policy,
    verify_oauth_state,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

def _use_cookies():
    return "cookies" in (current_app.config.get("JWT_TOKEN_LOCATION") or [])

def _should_expose_token():
    if not _use_cookies():
        return True
    return bool(current_app.config.get("AUTH_EXPOSE_ACCESS_TOKEN", True))

def _issue_access_token(user_id):
    ttl_days = current_app.config.get("AUTH_ACCESS_TOKEN_DAYS", 30)
    expires_delta = timedelta(days=ttl_days)
    access_token = create_access_token(identity=user_id, expires_delta=expires_delta)
    expires_at = datetime.utcnow() + expires_delta
    return access_token, expires_at


def _json_body():
    return request.get_json(silent=True) or {}


@auth_bp.route("/register", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH", "10 per minute"))
def register():
    """Register new user with email and password"""
    try:
        data = _json_body()
        name = (data.get("name") or "").strip()
        email = normalize_email(data.get("email"))
        password = data.get("password") or ""

        if not name or not email or not password:
            return {"error": "Missing required fields"}, 400

        email_ok, normalized_email, email_error = validate_email_address(email)
        if not email_ok:
            return {"error": f"Invalid email: {email_error}"}, 400

        password_ok, password_error = validate_password_policy(password)
        if not password_ok:
            return {"error": password_error}, 400

        if User.query.filter_by(email=normalized_email).first():
            return {"error": "Email already registered"}, 409

        user = User(
            id=str(uuid.uuid4()),
            name=name,
            email=normalized_email,
            password_hash=generate_password_hash(password),
            credits=350 + (500 if data.get("referral_code") else 0),
            last_login=datetime.utcnow(),
        )

        access_token, expires_at = _issue_access_token(user.id)
        db.session.add(user)
        create_user_session(user.id, access_token, expires_at)
        db.session.commit()

        payload = {
            "message": "User registered successfully",
            "user": user.to_dict(),
        }
        if _should_expose_token():
            payload["access_token"] = access_token

        if _use_cookies():
            response = jsonify(payload)
            set_access_cookies(response, access_token)
            return response, 201
        return payload, 201

    except Exception:
        db.session.rollback()
        logger.exception("Register error")
        return {"error": "Registration failed"}, 500


@auth_bp.route("/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH", "10 per minute"))
def login():
    """Login user with email and password"""
    try:
        data = _json_body()
        email = normalize_email(data.get("email"))
        password = data.get("password") or ""

        if not email or not password:
            return {"error": "Email and password required"}, 400

        user = User.query.filter_by(email=email).first()
        if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
            return {"error": "Invalid email or password"}, 401
        if user.status and user.status != "active":
            return {"error": f"Account is {user.status}"}, 403

        user.last_login = datetime.utcnow()
        access_token, expires_at = _issue_access_token(user.id)
        create_user_session(user.id, access_token, expires_at)
        db.session.commit()

        payload = {
            "message": "Login successful",
            "user": user.to_dict(),
        }
        if _should_expose_token():
            payload["access_token"] = access_token

        if _use_cookies():
            response = jsonify(payload)
            set_access_cookies(response, access_token)
            return response, 200
        return payload, 200

    except Exception:
        db.session.rollback()
        logger.exception("Login error")
        return {"error": "Login failed"}, 500


@auth_bp.route("/google/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH", "10 per minute"))
def google_login():
    """Initiate Google OAuth login"""
    try:
        data = _json_body()
        redirect_url = sanitize_frontend_url(data.get("redirect_url"))
        oauth_state = create_oauth_state(provider="google", mode="login", redirect_url=redirect_url)

        params = {
            "client_id": current_app.config["GOOGLE_CLIENT_ID"],
            "redirect_uri": current_app.config["GOOGLE_CALLBACK_URL"],
            "response_type": "code",
            "scope": "openid email profile https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": oauth_state,
        }

        response = requests.Request("GET", "https://accounts.google.com/o/oauth2/v2/auth", params=params).prepare()
        return {"auth_url": response.url}, 200

    except Exception:
        logger.exception("Google login init error")
        return {"error": "Failed to initialize Google login"}, 500


@auth_bp.route("/google/callback", methods=["GET"])
def google_callback():
    """Google OAuth callback"""
    try:
        if request.args.get("error"):
            return {"error": "Google OAuth authorization failed"}, 400

        code = request.args.get("code")
        state_token = request.args.get("state")
        if not code:
            return {"error": "No authorization code received"}, 400

        state_payload, state_error = verify_oauth_state(
            state_token, expected_provider="google", expected_mode="login"
        )
        if state_error:
            return {"error": state_error}, 400

        timeout = current_app.config.get("API_REQUEST_TIMEOUT_SECONDS", 15)
        token_data = {
            "code": code,
            "client_id": current_app.config["GOOGLE_CLIENT_ID"],
            "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": current_app.config["GOOGLE_CALLBACK_URL"],
            "grant_type": "authorization_code",
        }

        token_response = requests.post(
            "https://oauth2.googleapis.com/token", data=token_data, timeout=timeout
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        if "access_token" not in tokens:
            return {"error": "Google token exchange failed"}, 400

        user_info_response = requests.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=timeout,
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()

        provider_user_id = user_info.get("sub")
        email = normalize_email(user_info.get("email"))
        if not provider_user_id or not email:
            return {"error": "Google user profile missing required fields"}, 400

        oauth_account = OAuthAccount.query.filter_by(
            provider="google", provider_user_id=provider_user_id
        ).first()

        if oauth_account:
            user = oauth_account.user
            oauth_account.access_token = tokens["access_token"]
            oauth_account.refresh_token = tokens.get("refresh_token", oauth_account.refresh_token)
            oauth_account.token_expires_at = datetime.utcnow() + timedelta(
                seconds=tokens.get("expires_in", 3600)
            )
            oauth_account.updated_at = datetime.utcnow()
        else:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    name=user_info.get("name") or email,
                    email=email,
                    avatar_url=user_info.get("picture"),
                    credits=350,
                )
                db.session.add(user)
                db.session.flush()

            oauth_account = OAuthAccount(
                id=str(uuid.uuid4()),
                user_id=user.id,
                provider="google",
                provider_user_id=provider_user_id,
                provider_username=email,
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600)),
                scope="openid email profile youtube youtube.readonly yt-analytics.readonly",
            )
            db.session.add(oauth_account)

        user.last_login = datetime.utcnow()
        access_token, expires_at = _issue_access_token(user.id)
        create_user_session(user.id, access_token, expires_at)
        db.session.commit()

        frontend_url = sanitize_frontend_url(state_payload.get("redirect_url"))
        params = {
            "auth": "success",
            "provider": "google",
            "user": user.id,
        }
        if _should_expose_token() and not _use_cookies():
            params["token"] = access_token
        redirect_url = build_url_with_query(frontend_url, params)
        response = redirect(redirect_url)
        if _use_cookies():
            set_access_cookies(response, access_token)
        return response

    except requests.RequestException:
        db.session.rollback()
        logger.exception("Google OAuth network error")
        return {"error": "Google OAuth request failed"}, 502
    except Exception:
        db.session.rollback()
        logger.exception("Google callback error")
        return {"error": "Google login failed"}, 500


@auth_bp.route("/tiktok/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH", "10 per minute"))
def tiktok_login():
    """Initiate TikTok OAuth login"""
    return {"error": "TikTok integration has been removed from this project"}, 410
    try:
        data = _json_body()
        redirect_url = sanitize_frontend_url(data.get("redirect_url"))
        oauth_state = create_oauth_state(provider="tiktok", mode="login", redirect_url=redirect_url)

        params = {
            "client_key": current_app.config["TIKTOK_CLIENT_ID"],
            "redirect_uri": current_app.config["TIKTOK_CALLBACK_URL"],
            "response_type": "code",
            "scope": "user.info.basic,video.list,user_stat.read",
            "state": oauth_state,
        }

        response = requests.Request("GET", "https://www.tiktok.com/v1/oauth/authorize/", params=params).prepare()
        return {"auth_url": response.url}, 200

    except Exception:
        logger.exception("TikTok login init error")
        return {"error": "Failed to initialize TikTok login"}, 500


@auth_bp.route("/tiktok/callback", methods=["GET"])
def tiktok_callback():
    """TikTok OAuth callback"""
    return {"error": "TikTok integration has been removed from this project"}, 410
    try:
        if request.args.get("error"):
            return {"error": "TikTok OAuth authorization failed"}, 400

        code = request.args.get("code")
        state_token = request.args.get("state")
        if not code:
            return {"error": "No authorization code received"}, 400

        state_payload, state_error = verify_oauth_state(
            state_token, expected_provider="tiktok", expected_mode="login"
        )
        if state_error:
            return {"error": state_error}, 400

        timeout = current_app.config.get("API_REQUEST_TIMEOUT_SECONDS", 15)
        token_data = {
            "client_key": current_app.config["TIKTOK_CLIENT_ID"],
            "client_secret": current_app.config["TIKTOK_CLIENT_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
        }

        token_response = requests.post(
            "https://open.tiktokapis.com/v1/oauth/token/", json=token_data, timeout=timeout
        )
        token_response.raise_for_status()
        tokens = token_response.json()
        if "access_token" not in tokens:
            return {"error": "TikTok token exchange failed"}, 400

        user_response = requests.get(
            "https://open.tiktokapis.com/v1/user/info/",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            params={"fields": "open_id,union_id,avatar_url,display_name"},
            timeout=timeout,
        )
        user_response.raise_for_status()
        user_data = user_response.json()
        user_info = (user_data.get("data") or {}).get("user") or {}

        provider_user_id = user_info.get("open_id")
        if not provider_user_id:
            return {"error": "TikTok profile missing user id"}, 400

        oauth_account = OAuthAccount.query.filter_by(
            provider="tiktok", provider_user_id=provider_user_id
        ).first()

        if oauth_account:
            user = oauth_account.user
            oauth_account.access_token = tokens["access_token"]
            oauth_account.refresh_token = tokens.get("refresh_token", oauth_account.refresh_token)
            oauth_account.token_expires_at = datetime.utcnow() + timedelta(
                seconds=tokens.get("expires_in", 3600)
            )
            oauth_account.updated_at = datetime.utcnow()
        else:
            username = user_info.get("display_name") or f"tiktok_{provider_user_id[:8]}"
            email = f"{provider_user_id}@tiktok.oauth"
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    name=username,
                    email=email,
                    avatar_url=user_info.get("avatar_url"),
                    credits=350,
                )
                db.session.add(user)
                db.session.flush()

            oauth_account = OAuthAccount(
                id=str(uuid.uuid4()),
                user_id=user.id,
                provider="tiktok",
                provider_user_id=provider_user_id,
                provider_username=username,
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600)),
                scope="user.info.basic,video.list,user_stat.read",
            )
            db.session.add(oauth_account)

        user.last_login = datetime.utcnow()
        access_token, expires_at = _issue_access_token(user.id)
        create_user_session(user.id, access_token, expires_at)
        db.session.commit()

        frontend_url = sanitize_frontend_url(state_payload.get("redirect_url"))
        params = {
            "auth": "success",
            "provider": "tiktok",
            "user": user.id,
        }
        if _should_expose_token() and not _use_cookies():
            params["token"] = access_token
        redirect_url = build_url_with_query(frontend_url, params)
        response = redirect(redirect_url)
        if _use_cookies():
            set_access_cookies(response, access_token)
        return response

    except requests.RequestException:
        db.session.rollback()
        logger.exception("TikTok OAuth network error")
        return {"error": "TikTok OAuth request failed"}, 502
    except Exception:
        db.session.rollback()
        logger.exception("TikTok callback error")
        return {"error": "TikTok login failed"}, 500


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Logout user and invalidate current session"""
    try:
        raw_token = extract_access_token_from_request()
        deleted = revoke_session(raw_token)
        db.session.commit()
        response = jsonify({"message": "Logged out successfully", "sessions_revoked": deleted})
        if _use_cookies():
            unset_jwt_cookies(response)
        return response, 200
    except Exception:
        db.session.rollback()
        logger.exception("Logout error")
        return {"error": "Logout failed"}, 500


@auth_bp.route("/verify-token", methods=["GET"])
def verify_token():
    """Verify if JWT is valid and session is active"""
    try:
        verify_jwt_in_request()
        if current_app.config.get("AUTH_SESSION_CHECK", True):
            raw_token = extract_access_token_from_request()
            if not is_session_active(raw_token):
                return {"valid": False, "error": "Session expired or revoked"}, 401

        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {"valid": False, "error": "User not found"}, 401
        if user.status and user.status != "active":
            return {"valid": False, "error": f"Account is {user.status}"}, 403

        return {"valid": True, "user": user.to_dict()}, 200
    except Exception:
        return {"valid": False}, 401
