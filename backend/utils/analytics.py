"""
Enhanced Analytics Utilities for Real-Time Social Media Data Syncing
Production-ready utilities for syncing analytics from YouTube, Instagram, TikTok, Twitter, LinkedIn
"""

import os
import requests
import uuid
import logging
from datetime import datetime, date, timedelta
from flask import current_app
from models import db, Analytics, ConnectedPlatform

logger = logging.getLogger(__name__)


def _get_timeout():
    default_timeout = int(os.environ.get("API_REQUEST_TIMEOUT_SECONDS", 15))
    try:
        return int(current_app.config.get("API_REQUEST_TIMEOUT_SECONDS", default_timeout))
    except Exception:
        return default_timeout

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
        
        response = requests.post(token_url, data=data, timeout=_get_timeout())
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
        
        response = requests.get(token_url, params=params, timeout=_get_timeout())
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
        
        response = requests.post(token_url, json=data, timeout=_get_timeout())
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
        client_id = current_app.config.get('TWITTER_CLIENT_ID') or current_app.config.get('TWITTER_API_KEY')
        client_secret = current_app.config.get('TWITTER_CLIENT_SECRET') or current_app.config.get('TWITTER_API_SECRET')
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': platform.refresh_token,
            'client_id': client_id,
            'client_secret': client_secret
        }

        auth = (client_id, client_secret) if client_id and client_secret else None
        response = requests.post(token_url, json=data, auth=auth, timeout=_get_timeout())
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
        
        response = requests.post(token_url, data=data, timeout=_get_timeout())
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
        
        channels_response = requests.get(
            channels_url,
            headers=headers,
            params=channels_params,
            timeout=_get_timeout(),
        )
        channels_data = channels_response.json()
        
        if 'error' in channels_data or not channels_data.get('items'):
            logger.error(f"YouTube channels error: {channels_data}")
            return False
        
        channel_item = channels_data['items'][0]
        stats = channel_item.get('statistics', {})
        snippet = channel_item.get('snippet', {})
        
        # Get video analytics for engagement
        videos_url = 'https://www.googleapis.com/youtube/v3/videos'
        videos_params = {
            'part': 'statistics',
            'forMine': 'true',
            'maxResults': 50
        }
        
        videos_response = requests.get(
            videos_url,
            headers=headers,
            params=videos_params,
            timeout=_get_timeout(),
        )
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
            'channel_id': channel_item.get('id'),
            'channel_title': snippet.get('title'),
            'channel_custom_url': snippet.get('customUrl'),
            'channel_published_at': snippet.get('publishedAt'),
            'channel_country': snippet.get('country'),
            'view_count': int(stats.get('viewCount', 0)),
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'hidden_subscriber_count': bool(stats.get('hiddenSubscriberCount', False)),
            'comment_like_engagement': total_engagement
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

def sync_tiktok_analytics(user_id, platform_id, access_token):
    """Sync TikTok analytics"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get user stats
        url = 'https://open.tiktokapis.com/v1/user/stat/'
        params = {'fields': 'follower_count,video_count,heart_count'}
        response = requests.get(url, headers=headers, params=params, timeout=_get_timeout())
        data = response.json()
        
        if 'error' in data or 'data' not in data:
            return
        
        user_stats = data['data']['user_stat']
        
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='tiktok', metric_date=today
        ).first()
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='tiktok',
                metric_date=today,
                followers=user_stats.get('follower_count', 0),
                posts_count=user_stats.get('video_count', 0),
                engagement=user_stats.get('heart_count', 0)
            )
            db.session.add(analytics)
        else:
            analytics.followers = user_stats.get('follower_count', 0)
            analytics.posts_count = user_stats.get('video_count', 0)
            analytics.engagement = user_stats.get('heart_count', 0)
        
        db.session.commit()
    except Exception:
        logger.exception("TikTok sync error")

def sync_instagram_analytics(user_id, platform_id, access_token):
    """Sync Instagram analytics"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get Instagram Business Account insights
        url = 'https://graph.instagram.com/me'
        params = {
            'fields': 'name,followers_count,media_count,ig_id,biography,profile_picture_url',
            'access_token': access_token
        }
        response = requests.get(url, params=params, timeout=_get_timeout())
        data = response.json()
        
        if 'error' in data:
            return
        
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='instagram', metric_date=today
        ).first()
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='instagram',
                metric_date=today,
                followers=data.get('followers_count', 0),
                posts_count=data.get('media_count', 0)
            )
            db.session.add(analytics)
        else:
            analytics.followers = data.get('followers_count', 0)
            analytics.posts_count = data.get('media_count', 0)
        
        db.session.commit()
    except Exception:
        logger.exception("Instagram sync error")

def sync_twitter_analytics(user_id, platform_id, access_token):
    """Sync Twitter/X analytics"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get user info
        url = 'https://api.twitter.com/2/users/me'
        params = {'user.fields': 'public_metrics,created_at'}
        response = requests.get(url, headers=headers, params=params, timeout=_get_timeout())
        data = response.json()
        
        if 'error' in data or 'data' not in data:
            return
        
        user_data = data['data']
        metrics = user_data.get('public_metrics', {})
        
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='twitter', metric_date=today
        ).first()
        
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='twitter',
                metric_date=today,
                followers=metrics.get('followers_count', 0),
                posts_count=metrics.get('tweet_count', 0),
                views=metrics.get('impression_count', 0)
            )
            db.session.add(analytics)
        else:
            analytics.followers = metrics.get('followers_count', 0)
            analytics.posts_count = metrics.get('tweet_count', 0)
            analytics.views = metrics.get('impression_count', 0)
        
        db.session.commit()
    except Exception:
        logger.exception("Twitter sync error")

def sync_linkedin_analytics(user_id, platform_id, access_token):
    """Sync LinkedIn analytics"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}

        # Prefer OIDC userinfo for modern LinkedIn apps, fallback to /me.
        userinfo = {}
        profile = {}

        userinfo_response = requests.get(
            'https://api.linkedin.com/v2/userinfo',
            headers=headers,
            timeout=_get_timeout(),
        )
        if userinfo_response.ok:
            userinfo = userinfo_response.json() or {}

        if not userinfo.get('sub'):
            profile_response = requests.get(
                'https://api.linkedin.com/v2/me',
                headers=headers,
                timeout=_get_timeout(),
            )
            if profile_response.ok:
                profile = profile_response.json() or {}

        if not userinfo and not profile:
            return False
        
        today = date.today()
        analytics = Analytics.query.filter_by(
            user_id=user_id, platform='linkedin', metric_date=today
        ).first()

        full_name = (
            userinfo.get('name')
            or f"{profile.get('localizedFirstName', '')} {profile.get('localizedLastName', '')}".strip()
            or 'LinkedIn User'
        )

        member_id = userinfo.get('sub') or profile.get('id')
        person_urn = f"urn:li:person:{member_id}" if member_id else None
        followers_count = None
        posts_count = None

        # Best-effort: these endpoints may require additional LinkedIn permissions.
        if person_urn:
            try:
                followers_resp = requests.get(
                    f'https://api.linkedin.com/v2/networkSizes/{person_urn}',
                    headers=headers,
                    params={'edgeType': 'MemberToFollower'},
                    timeout=_get_timeout(),
                )
                if followers_resp.ok:
                    followers_json = followers_resp.json() or {}
                    followers_count = followers_json.get('firstDegreeSize')
            except Exception:
                followers_count = None

            try:
                posts_resp = requests.get(
                    'https://api.linkedin.com/v2/ugcPosts',
                    headers=headers,
                    params={'q': 'authors', 'authors': f'List({person_urn})', 'count': 1, 'start': 0},
                    timeout=_get_timeout(),
                )
                if posts_resp.ok:
                    posts_json = posts_resp.json() or {}
                    paging = posts_json.get('paging') or {}
                    posts_count = paging.get('total')
            except Exception:
                posts_count = None

        analytics_payload = {
            'member_id': userinfo.get('sub') or profile.get('id'),
            'name': full_name,
            'given_name': userinfo.get('given_name') or profile.get('localizedFirstName'),
            'family_name': userinfo.get('family_name') or profile.get('localizedLastName'),
            'email': userinfo.get('email'),
            'email_verified': userinfo.get('email_verified'),
            'locale': userinfo.get('locale'),
            'picture': userinfo.get('picture'),
            'raw_userinfo': userinfo if userinfo else None,
            'raw_profile': profile if profile else None,
            'followers_available': followers_count is not None,
            'posts_available': posts_count is not None,
            'synced_at': datetime.utcnow().isoformat()
        }

        # Member analytics are limited without additional LinkedIn products.
        if not analytics:
            analytics = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='linkedin',
                metric_date=today,
                posts_count=posts_count,
                views=0,
                followers=followers_count,
                engagement=0,
                data=analytics_payload
            )
            db.session.add(analytics)
        else:
            analytics.followers = followers_count
            analytics.posts_count = posts_count
            analytics.data = analytics_payload
        
        db.session.commit()
        return True
    except Exception:
        logger.exception("LinkedIn sync error")
        return False
