from flask import Blueprint, request, jsonify, current_app, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
import uuid
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
import logging
from models import db, ConnectedPlatform, User, OAuthAccount, Analytics
from utils.analytics import (sync_youtube_analytics, sync_tiktok_analytics, 
                             sync_instagram_analytics, sync_twitter_analytics, 
                             sync_linkedin_analytics, refresh_access_token)
from utils.auth_security import (
    build_url_with_query,
    create_oauth_state,
    sanitize_frontend_url,
    verify_oauth_state,
)
from extensions import limiter

logger = logging.getLogger(__name__)

platforms_bp = Blueprint('platforms', __name__)
_TWITTER_PKCE_STORE = {}

def _enqueue_sync_all(user_id):
    try:
        from tasks import sync_all_analytics_task
        sync_all_analytics_task.delay(user_id)
        return True
    except Exception:
        logger.exception("Failed to enqueue analytics sync")
        return False


def _redirect_to_frontend(state_payload, platform, success=True, error=None):
    frontend_url = sanitize_frontend_url((state_payload or {}).get('redirect_url'))
    params = {'platform': platform}
    if success:
        params['oauth'] = 'success'
    else:
        params['oauth'] = 'error'
        params['error'] = error or f'Failed to connect {platform}'
    return redirect(build_url_with_query(frontend_url, params))

# ═════════════════════════════════════════
#  PLATFORM CONNECTION ROUTES
# ═════════════════════════════════════════

@platforms_bp.route('/connected', methods=['GET'])
@jwt_required()
def get_connected_platforms():
    """Get all connected platforms for user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return {'error': 'User not found'}, 404
        
        platforms = ConnectedPlatform.query.filter_by(user_id=user_id, is_active=True).all()
        serialized = []

        for platform in platforms:
            item = platform.to_dict()
            latest = Analytics.query.filter_by(
                user_id=user_id,
                platform=platform.platform
            ).order_by(Analytics.metric_date.desc()).first()
            item['latest_analytics'] = latest.to_dict() if latest else None
            serialized.append(item)
        
        return {
            'count': len(serialized),
            'platforms': serialized
        }, 200
    except Exception:
        logger.exception("Error getting connected platforms")
        return {'error': 'Failed to fetch connected platforms'}, 500

# ═════════════════════════════════════════
#  YOUTUBE OAUTH
# ═════════════════════════════════════════

@platforms_bp.route('/youtube/auth', methods=['POST'])
@jwt_required()
def youtube_auth():
    """Initiate YouTube OAuth"""
    try:
        user_id = get_jwt_identity()
        payload = request.get_json(silent=True) or {}
        redirect_url = payload.get('redirect_url')
        
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        oauth_state = create_oauth_state(
            provider='youtube',
            mode='connect',
            user_id=user_id,
            redirect_url=redirect_url
        )
        params = {
            'client_id': current_app.config['GOOGLE_CLIENT_ID'],
            'redirect_uri': current_app.config['GOOGLE_PLATFORM_CALLBACK_URL'],
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl openid email profile',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': oauth_state
        }
        
        from urllib.parse import urlencode
        auth_url = google_auth_url + '?' + urlencode(params)
        return {'auth_url': auth_url}, 200
    except Exception:
        logger.exception("YouTube auth error")
        return {'error': 'Failed to initialize YouTube OAuth'}, 500

@platforms_bp.route('/youtube/callback', methods=['GET'])
def youtube_callback():
    """YouTube OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        provider_error = request.args.get('error')
        
        if not code or not state:
            return {'error': 'Missing code or state'}, 400

        state_payload, state_error = verify_oauth_state(
            state,
            expected_provider='youtube',
            expected_mode='connect'
        )
        if state_error:
            return {'error': state_error}, 400

        user_id = state_payload.get('user_id')
        if not user_id:
            return {'error': 'Invalid OAuth state payload'}, 400

        if provider_error:
            return _redirect_to_frontend(state_payload, 'youtube', success=False, error='YouTube authorization denied')
        
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'code': code,
            'client_id': current_app.config['GOOGLE_CLIENT_ID'],
            'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
            'redirect_uri': current_app.config['GOOGLE_PLATFORM_CALLBACK_URL'],
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=data, timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15))
        tokens = response.json()
        
        if 'error' in tokens:
            logger.error(f"Token exchange error: {tokens['error']}")
            return _redirect_to_frontend(state_payload, 'youtube', success=False, error='YouTube token exchange failed')

        granted_scopes = tokens.get('scope', '')
        if 'https://www.googleapis.com/auth/youtube' not in granted_scopes:
            return _redirect_to_frontend(state_payload, 'youtube', success=False, error='You must check the box for "Manage your YouTube account" to grant delete access.')
        
        # Get YouTube channel info
        youtube_url = 'https://www.googleapis.com/youtube/v3/channels'
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        params = {'part': 'snippet,statistics,contentDetails', 'mine': 'true'}
        
        yt_response = requests.get(youtube_url, headers=headers, params=params, timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15))
        yt_data = yt_response.json()
        
        if 'error' in yt_data or not yt_data.get('items'):
            logger.error(f"YouTube info error: {yt_data}")
            return _redirect_to_frontend(state_payload, 'youtube', success=False, error='Failed to fetch YouTube channel info')
        
        channel = yt_data['items'][0]
        channel_id = channel['id']
        
        # Find or update platform connection
        platform = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform='youtube'
        ).first()
        
        if platform:
            platform.access_token = tokens['access_token']
            platform.refresh_token = tokens.get('refresh_token', platform.refresh_token)
            platform.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
            platform.scope = 'youtube youtube.readonly yt-analytics.readonly youtube.upload youtube.force-ssl'
            platform.updated_at = datetime.utcnow()
            platform.is_active = True
        else:
            platform = ConnectedPlatform(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='youtube',
                platform_user_id=channel_id,
                platform_username=channel['snippet'].get('customUrl', channel['snippet']['title']),
                platform_display_name=channel['snippet']['title'],
                profile_url=f"https://www.youtube.com/channel/{channel_id}",
                avatar_url=channel['snippet']['thumbnails']['default']['url'],
                access_token=tokens['access_token'],
                refresh_token=tokens.get('refresh_token'),
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600)),
                scope='youtube youtube.readonly yt-analytics.readonly youtube.upload youtube.force-ssl'
            )
            db.session.add(platform)
        
        db.session.commit()
        
        # Sync analytics asynchronously
        try:
            sync_youtube_analytics(user_id, platform.id, tokens['access_token'])
        except Exception as e:
            logger.error(f"Analytics sync error: {str(e)}")
        
        return _redirect_to_frontend(state_payload, 'youtube', success=True)
    except Exception:
        db.session.rollback()
        logger.exception("YouTube callback error")
        return {'error': 'YouTube OAuth callback failed'}, 500

# ═════════════════════════════════════════
#  INSTAGRAM OAUTH
# ═════════════════════════════════════════

@platforms_bp.route('/instagram/auth', methods=['POST'])
@jwt_required()
def instagram_auth():
    """Initiate Instagram OAuth"""
    try:
        user_id = get_jwt_identity()
        payload = request.get_json(silent=True) or {}
        redirect_url = payload.get('redirect_url')
        
        oauth_state = create_oauth_state(
            provider='instagram',
            mode='connect',
            user_id=user_id,
            redirect_url=redirect_url
        )

        instagram_client_id = (current_app.config.get('INSTAGRAM_CLIENT_ID') or '').strip()
        instagram_client_secret = (current_app.config.get('INSTAGRAM_CLIENT_SECRET') or '').strip()
        has_real_credentials = (
            instagram_client_id
            and instagram_client_secret
            and not instagram_client_id.startswith('your-')
            and not instagram_client_secret.startswith('your-')
        )

        # Explicitly enabled local mock mode only.
        if not has_real_credentials and current_app.config.get('INSTAGRAM_TEST_MODE', False):
            return {
                'auth_url': f"http://localhost:5000/api/platforms/instagram/test-callback?state={oauth_state}",
                'test_mode': True,
                'message': 'Running in test mode. Use the returned URL to simulate Instagram OAuth.'
            }, 200

        if not has_real_credentials:
            return {
                'error': 'Instagram OAuth is not configured. Set INSTAGRAM_CLIENT_ID and INSTAGRAM_CLIENT_SECRET.'
            }, 400
        
        instagram_auth_url = "https://api.instagram.com/oauth/authorize"
        params = {
            'client_id': current_app.config['INSTAGRAM_CLIENT_ID'],
            'redirect_uri': current_app.config['INSTAGRAM_CALLBACK_URL'],
            'response_type': 'code',
            # Instagram Basic Display scopes
            'scope': 'user_profile,user_media',
            'state': oauth_state
        }
        
        from urllib.parse import urlencode
        auth_url = instagram_auth_url + '?' + urlencode(params)
        return {'auth_url': auth_url}, 200
    except Exception:
        logger.exception("Instagram auth error")
        return {'error': 'Failed to initialize Instagram OAuth'}, 500

@platforms_bp.route('/instagram/test-callback', methods=['GET'])
def instagram_test_callback():
    """Test Instagram callback for development mode"""
    try:
        if not current_app.config.get('INSTAGRAM_TEST_MODE', False):
            return {'error': 'Instagram test mode is disabled'}, 403

        state = request.args.get('state')
        state_payload, state_error = verify_oauth_state(
            state,
            expected_provider='instagram',
            expected_mode='connect'
        )
        if state_error:
            return {'error': state_error}, 400

        user_id = state_payload.get('user_id')
        if not user_id:
            return {'error': 'Invalid OAuth state payload'}, 400
        
        # Create mock Instagram user data
        mock_user_data = {
            'id': '123456789',
            'username': 'testrituraj',
            'name': 'Test Ritu Raj',
            'biography': 'Test Instagram Account',
            'profile_picture_url': 'https://via.placeholder.com/150',
            'followers_count': 150,
            'media_count': 25,
            'website': 'https://example.com'
        }
        
        short_lived_token = f"test_token_{user_id}_{datetime.utcnow().timestamp()}"
        expires_in = 5184000  # 60 days
        
        # Find or update platform connection
        platform = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform='instagram'
        ).first()
        
        if platform:
            platform.access_token = short_lived_token
            platform.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            platform.updated_at = datetime.utcnow()
            platform.is_active = True
        else:
            platform = ConnectedPlatform(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='instagram',
                platform_user_id=mock_user_data['id'],
                platform_username=mock_user_data.get('username', 'Unknown'),
                platform_display_name=mock_user_data.get('name', 'Unknown'),
                profile_url=f"https://instagram.com/{mock_user_data.get('username', 'Unknown')}",
                avatar_url=mock_user_data.get('profile_picture_url'),
                access_token=short_lived_token,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                scope='user_profile user_media instagram_business_profile',
                is_active=True
            )
            db.session.add(platform)
        
        db.session.commit()
        
        return {
            'message': 'Instagram connected successfully (TEST MODE)',
            'platform': platform.to_dict(),
            'note': 'This is test data. Fill in real Instagram credentials in .env to use real data.'
        }, 200
    except Exception:
        db.session.rollback()
        logger.exception("Instagram test callback error")
        return {'error': 'Instagram test callback failed'}, 500

@platforms_bp.route('/instagram/callback', methods=['GET'])
def instagram_callback():
    """Instagram OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        provider_error = request.args.get('error')
        
        if not code or not state:
            return {'error': 'Missing code or state'}, 400
        
        state_payload, state_error = verify_oauth_state(
            state,
            expected_provider='instagram',
            expected_mode='connect'
        )
        if state_error:
            return {'error': state_error}, 400

        user_id = state_payload.get('user_id')
        if not user_id:
            return {'error': 'Invalid OAuth state payload'}, 400

        if provider_error:
            return _redirect_to_frontend(state_payload, 'instagram', success=False, error='Instagram authorization denied')
        
        # Exchange code for short-lived token (Instagram Basic Display)
        token_url = "https://api.instagram.com/oauth/access_token"
        data = {
            'client_id': current_app.config['INSTAGRAM_CLIENT_ID'],
            'client_secret': current_app.config['INSTAGRAM_CLIENT_SECRET'],
            'grant_type': 'authorization_code',
            'redirect_uri': current_app.config['INSTAGRAM_CALLBACK_URL'],
            'code': code
        }
        
        response = requests.post(token_url, data=data, timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15))
        tokens = response.json()
        
        if 'error' in tokens:
            logger.error(f"Instagram token error: {tokens['error']}")
            return _redirect_to_frontend(state_payload, 'instagram', success=False, error='Instagram token exchange failed')
        
        short_lived_token = tokens['access_token']
        
        # Exchange short-lived token for long-lived token
        long_token_url = "https://graph.instagram.com/access_token"
        long_token_params = {
            'grant_type': 'ig_exchange_token',
            'client_secret': current_app.config['INSTAGRAM_CLIENT_SECRET'],
            'access_token': short_lived_token
        }
        
        long_response = requests.get(long_token_url, params=long_token_params, timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15))
        long_tokens = long_response.json()
        
        if 'error' not in long_tokens:
            short_lived_token = long_tokens['access_token']
            expires_in = long_tokens.get('expires_in', 5184000)  # 60 days default
        else:
            expires_in = 3600  # Fallback to 1 hour
        
        # Get Instagram user info (Basic Display)
        user_info_url = "https://graph.instagram.com/me"
        params = {
            'fields': 'id,username,media_count,account_type',
            'access_token': short_lived_token
        }
        
        user_response = requests.get(user_info_url, params=params, timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15))
        user_data = user_response.json()
        
        if 'error' in user_data:
            logger.error(f"Instagram user info error: {user_data['error']}")
            return _redirect_to_frontend(state_payload, 'instagram', success=False, error='Failed to get Instagram profile info')
        
        # Find or update platform connection
        platform = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform='instagram'
        ).first()
        
        if platform:
            platform.access_token = short_lived_token
            platform.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            platform.updated_at = datetime.utcnow()
            platform.is_active = True
        else:
            platform = ConnectedPlatform(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='instagram',
                platform_user_id=user_data['id'],
                platform_username=user_data.get('username', 'Unknown'),
                platform_display_name=user_data.get('username', 'Unknown'),
                profile_url=f"https://instagram.com/{user_data.get('username', 'Unknown')}",
                avatar_url=None,
                access_token=short_lived_token,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                scope='user_profile user_media'
            )
            db.session.add(platform)
        
        db.session.commit()
        
        # Sync analytics
        try:
            sync_instagram_analytics(user_id, platform.id, short_lived_token)
        except Exception as e:
            logger.error(f"Instagram analytics sync error: {str(e)}")
        
        return _redirect_to_frontend(state_payload, 'instagram', success=True)
    except Exception:
        db.session.rollback()
        logger.exception("Instagram callback error")
        return {'error': 'Instagram OAuth callback failed'}, 500

# ═════════════════════════════════════════
#  TIKTOK OAUTH
# ═════════════════════════════════════════

@platforms_bp.route('/tiktok/auth', methods=['POST'])
@jwt_required()
def tiktok_auth():
    """Initiate TikTok OAuth"""
    return {'error': 'TikTok integration has been removed from this project'}, 410
    try:
        user_id = get_jwt_identity()
        payload = request.get_json(silent=True) or {}
        redirect_url = payload.get('redirect_url')
        
        tiktok_auth_url = "https://www.tiktok.com/v1/oauth/authorize/"
        oauth_state = create_oauth_state(
            provider='tiktok',
            mode='connect',
            user_id=user_id,
            redirect_url=redirect_url
        )
        params = {
            'client_key': current_app.config['TIKTOK_CLIENT_ID'],
            'redirect_uri': current_app.config['TIKTOK_PLATFORM_CALLBACK_URL'],
            'response_type': 'code',
            'scope': 'user.info.basic,video.list,user_stat.read',
            'state': oauth_state
        }
        
        from urllib.parse import urlencode
        auth_url = tiktok_auth_url + '?' + urlencode(params)
        return {'auth_url': auth_url}, 200
    except Exception:
        logger.exception("TikTok auth error")
        return {'error': 'Failed to initialize TikTok OAuth'}, 500

@platforms_bp.route('/tiktok/callback', methods=['GET'])
def tiktok_callback():
    """TikTok OAuth callback"""
    return {'error': 'TikTok integration has been removed from this project'}, 410
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        provider_error = request.args.get('error')
        
        if not code or not state:
            return {'error': 'Missing code or state'}, 400
        
        state_payload, state_error = verify_oauth_state(
            state,
            expected_provider='tiktok',
            expected_mode='connect'
        )
        if state_error:
            return {'error': state_error}, 400

        user_id = state_payload.get('user_id')
        if not user_id:
            return {'error': 'Invalid OAuth state payload'}, 400

        if provider_error:
            return _redirect_to_frontend(state_payload, 'tiktok', success=False, error='TikTok authorization denied')
        
        # Exchange code for token
        token_url = "https://open.tiktokapis.com/v1/oauth/token/"
        data = {
            'client_key': current_app.config['TIKTOK_CLIENT_ID'],
            'client_secret': current_app.config['TIKTOK_CLIENT_SECRET'],
            'code': code,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, json=data, timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15))
        tokens = response.json()
        
        if 'error' in tokens:
            logger.error(f"TikTok token error: {tokens['error']}")
            return _redirect_to_frontend(state_payload, 'tiktok', success=False, error='TikTok token exchange failed')
        
        # Get user info
        user_info_url = 'https://open.tiktokapis.com/v1/user/info/'
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        params = {'fields': 'open_id,union_id,avatar_url,display_name'}
        user_response = requests.get(user_info_url, headers=headers, params=params, timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15))
        user_data = user_response.json()
        
        if 'error' in user_data:
            logger.error(f"TikTok user info error: {user_data['error']}")
            return _redirect_to_frontend(state_payload, 'tiktok', success=False, error='Failed to fetch TikTok profile')
        
        user_info = user_data['data']['user']
        
        # Find or update platform connection
        platform = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform='tiktok'
        ).first()
        
        if platform:
            platform.access_token = tokens['access_token']
            platform.refresh_token = tokens.get('refresh_token', platform.refresh_token)
            platform.token_expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
            platform.updated_at = datetime.utcnow()
            platform.is_active = True
        else:
            platform = ConnectedPlatform(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='tiktok',
                platform_user_id=user_info['open_id'],
                platform_username=user_info.get('display_name', 'Unknown'),
                platform_display_name=user_info.get('display_name', 'Unknown'),
                avatar_url=user_info.get('avatar_url'),
                access_token=tokens['access_token'],
                refresh_token=tokens.get('refresh_token'),
                token_expires_at=datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600)),
                scope='user.info.basic,video.list,user_stat.read'
            )
            db.session.add(platform)
        
        db.session.commit()
        
        # Sync analytics
        try:
            sync_tiktok_analytics(user_id, platform.id, tokens['access_token'])
        except Exception as e:
            logger.error(f"TikTok analytics sync error: {str(e)}")
        
        return _redirect_to_frontend(state_payload, 'tiktok', success=True)
    except Exception:
        db.session.rollback()
        logger.exception("TikTok callback error")
        return {'error': 'TikTok OAuth callback failed'}, 500

# ═════════════════════════════════════════
#  TWITTER/X OAUTH
# ═════════════════════════════════════════

@platforms_bp.route('/twitter/auth', methods=['POST'])
@jwt_required()
def twitter_auth():
    """Initiate Twitter/X OAuth 2.0 PKCE"""
    try:
        user_id = get_jwt_identity()
        payload = request.get_json(silent=True) or {}
        redirect_url = payload.get('redirect_url')

        client_id = (current_app.config.get('TWITTER_CLIENT_ID') or '').strip()
        if not client_id or client_id.startswith('your-'):
            return {'error': 'Twitter OAuth is not configured. Set TWITTER_CLIENT_ID.'}, 400

        oauth_state = create_oauth_state(
            provider='twitter',
            mode='connect',
            user_id=user_id,
            redirect_url=redirect_url
        )

        code_verifier = secrets.token_urlsafe(64)
        challenge_digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_digest).decode('utf-8').rstrip('=')
        _TWITTER_PKCE_STORE[oauth_state] = {
            'code_verifier': code_verifier,
            'created_at': datetime.utcnow()
        }

        twitter_auth_url = "https://twitter.com/i/oauth2/authorize"
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': current_app.config['TWITTER_CALLBACK_URL'],
            'scope': current_app.config.get('TWITTER_SCOPES', 'tweet.read users.read offline.access'),
            'state': oauth_state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }

        from urllib.parse import urlencode
        auth_url = twitter_auth_url + '?' + urlencode(params)
        return {'auth_url': auth_url}, 200
    except Exception:
        logger.exception("Twitter auth error")
        return {'error': 'Failed to initialize Twitter OAuth'}, 500


@platforms_bp.route('/twitter/callback', methods=['GET'])
def twitter_callback():
    """Twitter/X OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        provider_error = request.args.get('error')

        if not state:
            return {'error': 'Missing OAuth state'}, 400

        state_payload, state_error = verify_oauth_state(
            state,
            expected_provider='twitter',
            expected_mode='connect'
        )
        if state_error:
            return {'error': state_error}, 400

        user_id = state_payload.get('user_id')
        if not user_id:
            return {'error': 'Invalid OAuth state payload'}, 400

        if provider_error:
            provider_error_description = request.args.get('error_description') or 'Twitter authorization denied'
            return _redirect_to_frontend(state_payload, 'twitter', success=False, error=provider_error_description)

        if not code:
            return _redirect_to_frontend(state_payload, 'twitter', success=False, error='Missing Twitter authorization code')

        verifier_item = _TWITTER_PKCE_STORE.pop(state, None)
        if not verifier_item:
            return _redirect_to_frontend(state_payload, 'twitter', success=False, error='Twitter session expired. Start connect again.')
        code_verifier = verifier_item.get('code_verifier')

        token_url = "https://api.twitter.com/2/oauth2/token"
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': current_app.config['TWITTER_CALLBACK_URL'],
            'client_id': current_app.config['TWITTER_CLIENT_ID'],
            'code_verifier': code_verifier
        }
        token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        client_secret = current_app.config.get('TWITTER_CLIENT_SECRET')
        if client_secret:
            token_response = requests.post(
                token_url,
                data=token_data,
                headers=token_headers,
                auth=(current_app.config['TWITTER_CLIENT_ID'], client_secret),
                timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15)
            )
        else:
            token_response = requests.post(
                token_url,
                data=token_data,
                headers=token_headers,
                timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15)
            )
        tokens = token_response.json()

        if 'error' in tokens or 'access_token' not in tokens:
            logger.error(f"Twitter token exchange error: {tokens}")
            return _redirect_to_frontend(state_payload, 'twitter', success=False, error='Twitter token exchange failed')

        access_token = tokens['access_token']
        expires_in = int(tokens.get('expires_in', 7200))

        me_headers = {'Authorization': f"Bearer {access_token}"}
        me_params = {'user.fields': 'profile_image_url,public_metrics,username,name,url'}
        me_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers=me_headers,
            params=me_params,
            timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15)
        )
        me_json = me_response.json()
        me_data = me_json.get('data') if isinstance(me_json, dict) else None
        if not me_data or 'id' not in me_data:
            logger.error(f"Twitter profile fetch error: {me_json}")
            return _redirect_to_frontend(state_payload, 'twitter', success=False, error='Failed to fetch Twitter profile')

        username = me_data.get('username')
        display_name = me_data.get('name') or username or me_data.get('id')

        platform = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform='twitter'
        ).first()

        if platform:
            platform.access_token = access_token
            platform.refresh_token = tokens.get('refresh_token', platform.refresh_token)
            platform.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            platform.updated_at = datetime.utcnow()
            platform.is_active = True
            platform.platform_user_id = me_data.get('id')
            platform.platform_username = username or platform.platform_username
            platform.platform_display_name = display_name or platform.platform_display_name
            platform.profile_url = f"https://x.com/{username}" if username else platform.profile_url
            platform.avatar_url = me_data.get('profile_image_url') or platform.avatar_url
            platform.scope = tokens.get('scope', current_app.config.get('TWITTER_SCOPES'))
        else:
            platform = ConnectedPlatform(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='twitter',
                platform_user_id=me_data.get('id'),
                platform_username=username or me_data.get('id'),
                platform_display_name=display_name,
                profile_url=f"https://x.com/{username}" if username else None,
                avatar_url=me_data.get('profile_image_url'),
                access_token=access_token,
                refresh_token=tokens.get('refresh_token'),
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                scope=tokens.get('scope', current_app.config.get('TWITTER_SCOPES'))
            )
            db.session.add(platform)

        db.session.commit()

        try:
            sync_twitter_analytics(user_id, platform.id, access_token)
        except Exception as sync_error:
            logger.error(f"Twitter analytics sync error: {str(sync_error)}")

        return _redirect_to_frontend(state_payload, 'twitter', success=True)
    except Exception:
        db.session.rollback()
        logger.exception("Twitter callback error")
        return {'error': 'Twitter OAuth callback failed'}, 500

# ═════════════════════════════════════════
#  LINKEDIN OAUTH
# ═════════════════════════════════════════

@platforms_bp.route('/linkedin/auth', methods=['POST'])
@jwt_required()
def linkedin_auth():
    """Initiate LinkedIn OAuth"""
    try:
        user_id = get_jwt_identity()
        payload = request.get_json(silent=True) or {}
        redirect_url = payload.get('redirect_url')

        linkedin_client_id = (current_app.config.get('LINKEDIN_CLIENT_ID') or '').strip()
        linkedin_client_secret = (current_app.config.get('LINKEDIN_CLIENT_SECRET') or '').strip()
        has_real_credentials = (
            linkedin_client_id
            and linkedin_client_secret
            and not linkedin_client_id.startswith('your-')
            and not linkedin_client_secret.startswith('your-')
        )
        if not has_real_credentials:
            return {
                'error': 'LinkedIn OAuth is not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET.'
            }, 400

        oauth_state = create_oauth_state(
            provider='linkedin',
            mode='connect',
            user_id=user_id,
            redirect_url=redirect_url
        )

        linkedin_auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        params = {
            'response_type': 'code',
            'client_id': current_app.config['LINKEDIN_CLIENT_ID'],
            'redirect_uri': current_app.config['LINKEDIN_CALLBACK_URL'],
            'scope': current_app.config.get('LINKEDIN_SCOPES', 'openid profile email'),
            'state': oauth_state,
        }

        from urllib.parse import urlencode
        auth_url = linkedin_auth_url + '?' + urlencode(params)
        return {'auth_url': auth_url}, 200
    except Exception:
        logger.exception("LinkedIn auth error")
        return {'error': 'Failed to initialize LinkedIn OAuth'}, 500


@platforms_bp.route('/linkedin/callback', methods=['GET'])
def linkedin_callback():
    """LinkedIn OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        provider_error = request.args.get('error')

        if not state:
            return {'error': 'Missing OAuth state'}, 400

        state_payload, state_error = verify_oauth_state(
            state,
            expected_provider='linkedin',
            expected_mode='connect'
        )
        if state_error:
            return {'error': state_error}, 400

        user_id = state_payload.get('user_id')
        if not user_id:
            return {'error': 'Invalid OAuth state payload'}, 400

        if provider_error:
            provider_error_description = request.args.get('error_description') or 'LinkedIn authorization denied'
            return _redirect_to_frontend(
                state_payload,
                'linkedin',
                success=False,
                error=provider_error_description
            )

        if not code:
            return _redirect_to_frontend(state_payload, 'linkedin', success=False, error='Missing LinkedIn authorization code')

        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': current_app.config['LINKEDIN_CALLBACK_URL'],
            'client_id': current_app.config['LINKEDIN_CLIENT_ID'],
            'client_secret': current_app.config['LINKEDIN_CLIENT_SECRET'],
        }
        token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        token_response = requests.post(
            token_url,
            data=token_data,
            headers=token_headers,
            timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15)
        )
        tokens = token_response.json()

        if 'error' in tokens or 'access_token' not in tokens:
            logger.error(f"LinkedIn token exchange error: {tokens}")
            return _redirect_to_frontend(state_payload, 'linkedin', success=False, error='LinkedIn token exchange failed')

        access_token = tokens['access_token']
        expires_in = int(tokens.get('expires_in', 3600))

        me_headers = {'Authorization': f"Bearer {access_token}"}
        profile = {}
        profile_id = None
        display_name = None
        profile_url = None

        # Try legacy profile endpoint first (works with r_liteprofile).
        me_response = requests.get(
            "https://api.linkedin.com/v2/me",
            headers=me_headers,
            timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15)
        )
        me_data = me_response.json()
        if 'id' in me_data:
            profile_id = me_data.get('id')
            localized_first = ((me_data.get('localizedFirstName') or '').strip())
            localized_last = ((me_data.get('localizedLastName') or '').strip())
            display_name = (f"{localized_first} {localized_last}".strip() or profile_id)
            profile_url = f"https://www.linkedin.com/in/{profile_id}"
            profile = me_data
        else:
            # Fallback for apps configured with OIDC userinfo.
            userinfo_response = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers=me_headers,
                timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15)
            )
            userinfo = userinfo_response.json()
            if 'sub' in userinfo:
                profile_id = userinfo.get('sub')
                display_name = (userinfo.get('name') or userinfo.get('given_name') or profile_id)
                profile_url = userinfo.get('profile')
                profile = userinfo

        if not profile_id:
            logger.error(f"LinkedIn profile fetch failed: {me_data}")
            return _redirect_to_frontend(state_payload, 'linkedin', success=False, error='Failed to fetch LinkedIn profile')

        # Optional email fetch
        username = display_name
        try:
            email_response = requests.get(
                "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                headers=me_headers,
                timeout=current_app.config.get('API_REQUEST_TIMEOUT_SECONDS', 15)
            )
            email_data = email_response.json()
            elements = email_data.get('elements') or []
            if elements and isinstance(elements[0], dict):
                handle = elements[0].get('handle~') or {}
                email = handle.get('emailAddress')
                if email:
                    username = email
        except Exception:
            logger.info("LinkedIn email endpoint unavailable for this app/scopes")

        platform = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform='linkedin'
        ).first()

        if platform:
            platform.access_token = access_token
            platform.refresh_token = tokens.get('refresh_token', platform.refresh_token)
            platform.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            platform.updated_at = datetime.utcnow()
            platform.is_active = True
            platform.platform_user_id = profile_id
            platform.platform_username = username or platform.platform_username
            platform.platform_display_name = display_name or platform.platform_display_name
            platform.profile_url = profile_url or platform.profile_url
            platform.scope = current_app.config.get('LINKEDIN_SCOPES', 'openid profile email')
        else:
            platform = ConnectedPlatform(
                id=str(uuid.uuid4()),
                user_id=user_id,
                platform='linkedin',
                platform_user_id=profile_id,
                platform_username=username or display_name or profile_id,
                platform_display_name=display_name or profile_id,
                profile_url=profile_url,
                avatar_url=None,
                access_token=access_token,
                refresh_token=tokens.get('refresh_token'),
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                scope=current_app.config.get('LINKEDIN_SCOPES', 'openid profile email')
            )
            db.session.add(platform)

        db.session.commit()

        try:
            sync_linkedin_analytics(user_id, platform.id, access_token)
        except Exception as sync_error:
            logger.error(f"LinkedIn analytics sync error: {str(sync_error)}")

        return _redirect_to_frontend(state_payload, 'linkedin', success=True)
    except Exception:
        db.session.rollback()
        logger.exception("LinkedIn callback error")
        return {'error': 'LinkedIn OAuth callback failed'}, 500

# ═════════════════════════════════════════
#  PLATFORM MANAGEMENT
# ═════════════════════════════════════════

@platforms_bp.route('/disconnect', methods=['POST'])
@jwt_required()
def disconnect_platform():
    """Disconnect a platform"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        platform_name = data.get('platform')
        
        if not platform_name:
            return {'error': 'Platform name required'}, 400
        
        platform = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform=platform_name
        ).first()
        
        if not platform:
            return {'error': 'Platform not connected'}, 404
        
        platform.is_active = False
        db.session.commit()
        
        return {'message': f'{platform_name} disconnected successfully'}, 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Disconnect error: {str(e)}")
        return {'error': 'Failed to disconnect platform'}, 500

@platforms_bp.route('/sync-all', methods=['POST'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_SYNC", "10 per hour"))
def sync_all_analytics():
    """Sync analytics from all connected platforms"""
    try:
        user_id = get_jwt_identity()

        if _enqueue_sync_all(user_id):
            return {'message': 'Sync queued'}, 202
        
        platforms = ConnectedPlatform.query.filter_by(
            user_id=user_id, is_active=True
        ).all()
        
        synced = []
        errors = []
        
        for platform in platforms:
            try:
                # Check and refresh token if needed
                if platform.token_expires_at and datetime.utcnow() >= platform.token_expires_at:
                    refresh_access_token(platform)
                
                if platform.platform == 'youtube':
                    sync_youtube_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'tiktok':
                    sync_tiktok_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'instagram':
                    sync_instagram_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'twitter':
                    sync_twitter_analytics(user_id, platform.id, platform.access_token)
                elif platform.platform == 'linkedin':
                    sync_linkedin_analytics(user_id, platform.id, platform.access_token)
                
                synced.append(platform.platform)
                platform.last_sync = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error syncing {platform.platform}: {str(e)}")
                errors.append({'platform': platform.platform, 'error': str(e)})
        
        db.session.commit()
        
        return {
            'message': 'Sync complete',
            'synced_platforms': synced,
            'errors': errors if errors else None
        }, 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Sync all error: {str(e)}")
        return {'error': 'Failed to sync analytics'}, 500

@platforms_bp.route('/<platform>/info', methods=['GET'])
@jwt_required()
def get_platform_info(platform):
    """Get specific platform info"""
    try:
        user_id = get_jwt_identity()
        
        platform_obj = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform=platform, is_active=True
        ).first()
        
        if not platform_obj:
            return {'error': 'Platform not connected'}, 404
        
        return {
            'platform': platform_obj.to_dict()
        }, 200
    except Exception as e:
        logger.error(f"Get platform info error: {str(e)}")
        return {'error': 'Failed to fetch platform info'}, 500


@platforms_bp.route('/<platform>/analytics-live', methods=['GET'])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_SYNC", "10 per hour"))
def get_platform_analytics_live(platform):
    """Get live analytics for a platform by forcing a sync and returning latest record."""
    try:
        user_id = get_jwt_identity()
        platform_name = (platform or '').strip().lower()
        allowed = {'youtube', 'instagram', 'twitter', 'linkedin'}
        if platform_name not in allowed:
            return {'error': 'Unsupported platform'}, 400

        platform_obj = ConnectedPlatform.query.filter_by(
            user_id=user_id, platform=platform_name, is_active=True
        ).first()

        if not platform_obj:
            return {'error': 'Platform not connected'}, 404

        if platform_obj.token_expires_at and datetime.utcnow() >= platform_obj.token_expires_at:
            refresh_access_token(platform_obj)

        sync_error = None
        try:
            if platform_name == 'youtube':
                sync_youtube_analytics(user_id, platform_obj.id, platform_obj.access_token)
            elif platform_name == 'instagram':
                sync_instagram_analytics(user_id, platform_obj.id, platform_obj.access_token)
            elif platform_name == 'twitter':
                sync_twitter_analytics(user_id, platform_obj.id, platform_obj.access_token)
            elif platform_name == 'linkedin':
                sync_linkedin_analytics(user_id, platform_obj.id, platform_obj.access_token)
            platform_obj.last_sync = datetime.utcnow()
            db.session.commit()
        except Exception as err:
            db.session.rollback()
            logger.error(f"Live sync error for {platform_name}: {str(err)}")
            sync_error = str(err)

        latest = Analytics.query.filter_by(
            user_id=user_id, platform=platform_name
        ).order_by(Analytics.metric_date.desc()).first()

        return {
            'platform': platform_obj.to_dict(),
            'latest_analytics': latest.to_dict() if latest else None,
            'sync_error': sync_error
        }, 200
    except Exception as e:
        logger.error(f"Live analytics fetch error: {str(e)}")
        return {'error': 'Failed to fetch live analytics'}, 500
