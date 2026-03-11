from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Centralized extensions to avoid circular imports.
limiter = Limiter(key_func=get_remote_address)
