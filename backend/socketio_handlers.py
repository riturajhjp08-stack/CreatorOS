import logging
import time
import uuid
from datetime import datetime

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import disconnect, emit, join_room
from sqlalchemy import and_, or_

from extensions import socketio
from models import db, User, FriendRequest, Message
from realtime_state import (
    add_connection,
    remove_connection,
    is_user_online,
    get_user_id_for_sid,
)
from utils.chat import decorate_attachments
from utils.notify import create_notification

logger = logging.getLogger(__name__)

_RATE_WINDOW_SECONDS = 3
_RATE_MAX_MESSAGES = 6
_rate_window = {}


def _extract_token(auth):
    token = None
    if isinstance(auth, dict):
        token = auth.get("token") or auth.get("access_token")
    if not token:
        token = request.args.get("token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1].strip()
    return token


def _get_user_id_from_token(token):
    if not token:
        return None
    try:
        decoded = decode_token(token)
        return decoded.get("sub") or decoded.get("identity")
    except Exception:
        return None


def _get_user_id_from_sid():
    user_id = get_user_id_for_sid(request.sid)
    if user_id:
        return user_id
    auth = request.environ.get("socketio.auth") or {}
    token = _extract_token(auth)
    return _get_user_id_from_token(token)


def _are_friends(user_id, other_id):
    return (
        FriendRequest.query.filter(
            FriendRequest.status == "accepted",
            or_(
                and_(FriendRequest.requester_id == user_id, FriendRequest.recipient_id == other_id),
                and_(FriendRequest.requester_id == other_id, FriendRequest.recipient_id == user_id),
            ),
        ).first()
        is not None
    )


def _touch_last_seen(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return
        user.last_seen = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()


def _rate_limited(user_id):
    now = time.time()
    window = _rate_window.get(user_id)
    if not window or now - window[0] > _RATE_WINDOW_SECONDS:
        _rate_window[user_id] = [now, 1]
        return False
    if window[1] >= _RATE_MAX_MESSAGES:
        return True
    window[1] += 1
    return False


def _build_payload(message, from_me):
    payload = message.to_dict()
    payload["from_me"] = from_me
    if payload.get("attachments"):
        payload["attachments"] = decorate_attachments(message, payload.get("attachments", []))
    return payload


@socketio.on("connect")
def handle_connect(auth):
    token = _extract_token(auth)
    user_id = _get_user_id_from_token(token)
    if not user_id:
        return False
    join_room(user_id)
    add_connection(user_id, request.sid)
    _touch_last_seen(user_id)
    emit("socket:ready", {"user_id": user_id})


@socketio.on("disconnect")
def handle_disconnect():
    user_id = remove_connection(request.sid)
    if user_id:
        _touch_last_seen(user_id)


@socketio.on("message:send")
def handle_message_send(data):
    user_id = _get_user_id_from_sid()
    if not user_id:
        disconnect()
        return
    if _rate_limited(user_id):
        emit("message:error", {"error": "Rate limit exceeded"})
        return

    receiver_id = (data or {}).get("receiver_id")
    content = ((data or {}).get("content") or "").strip()
    attachments = (data or {}).get("attachments") or []
    if not receiver_id:
        emit("message:error", {"error": "receiver_id required"})
        return
    if not User.query.get(receiver_id):
        emit("message:error", {"error": "User not found"})
        return
    if not content and not attachments:
        emit("message:error", {"error": "Message content required"})
        return
    if not _are_friends(user_id, receiver_id):
        emit("message:error", {"error": "Not connected"})
        return

    msg = Message(
        id=str(uuid.uuid4()),
        sender_id=user_id,
        receiver_id=receiver_id,
        content=content,
        attachments=attachments,
        created_at=datetime.utcnow(),
    )
    if is_user_online(receiver_id):
        msg.delivered_at = datetime.utcnow()

    try:
        db.session.add(msg)
        create_notification(
            user_id=receiver_id,
            title="New message",
            message=content[:120] if content else "New attachment received.",
            notif_type="message",
            actor_user_id=user_id,
            data={"message_id": msg.id, "from_user_id": user_id},
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Socket send message error")
        emit("message:error", {"error": "Failed to send message"})
        return

    sender_payload = _build_payload(msg, True)
    receiver_payload = _build_payload(msg, False)
    emit("message:new", {"message": sender_payload, "peer_id": receiver_id}, room=user_id)
    emit("message:new", {"message": receiver_payload, "peer_id": user_id}, room=receiver_id)


@socketio.on("typing")
def handle_typing(data):
    user_id = _get_user_id_from_sid()
    if not user_id:
        return
    receiver_id = (data or {}).get("user_id")
    is_typing = bool((data or {}).get("typing", True))
    if not receiver_id:
        return
    emit(
        "typing",
        {"user_id": user_id, "typing": is_typing},
        room=receiver_id,
    )


@socketio.on("messages:read")
def handle_messages_read(data):
    user_id = _get_user_id_from_sid()
    if not user_id:
        return
    peer_id = (data or {}).get("user_id")
    if not peer_id:
        return
    try:
        updated = (
            Message.query.filter_by(sender_id=peer_id, receiver_id=user_id, read_at=None)
            .update({"read_at": datetime.utcnow()}, synchronize_session=False)
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Socket read receipts error")
        return
    emit(
        "message:read",
        {"user_id": user_id, "peer_id": peer_id, "updated": updated},
        room=peer_id,
    )
