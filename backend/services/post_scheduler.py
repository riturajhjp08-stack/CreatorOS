import json
import logging
import mimetypes
import os
import uuid
from datetime import datetime

import requests
from flask import current_app

from models import db, User, ConnectedPlatform, ScheduledPost
from storage import get_storage
from utils.analytics import refresh_access_token

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def pick_video_file(user_id, media_items):
    storage = get_storage()
    for item in (media_items or []):
        stored_name = item.get("stored_name") or ""
        name = item.get("name") or ""
        ext = os.path.splitext(stored_name or name)[1].lower()
        if ext not in ALLOWED_VIDEO_EXT:
            continue
        path = storage.prepare_local(user_id, item)
        if path and os.path.exists(path):
            cloned = dict(item)
            cloned["path"] = path
            return cloned
    return None


def _ensure_valid_platform_token(platform):
    if platform.token_expires_at and platform.token_expires_at <= datetime.utcnow():
        refresh_access_token(platform)
        db.session.flush()


def _caption_to_title_description(caption):
    raw = (caption or "").strip()
    if not raw:
        return "CreatorOS Upload", ""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    title = lines[0][:100] if lines else raw[:100]
    description = raw[:5000]
    return title, description


def _safe_tags(hashtags):
    tags = [t.strip().lstrip("#") for t in (hashtags or "").split() if t.strip()]
    return [t for t in tags if t][:15]


def publish_youtube_post(post, connected):
    file_path = None
    try:
        _ensure_valid_platform_token(connected)
        token = connected.access_token
        if not token:
            post.status = "failed"
            post.error_message = "Missing YouTube access token."
            return False

        if "youtube.upload" not in (connected.scope or ""):
            post.status = "failed"
            post.error_message = "YouTube upload scope missing. Reconnect YouTube with upload permission."
            return False

        media_item = pick_video_file(post.user_id, post.media_items)
        if not media_item:
            post.status = "failed"
            post.error_message = "No uploaded video file found for YouTube post."
            return False

        file_path = media_item.get("path")
        yt_settings = (post.publish_response or {}).get("youtube_settings", {})
        title, description = _caption_to_title_description(post.caption)
        if yt_settings.get("title"):
            title = str(yt_settings.get("title"))[:100]
        if yt_settings.get("description"):
            description = str(yt_settings.get("description"))[:5000]
        tags = _safe_tags(post.hashtags)
        privacy = str(yt_settings.get("privacy") or "public").lower()
        if privacy not in {"public", "private", "unlisted"}:
            privacy = "public"
        metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy,
            },
        }

        mime = media_item.get("type") or mimetypes.guess_type(file_path)[0] or "video/mp4"
        file_size = os.path.getsize(file_path)
        init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
        init_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime,
            "X-Upload-Content-Length": str(file_size),
        }
        init_resp = requests.post(
            init_url,
            headers=init_headers,
            data=json.dumps(metadata),
            timeout=current_app.config.get("API_REQUEST_TIMEOUT_SECONDS", 30),
        )
        if init_resp.status_code not in (200, 201):
            post.status = "failed"
            post.error_message = f"YouTube init upload failed ({init_resp.status_code})"
            try:
                post.publish_response = init_resp.json()
            except Exception:
                post.publish_response = {"body": init_resp.text[:500]}
            return False

        upload_location = init_resp.headers.get("Location")
        if not upload_location:
            post.status = "failed"
            post.error_message = "YouTube upload URL not returned."
            post.publish_response = {"headers": dict(init_resp.headers)}
            return False

        with open(file_path, "rb") as fh:
            upload_resp = requests.put(
                upload_location,
                headers={"Content-Type": mime},
                data=fh,
                timeout=600,
            )

        if upload_resp.status_code not in (200, 201):
            post.status = "failed"
            post.error_message = f"YouTube file upload failed ({upload_resp.status_code})"
            try:
                post.publish_response = upload_resp.json()
            except Exception:
                post.publish_response = {"body": upload_resp.text[:500]}
            return False

        payload = upload_resp.json()
        video_id = payload.get("id")
        post.external_post_id = video_id
        post.publish_response = payload
        return True
    except Exception as exc:
        post.status = "failed"
        post.error_message = f"YouTube publish exception: {str(exc)}"
        logger.exception("YouTube publish exception")
        return False
    finally:
        try:
            if file_path:
                storage = get_storage()
                storage.cleanup_local(file_path)
        except Exception:
            logger.exception("Failed to cleanup temporary upload")


def publish_post(post):
    post.status = "processing"
    post.updated_at = datetime.utcnow()
    db.session.flush()

    connected = ConnectedPlatform.query.filter_by(
        user_id=post.user_id, platform=post.platform, is_active=True
    ).first()
    if not connected:
        post.status = "failed"
        post.error_message = "Platform not connected."
        post.updated_at = datetime.utcnow()
        return False

    if post.platform == "youtube":
        ok = publish_youtube_post(post, connected)
        if not ok:
            post.updated_at = datetime.utcnow()
            return False
    else:
        post.external_post_id = f"sim_{post.platform}_{uuid.uuid4().hex[:10]}"
        post.publish_response = {
            "simulated": True,
            "message": "Published by CreatorOS scheduler (demo mode).",
            "profile": connected.platform_display_name or connected.platform_username,
        }

    post.status = "published"
    post.published_at = datetime.utcnow()
    post.updated_at = datetime.utcnow()

    if not post.reward_granted:
        reward = _compute_reward(post)
        user = User.query.get(post.user_id)
        if user and reward > 0:
            user.credits += reward
            post.credits_earned = reward
            post.reward_granted = True
    return True


def _compute_reward(post):
    base_reward = 2
    max_reward = 15
    reward = base_reward
    score = int(post.virality_score or 0)
    if score >= 90:
        reward += 10
    elif score >= 80:
        reward += 7
    elif score >= 70:
        reward += 4
    if post.caption and len(post.caption) >= 140:
        reward += 2
    hashtags = (post.hashtags or "").split()
    if len(hashtags) >= 8:
        reward += 1
    return max(0, min(max_reward, reward))


def process_due_posts(user_id=None, limit=25):
    query = ScheduledPost.query.filter(
        ScheduledPost.status == "scheduled",
        ScheduledPost.scheduled_for <= datetime.utcnow(),
    )
    if user_id:
        query = query.filter(ScheduledPost.user_id == user_id)
    query = query.order_by(ScheduledPost.scheduled_for.asc())
    try:
        if db.session.bind and db.session.bind.dialect.name != "sqlite":
            query = query.with_for_update(skip_locked=True)
    except Exception:
        pass

    posts = query.limit(limit).all()
    if not posts:
        return []

    now = datetime.utcnow()
    for post in posts:
        post.status = "processing"
        post.updated_at = now
    db.session.commit()

    processed = []
    for post in posts:
        ok = publish_post(post)
        processed.append({"id": post.id, "platform": post.platform, "ok": ok, "status": post.status})
    return processed
