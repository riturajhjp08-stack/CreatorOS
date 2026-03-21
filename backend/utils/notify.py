import uuid
from datetime import datetime

from models import db, Notification


def create_notification(user_id, title, message="", notif_type=None, actor_user_id=None, data=None):
    notif = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
        actor_user_id=actor_user_id,
        data=data or {},
        created_at=datetime.utcnow(),
    )
    db.session.add(notif)
    return notif
