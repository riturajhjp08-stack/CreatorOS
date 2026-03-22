from collections import defaultdict
from threading import Lock

_user_sids = defaultdict(set)
_sid_user = {}
_lock = Lock()


def add_connection(user_id, sid):
    with _lock:
        _user_sids[user_id].add(sid)
        _sid_user[sid] = user_id


def remove_connection(sid):
    with _lock:
        user_id = _sid_user.pop(sid, None)
        if not user_id:
            return None
        sids = _user_sids.get(user_id)
        if sids:
            sids.discard(sid)
            if not sids:
                _user_sids.pop(user_id, None)
        return user_id


def is_user_online(user_id):
    with _lock:
        return bool(_user_sids.get(user_id))


def get_user_sids(user_id):
    with _lock:
        return set(_user_sids.get(user_id, set()))


def get_user_id_for_sid(sid):
    with _lock:
        return _sid_user.get(sid)
