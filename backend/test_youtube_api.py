from app import create_app
from models import db, User, ConnectedPlatform
import requests

app = create_app()
with app.app_context():
    # Find a user with active youtube
    p = ConnectedPlatform.query.filter(ConnectedPlatform.platform=='youtube', ConnectedPlatform.user_id.in_(
        db.session.query(User.id).filter(User.email == 'agent_tester1@example.com')
    )).first()
    if not p:
        print("No active youtube accounts")
        exit(0)
    
    print(f"Testing for user ID: {p.user_id}")
    headers = {'Authorization': f'Bearer {p.access_token}'}
    channels_url = 'https://www.googleapis.com/youtube/v3/channels'
    channels_params = {
        'part': 'statistics,snippet',
        'mine': 'true'
    }
    
    response = requests.get(channels_url, headers=headers, params=channels_params)
    data = response.json()
    print("YouTube API Response:")
    print(data)
