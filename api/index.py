import os
import sys
from io import BytesIO
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
from wsgiref.util import setup_testing_defaults

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402

# Ensure serverless-friendly defaults
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("SERVERLESS_MODE", "true")


def _build_fallback_app(exc):
    from flask import Flask

    error_type = exc.__class__.__name__
    error_message = str(exc)

    fallback = Flask(__name__)

    @fallback.route("/health", methods=["GET"])
    @fallback.route("/api/health", methods=["GET"])
    def _health_error():  # type: ignore[no-redef]
        return {
            "status": "error",
            "error": "app_init_failed",
            "detail": f"{error_type}: {error_message}",
        }, 500

    return fallback


try:
    _app = create_app(os.getenv("FLASK_ENV", "production"))
except Exception as exc:  # noqa: BLE001 - surface init errors for health checks
    _app = _build_fallback_app(exc)


def _wsgi_environ(request_handler, body_bytes):
    parsed = urlparse(request_handler.path)
    environ = {}
    setup_testing_defaults(environ)

    environ["REQUEST_METHOD"] = request_handler.command
    environ["PATH_INFO"] = parsed.path
    environ["QUERY_STRING"] = parsed.query
    environ["CONTENT_TYPE"] = request_handler.headers.get("Content-Type", "")
    environ["CONTENT_LENGTH"] = str(len(body_bytes)) if body_bytes else "0"
    environ["wsgi.input"] = BytesIO(body_bytes)

    host = request_handler.headers.get("Host", "")
    environ["SERVER_NAME"] = host
    forwarded_port = request_handler.headers.get("X-Forwarded-Port")
    if forwarded_port:
        environ["SERVER_PORT"] = forwarded_port
    else:
        environ["SERVER_PORT"] = "443" if request_handler.headers.get("X-Forwarded-Proto", "https") == "https" else "80"
    environ["wsgi.url_scheme"] = request_handler.headers.get("X-Forwarded-Proto", "https")
    environ["REMOTE_ADDR"] = request_handler.headers.get("X-Forwarded-For", "").split(",")[0].strip()

    for key, value in request_handler.headers.items():
        header_key = "HTTP_" + key.upper().replace("-", "_")
        if header_key in {"HTTP_CONTENT_TYPE", "HTTP_CONTENT_LENGTH"}:
            continue
        environ[header_key] = value

    return environ


class handler(BaseHTTPRequestHandler):
    def _handle_request(self):
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(content_length) if content_length > 0 else b""

        status_headers = {"status": "500 Internal Server Error", "headers": []}
        response_body = BytesIO()

        def start_response(status, headers, exc_info=None):
            status_headers["status"] = status
            status_headers["headers"] = headers
            return response_body.write

        environ = _wsgi_environ(self, body)
        result = _app(environ, start_response)
        try:
            for chunk in result:
                response_body.write(chunk)
        finally:
            if hasattr(result, "close"):
                result.close()

        status_code = int(status_headers["status"].split(" ", 1)[0])
        self.send_response(status_code)
        for header, value in status_headers["headers"]:
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(response_body.getvalue())

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_PATCH(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def do_OPTIONS(self):
        self._handle_request()
