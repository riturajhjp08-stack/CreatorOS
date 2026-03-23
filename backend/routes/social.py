import logging
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app, send_file, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, or_, case, func

from models import db, User, FriendRequest, Message, Follow
from extensions import limiter, socketio
from realtime_state import is_user_online
from utils.pagination import parse_pagination, pagination_meta
from utils.cache import get_cache
from utils.notify import create_notification
from utils.chat import decorate_attachments
from storage import get_storage

logger = logging.getLogger(__name__)

social_bp = Blueprint("social", __name__)


def _json_body():
    return request.get_json(silent=True) or {}


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


def _user_summary(user):
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "category": user.category,
        "avatar_url": user.avatar_url,
        "last_seen": user.last_seen.isoformat() if user.last_seen else None,
    }


@social_bp.route("/friends/requests", methods=["POST"])
@jwt_required()
def send_friend_request():
    try:
        user_id = get_jwt_identity()
        data = _json_body()
        recipient_id = data.get("recipient_id")
        if not recipient_id:
            return {"error": "recipient_id required"}, 400
        if recipient_id == user_id:
            return {"error": "Cannot request yourself"}, 400
        if not User.query.get(recipient_id):
            return {"error": "User not found"}, 404

        existing = FriendRequest.query.filter_by(requester_id=user_id, recipient_id=recipient_id).first()
        if existing:
            return {"error": "Request already sent"}, 409

        inverse = FriendRequest.query.filter_by(requester_id=recipient_id, recipient_id=user_id).first()
        if inverse and inverse.status == "pending":
            inverse.status = "accepted"
            inverse.responded_at = datetime.utcnow()
            create_notification(
                user_id=recipient_id,
                title="Connection accepted",
                message="You are now connected.",
                notif_type="friend_accept",
                actor_user_id=user_id,
                data={"friend_id": user_id},
            )
            create_notification(
                user_id=user_id,
                title="Connection accepted",
                message="You are now connected.",
                notif_type="friend_accept",
                actor_user_id=recipient_id,
                data={"friend_id": recipient_id},
            )
            db.session.commit()
            return {"message": "Connection accepted"}, 200

        fr = FriendRequest(
            id=str(uuid.uuid4()),
            requester_id=user_id,
            recipient_id=recipient_id,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.session.add(fr)
        create_notification(
            user_id=recipient_id,
            title="New connection request",
            message="Someone wants to connect with you.",
            notif_type="friend_request",
            actor_user_id=user_id,
            data={"request_id": fr.id, "from_user_id": user_id},
        )
        create_notification(
            user_id=user_id,
            title="Request sent",
            message="Your connection request was sent.",
            notif_type="friend_request_sent",
            actor_user_id=recipient_id,
            data={"request_id": fr.id, "to_user_id": recipient_id},
        )
        db.session.commit()
        return {"message": "Request sent", "request": fr.to_dict()}, 201
    except Exception:
        db.session.rollback()
        logger.exception("Send friend request error")
        return {"error": "Failed to send request"}, 500


@social_bp.route("/friends/requests", methods=["GET"])
@jwt_required()
def list_friend_requests():
    try:
        user_id = get_jwt_identity()
        req_type = (request.args.get("type") or "incoming").lower()
        query = FriendRequest.query
        if req_type == "outgoing":
            query = query.filter_by(requester_id=user_id)
        elif req_type == "all":
            query = query.filter(
                or_(FriendRequest.requester_id == user_id, FriendRequest.recipient_id == user_id)
            )
        else:
            query = query.filter_by(recipient_id=user_id)
        requests_list = query.order_by(FriendRequest.created_at.desc()).all()

        user_ids = set()
        for fr in requests_list:
            user_ids.add(fr.requester_id)
            user_ids.add(fr.recipient_id)
        users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

        payload = []
        for fr in requests_list:
            payload.append({
                **fr.to_dict(),
                "requester": _user_summary(users.get(fr.requester_id)) if users.get(fr.requester_id) else None,
                "recipient": _user_summary(users.get(fr.recipient_id)) if users.get(fr.recipient_id) else None,
            })
        return {"requests": payload, "count": len(payload)}, 200
    except Exception:
        logger.exception("List friend requests error")
        return {"error": "Failed to fetch requests"}, 500


@social_bp.route("/friends/requests/<request_id>/respond", methods=["POST"])
@jwt_required()
def respond_friend_request(request_id):
    try:
        user_id = get_jwt_identity()
        data = _json_body()
        action = (data.get("action") or "").lower()
        if action not in {"accept", "reject"}:
            return {"error": "Invalid action"}, 400

        fr = FriendRequest.query.filter_by(id=request_id, recipient_id=user_id).first()
        if not fr:
            return {"error": "Request not found"}, 404
        fr.status = "accepted" if action == "accept" else "rejected"
        fr.responded_at = datetime.utcnow()

        if action == "accept":
            create_notification(
                user_id=fr.requester_id,
                title="Connection accepted",
                message="Your connection request was accepted.",
                notif_type="friend_accept",
                actor_user_id=user_id,
                data={"friend_id": user_id},
            )
            create_notification(
                user_id=user_id,
                title="Connection confirmed",
                message="You are now connected.",
                notif_type="friend_accept",
                actor_user_id=fr.requester_id,
                data={"friend_id": fr.requester_id},
            )
        if action == "reject":
            create_notification(
                user_id=fr.requester_id,
                title="Connection declined",
                message="Your connection request was declined.",
                notif_type="friend_reject",
                actor_user_id=user_id,
                data={"friend_id": user_id},
            )
        db.session.commit()
        return {"message": f"Request {action}ed"}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Respond friend request error")
        return {"error": "Failed to respond"}, 500


@social_bp.route("/friends", methods=["GET"])
@jwt_required()
def list_friends():
    try:
        user_id = get_jwt_identity()
        accepted = FriendRequest.query.filter(
            FriendRequest.status == "accepted",
            or_(FriendRequest.requester_id == user_id, FriendRequest.recipient_id == user_id),
        ).all()
        friend_ids = []
        for fr in accepted:
            friend_ids.append(fr.recipient_id if fr.requester_id == user_id else fr.requester_id)
        if not friend_ids:
            return {"friends": [], "count": 0}, 200
        friends = User.query.filter(User.id.in_(friend_ids)).all()

        unread_map = {}
        last_message_map = {}
        unread_rows = (
            db.session.query(Message.sender_id, func.count(Message.id))
            .filter(
                Message.receiver_id == user_id,
                Message.read_at.is_(None),
                Message.sender_id.in_(friend_ids),
            )
            .group_by(Message.sender_id)
            .all()
        )
        unread_map = {row[0]: int(row[1]) for row in unread_rows}

        peer_case = case(
            (Message.sender_id == user_id, Message.receiver_id),
            else_=Message.sender_id,
        )
        last_subq = (
            db.session.query(
                peer_case.label("peer_id"),
                func.max(Message.created_at).label("last_time"),
            )
            .filter(
                or_(
                    and_(Message.sender_id == user_id, Message.receiver_id.in_(friend_ids)),
                    and_(Message.receiver_id == user_id, Message.sender_id.in_(friend_ids)),
                )
            )
            .group_by(peer_case)
            .subquery()
        )

        last_rows = (
            db.session.query(Message, last_subq.c.peer_id)
            .join(
                last_subq,
                and_(
                    Message.created_at == last_subq.c.last_time,
                    peer_case == last_subq.c.peer_id,
                ),
            )
            .all()
        )
        for msg, peer_id in last_rows:
            last_message_map[peer_id] = msg

        payload = []
        for friend in friends:
            summary = _user_summary(friend)
            last_msg = last_message_map.get(friend.id)
            if last_msg:
                last_msg_payload = last_msg.to_dict()
                last_msg_payload["from_me"] = last_msg.sender_id == user_id
            else:
                last_msg_payload = None
            summary.update({
                "unread_count": unread_map.get(friend.id, 0),
                "last_message": last_msg_payload,
            })
            payload.append(summary)

        return {"friends": payload, "count": len(payload)}, 200
    except Exception:
        logger.exception("List friends error")
        return {"error": "Failed to fetch friends"}, 500


@social_bp.route("/follow", methods=["POST"])
@jwt_required()
def follow_user():
    try:
        user_id = get_jwt_identity()
        data = _json_body()
        target_id = data.get("user_id")
        follow = bool(data.get("follow", True))
        if not target_id:
            return {"error": "user_id required"}, 400
        if target_id == user_id:
            return {"error": "Cannot follow yourself"}, 400
        if not User.query.get(target_id):
            return {"error": "User not found"}, 404

        existing = Follow.query.filter_by(follower_id=user_id, following_id=target_id).first()
        if follow and not existing:
            relation = Follow(
                id=str(uuid.uuid4()),
                follower_id=user_id,
                following_id=target_id,
                created_at=datetime.utcnow(),
            )
            db.session.add(relation)
            create_notification(
                user_id=target_id,
                title="New follower",
                message="Someone followed your profile.",
                notif_type="follow",
                actor_user_id=user_id,
                data={"follower_id": user_id},
            )
        if not follow and existing:
            db.session.delete(existing)
        db.session.commit()
        return {"success": True, "following": follow}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Follow error")
        return {"error": "Failed to update follow"}, 500


@social_bp.route("/messages", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_MESSAGES", "120 per minute"))
def get_messages():
    try:
        user_id = get_jwt_identity()
        peer_id = request.args.get("user_id")
        if not peer_id:
            return {"error": "user_id required"}, 400
        if not _are_friends(user_id, peer_id):
            return {"error": "Not connected"}, 403

        page, page_size, offset = parse_pagination(request.args, default_page_size=30, max_page_size=100)
        query = Message.query.filter(
            or_(
                and_(Message.sender_id == user_id, Message.receiver_id == peer_id),
                and_(Message.sender_id == peer_id, Message.receiver_id == user_id),
            )
        )
        total = query.count()
        messages = (
            query.order_by(Message.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        # Build attachment URLs for local storage
        items = []
        for msg in reversed(messages):
            data = msg.to_dict()
            data["from_me"] = msg.sender_id == user_id
            if msg.attachments:
                data["attachments"] = decorate_attachments(msg, data.get("attachments", []))
            items.append(data)

        return {
            "messages": items,
            "count": len(items),
            "total": total,
            "pagination": pagination_meta(total, page, page_size),
        }, 200
    except Exception:
        logger.exception("Get messages error")
        return {"error": "Failed to fetch messages"}, 500




@social_bp.route("/messages", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_MESSAGES", "120 per minute"))
def send_message():
    try:
        user_id = get_jwt_identity()
        data = _json_body()
        receiver_id = data.get("receiver_id")
        content = (data.get("content") or "").strip()
        attachments = data.get("attachments") or []
        if not receiver_id:
            return {"error": "receiver_id required"}, 400
        if not User.query.get(receiver_id):
            return {"error": "User not found"}, 404
        if not isinstance(attachments, list):
            return {"error": "Invalid attachments"}, 400
        if not content and not attachments:
            return {"error": "Message content required"}, 400
        if not _are_friends(user_id, receiver_id):
            return {"error": "Not connected"}, 403

        msg = Message(
            id=str(uuid.uuid4()),
            sender_id=user_id,
            receiver_id=receiver_id,
            content=content,
            attachments=attachments,
            created_at=datetime.utcnow(),
            delivered_at=datetime.utcnow() if is_user_online(receiver_id) else None,
        )
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
        payload = msg.to_dict()
        payload["from_me"] = True
        payload["attachments"] = decorate_attachments(msg, payload.get("attachments", []))
        receiver_payload = msg.to_dict()
        receiver_payload["from_me"] = False
        receiver_payload["attachments"] = decorate_attachments(msg, receiver_payload.get("attachments", []))
        try:
            socketio.emit("message:new", {"message": receiver_payload, "peer_id": user_id}, room=receiver_id)
            socketio.emit("message:new", {"message": payload, "peer_id": receiver_id}, room=user_id)
        except Exception:
            logger.exception("Socket emit failed")
        return {"message": payload}, 201
    except Exception:
        db.session.rollback()
        logger.exception("Send message error")
        return {"error": "Failed to send message"}, 500


@social_bp.route("/messages/read", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_MESSAGES", "120 per minute"))
def mark_messages_read():
    try:
        user_id = get_jwt_identity()
        data = _json_body()
        peer_id = data.get("user_id")
        if not peer_id:
            return {"error": "user_id required"}, 400
        updated = (
            Message.query.filter_by(sender_id=peer_id, receiver_id=user_id, read_at=None)
            .update({"read_at": datetime.utcnow()}, synchronize_session=False)
        )
        db.session.commit()
        try:
            socketio.emit(
                "message:read",
                {"user_id": user_id, "peer_id": peer_id, "updated": updated},
                room=peer_id,
            )
        except Exception:
            logger.exception("Socket read receipt emit failed")
        return {"success": True, "updated": updated}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Mark read error")
        return {"error": "Failed to mark read"}, 500


@social_bp.route("/messages/upload", methods=["POST"])
@jwt_required()
def upload_message_attachment():
    try:
        user_id = get_jwt_identity()
        if "file" not in request.files:
            return {"error": "file required"}, 400
        file_obj = request.files["file"]
        if not file_obj:
            return {"error": "file required"}, 400
        storage = get_storage()
        saved = storage.save(file_obj, user_id)
        if not saved:
            return {"error": "Upload failed"}, 400
        return {"attachment": saved}, 201
    except Exception:
        logger.exception("Upload attachment error")
        return {"error": "Failed to upload"}, 500


@social_bp.route("/messages/attachments/<message_id>/<stored_name>", methods=["GET"])
@jwt_required()
def download_attachment(message_id, stored_name):
    try:
        user_id = get_jwt_identity()
        msg = Message.query.filter_by(id=message_id).first()
        if not msg:
            return {"error": "Message not found"}, 404
        if user_id not in {msg.sender_id, msg.receiver_id}:
            return {"error": "Unauthorized"}, 403

        storage = get_storage()
        key = None
        for item in msg.attachments or []:
            if item.get("stored_name") == stored_name:
                key = item.get("key")
        if hasattr(storage, "client") and hasattr(storage, "bucket"):
            if not key:
                return {"error": "File not found"}, 404
            try:
                url = storage.client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": storage.bucket, "Key": key},
                    ExpiresIn=3600,
                )
                return redirect(url)
            except Exception:
                return {"error": "Failed to generate download"}, 500

        owner_id = None
        if key and "/" in key:
            owner_id = key.split("/", 1)[0]
        path = storage.resolve_path(owner_id or msg.sender_id, {"stored_name": stored_name})
        if not path:
            return {"error": "File not found"}, 404
        return send_file(path, as_attachment=True)
    except Exception:
        logger.exception("Download attachment error")
        return {"error": "Failed to download"}, 500


@social_bp.route("/typing", methods=["POST"])
@jwt_required()
def set_typing():
    try:
        user_id = get_jwt_identity()
        data = _json_body()
        target_id = data.get("user_id")
        typing = bool(data.get("typing", True))
        if not target_id:
            return {"error": "user_id required"}, 400
        cache = get_cache(redis_url=current_app.config.get("REDIS_URL"))
        key = f"typing:{user_id}:{target_id}"
        cache.set(key, {"typing": typing}, ttl_seconds=5 if typing else 1)
        return {"success": True}, 200
    except Exception:
        logger.exception("Typing error")
        return {"error": "Failed to set typing"}, 500


@social_bp.route("/typing", methods=["GET"])
@jwt_required()
def get_typing():
    try:
        user_id = get_jwt_identity()
        peer_id = request.args.get("user_id")
        if not peer_id:
            return {"error": "user_id required"}, 400
        cache = get_cache(redis_url=current_app.config.get("REDIS_URL"))
        key = f"typing:{peer_id}:{user_id}"
        payload = cache.get(key) or {}
        return {"typing": bool(payload.get("typing"))}, 200
    except Exception:
        logger.exception("Typing get error")
        return {"error": "Failed to fetch typing"}, 500


@social_bp.route("/presence", methods=["POST"])
@jwt_required()
def presence_ping():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        user.last_seen = datetime.utcnow()
        db.session.commit()
        return {"success": True}, 200
    except Exception:
        db.session.rollback()
        logger.exception("Presence ping error")
        return {"error": "Failed to update presence"}, 500


@social_bp.route("/presence", methods=["GET"])
@jwt_required()
def presence_status():
    try:
        target_id = request.args.get("user_id")
        if not target_id:
            return {"error": "user_id required"}, 400
        user = User.query.get(target_id)
        if not user:
            return {"error": "User not found"}, 404
        online = False
        if user.last_seen:
            online = user.last_seen >= (datetime.utcnow() - timedelta(seconds=120))
        return {
            "online": online,
            "last_seen": user.last_seen.isoformat() if user.last_seen else None,
        }, 200
    except Exception:
        logger.exception("Presence status error")
        return {"error": "Failed to fetch presence"}, 500
