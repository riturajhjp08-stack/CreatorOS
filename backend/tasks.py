import os
import logging
import uuid
from datetime import datetime

from celery_app import create_celery
from models import db, ConnectedPlatform, User, Notification
from sqlalchemy import func
from services.post_scheduler import process_due_posts
from utils.analytics import (
    sync_youtube_analytics,
    sync_tiktok_analytics,
    sync_instagram_analytics,
    sync_twitter_analytics,
    sync_linkedin_analytics,
    refresh_access_token,
)
from utils.auth_security import cleanup_expired_sessions

logger = logging.getLogger(__name__)

celery = create_celery()


def _get_app():
    from app import create_app
    return create_app(os.getenv("FLASK_ENV", "development"))


@celery.task
def process_due_posts_task(user_id=None, limit=200):
    app = _get_app()
    with app.app_context():
        try:
            processed = process_due_posts(user_id=user_id, limit=limit)
            db.session.commit()
            return processed
        except Exception as exc:
            db.session.rollback()
            logger.exception("Process due posts task failed")
            raise exc


@celery.task
def sync_all_analytics_task(user_id):
    app = _get_app()
    with app.app_context():
        try:
            platforms = ConnectedPlatform.query.filter_by(user_id=user_id, is_active=True).all()
            synced = []
            errors = []

            for platform in platforms:
                try:
                    if platform.token_expires_at and datetime.utcnow() >= platform.token_expires_at:
                        refresh_access_token(platform)

                    if platform.platform == "youtube":
                        sync_youtube_analytics(user_id, platform.id, platform.access_token)
                    elif platform.platform == "tiktok":
                        sync_tiktok_analytics(user_id, platform.id, platform.access_token)
                    elif platform.platform == "instagram":
                        sync_instagram_analytics(user_id, platform.id, platform.access_token)
                    elif platform.platform == "twitter":
                        sync_twitter_analytics(user_id, platform.id, platform.access_token)
                    elif platform.platform == "linkedin":
                        sync_linkedin_analytics(user_id, platform.id, platform.access_token)

                    platform.last_sync = datetime.utcnow()
                    synced.append(platform.platform)
                except Exception as err:
                    errors.append({"platform": platform.platform, "error": str(err)})

            db.session.commit()
            return {"synced": synced, "errors": errors}
        except Exception as exc:
            db.session.rollback()
            logger.exception("Sync analytics task failed")
            raise exc


@celery.task
def sync_all_analytics_for_all_users_task(limit=200):
    app = _get_app()
    with app.app_context():
        try:
            query = (
                db.session.query(
                    ConnectedPlatform.user_id,
                    func.min(ConnectedPlatform.last_sync).label("last_sync"),
                )
                .filter_by(is_active=True)
                .group_by(ConnectedPlatform.user_id)
                .order_by(func.min(ConnectedPlatform.last_sync).asc())
            )
            if limit:
                query = query.limit(limit)
            user_ids = [row[0] for row in query.all()]
            for user_id in user_ids:
                sync_all_analytics_task.delay(user_id)
            return {"queued": len(user_ids)}
        except Exception as exc:
            logger.exception("Sync all analytics for all users failed")
            raise exc


@celery.task
def cleanup_expired_sessions_task():
    app = _get_app()
    with app.app_context():
        try:
            deleted = cleanup_expired_sessions()
            db.session.commit()
            return {"deleted": deleted}
        except Exception as exc:
            db.session.rollback()
            logger.exception("Cleanup sessions task failed")
            raise exc


@celery.task
def broadcast_notification_task(title, message, batch_size=500):
    app = _get_app()
    with app.app_context():
        try:
            query = User.query.with_entities(User.id)
            total = query.count()
            for idx, row in enumerate(query.yield_per(batch_size), start=1):
                user_id = row[0]
                notification = Notification(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=title,
                    message=message,
                )
                db.session.add(notification)
                if idx % batch_size == 0:
                    db.session.flush()
            db.session.commit()
            return {"count": total}
        except Exception as exc:
            db.session.rollback()
            logger.exception("Broadcast notification task failed")
            raise exc
