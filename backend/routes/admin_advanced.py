import logging
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt
from models import db, User, Complaint, ContentReport, ActivityLog, Feedback, Session
from extensions import limiter
from utils.pagination import parse_pagination, pagination_meta

admin_advanced_bp = Blueprint('admin_advanced', __name__)
logger = logging.getLogger(__name__)

def admin_required():
    """Verify the JWT token belongs to the admin sub"""
    claims = get_jwt()
    return bool(claims.get("is_admin"))

@admin_advanced_bp.route('/overview', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_overview():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        total_users = User.query.count()
        total_complaints = Complaint.query.count()
        resolved_complaints = Complaint.query.filter_by(status='resolved').count()
        pending_complaints = Complaint.query.filter_by(status='pending').count()
        
        # Simple mock list for active platforms since we don't have analytics yet
        active_platforms = ["Twitter", "LinkedIn", "Instagram"]
        
        return jsonify({
            'total_users': total_users,
            'total_complaints': total_complaints,
            'resolved_complaints': resolved_complaints,
            'pending_complaints': pending_complaints,
            'active_platforms': active_platforms,
            'reports_today': 0 # To be implemented
        }), 200
    except Exception as e:
        logger.exception("Error fetching overview data")
        return jsonify({'error': str(e)}), 500

@admin_advanced_bp.route('/complaints', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_complaints():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        page, page_size, offset = parse_pagination(request.args, default_page_size=50, max_page_size=200)
        status_filter = (request.args.get('status') or '').strip().lower()
        query = Complaint.query
        if status_filter:
            query = query.filter(Complaint.status == status_filter)
        total = query.count()
        complaints = (
            query.order_by(Complaint.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return jsonify({
            'complaints': [c.to_dict() for c in complaints],
            'count': len(complaints),
            'total': total,
            'pagination': pagination_meta(total, page, page_size),
        }), 200
    except Exception as e:
        logger.exception("Error fetching complaints")
        return jsonify({'error': str(e)}), 500

@admin_advanced_bp.route('/users/<user_id>/ban', methods=['PUT'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def ban_user(user_id):
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        user.status = 'banned'
        Session.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        
        log = ActivityLog(action='banned_user', admin_id='admin', target=user_id)
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'message': 'User banned successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error banning user {user_id}")
        return jsonify({'error': str(e)}), 500
