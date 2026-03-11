import logging
import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Analytics, User, ConnectedPlatform, ScheduledPost
from datetime import datetime, timedelta, date
import uuid
from utils.analytics import refresh_access_token

analytics_bp = Blueprint('analytics', __name__)
logger = logging.getLogger(__name__)


def _post_title(post):
    publish = post.publish_response or {}
    snippet = publish.get('snippet') if isinstance(publish, dict) else {}
    title = (snippet or {}).get('title')
    if title:
        return str(title)
    caption = (post.caption or '').strip()
    if not caption:
        return 'Published content'
    return caption.splitlines()[0][:120]


def _youtube_video_url(video_id):
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def _fetch_youtube_video_stats(platform_obj, video_ids):
    if not video_ids:
        return {}

    if platform_obj.token_expires_at and platform_obj.token_expires_at <= datetime.utcnow():
        refresh_access_token(platform_obj)
        db.session.flush()

    headers = {'Authorization': f'Bearer {platform_obj.access_token}'}
    params = {
        'part': 'snippet,statistics',
        'id': ','.join(video_ids[:50]),
        'maxResults': 50
    }
    response = requests.get(
        'https://www.googleapis.com/youtube/v3/videos',
        headers=headers,
        params=params,
        timeout=20
    )
    payload = response.json() if response.content else {}
    if response.status_code >= 400:
        logger.error("YouTube video stats fetch failed: %s", payload)
        return {}

    stats_by_id = {}
    for item in payload.get('items', []):
        vid = item.get('id')
        if not vid:
            continue
        snippet = item.get('snippet') or {}
        statistics = item.get('statistics') or {}
        stats_by_id[vid] = {
            'title': snippet.get('title') or 'YouTube video',
            'published_at': snippet.get('publishedAt'),
            'views': int(statistics.get('viewCount', 0) or 0),
            'likes': int(statistics.get('likeCount', 0) or 0),
            'comments': int(statistics.get('commentCount', 0) or 0),
            'url': _youtube_video_url(vid),
        }
    return stats_by_id

@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_analytics():
    """Get overall dashboard analytics"""
    try:
        user_id = get_jwt_identity()
        
        # Get latest analytics for each platform
        platforms = ConnectedPlatform.query.filter_by(
            user_id=user_id, is_active=True
        ).all()
        
        platform_data = {}
        total_stats = {
            'total_views': 0,
            'total_followers': 0,
            'total_posts': 0,
            'total_engagement': 0
        }
        
        for platform in platforms:
            # Get latest analytics record
            latest = Analytics.query.filter_by(
                user_id=user_id, platform=platform.platform
            ).order_by(Analytics.metric_date.desc()).first()
            
            if latest:
                platform_data[platform.platform] = latest.to_dict()
                total_stats['total_views'] += latest.views or 0
                total_stats['total_followers'] += latest.followers or 0
                total_stats['total_posts'] += latest.posts_count or 0
                total_stats['total_engagement'] += latest.engagement or 0
        
        return {
            'platforms': platform_data,
            'summary': total_stats
        }, 200
    except Exception:
        logger.exception("Dashboard analytics error")
        return {'error': 'Failed to fetch dashboard analytics'}, 500

@analytics_bp.route('/platform/<platform>', methods=['GET'])
@jwt_required()
def get_platform_analytics(platform):
    """Get analytics for specific platform"""
    try:
        user_id = get_jwt_identity()
        days = request.args.get('days', 30, type=int)
        
        start_date = date.today() - timedelta(days=days)
        
        analytics = Analytics.query.filter(
            Analytics.user_id == user_id,
            Analytics.platform == platform,
            Analytics.metric_date >= start_date
        ).order_by(Analytics.metric_date).all()
        
        if not analytics:
            return {'error': f'No analytics found for {platform}'}, 404
        
        return {
            'platform': platform,
            'period_days': days,
            'data': [a.to_dict() for a in analytics]
        }, 200
    except Exception:
        logger.exception("Platform analytics error")
        return {'error': 'Failed to fetch platform analytics'}, 500

@analytics_bp.route('/platform/<platform>/latest', methods=['GET'])
@jwt_required()
def get_latest_analytics(platform):
    """Get latest analytics for a platform"""
    try:
        user_id = get_jwt_identity()
        
        latest = Analytics.query.filter_by(
            user_id=user_id, platform=platform
        ).order_by(Analytics.metric_date.desc()).first()
        
        if not latest:
            return {'error': f'No analytics found for {platform}'}, 404
        
        return latest.to_dict(), 200
    except Exception:
        logger.exception("Latest analytics error")
        return {'error': 'Failed to fetch latest analytics'}, 500

@analytics_bp.route('/trending', methods=['GET'])
@jwt_required()
def get_trending():
    """Get overall trending metrics"""
    try:
        user_id = get_jwt_identity()
        days = request.args.get('days', 7, type=int)
        
        start_date = date.today() - timedelta(days=days)
        
        analytics = Analytics.query.filter(
            Analytics.user_id == user_id,
            Analytics.metric_date >= start_date
        ).all()
        
        if not analytics:
            return {'trending': []}, 200
        
        # Calculate growth rates
        trending_data = []
        
        platforms_dict = {}
        for record in analytics:
            if record.platform not in platforms_dict:
                platforms_dict[record.platform] = []
            platforms_dict[record.platform].append(record)
        
        for platform, records in platforms_dict.items():
            if len(records) >= 2:
                old = records[0]
                new = records[-1]
                
                growth = {}
                if old.views and new.views:
                    growth['views'] = ((new.views - old.views) / old.views * 100) if old.views > 0 else 0
                if old.followers and new.followers:
                    growth['followers'] = ((new.followers - old.followers) / old.followers * 100) if old.followers > 0 else 0
                if old.engagement and new.engagement:
                    growth['engagement'] = ((new.engagement - old.engagement) / old.engagement * 100) if old.engagement > 0 else 0
                
                trending_data.append({
                    'platform': platform,
                    'growth': growth
                })
        
        return {'trending': trending_data}, 200
    except Exception:
        logger.exception("Trending analytics error")
        return {'error': 'Failed to fetch trending analytics'}, 500

@analytics_bp.route('/comparison', methods=['GET'])
@jwt_required()
def compare_platforms():
    """Compare metrics across platforms"""
    try:
        user_id = get_jwt_identity()
        
        # Get latest for each platform
        platforms = ConnectedPlatform.query.filter_by(
            user_id=user_id, is_active=True
        ).all()
        
        comparison = []
        for platform in platforms:
            latest = Analytics.query.filter_by(
                user_id=user_id, platform=platform.platform
            ).order_by(Analytics.metric_date.desc()).first()
            
            if latest:
                comparison.append({
                    'platform': platform.platform,
                    'views': latest.views,
                    'followers': latest.followers,
                    'engagement': latest.engagement,
                    'posts': latest.posts_count
                })
        
        return {'comparison': comparison}, 200
    except Exception:
        logger.exception("Comparison analytics error")
        return {'error': 'Failed to compare platforms'}, 500

@analytics_bp.route('/export', methods=['GET'])
@jwt_required()
def export_analytics():
    """Export analytics as CSV"""
    try:
        user_id = get_jwt_identity()
        days = request.args.get('days', 90, type=int)
        
        start_date = date.today() - timedelta(days=days)
        
        analytics = Analytics.query.filter(
            Analytics.user_id == user_id,
            Analytics.metric_date >= start_date
        ).order_by(Analytics.metric_date).all()
        
        if not analytics:
            return {'error': 'No data to export'}, 404
        
        # Prepare CSV
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Date', 'Platform', 'Posts', 'Views', 'Followers', 'Engagement'
        ])
        
        # Data
        for record in analytics:
            writer.writerow([
                record.metric_date,
                record.platform,
                record.posts_count,
                record.views,
                record.followers,
                record.engagement
            ])
        
        csv_data = output.getvalue()
        
        return {
            'csv': csv_data,
            'filename': f'analytics_{datetime.now().strftime("%Y%m%d")}.csv'
        }, 200
    except Exception:
        logger.exception("Export analytics error")
        return {'error': 'Failed to export analytics'}, 500


@analytics_bp.route('/published-videos', methods=['GET'])
@jwt_required()
def published_videos():
    """
    Return per-platform published video/post rows plus combined views summary.
    YouTube rows include real per-video views fetched from YouTube Data API.
    """
    try:
        user_id = get_jwt_identity()
        platform_filter = (request.args.get('platform') or '').strip().lower()

        query = ScheduledPost.query.filter(
            ScheduledPost.user_id == user_id,
            ScheduledPost.status == 'published'
        )
        if platform_filter:
            query = query.filter(ScheduledPost.platform == platform_filter)
        posts = query.order_by(ScheduledPost.published_at.desc(), ScheduledPost.created_at.desc()).limit(300).all()

        platforms = ConnectedPlatform.query.filter_by(user_id=user_id, is_active=True).all()
        platform_map = {p.platform: p for p in platforms}

        # Fetch live YouTube per-video metrics for videos posted via app.
        youtube_posts = [p for p in posts if p.platform == 'youtube' and p.external_post_id and not str(p.external_post_id).startswith('sim_')]
        youtube_ids = [str(p.external_post_id) for p in youtube_posts]
        yt_stats = {}
        yt_platform = platform_map.get('youtube')
        if yt_platform and youtube_ids:
            yt_stats = _fetch_youtube_video_stats(yt_platform, youtube_ids)

        rows = []
        summary = {}
        for post in posts:
            platform_name = post.platform
            external_id = str(post.external_post_id or '')
            base = {
                'post_id': post.id,
                'platform': platform_name,
                'external_post_id': external_id or None,
                'title': _post_title(post),
                'published_at': post.published_at.isoformat() if post.published_at else (post.created_at.isoformat() if post.created_at else None),
                'url': None,
                'views': None,
                'likes': None,
                'comments': None,
            }

            if platform_name == 'youtube' and external_id:
                stat = yt_stats.get(external_id) or {}
                if stat:
                    base['title'] = stat.get('title') or base['title']
                    base['url'] = stat.get('url')
                    base['views'] = stat.get('views')
                    base['likes'] = stat.get('likes')
                    base['comments'] = stat.get('comments')
                else:
                    base['url'] = _youtube_video_url(external_id)

            rows.append(base)

            if platform_name not in summary:
                summary[platform_name] = {
                    'published_count': 0,
                    'total_views': 0,
                    'videos_with_views': 0
                }
            summary[platform_name]['published_count'] += 1
            if isinstance(base['views'], int):
                summary[platform_name]['total_views'] += int(base['views'])
                summary[platform_name]['videos_with_views'] += 1

        # Fallback: if per-video views are unavailable, use latest platform-level analytics views.
        platforms_to_fill = set(summary.keys()) | set(platform_map.keys())
        for platform_name in platforms_to_fill:
            stats = summary.setdefault(platform_name, {
                'published_count': 0,
                'total_views': 0,
                'videos_with_views': 0
            })
            if stats['total_views'] > 0:
                continue
            latest = Analytics.query.filter_by(
                user_id=user_id,
                platform=platform_name
            ).order_by(Analytics.metric_date.desc()).first()
            if latest and latest.views:
                stats['total_views'] = int(latest.views or 0)

        daily_series = []
        if platform_filter:
            start_day = date.today() - timedelta(days=29)
            daily_map = {(start_day + timedelta(days=i)).isoformat(): 0 for i in range(30)}

            # Preferred source: daily delta from historical cumulative analytics.
            history = Analytics.query.filter(
                Analytics.user_id == user_id,
                Analytics.platform == platform_filter,
                Analytics.metric_date >= (date.today() - timedelta(days=31))
            ).order_by(Analytics.metric_date.asc()).all()

            if len(history) >= 2:
                prev = None
                for row in history:
                    if prev is None:
                        prev = row
                        continue
                    key = row.metric_date.isoformat()
                    if key in daily_map:
                        daily_map[key] = int((row.views or 0) - (prev.views or 0))
                    prev = row
            else:
                # Fallback: aggregate current known per-video views by publish day.
                for row in rows:
                    if row.get('platform') != platform_filter:
                        continue
                    if not isinstance(row.get('views'), int):
                        continue
                    published_at = row.get('published_at')
                    if not published_at:
                        continue
                    day_key = str(published_at)[:10]
                    if day_key in daily_map:
                        daily_map[day_key] += int(row.get('views') or 0)

            daily_series = [{'date': day, 'views': int(val)} for day, val in sorted(daily_map.items())]

        return {
            'platform': platform_filter or None,
            'summary': summary,
            'daily_series': daily_series,
            'videos': rows
        }, 200
    except Exception:
        logger.exception("Published videos analytics error")
        return {'error': 'Failed to fetch published video analytics'}, 500
