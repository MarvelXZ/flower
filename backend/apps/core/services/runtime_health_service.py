"""Runtime health checks for production observability."""

import logging
from datetime import datetime, timezone

from django.db import connection

logger = logging.getLogger(__name__)


def get_runtime_health() -> dict:
    """Return a summary health report for the entire runtime."""
    deps = get_dependency_health()
    overall = "healthy"
    for dep in deps.values():
        if dep.get("status") == "degraded":
            overall = "degraded"
            break
        if dep.get("status") == "down":
            overall = "down"
            break
    return {
        "status": overall,
        "checks": deps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_dependency_health() -> dict:
    """Check health of all runtime dependencies."""
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "celery": _check_celery(),
    }
    return checks


def _check_database() -> dict:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"status": "healthy", "detail": "PostgreSQL connection OK"}
    except Exception as exc:
        logger.warning("health_db_failed", extra={"error": str(exc)[:200]})
        return {"status": "degraded", "detail": str(exc)[:200]}


def _check_redis() -> dict:
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        conn.ping()
        return {"status": "healthy", "detail": "Redis ping OK"}
    except Exception:
        return {"status": "degraded", "detail": "Redis unavailable"}


def _check_celery() -> dict:
    try:
        from celery.app.control import Inspect
        from config.celery import app
        inspect = Inspect(app=app)
        stats = inspect.stats()
        if stats:
            return {"status": "healthy", "detail": "Celery worker OK"}
        return {"status": "degraded", "detail": "No Celery workers responding"}
    except Exception:
        return {"status": "degraded", "detail": "Celery unavailable"}
