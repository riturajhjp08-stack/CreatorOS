from app import create_app
from models import db, User, ConnectedPlatform, Analytics

app = create_app()
with app.app_context():
    users = User.query.all()
    if not users:
        print("No users in DB")
        exit(0)
    
    for user in users:
        platforms = ConnectedPlatform.query.filter_by(user_id=user.id).all()
        print(f"User: {user.email}")
        if not platforms:
            print("  No platforms connected")
        for p in platforms:
            print(f"  Platform: {p.platform} (Active: {p.is_active})")
            latest = Analytics.query.filter_by(platform=p.platform, user_id=user.id).order_by(Analytics.metric_date.desc()).first()
            if latest:
                print(f"    Views: {latest.views}, Posts: {latest.posts_count}, Followers: {latest.followers}")
            else:
                print("    No analytics data found.")
