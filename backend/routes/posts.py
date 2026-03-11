import uuid
import logging
import os
from datetime import datetime, timedelta

import requests
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from models import db, User, ConnectedPlatform, ScheduledPost
from storage import get_storage
from extensions import limiter
from services.post_scheduler import process_due_posts, pick_video_file
from utils.pagination import parse_pagination, pagination_meta

logger = logging.getLogger(__name__)

posts_bp = Blueprint("posts", __name__)

SUPPORTED_PLATFORMS = {"youtube", "instagram", "tiktok", "twitter", "linkedin"}

CREDITS_COST_SCHEDULE = 5
CREDITS_COST_PUBLISH_NOW = 8
UPLOAD_ALLOWED_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".jpg", ".jpeg", ".png", ".webp"}


def _json_body():
    return request.get_json(silent=True) or {}

def _enqueue_due_posts(user_id=None, limit=100):
    try:
        from tasks import process_due_posts_task
        process_due_posts_task.delay(user_id=user_id, limit=limit)
        return True
    except Exception:
        logger.exception("Failed to enqueue due posts")
        return False

def _sanitize_media_items(items, user_id=None):
    """Ensure media_items payload is JSON-safe and only references allowed user uploads."""
    safe = []
    if not isinstance(items, list):
        return safe
    for raw in items[:10]:
        if not isinstance(raw, dict):
            continue
        size = raw.get("size", 0)
        try:
            size = int(size or 0)
        except (TypeError, ValueError):
            size = 0
        safe.append({
            "name": str(raw.get("name") or "")[:255],
            "stored_name": str(raw.get("stored_name") or "")[:255],
            "size": size,
            "type": str(raw.get("type") or "")[:120],
            "key": str(raw.get("key") or "")[:1000],
        })
    return safe


def _sanitize_youtube_settings(value):
    if not isinstance(value, dict):
        value = {}
    privacy = str(value.get("privacy") or "public").lower()
    if privacy not in {"public", "private", "unlisted"}:
        privacy = "public"
    return {
        "title": str(value.get("title") or "")[:100],
        "description": str(value.get("description") or "")[:5000],
        "privacy": privacy,
    }


def _next_optimal_time():
    now = datetime.utcnow()
    candidate = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
    return candidate




@posts_bp.route("/upload", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_UPLOAD", "20 per hour"))
def upload_media():
    """Upload media files for scheduler/publish queue."""
    try:
        user_id = get_jwt_identity()
        files = request.files.getlist("media")
        if not files:
            return {"error": "No media files uploaded"}, 400

        saved_items = []
        storage = get_storage()
        for file in files[:10]:
            original_name = secure_filename(file.filename or "")
            if not original_name:
                continue
            ext = os.path.splitext(original_name)[1].lower()
            if ext not in UPLOAD_ALLOWED_EXT:
                continue
            saved = storage.save(file, user_id)
            if not saved:
                continue
            if not saved.get("type"):
                saved["type"] = file.mimetype or "application/octet-stream"
            saved_items.append(saved)

        if not saved_items:
            return {"error": "No valid media files uploaded"}, 400
        return {"media_items": saved_items, "count": len(saved_items)}, 201
    except Exception:
        logger.exception("Upload media error")
        return {"error": "Failed to upload media"}, 500




@posts_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_POSTS", "60 per hour"))
def create_post():
    """Create one or more scheduled posts (one record per platform)."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404

        data = _json_body()
        platforms = [str(p).lower().strip() for p in (data.get("platforms") or []) if str(p).strip()]
        caption = (data.get("caption") or "").strip()
        hashtags = (data.get("hashtags") or "").strip()
        media_items = _sanitize_media_items(data.get("media_items") or [])
        schedule_type = (data.get("schedule_type") or "now").lower()
        scheduled_for_raw = data.get("scheduled_for")
        virality_score = data.get("virality_score")
        youtube_settings = _sanitize_youtube_settings(data.get("youtube_settings") or {})

        if not platforms:
            return {"error": "Select at least one platform"}, 400
        invalid = [p for p in platforms if p not in SUPPORTED_PLATFORMS]
        if invalid:
            return {"error": f"Unsupported platforms: {', '.join(invalid)}"}, 400
        if not caption:
            return {"error": "Caption is required"}, 400
        if schedule_type not in {"now", "optimal", "custom"}:
            return {"error": "Invalid schedule type"}, 400

        connected = ConnectedPlatform.query.filter(
            ConnectedPlatform.user_id == user_id,
            ConnectedPlatform.is_active.is_(True),
            ConnectedPlatform.platform.in_(platforms),
        ).all()
        connected_set = {p.platform for p in connected}
        missing = [p for p in platforms if p not in connected_set]
        if missing:
            return {"error": f"Connect platform(s) first: {', '.join(missing)}"}, 400
        if "youtube" in platforms and not pick_video_file(user_id, media_items):
            return {"error": "YouTube post requires one uploaded video file (mp4/mov/etc)."}, 400

        if schedule_type == "custom":
            if not scheduled_for_raw:
                return {"error": "Custom schedule requires date/time"}, 400
            try:
                scheduled_for = datetime.fromisoformat(str(scheduled_for_raw).replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return {"error": "Invalid scheduled_for datetime"}, 400
        elif schedule_type == "optimal":
            scheduled_for = _next_optimal_time()
        else:
            scheduled_for = datetime.utcnow()

        cost_per_post = CREDITS_COST_PUBLISH_NOW if schedule_type == "now" else CREDITS_COST_SCHEDULE
        total_cost = cost_per_post * len(platforms)
        if user.credits < total_cost:
            return {"error": f"Insufficient credits. Need {total_cost}, have {user.credits}"}, 402
        user.credits -= total_cost
        user.updated_at = datetime.utcnow()

        created = []
        for platform in platforms:
            post = ScheduledPost(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform=platform,
                status="scheduled",
                schedule_type=schedule_type,
                scheduled_for=scheduled_for,
                caption=caption,
                hashtags=hashtags,
                media_items=media_items,
                virality_score=int(virality_score) if virality_score is not None else None,
                publish_response={"youtube_settings": youtube_settings} if platform == "youtube" else {},
                credits_spent=cost_per_post,
            )
            db.session.add(post)
            created.append(post)

        # If publish now, process immediately.
        processed_now = []
        if schedule_type == "now":
            processed_now = [post.id for post in created]

        db.session.commit()

        if schedule_type == "now":
            _enqueue_due_posts(user_id=user_id, limit=100)
        return {
            "message": "Posts queued successfully",
            "created_count": len(created),
            "processed_now": processed_now,
            "credits_spent": total_cost,
            "remaining_credits": user.credits,
            "posts": [p.to_dict() for p in created],
        }, 201
    except Exception as e:
        db.session.rollback()
        logger.exception("Create scheduled post error")
        return {
            "error": "Failed to create scheduled post",
            "details": "Check backend logs for provider error.",
            "exception": str(e),
        }, 500


@posts_bp.route("", methods=["GET"])
@jwt_required()
def list_posts():
    """List scheduled/published posts for current user."""
    try:
        user_id = get_jwt_identity()
        # Enqueue due processing in background.
        _enqueue_due_posts(user_id=user_id, limit=50)

        page, page_size, offset = parse_pagination(request.args, default_page_size=50, max_page_size=200)
        status_filter = (request.args.get("status") or "").strip().lower()
        platform_filter = (request.args.get("platform") or "").strip().lower()

        query = ScheduledPost.query.filter_by(user_id=user_id)
        if status_filter:
            query = query.filter(ScheduledPost.status == status_filter)
        if platform_filter:
            query = query.filter(ScheduledPost.platform == platform_filter)

        total = query.count()
        posts = query.order_by(ScheduledPost.created_at.desc()).offset(offset).limit(page_size).all()
        user = User.query.get(user_id)
        summary = {
            "scheduled": ScheduledPost.query.filter_by(user_id=user_id, status="scheduled").count(),
            "published": ScheduledPost.query.filter_by(user_id=user_id, status="published").count(),
            "failed": ScheduledPost.query.filter_by(user_id=user_id, status="failed").count(),
        }
        return {
            "posts": [p.to_dict() for p in posts],
            "summary": summary,
            "credits": user.credits if user else None,
            "count": len(posts),
            "total": total,
            "pagination": pagination_meta(total, page, page_size),
        }, 200
    except Exception:
        db.session.rollback()
        logger.exception("List scheduled posts error")
        return {"error": "Failed to fetch posts"}, 500


@posts_bp.route("/process-due", methods=["POST"])
@jwt_required()
def process_due():
    """Force process due posts for current user."""
    try:
        user_id = get_jwt_identity()
        enqueued = _enqueue_due_posts(user_id=user_id, limit=100)
        if not enqueued:
            processed = process_due_posts(user_id=user_id, limit=100)
            db.session.commit()
            return {"processed": processed, "count": len(processed)}, 200
        return {"processed": [], "count": 0, "queued": True}, 202
    except Exception:
        db.session.rollback()
        logger.exception("Process due posts error")
        return {"error": "Failed to process due posts"}, 500


@posts_bp.route("/<post_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_post(post_id):
    try:
        user_id = get_jwt_identity()
        post = ScheduledPost.query.filter_by(id=post_id, user_id=user_id).first()
        if not post:
            return {"error": "Post not found"}, 404
        if post.status not in {"scheduled", "failed"}:
            return {"error": f"Cannot cancel post in status {post.status}"}, 400

        post.status = "cancelled"
        post.updated_at = datetime.utcnow()
        db.session.commit()
        return {"message": "Post cancelled", "post": post.to_dict()}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Cancel post error")
        return {"error": "Failed to cancel post"}, 500


@posts_bp.route("/<post_id>/delete", methods=["POST"])
@jwt_required()
def delete_post(post_id):
    """
    Delete a post record; for YouTube published posts, attempt real deletion on YouTube first.
    """
    try:
        user_id = get_jwt_identity()
        post = ScheduledPost.query.filter_by(id=post_id, user_id=user_id).first()
        if not post:
            return {"error": "Post not found"}, 404
        payload = request.get_json(silent=True) or {}
        force_local = bool(payload.get("force_local", False))
        warning = None

        if post.platform == "youtube" and post.status == "published":
            external_id = (post.external_post_id or "").strip()
            if external_id and not external_id.startswith("sim_"):
                connected = ConnectedPlatform.query.filter_by(
                    user_id=user_id, platform="youtube", is_active=True
                ).first()
                if not connected:
                    return {"error": "YouTube is not connected"}, 400
                _ensure_valid_platform_token(connected)
                token = connected.access_token
                if not token:
                    return {"error": "Missing YouTube access token"}, 400

                resp = requests.delete(
                    "https://www.googleapis.com/youtube/v3/videos",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"id": external_id},
                    timeout=current_app.config.get("API_REQUEST_TIMEOUT_SECONDS", 30),
                )
                if resp.status_code not in (200, 202, 204):
                    err = "YouTube delete failed"
                    try:
                        payload = resp.json()
                        err = payload.get("error", {}).get("message") or err
                    except Exception:
                        pass
                    if not force_local:
                        return {"error": err}, 400
                    warning = f"YouTube API delete failed: {err}. Removed from app only."

        db.session.delete(post)
        db.session.commit()
        return {"message": "Post deleted", "warning": warning}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Delete post error")
        return {"error": "Failed to delete post"}, 500
