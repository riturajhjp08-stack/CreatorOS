import logging
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_, case

from models import db, User, ConnectedPlatform, Analytics, Follow
from utils.pagination import parse_pagination, pagination_meta
from utils.cache import get_cache

logger = logging.getLogger(__name__)

discovery_bp = Blueprint("discovery", __name__)


def _normalize_list(value):
    raw = (value or "").strip()
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def _is_online(last_seen, window_seconds=120):
    if not last_seen:
        return False
    return last_seen >= (datetime.utcnow() - timedelta(seconds=window_seconds))


@discovery_bp.route("/users", methods=["GET"])
@jwt_required()
def search_users():
    """Search users by username/category/platform with pagination."""
    try:
        user_id = get_jwt_identity()
        query_text = (request.args.get("q") or "").strip()
        category = (request.args.get("category") or "").strip()
        platforms = _normalize_list(request.args.get("platforms"))
        page, page_size, offset = parse_pagination(request.args, default_page_size=20, max_page_size=50)

        query = User.query
        if query_text:
            query = query.filter(User.username.ilike(f"%{query_text}%"))
        if category:
            query = query.filter(User.category.ilike(f"%{category}%"))
        if platforms:
            query = (
                query.join(ConnectedPlatform, ConnectedPlatform.user_id == User.id)
                .filter(ConnectedPlatform.platform.in_(platforms))
            )

        # Exclude self
        query = query.filter(User.id != user_id)

        total = query.distinct().count()
        users = (
            query.distinct()
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        user_ids = [u.id for u in users]
        platform_map = {}
        following_ids = set()
        if user_ids:
            rows = (
                db.session.query(ConnectedPlatform.user_id, ConnectedPlatform.platform)
                .filter(ConnectedPlatform.user_id.in_(user_ids))
                .all()
            )
            for uid, platform in rows:
                platform_map.setdefault(uid, set()).add(platform)
            following_rows = (
                db.session.query(Follow.following_id)
                .filter(Follow.follower_id == user_id, Follow.following_id.in_(user_ids))
                .all()
            )
            following_ids = {row[0] for row in following_rows}

        followers_map = {}
        if user_ids:
            latest = (
                db.session.query(
                    Analytics.user_id.label("user_id"),
                    Analytics.platform.label("platform"),
                    func.max(Analytics.metric_date).label("max_date"),
                )
                .filter(Analytics.user_id.in_(user_ids))
                .group_by(Analytics.user_id, Analytics.platform)
                .subquery()
            )
            latest_stats = (
                db.session.query(
                    Analytics.user_id,
                    Analytics.platform,
                    Analytics.followers,
                )
                .join(
                    latest,
                    and_(
                        Analytics.user_id == latest.c.user_id,
                        Analytics.platform == latest.c.platform,
                        Analytics.metric_date == latest.c.max_date,
                    ),
                )
                .all()
            )
            for row in latest_stats:
                followers_map.setdefault(row.user_id, {})[row.platform] = row.followers or 0

        items = []
        for user in users:
            platform_reach = followers_map.get(user.id, {})
            total_reach = sum(platform_reach.values()) if platform_reach else 0
            items.append({
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "category": user.category,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
                "platforms": sorted(list(platform_map.get(user.id, []))),
                "platform_reach": platform_reach,
                "total_reach": total_reach,
                "online": _is_online(user.last_seen),
                "is_following": user.id in following_ids,
            })

        return {
            "users": items,
            "count": len(items),
            "total": total,
            "pagination": pagination_meta(total, page, page_size),
        }, 200
    except Exception:
        logger.exception("Search users error")
        return {"error": "Failed to search users"}, 500


@discovery_bp.route("/users/<user_id>", methods=["GET"])
@jwt_required()
def get_user_profile(user_id):
    """Get creator profile + analytics summary."""
    try:
        viewer_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404

        latest = (
            db.session.query(
                Analytics.platform.label("platform"),
                func.max(Analytics.metric_date).label("max_date"),
            )
            .filter(Analytics.user_id == user_id)
            .group_by(Analytics.platform)
            .subquery()
        )
        latest_stats = (
            db.session.query(
                Analytics.platform,
                Analytics.followers,
                Analytics.posts_count,
                Analytics.views,
                Analytics.engagement,
            )
            .join(
                latest,
                and_(
                    Analytics.platform == latest.c.platform,
                    Analytics.metric_date == latest.c.max_date,
                ),
            )
            .filter(Analytics.user_id == user_id)
            .all()
        )
        platform_reach = {row.platform: row.followers or 0 for row in latest_stats}
        total_reach = sum(platform_reach.values()) if platform_reach else 0

        following = Follow.query.filter_by(follower_id=viewer_id, following_id=user_id).first()
        followers_count = Follow.query.filter_by(following_id=user_id).count()
        following_count = Follow.query.filter_by(follower_id=user_id).count()

        profile = user.to_dict()
        profile.update({
            "platform_reach": platform_reach,
            "total_reach": total_reach,
            "online": _is_online(user.last_seen),
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following": bool(following),
        })
        return profile, 200
    except Exception:
        logger.exception("Get user profile error")
        return {"error": "Failed to fetch profile"}, 500


@discovery_bp.route("/leaderboard", methods=["GET"])
@jwt_required()
def leaderboard():
    """Leaderboard based on total or platform-specific reach."""
    try:
        sort = (request.args.get("sort") or "total").lower()
        page, page_size, offset = parse_pagination(request.args, default_page_size=20, max_page_size=50)

        cache = get_cache(redis_url=current_app.config.get("REDIS_URL"))
        cache_key = f"leaderboard:{sort}:{page}:{page_size}"
        cached = cache.get(cache_key)
        if cached:
            return cached, 200

        latest = (
            db.session.query(
                Analytics.user_id.label("user_id"),
                Analytics.platform.label("platform"),
                func.max(Analytics.metric_date).label("max_date"),
            )
            .group_by(Analytics.user_id, Analytics.platform)
            .subquery()
        )
        latest_stats = (
            db.session.query(
                Analytics.user_id.label("user_id"),
                Analytics.platform.label("platform"),
                Analytics.followers.label("followers"),
            )
            .join(
                latest,
                and_(
                    Analytics.user_id == latest.c.user_id,
                    Analytics.platform == latest.c.platform,
                    Analytics.metric_date == latest.c.max_date,
                ),
            )
            .subquery()
        )

        columns = {
            "youtube": func.coalesce(func.sum(case((latest_stats.c.platform == "youtube", latest_stats.c.followers), else_=0)), 0),
            "instagram": func.coalesce(func.sum(case((latest_stats.c.platform == "instagram", latest_stats.c.followers), else_=0)), 0),
            "twitter": func.coalesce(func.sum(case((latest_stats.c.platform == "twitter", latest_stats.c.followers), else_=0)), 0),
            "tiktok": func.coalesce(func.sum(case((latest_stats.c.platform == "tiktok", latest_stats.c.followers), else_=0)), 0),
            "linkedin": func.coalesce(func.sum(case((latest_stats.c.platform == "linkedin", latest_stats.c.followers), else_=0)), 0),
        }
        total_reach = func.coalesce(func.sum(latest_stats.c.followers), 0)

        base_query = (
            db.session.query(
                User.id,
                User.name,
                User.username,
                User.category,
                User.avatar_url,
                total_reach.label("total_reach"),
                columns["youtube"].label("youtube"),
                columns["instagram"].label("instagram"),
                columns["twitter"].label("twitter"),
                columns["tiktok"].label("tiktok"),
                columns["linkedin"].label("linkedin"),
            )
            .outerjoin(latest_stats, latest_stats.c.user_id == User.id)
            .group_by(User.id)
        )

        order_column = total_reach if sort == "total" else columns.get(sort, total_reach)
        query = base_query.order_by(order_column.desc())

        total = query.count()
        rows = query.offset(offset).limit(page_size).all()

        entries = []
        for row in rows:
            platform_reach = {
                "youtube": int(row.youtube or 0),
                "instagram": int(row.instagram or 0),
                "twitter": int(row.twitter or 0),
                "tiktok": int(row.tiktok or 0),
                "linkedin": int(row.linkedin or 0),
            }
            entries.append({
                "id": row.id,
                "name": row.name,
                "username": row.username,
                "category": row.category,
                "avatar_url": row.avatar_url,
                "total_reach": int(row.total_reach or 0),
                "platform_reach": platform_reach,
            })

        payload = {
            "leaders": entries,
            "count": len(entries),
            "total": total,
            "pagination": pagination_meta(total, page, page_size),
        }
        cache.set(cache_key, payload, ttl_seconds=30)
        return payload, 200
    except Exception:
        logger.exception("Leaderboard error")
        return {"error": "Failed to fetch leaderboard"}, 500
