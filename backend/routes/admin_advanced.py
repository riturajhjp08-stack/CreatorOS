import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func, and_

from models import db, User, Complaint, ContentReport, ActivityLog, Analytics, ConnectedPlatform
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

        now = datetime.utcnow()
        start_day = datetime(now.year, now.month, now.day)
        complaints_today = Complaint.query.filter(Complaint.created_at >= start_day).count()
        content_reports_today = ContentReport.query.filter(ContentReport.created_at >= start_day).count()

        platform_rows = (
            db.session.query(
                ConnectedPlatform.platform,
                func.count(ConnectedPlatform.id).label("count"),
            )
            .group_by(ConnectedPlatform.platform)
            .order_by(func.count(ConnectedPlatform.id).desc())
            .limit(8)
            .all()
        )
        active_platforms = [
            {"platform": row[0], "count": int(row[1])}
            for row in platform_rows
            if row[0]
        ]
        
        return jsonify({
            'total_users': total_users,
            'total_complaints': total_complaints,
            'resolved_complaints': resolved_complaints,
            'pending_complaints': pending_complaints,
            'active_platforms': active_platforms,
            'complaints_today': complaints_today,
            'content_reports_today': content_reports_today,
            'reports_today': complaints_today + content_reports_today,
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


@admin_advanced_bp.route('/social-metrics', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_social_metrics():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        latest = (
            db.session.query(
                Analytics.user_id.label("user_id"),
                Analytics.platform.label("platform"),
                func.max(Analytics.metric_date).label("max_date"),
            )
            .group_by(Analytics.user_id, Analytics.platform)
            .subquery()
        )
        rows = (
            db.session.query(
                Analytics.platform.label("platform"),
                func.sum(Analytics.followers).label("followers"),
                func.sum(Analytics.views).label("views"),
                func.sum(Analytics.engagement).label("engagement"),
                func.sum(Analytics.posts_count).label("posts_count"),
            )
            .join(
                latest,
                and_(
                    Analytics.user_id == latest.c.user_id,
                    Analytics.platform == latest.c.platform,
                    Analytics.metric_date == latest.c.max_date,
                ),
            )
            .group_by(Analytics.platform)
            .order_by(func.sum(Analytics.followers).desc())
            .all()
        )
        metrics = [
            {
                "platform": row.platform,
                "followers": int(row.followers or 0),
                "views": int(row.views or 0),
                "engagement": int(row.engagement or 0),
                "posts_count": int(row.posts_count or 0),
            }
            for row in rows
            if row.platform
        ]
        return jsonify({"metrics": metrics, "count": len(metrics)}), 200
    except Exception as e:
        logger.exception("Error fetching social metrics")
        return jsonify({'error': str(e)}), 500


@admin_advanced_bp.route('/content-reports', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_content_reports():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        page, page_size, offset = parse_pagination(request.args, default_page_size=50, max_page_size=200)
        query = ContentReport.query
        total = query.count()
        reports = (
            query.order_by(ContentReport.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return jsonify({
            "reports": [r.to_dict() for r in reports],
            "count": len(reports),
            "total": total,
            "pagination": pagination_meta(total, page, page_size),
        }), 200
    except Exception as e:
        logger.exception("Error fetching content reports")
        return jsonify({'error': str(e)}), 500


@admin_advanced_bp.route('/activity', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_activity_logs():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        page, page_size, offset = parse_pagination(request.args, default_page_size=50, max_page_size=200)
        query = ActivityLog.query
        total = query.count()
        logs = (
            query.order_by(ActivityLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return jsonify({
            "logs": [l.to_dict() for l in logs],
            "count": len(logs),
            "total": total,
            "pagination": pagination_meta(total, page, page_size),
        }), 200
    except Exception as e:
        logger.exception("Error fetching activity logs")
        return jsonify({'error': str(e)}), 500


@admin_advanced_bp.route('/trending', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_ADMIN", "60 per minute"))
def get_trending():
    if not admin_required():
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        complaint_type_rows = (
            db.session.query(Complaint.complaint_type, func.count(Complaint.id))
            .filter(Complaint.complaint_type.isnot(None))
            .group_by(Complaint.complaint_type)
            .order_by(func.count(Complaint.id).desc())
            .limit(5)
            .all()
        )
        complaint_platform_rows = (
            db.session.query(Complaint.platform, func.count(Complaint.id))
            .filter(Complaint.platform.isnot(None))
            .group_by(Complaint.platform)
            .order_by(func.count(Complaint.id).desc())
            .limit(5)
            .all()
        )
        report_type_rows = (
            db.session.query(ContentReport.report_type, func.count(ContentReport.id))
            .filter(ContentReport.report_type.isnot(None))
            .group_by(ContentReport.report_type)
            .order_by(func.count(ContentReport.id).desc())
            .limit(5)
            .all()
        )

        return jsonify({
            "complaints_by_type": [
                {"label": row[0], "count": int(row[1])} for row in complaint_type_rows if row[0]
            ],
            "complaints_by_platform": [
                {"label": row[0], "count": int(row[1])} for row in complaint_platform_rows if row[0]
            ],
            "reports_by_type": [
                {"label": row[0], "count": int(row[1])} for row in report_type_rows if row[0]
            ],
        }), 200
    except Exception as e:
        logger.exception("Error fetching trending data")
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
