import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Notification
from extensions import limiter
from utils.pagination import parse_pagination, pagination_meta

notifications_bp = Blueprint('notifications', __name__)
logger = logging.getLogger(__name__)

@notifications_bp.route('', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_NOTIFICATIONS", "120 per minute"))
def get_notifications():
    """Get all notifications for the authenticated user"""
    try:
        user_id = get_jwt_identity()
        page, page_size, offset = parse_pagination(request.args, default_page_size=50, max_page_size=200)
        unread = str(request.args.get("unread", "")).lower() in {"1", "true", "yes"}

        query = Notification.query.filter_by(user_id=user_id)
        if unread:
            query = query.filter_by(is_read=False)

        total = query.count()
        notifications = (
            query.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        return {
            'notifications': [n.to_dict() for n in notifications],
            'count': len(notifications),
            'total': total,
            'unread_count': unread_count,
            'pagination': pagination_meta(total, page, page_size),
        }, 200
    except Exception as e:
        logger.exception("Error fetching notifications")
        return {'error': 'Failed to fetch notifications'}, 500

@notifications_bp.route('/<notif_id>/read', methods=['PUT'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_NOTIFICATIONS", "120 per minute"))
def mark_read(notif_id):
    """Mark a notification as read"""
    try:
        user_id = get_jwt_identity()
        notification = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
        if not notification:
            return {'error': 'Notification not found'}, 404
            
        notification.is_read = True
        db.session.commit()
        return {'success': True}, 200
    except Exception as e:
        logger.exception("Error marking notification read")
        return {'error': 'Failed to mark notification read'}, 500


@notifications_bp.route('/read-all', methods=['PUT'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_NOTIFICATIONS", "120 per minute"))
def mark_all_read():
    """Mark all notifications as read"""
    try:
        user_id = get_jwt_identity()
        updated = Notification.query.filter_by(user_id=user_id, is_read=False).update(
            {"is_read": True},
            synchronize_session=False,
        )
        db.session.commit()
        return {'success': True, 'updated': updated}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Error marking all notifications read")
        return {'error': 'Failed to mark notifications read'}, 500
