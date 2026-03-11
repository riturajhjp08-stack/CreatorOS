import os
from datetime import timedelta
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


def create_celery(app=None):
    broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    celery = Celery("creatoros", broker=broker, backend=backend)
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        task_acks_late=_get_bool("CELERY_TASK_ACKS_LATE", True),
        task_reject_on_worker_lost=_get_bool("CELERY_TASK_REJECT_ON_WORKER_LOST", True),
        worker_prefetch_multiplier=_get_int("CELERY_WORKER_PREFETCH_MULTIPLIER", 1),
        task_soft_time_limit=_get_int("CELERY_TASK_SOFT_TIME_LIMIT", 300),
        task_time_limit=_get_int("CELERY_TASK_TIME_LIMIT", 600),
        worker_concurrency=_get_int("CELERY_WORKER_CONCURRENCY", 2),
        broker_pool_limit=_get_int("CELERY_BROKER_POOL_LIMIT", 10),
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
