import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Feedback
import uuid
from extensions import limiter

feedback_bp = Blueprint('feedback', __name__)
logger = logging.getLogger(__name__)

@feedback_bp.route('', methods=['POST'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_FEEDBACK", "10 per hour"))
def submit_feedback():
    """Submit user feedback and rating"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        
        rating = data.get('rating')
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return {'error': 'A valid rating between 1 and 5 is required'}, 400
            
        message = (data.get('message') or '').strip()
        if len(message) > 2000:
            return {'error': 'Message too long (max 2000 characters)'}, 400
        
        feedback = Feedback(
            id=str(uuid.uuid4()),
            user_id=user_id,
            rating=rating,
            message=message
        )
        db.session.add(feedback)
        db.session.commit()
        
        return {'success': True, 'feedback': feedback.to_dict()}, 201
        
    except Exception as e:
        logger.exception("Error submitting feedback")
        return {'error': 'Failed to submit feedback'}, 500
