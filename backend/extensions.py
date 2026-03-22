import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO

# Centralized extensions to avoid circular imports.
limiter = Limiter(key_func=get_remote_address)
socketio = SocketIO(
    cors_allowed_origins=[],
    async_mode=os.environ.get("SOCKETIO_ASYNC_MODE") or None,
)
