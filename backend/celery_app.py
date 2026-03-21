import os
from datetime import timedelta
from urllib.parse import urlparse, urlunparse

from celery import Celery


def _get_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _normalize_redis_url(url, db=None):
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"redis", "rediss"}:
        return url
    if db is None:
        return url
    path = f"/{db}"
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def create_celery(app=None):
    redis_url = os.environ.get("REDIS_URL", "")
    broker_db = _get_int("CELERY_BROKER_DB", 1)
    result_db = _get_int("CELERY_RESULT_DB", 2)
    broker = os.environ.get("CELERY_BROKER_URL") or _normalize_redis_url(redis_url, broker_db)
    backend = os.environ.get("CELERY_RESULT_BACKEND") or _normalize_redis_url(redis_url, result_db)
    broker = broker or "redis://localhost:6379/1"
    backend = backend or "redis://localhost:6379/2"

    task_soft_time_limit = _get_int("CELERY_TASK_SOFT_TIME_LIMIT", 300)
    task_time_limit = _get_int("CELERY_TASK_TIME_LIMIT", 600)
    visibility_timeout = _get_int("CELERY_VISIBILITY_TIMEOUT", max(task_time_limit * 2, 3600))
    socket_timeout = _get_int("CELERY_REDIS_SOCKET_TIMEOUT", 10)
    socket_connect_timeout = _get_int("CELERY_REDIS_SOCKET_CONNECT_TIMEOUT", 10)
    max_connections = _get_int("CELERY_REDIS_MAX_CONNECTIONS", 20)

    celery = Celery("creatoros", broker=broker, backend=backend)
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=_get_int("CELERY_BROKER_MAX_RETRIES", 5),
        task_track_started=_get_bool("CELERY_TASK_TRACK_STARTED", True),
        task_acks_late=_get_bool("CELERY_TASK_ACKS_LATE", True),
        task_reject_on_worker_lost=_get_bool("CELERY_TASK_REJECT_ON_WORKER_LOST", True),
        worker_prefetch_multiplier=_get_int("CELERY_WORKER_PREFETCH_MULTIPLIER", 1),
        task_soft_time_limit=task_soft_time_limit,
        task_time_limit=task_time_limit,
        worker_concurrency=_get_int("CELERY_WORKER_CONCURRENCY", 2),
        broker_pool_limit=_get_int("CELERY_BROKER_POOL_LIMIT", 10),
        worker_max_tasks_per_child=_get_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 200),
        result_expires=_get_int("CELERY_RESULT_EXPIRES", 86400),
        broker_transport_options={
            "visibility_timeout": visibility_timeout,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "retry_on_timeout": True,
            "health_check_interval": _get_int("CELERY_REDIS_HEALTH_CHECK_INTERVAL", 30),
            "max_connections": max_connections,
        },
        result_backend_transport_options={
            "retry_on_timeout": True,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "health_check_interval": _get_int("CELERY_REDIS_HEALTH_CHECK_INTERVAL", 30),
            "max_connections": max_connections,
        },
    )

    due_posts_interval = _get_int("DUE_POSTS_INTERVAL_SECONDS", 60)
    cleanup_interval_minutes = _get_int("CLEANUP_SESSIONS_INTERVAL_MINUTES", 60)
    analytics_interval_minutes = _get_int("ANALYTICS_SYNC_INTERVAL_MINUTES", 60)
    due_posts_batch = _get_int("DUE_POSTS_BATCH_SIZE", 200)
    analytics_batch = _get_int("ANALYTICS_SYNC_BATCH_SIZE", 200)

    celery.conf.beat_schedule = {
        "process-due-posts": {
            "task": "tasks.process_due_posts_task",
            "schedule": timedelta(seconds=due_posts_interval),
            "kwargs": {"limit": due_posts_batch},
        },
        "cleanup-expired-sessions": {
            "task": "tasks.cleanup_expired_sessions_task",
            "schedule": timedelta(minutes=cleanup_interval_minutes),
        },
        "sync-all-analytics": {
            "task": "tasks.sync_all_analytics_for_all_users_task",
            "schedule": timedelta(minutes=analytics_interval_minutes),
            "kwargs": {"limit": analytics_batch},
        },
    }

    if app is not None:
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
    return celery
