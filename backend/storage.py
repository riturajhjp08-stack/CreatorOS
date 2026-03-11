import os
import uuid

import boto3
from werkzeug.utils import secure_filename
from flask import current_app


def _default_upload_root():
    root = os.path.join(os.path.dirname(__file__), "uploads")
    return os.path.abspath(root)


class LocalStorage:
    def __init__(self, root):
        self.root = os.path.abspath(root or _default_upload_root())

    def _user_dir(self, user_id):
        return os.path.join(self.root, str(user_id))

    def save(self, file_obj, user_id):
        user_dir = self._user_dir(user_id)
        os.makedirs(user_dir, exist_ok=True)

        original_name = secure_filename(file_obj.filename or "")
        if not original_name:
            return None
        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        path = os.path.join(user_dir, stored_name)
        file_obj.save(path)
        return {
            "name": original_name,
            "stored_name": stored_name,
            "size": os.path.getsize(path),
            "type": file_obj.mimetype or "",
            "key": f"{user_id}/{stored_name}",
        }

    def resolve_path(self, user_id, item):
        stored_name = (item or {}).get("stored_name")
        if not stored_name:
            return None
        return os.path.join(self._user_dir(user_id), stored_name)

    def prepare_local(self, user_id, item):
        path = self.resolve_path(user_id, item)
        if path and os.path.exists(path):
            return path
        return None

    def cleanup_local(self, path):
        # Local uploads are persisted; do not delete.
        return None


class S3Storage:
    def __init__(self, bucket, region=None, access_key=None, secret_key=None, endpoint_url=None):
        session = boto3.session.Session(
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            region_name=region or None,
        )
        self.client = session.client("s3", endpoint_url=endpoint_url or None)
        self.bucket = bucket
        self.endpoint_url = endpoint_url

    def save(self, file_obj, user_id):
        original_name = secure_filename(file_obj.filename or "")
        if not original_name:
            return None
        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        key = f"{user_id}/{stored_name}"
        self.client.upload_fileobj(file_obj, self.bucket, key)
        return {
            "name": original_name,
            "stored_name": stored_name,
            "size": getattr(file_obj, "content_length", 0) or 0,
            "type": file_obj.mimetype or "",
            "key": key,
        }

    def resolve_path(self, user_id, item):
        # Not applicable for S3 (no local path)
        return None

    def _temp_root(self):
        try:
            base = current_app.config.get("STORAGE_TEMP_DIR") or os.environ.get("STORAGE_TEMP_DIR") or "/tmp"
        except Exception:
            base = os.environ.get("STORAGE_TEMP_DIR") or "/tmp"
        root = os.path.join(base, "creatoros_downloads")
        os.makedirs(root, exist_ok=True)
        return root

    def prepare_local(self, user_id, item):
        key = (item or {}).get("key") or ""
        key = key.strip()
        if not key:
            stored_name = (item or {}).get("stored_name") or ""
            stored_name = stored_name.strip()
            if stored_name:
                key = f"{user_id}/{stored_name}"
        if not key:
            return None

        filename = os.path.basename(key)
        local_path = os.path.join(self._temp_root(), f"{uuid.uuid4().hex}_{filename}")
        try:
            self.client.download_file(self.bucket, key, local_path)
            return local_path
        except Exception:
            return None

    def cleanup_local(self, path):
        if not path:
            return None
        try:
            os.remove(path)
        except FileNotFoundError:
            return None


def get_storage():
    backend = (current_app.config.get("STORAGE_BACKEND") or "local").lower()
    if backend == "s3":
        bucket = current_app.config.get("S3_BUCKET")
        if not bucket:
            raise RuntimeError("S3_BUCKET is required for S3 storage backend.")
        return S3Storage(
            bucket=bucket,
            region=current_app.config.get("S3_REGION"),
            access_key=current_app.config.get("S3_ACCESS_KEY_ID"),
            secret_key=current_app.config.get("S3_SECRET_ACCESS_KEY"),
            endpoint_url=current_app.config.get("S3_ENDPOINT_URL"),
        )

    upload_dir = current_app.config.get("UPLOAD_DIR") or ""
    return LocalStorage(upload_dir)
