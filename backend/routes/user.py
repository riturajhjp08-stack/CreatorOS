import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Session
from datetime import datetime
from utils.auth_security import validate_password_policy
from extensions import limiter

user_bp = Blueprint('user', __name__)
logger = logging.getLogger(__name__)


def _json_body():
    return request.get_json(silent=True) or {}


def _current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        return user.to_dict(), 200
    except Exception:
        logger.exception("Get profile error")
        return {'error': 'Failed to fetch profile'}, 500

@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        data = _json_body()
        
        if 'name' in data:
            user.name = data['name']
        if 'bio' in data:
            user.bio = data['bio']
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url']
        if 'email_notifications' in data:
            user.email_notifications = data['email_notifications']
        if 'marketing_emails' in data:
            user.marketing_emails = data['marketing_emails']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }, 200
    except Exception:
        db.session.rollback()
        logger.exception("Update profile error")
        return {'error': 'Failed to update profile'}, 500

@user_bp.route('/password', methods=['POST'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH", "10 per minute"))
def change_password():
    """Change user password"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        data = _json_body()
        
        if not data.get('old_password') or not data.get('new_password'):
            return {'error': 'Old and new passwords required'}, 400
        
        if not user.password_hash or not check_password_hash(user.password_hash, data['old_password']):
            return {'error': 'Current password is incorrect'}, 401
        
        password_ok, password_error = validate_password_policy(data['new_password'])
        if not password_ok:
            return {'error': password_error}, 400
        
        user.password_hash = generate_password_hash(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {'message': 'Password updated successfully'}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Change password error")
        return {'error': 'Failed to change password'}, 500

@user_bp.route('/credits', methods=['GET'])
@jwt_required()
def get_credits():
    """Get user credits"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        return {
            'credits': user.credits,
            'premium': user.premium,
            'premium_expires': user.premium_expires.isoformat() if user.premium_expires else None
        }, 200
    except Exception:
        logger.exception("Get credits error")
        return {'error': 'Failed to fetch credits'}, 500

@user_bp.route('/credits/use', methods=['POST'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_POSTS", "60 per hour"))
def use_credits():
    """Use credits for a feature"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        data = _json_body()
        amount = data.get('amount', 0)
        
        if amount <= 0:
            return {'error': 'Invalid amount'}, 400
        
        if user.credits < amount:
            return {'error': 'Insufficient credits'}, 402
        
        user.credits -= amount
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'message': f'{amount} credits used',
            'remaining_credits': user.credits
        }, 200
    except Exception:
        db.session.rollback()
        logger.exception("Use credits error")
        return {'error': 'Failed to use credits'}, 500

@user_bp.route('/2fa/enable', methods=['POST'])
@jwt_required()
def enable_2fa():
    """Enable two-factor authentication"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        user.two_fa_enabled = True
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {'message': '2FA enabled'}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Enable 2FA error")
        return {'error': 'Failed to enable 2FA'}, 500

@user_bp.route('/2fa/disable', methods=['POST'])
@jwt_required()
def disable_2fa():
    """Disable two-factor authentication"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        user.two_fa_enabled = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {'message': '2FA disabled'}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Disable 2FA error")
        return {'error': 'Failed to disable 2FA'}, 500

@user_bp.route('/oauth-accounts', methods=['GET'])
@jwt_required()
def get_oauth_accounts():
    """Get linked OAuth accounts"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        accounts = [acc.to_dict() for acc in user.oauth_accounts]
        
        return {'oauth_accounts': accounts}, 200
    except Exception:
        logger.exception("Get OAuth accounts error")
        return {'error': 'Failed to fetch OAuth accounts'}, 500

@user_bp.route('/delete', methods=['POST'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AUTH", "10 per minute"))
def delete_account():
    """Delete user account"""
    try:
        user = _current_user()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        data = _json_body()
        if not data.get('confirm'):
            return {'error': 'Deletion not confirmed'}, 400
        
        Session.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        db.session.delete(user)
        db.session.commit()
        
        return {'message': 'Account deleted successfully'}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Delete account error")
        return {'error': 'Failed to delete account'}, 500
