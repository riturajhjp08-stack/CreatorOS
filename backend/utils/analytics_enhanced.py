"""
Enhanced Analytics Utilities for Real-Time Social Media Data Syncing
Production-ready utilities for syncing analytics from YouTube, Instagram, TikTok, Twitter, LinkedIn
"""

import requests
import uuid
import logging
from datetime import datetime, date, timedelta
from models import db, Analytics, ConnectedPlatform
import json

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
#  TOKEN MANAGEMENT
# ══════════════════════════════════════════════════════════════════

def refresh_access_token(platform):
    """
    Refresh expired access tokens for a platform
    
    Args:
        platform: ConnectedPlatform object
    
    Returns:
        bool: True if refresh successful, False otherwise
    """
    try:
        if platform.platform == 'youtube':
            return refresh_google_token(platform)
        elif platform.platform == 'instagram':
            return refresh_instagram_token(platform)
        elif platform.platform == 'tiktok':
            return refresh_tiktok_token(platform)
        elif platform.platform == 'twitter':
            return refresh_twitter_token(platform)
        elif platform.platform == 'linkedin':
            return refresh_linkedin_token(platform)
    except Exception as e:
        logger.error(f"Token refresh error for {platform.platform}: {str(e)}")
        return False

def refresh_google_token(platform):
    """Refresh Google OAuth token"""
    from flask import current_app
    
    if not platform.refresh_token:
        return False
    
    try:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': current_app.config['GOOGLE_CLIENT_ID'],
            'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
            'refresh_token': platform.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=data)
        tokens = response.json()
        
        if 'error' in tokens:
            logger.error(f"Google token refresh failed: {tokens['error']}")
            return False
        
        platform.access_token = tokens['access_token']
        if 'refresh_token' in tokens:
            platform.refresh_token = tokens['refresh_token']
        platform.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
        platform.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Google token refreshed for platform {platform.id}")
        return True
    except Exception as e:
        logger.error(f"Google token refresh exception: {str(e)}")
        return False

def refresh_instagram_token(platform):
    """Refresh Instagram long-lived token"""
    from flask import current_app
    
    try:
        token_url = "https://graph.instagram.com/v18.0/refresh_access_token"
        params = {
            'grant_type': 'ig_refresh_token',
            'access_token': platform.access_token
        }
        
        response = requests.get(token_url, params=params)
        data = response.json()
        
        if 'error' in data:
            logger.error(f"Instagram token refresh failed: {data['error']}")
            return False
        
        platform.access_token = data['access_token']
        expires_in = data.get('expires_in', 5184000)  # 60 days default
        platform.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        platform.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Instagram token refreshed for platform {platform.id}")
        return True
    except Exception as e:
        logger.error(f"Instagram token refresh exception: {str(e)}")
        return False

def refresh_tiktok_token(platform):
    """Refresh TikTok token"""
    from flask import current_app
    
    if not platform.refresh_token:
        return False
    
    try:
        token_url = "https://open.tiktokapis.com/v1/oauth/token/"
        data = {
            'client_key': current_app.config['TIKTOK_CLIENT_ID'],
            'client_secret': current_app.config['TIKTOK_CLIENT_SECRET'],
            'grant_type': 'refresh_token',
            'refresh_token': platform.refresh_token
        }
        
        response = requests.post(token_url, json=data)
        tokens = response.json()
        
        if 'error' in tokens:
            logger.error(f"TikTok token refresh failed: {tokens['error']}")
            return False
        
        platform.access_token = tokens['access_token']
        if 'refresh_token' in tokens:
            platform.refresh_token = tokens['refresh_token']
        platform.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
        platform.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"TikTok token refreshed for platform {platform.id}")
        return True
    except Exception as e:
        logger.error(f"TikTok token refresh exception: {str(e)}")
        return False

def refresh_twitter_token(platform):
    """Refresh Twitter OAuth token"""
    from flask import current_app
    
    if not platform.refresh_token:
        return False
    
    try:
        token_url = "https://api.twitter.com/2/oauth2/token"
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': platform.refresh_token,
            'client_id': current_app.config['TWITTER_API_KEY'],
            'client_secret': current_app.config['TWITTER_API_SECRET']
        }
        
        response = requests.post(token_url, json=data, auth=(
            current_app.config['TWITTER_API_KEY'],
            current_app.config['TWITTER_API_SECRET']
        ))
        tokens = response.json()
        
        if 'error' in tokens:
            logger.error(f"Twitter token refresh failed: {tokens['error']}")
            return False
        
        platform.access_token = tokens['access_token']
        if 'refresh_token' in tokens:
            platform.refresh_token = tokens['refresh_token']
        platform.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
        platform.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Twitter token refreshed for platform {platform.id}")
        return True
    except Exception as e:
        logger.error(f"Twitter token refresh exception: {str(e)}")
        return False

def refresh_linkedin_token(platform):
    """Refresh LinkedIn token"""
    from flask import current_app
    
    if not platform.refresh_token:
        return False
    
    try:
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': platform.refresh_token,
            'client_id': current_app.config['LINKEDIN_CLIENT_ID'],
            'client_secret': current_app.config['LINKEDIN_CLIENT_SECRET']
        }
        
        response = requests.post(token_url, data=data)
        tokens = response.json()
        
        if 'error' in tokens:
            logger.error(f"LinkedIn token refresh failed: {tokens['error']}")
            return False
        
        platform.access_token = tokens['access_token']
        platform.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
        platform.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"LinkedIn token refreshed for platform {platform.id}")
        return True
    except Exception as e:
        logger.error(f"LinkedIn token refresh exception: {str(e)}")
        return False

# ══════════════════════════════════════════════════════════════════
#  YOUTUBE ANALYTICS
# ══════════════════════════════════════════════════════════════════

def sync_youtube_analytics(user_id, platform_id, access_token):
    """
    Sync YouTube channel analytics in real-time
    Fetches: subscribers, views, engagement, video count
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get channel statistics
        channels_url = 'https://www.googleapis.com/youtube/v3/channels'
        channels_params = {
            'part': 'statistics,snippet',
            'mine': 'true'
        }
        
        channels_response = requests.get(channels_url, headers=headers, params=channels_params)
        channels_data = channels_response.json()
        
        if 'error' in channels_data or not channels_data.get('items'):
            logger.error(f"YouTube channels error: {channels_data}")
            return False
        
        stats = channels_data['items'][0]['statistics']
        
        # Get video analytics for engagement
        videos_url = 'https://www.googleapis.com/youtube/v3/videos'
        videos_params = {
            'part': 'statistics',
            'forMine': 'true',
            'maxResults': 50
        }
        
        videos_response = requests.get(videos_url, headers=headers, params=videos_params)
        videos_data = videos_response.json()
        
        total_engagement = 0
        if 'items' in videos_data:
            for video in videos_data['items']:
                video_stats = video.get('statistics', {})
                total_engagement += int(video_stats.get('likeCount', 0)) + int(video_stats.get('commentCount', 0))
        
        # Create or update analytics record
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='youtube', metric_date=today
        ).first()
        
        analytics_data = {
            'view_count': int(stats.get('viewCount', 0)),
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'comment_count': total_engagement
        }
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='youtube',
                metric_date=today,
                views=int(stats.get('viewCount', 0)),
                followers=int(stats.get('subscriberCount', 0)),
                posts_count=int(stats.get('videoCount', 0)),
                engagement=total_engagement,
                data=analytics_data
            )
            db.session.add(analytics)
        else:
            analytics.views = int(stats.get('viewCount', 0))
            analytics.followers = int(stats.get('subscriberCount', 0))
            analytics.posts_count = int(stats.get('videoCount', 0))
            analytics.engagement = total_engagement
            analytics.data = analytics_data
        
        db.session.commit()
        logger.info(f"YouTube analytics synced for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"YouTube sync error: {str(e)}")
        return False

# ══════════════════════════════════════════════════════════════════
#  INSTAGRAM ANALYTICS
# ══════════════════════════════════════════════════════════════════

def sync_instagram_analytics(user_id, platform_id, access_token):
    """
    Sync Instagram Business Account analytics in real-time
    Fetches: followers, posts, likes, comments, reach engagement
    """
    try:
        # Get Instagram Business Account insights
        user_url = 'https://graph.instagram.com/v18.0/me'
        user_params = {
            'fields': 'id,username,name,followers_count,biography,profile_picture_url,media_count,ig_id,website',
            'access_token': access_token
        }
        
        user_response = requests.get(user_url, params=user_params)
        user_data = user_response.json()
        
        if 'error' in user_data:
            logger.error(f"Instagram user error: {user_data['error']}")
            return False
        
        # Get insights
        insights_url = f"https://graph.instagram.com/v18.0/{user_data['id']}/insights"
        insights_params = {
            'metric': 'impressions,reach,engagement',
            'access_token': access_token
        }
        
        insights_response = requests.get(insights_url, params=insights_params)
        insights_data = insights_response.json()
        
        total_reach = 0
        total_impressions = 0
        total_engagement = 0
        
        if 'data' in insights_data:
            for metric in insights_data['data']:
                if metric['name'] == 'reach':
                    total_reach = metric['values'][0]['value']
                elif metric['name'] == 'impressions':
                    total_impressions = metric['values'][0]['value']
                elif metric['name'] == 'engagement':
                    total_engagement = metric['values'][0]['value']
        
        # Create or update analytics record
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='instagram', metric_date=today
        ).first()
        
        analytics_data = {
            'followers_count': user_data.get('followers_count', 0),
            'media_count': user_data.get('media_count', 0),
            'reach': total_reach,
            'impressions': total_impressions,
            'engagement': total_engagement,
            'username': user_data.get('username'),
            'biography': user_data.get('biography')
        }
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='instagram',
                metric_date=today,
                followers=user_data.get('followers_count', 0),
                posts_count=user_data.get('media_count', 0),
                views=total_impressions,
                engagement=total_engagement,
                data=analytics_data
            )
            db.session.add(analytics)
        else:
            analytics.followers = user_data.get('followers_count', 0)
            analytics.posts_count = user_data.get('media_count', 0)
            analytics.views = total_impressions
            analytics.engagement = total_engagement
            analytics.data = analytics_data
        
        db.session.commit()
        logger.info(f"Instagram analytics synced for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Instagram sync error: {str(e)}")
        return False

# ══════════════════════════════════════════════════════════════════
#  TIKTOK ANALYTICS
# ══════════════════════════════════════════════════════════════════

def sync_tiktok_analytics(user_id, platform_id, access_token):
    """
    Sync TikTok user analytics in real-time
    Fetches: followers, video count, likes, views
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get user statistics
        stat_url = 'https://open.tiktokapis.com/v1/user/stat/'
        stat_params = {
            'fields': 'follower_count,video_count,heart_count,download_count,share_count,comment_count'
        }
        
        stat_response = requests.get(stat_url, headers=headers, params=stat_params)
        stat_data = stat_response.json()
        
        if 'error' in stat_data or 'data' not in stat_data:
            logger.error(f"TikTok stats error: {stat_data}")
            return False
        
        user_stat = stat_data['data']['user_stat']
        
        # Get video analytics for more details
        videos_url = 'https://open.tiktokapis.com/v1/video/list/'
        videos_params = {
            'fields': 'id,create_time,view_count,like_count,comment_count,share_count'
        }
        
        total_views = 0
        try:
            videos_response = requests.get(videos_url, headers=headers, params=videos_params)
            videos_data = videos_response.json()
            
            if 'data' in videos_data and 'videos' in videos_data['data']:
                for video in videos_data['data']['videos']:
                    total_views += int(video.get('view_count', 0))
        except:
            pass
        
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='tiktok', metric_date=today
        ).first()
        
        analytics_data = {
            'follower_count': user_stat.get('follower_count', 0),
            'video_count': user_stat.get('video_count', 0),
            'heart_count': user_stat.get('heart_count', 0),
            'download_count': user_stat.get('download_count', 0),
            'share_count': user_stat.get('share_count', 0),
            'comment_count': user_stat.get('comment_count', 0)
        }
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='tiktok',
                metric_date=today,
                followers=user_stat.get('follower_count', 0),
                posts_count=user_stat.get('video_count', 0),
                views=total_views,
                engagement=user_stat.get('heart_count', 0) + user_stat.get('comment_count', 0),
                data=analytics_data
            )
            db.session.add(analytics)
        else:
            analytics.followers = user_stat.get('follower_count', 0)
            analytics.posts_count = user_stat.get('video_count', 0)
            analytics.views = total_views
            analytics.engagement = user_stat.get('heart_count', 0) + user_stat.get('comment_count', 0)
            analytics.data = analytics_data
        
        db.session.commit()
        logger.info(f"TikTok analytics synced for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"TikTok sync error: {str(e)}")
        return False

# ══════════════════════════════════════════════════════════════════
#  TWITTER ANALYTICS
# ══════════════════════════════════════════════════════════════════

def sync_twitter_analytics(user_id, platform_id, access_token):
    """Sync Twitter/X user analytics in real-time"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get user metrics
        user_url = 'https://api.twitter.com/2/users/me'
        user_params = {
            'user.fields': 'public_metrics,created_at,followers_count'
        }
        
        user_response = requests.get(user_url, headers=headers, params=user_params)
        user_data = user_response.json()
        
        if 'error' in user_data or 'data' not in user_data:
            logger.error(f"Twitter user error: {user_data}")
            return False
        
        metrics = user_data['data'].get('public_metrics', {})
        
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='twitter', metric_date=today
        ).first()
        
        analytics_data = {
            'followers_count': metrics.get('followers_count', 0),
            'following_count': metrics.get('following_count', 0),
            'tweet_count': metrics.get('tweet_count', 0),
            'listed_count': metrics.get('listed_count', 0)
        }
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='twitter',
                metric_date=today,
                followers=metrics.get('followers_count', 0),
                posts_count=metrics.get('tweet_count', 0),
                data=analytics_data
            )
            db.session.add(analytics)
        else:
            analytics.followers = metrics.get('followers_count', 0)
            analytics.posts_count = metrics.get('tweet_count', 0)
            analytics.data = analytics_data
        
        db.session.commit()
        logger.info(f"Twitter analytics synced for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Twitter sync error: {str(e)}")
        return False

# ══════════════════════════════════════════════════════════════════
#  LINKEDIN ANALYTICS
# ══════════════════════════════════════════════════════════════════

def sync_linkedin_analytics(user_id, platform_id, access_token):
    """Sync LinkedIn profile analytics"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get profile info
        me_url = 'https://api.linkedin.com/v2/me'
        me_response = requests.get(me_url, headers=headers)
        me_data = me_response.json()
        
        if 'error' in me_data:
            logger.error(f"LinkedIn profile error: {me_data}")
            return False
        
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='linkedin', metric_date=today
        ).first()
        
        # LinkedIn followers data structure
        analytics_data = {
            'profile_id': me_data.get('id'),
            'first_name': me_data.get('firstName', {}).get('localized', {}).get('en_US'),
            'last_name': me_data.get('lastName', {}).get('localized', {}).get('en_US')
        }
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='linkedin',
                metric_date=today,
                data=analytics_data
            )
            db.session.add(analytics)
        else:
            analytics.data = analytics_data
        
        db.session.commit()
        logger.info(f"LinkedIn analytics synced for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"LinkedIn sync error: {str(e)}")
        return False

# ══════════════════════════════════════════════════════════════════
#  CONCURRENT SYNC (for background tasks)
# ══════════════════════════════════════════════════════════════════

def sync_all_user_platforms(user_id):
    """
    Sync analytics for all active platforms of a user
    Suitable for background task execution
    """
    try:
        from models import ConnectedPlatform
        
        platforms = ConnectedPlatform.query.filter_by(
            user_id=user_id, is_active=True
        ).all()
        
        results = {
            'synced': [],
            'failed': []
        }
        
        for platform in platforms:
            try:
                # Refresh token if expired
                if platform.token_expires_at and datetime.utcnow() >= platform.token_expires_at:
                    if not refresh_access_token(platform):
                        results['failed'].append(f"{platform.platform}: Token refresh failed")
                        continue
                
                # Sync analytics based on platform
                success = False
                if platform.platform == 'youtube':
                    success = sync_youtube_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'instagram':
                    success = sync_instagram_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'tiktok':
                    success = sync_tiktok_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'twitter':
                    success = sync_twitter_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'linkedin':
                    success = sync_linkedin_analytics(user_id, platform.id, platform.access_token)
                
                if success:
                    platform.last_sync = datetime.utcnow()
                    db.session.commit()
                    results['synced'].append(platform.platform)
                else:
                    results['failed'].append(f"{platform.platform}: Sync failed")
                    
            except Exception as e:
                logger.error(f"Error syncing {platform.platform}: {str(e)}")
                results['failed'].append(f"{platform.platform}: {str(e)}")
        
        return results
    except Exception as e:
        logger.error(f"Sync all platforms error: {str(e)}")
        return {'error': str(e)}
