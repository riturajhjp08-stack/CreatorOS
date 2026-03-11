import logging
from datetime import timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt,
    get_jwt_identity,
    set_access_cookies,
)
from models import db, User, Feedback
from extensions import limiter
from utils.pagination import parse_pagination, pagination_meta

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

def _is_admin():
    claims = get_jwt()
    return bool(claims.get("is_admin"))


def _enqueue_broadcast_notification(title, message):
    try:
        from tasks import broadcast_notification_task
        broadcast_notification_task.delay(title=title, message=message)
        return True
    except Exception:
        logger.exception("Failed to enqueue broadcast notification")
        return False

@admin_bp.route('/login', methods=['POST'])
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH", "10 per minute"))
def admin_login():
    """Verify admin secret code and issue admin token"""
    try:
        data = request.get_json(silent=True) or {}
        code = data.get('code')
        
        expected_code = current_app.config.get('ADMIN_SECRET_CODE')
        if not expected_code or code != expected_code:
            return {'error': 'Invalid secret code'}, 401
            
        # Create a special token with an 'admin' claim
        access_token = create_access_token(
            identity="admin",
            additional_claims={"is_admin": True},
            expires_delta=timedelta(hours=1),
        )
        payload = {'access_token': access_token}
        response = jsonify(payload)
        if "cookies" in (current_app.config.get("JWT_TOKEN_LOCATION") or []):
            set_access_cookies(response, access_token)
        return response, 200
        
    except Exception as e:
        logger.exception("Admin login error")
        return {'error': 'Login failed'}, 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_users():
    """Get all users (Admin only)"""
    try:
        # Check if caller is admin
        if not _is_admin():
            return {'error': 'Unauthorized'}, 403
            
        page, page_size, offset = parse_pagination(request.args, default_page_size=50, max_page_size=200)
        query = User.query.order_by(User.created_at.desc())
        total = query.count()
        users = query.offset(offset).limit(page_size).all()
        return {
            'count': total,
            'page_count': len(users),
            'total': total,
            'users': [u.to_dict() for u in users],
            'pagination': pagination_meta(total, page, page_size),
        }, 200
        
    except Exception as e:
        logger.exception("Error fetching users")
        return {'error': 'Failed to fetch users'}, 500

@admin_bp.route('/feedback', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_feedback():
    """Get all feedback (Admin only)"""
    try:
        if not _is_admin():
            return {'error': 'Unauthorized'}, 403
            
        page, page_size, offset = parse_pagination(request.args, default_page_size=50, max_page_size=200)
        query = Feedback.query.order_by(Feedback.created_at.desc())
        total = query.count()
        feedback_list = query.offset(offset).limit(page_size).all()
        return {
            'count': total,
            'page_count': len(feedback_list),
            'total': total,
            'feedback': [f.to_dict() for f in feedback_list],
            'pagination': pagination_meta(total, page, page_size),
        }, 200
        
    except Exception as e:
        logger.exception("Error fetching feedback")
        return {'error': 'Failed to fetch feedback'}, 500

@admin_bp.route('/feedback/<feedback_id>/reply', methods=['POST'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def reply_feedback(feedback_id):
    """Admin replies to a user's feedback"""
    from models import Notification
    import uuid
    from datetime import datetime

    try:
        if not _is_admin():
            return {'error': 'Unauthorized'}, 403

        data = request.get_json(silent=True) or {}
        reply_message = data.get('reply')

        if not reply_message:
            return {'error': 'Reply message is required'}, 400

        feedback = Feedback.query.get(feedback_id)
        if not feedback:
            return {'error': 'Feedback not found'}, 404

        feedback.reply = reply_message
        feedback.replied_at = datetime.utcnow()

        # Generate a notification for the user
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=feedback.user_id,
            title="Update on your feedback",
            message=f"An admin has replied to your feedback: '{reply_message}'"
        )
        db.session.add(notification)
        db.session.commit()

        return {'success': True, 'feedback': feedback.to_dict()}, 200

    except Exception as e:
        logger.exception("Error replying to feedback")
        return {'error': 'Failed to reply to feedback'}, 500

@admin_bp.route('/notifications/send', methods=['POST'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def send_notification():
    """Admin sends a custom notification"""
    from models import Notification, User
    import uuid

    try:
        if not _is_admin():
            return {'error': 'Unauthorized'}, 403

        data = request.get_json(silent=True) or {}
        target = data.get('target', 'all')  # "all" or user id
        title = data.get('title')
        message = data.get('message')

        if not title or not message:
            return {'error': 'Title and message are required'}, 400

        user_query = None
        if target == 'all':
            if _enqueue_broadcast_notification(title, message):
                return {'success': True, 'queued': True}, 202
            user_query = User.query.with_entities(User.id)
        else:
            user = User.query.get(target)
            if not user:
                return {'error': 'Target user not found'}, 404
            user_query = [(user.id,)]

        batch_size = 500
        if hasattr(user_query, "yield_per"):
            total = user_query.count()
            iterable = user_query.yield_per(batch_size)
        else:
            total = len(user_query)
            iterable = user_query
        for idx, uid_row in enumerate(iterable, start=1):
            uid = uid_row[0]
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=uid,
                title=title,
                message=message
            )
            db.session.add(notification)
            if idx % batch_size == 0:
                db.session.flush()
            
        db.session.commit()

        return {'success': True, 'count': total, 'queued': False}, 200

    except Exception as e:
        logger.exception("Error sending custom notification")
        return {'error': 'Failed to send notification'}, 500
