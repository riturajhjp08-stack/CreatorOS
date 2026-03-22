from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    __table_args__ = (
        db.Index('idx_users_username', 'username'),
        db.Index('idx_users_category', 'category'),
        db.Index('idx_users_name', 'name'),
    )
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # None for OAuth users
    credits = db.Column(db.Integer, default=350)
    premium = db.Column(db.Boolean, default=False)
    premium_expires = db.Column(db.DateTime, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    username = db.Column(db.String(60), nullable=True)
    category = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    default_hashtags = db.Column(db.Text, nullable=True)
    default_cta = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    two_fa_enabled = db.Column(db.Boolean, default=False)
    email_notifications = db.Column(db.Boolean, default=True)
    marketing_emails = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(50), default='active')  # active, suspended, banned
    last_seen = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    oauth_accounts = db.relationship('OAuthAccount', backref='user', lazy=True, cascade='all, delete-orphan')
    connected_platforms = db.relationship('ConnectedPlatform', backref='user', lazy=True, cascade='all, delete-orphan')
    analytics_records = db.relationship('Analytics', backref='user', lazy=True, cascade='all, delete-orphan')
    scheduled_posts = db.relationship('ScheduledPost', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'category': self.category,
            'website': self.website,
            'default_hashtags': self.default_hashtags,
            'default_cta': self.default_cta,
            'email': self.email,
            'credits': self.credits,
            'premium': self.premium,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
        }

class OAuthAccount(db.Model):
    """OAuth account linking"""
    __tablename__ = 'oauth_accounts'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # google, tiktok, instagram, twitter, linkedin
    provider_user_id = db.Column(db.String(255), nullable=False)
    provider_username = db.Column(db.String(255), nullable=True)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    scope = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'provider', name='unique_user_provider'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'provider_username': self.provider_username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class ConnectedPlatform(db.Model):
    """Connected content platforms"""
    __tablename__ = 'connected_platforms'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # youtube, tiktok, instagram, twitter, linkedin
    platform_user_id = db.Column(db.String(255), nullable=False)
    platform_username = db.Column(db.String(255), nullable=True)
    platform_display_name = db.Column(db.String(255), nullable=True)
    profile_url = db.Column(db.String(500), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    scope = db.Column(db.String(1000), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'platform', name='unique_user_platform'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'platform_username': self.platform_username,
            'platform_display_name': self.platform_display_name,
            'profile_url': self.profile_url,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class Analytics(db.Model):
    """Platform analytics data"""
    __tablename__ = 'analytics'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    metric_date = db.Column(db.Date, nullable=False)
    
    # Basic metrics
    posts_count = db.Column(db.Integer, default=0)
    views = db.Column(db.BigInteger, default=0)
    engagement = db.Column(db.Integer, default=0)
    followers = db.Column(db.Integer, default=0)
    new_followers = db.Column(db.Integer, default=0)
    
    # Platform-specific data
    data = db.Column(db.JSON, default=dict)  # Stores platform-specific metrics
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.Index('idx_user_platform_date', 'user_id', 'platform', 'metric_date'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'metric_date': self.metric_date.isoformat() if self.metric_date else None,
            'posts_count': self.posts_count,
            'views': self.views,
            'engagement': self.engagement,
            'followers': self.followers,
            'new_followers': self.new_followers,
            'data': self.data,
        }

class Session(db.Model):
    """User sessions for JWT tracking"""
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(500), unique=True, nullable=False)
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class ScheduledPost(db.Model):
    """Scheduled and published posts managed by CreatorOS"""
    __tablename__ = 'scheduled_posts'

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    platform = db.Column(db.String(50), nullable=False, index=True)  # youtube, instagram, tiktok, twitter, linkedin
    status = db.Column(db.String(20), nullable=False, default='scheduled', index=True)  # scheduled, processing, published, failed, cancelled
    schedule_type = db.Column(db.String(20), nullable=False, default='now')  # now, optimal, custom
    scheduled_for = db.Column(db.DateTime, nullable=False, index=True)
    caption = db.Column(db.Text, nullable=True)
    hashtags = db.Column(db.String(1000), nullable=True)
    media_items = db.Column(db.JSON, default=list)  # file names and metadata only
    virality_score = db.Column(db.Integer, nullable=True)
    external_post_id = db.Column(db.String(255), nullable=True)
    publish_response = db.Column(db.JSON, default=dict)
    error_message = db.Column(db.String(500), nullable=True)
    credits_spent = db.Column(db.Integer, default=0)
    credits_earned = db.Column(db.Integer, default=0)
    reward_granted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'status': self.status,
            'schedule_type': self.schedule_type,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'caption': self.caption,
            'hashtags': self.hashtags,
            'media_items': self.media_items or [],
            'virality_score': self.virality_score,
            'external_post_id': self.external_post_id,
            'publish_response': self.publish_response or {},
            'error_message': self.error_message,
            'credits_spent': self.credits_spent,
            'credits_earned': self.credits_earned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }

class Feedback(db.Model):
    """User feedback and ratings for the CreatorOS app"""
    __tablename__ = 'feedback'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    message = db.Column(db.Text, nullable=True)
    reply = db.Column(db.Text, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('feedback', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else 'Unknown',
            'user_email': self.user.email if self.user else 'Unknown',
            'rating': self.rating,
            'message': self.message,
            'reply': self.reply,
            'replied_at': self.replied_at.isoformat() if self.replied_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class Notification(db.Model):
    """Real-time user notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=True, index=True)
    actor_user_id = db.Column(db.String(36), nullable=True, index=True)
    data = db.Column(db.JSON, default=dict)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'actor_user_id': self.actor_user_id,
            'data': self.data or {},
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class FriendRequest(db.Model):
    """Friend/connection requests for messaging"""
    __tablename__ = 'friend_requests'

    id = db.Column(db.String(36), primary_key=True)
    requester_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    responded_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('requester_id', 'recipient_id', name='unique_friend_request'),
        db.Index('idx_friend_request_pair', 'requester_id', 'recipient_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'requester_id': self.requester_id,
            'recipient_id': self.recipient_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
        }

class Message(db.Model):
    """Direct messages between users"""
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True)
    sender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=True)
    attachments = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime, nullable=True, index=True)
    delivered_at = db.Column(db.DateTime, nullable=True, index=True)

    __table_args__ = (
        db.Index('idx_messages_pair_time', 'sender_id', 'receiver_id', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'attachments': self.attachments or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
        }

class Follow(db.Model):
    """One-way follow relationships"""
    __tablename__ = 'follows'

    id = db.Column(db.String(36), primary_key=True)
    follower_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    following_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.UniqueConstraint('follower_id', 'following_id', name='unique_follow'),
        db.Index('idx_follow_pair', 'follower_id', 'following_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'follower_id': self.follower_id,
            'following_id': self.following_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class Complaint(db.Model):
    """User complaints about platform issues or other users"""
    __tablename__ = 'complaints'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(50)) # e.g. youtube, twitter
    complaint_type = db.Column(db.String(100)) # e.g. spam, bug, abuse
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending') # pending, resolved
    assigned_to = db.Column(db.String(255), nullable=True) # Admin name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('complaints', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user.name if self.user else 'Unknown',
            'platform': self.platform,
            'complaint_type': self.complaint_type,
            'message': self.message,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class ContentReport(db.Model):
    """Flags for specific malicious content"""
    __tablename__ = 'content_reports'
    
    id = db.Column(db.String(36), primary_key=True)
    post_id = db.Column(db.String(255), nullable=False) # ID of the post reported
    reporter_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    report_type = db.Column(db.String(100)) # spam, hate_speech, fake_account
    status = db.Column(db.String(50), default='pending') # pending, removed, ignored
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'report_type': self.report_type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class ActivityLog(db.Model):
    """Audit logs for Admin actions"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.String(36), primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    admin_id = db.Column(db.String(255), nullable=False)
    target = db.Column(db.String(255), nullable=True)
    platform = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'admin_id': self.admin_id,
            'target': self.target,
            'platform': self.platform,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
