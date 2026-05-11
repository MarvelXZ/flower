"""JSON log formatter for production structured logging.

Produces JSON lines parsable by Loki, ELK, or any JSON log shipper.
In local development, use the default Django console formatter.
"""

import json
import logging
from datetime import datetime, timezone


class JSONLogFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add optional structured fields from extra
        for key in ("request_id", "correlation_id", "tenant_schema", "user_id",
                     "path", "method", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        # Never log sensitive keys
        sensitive = ("password", "secret", "token", "auth", "authorization",
                     "hmac", "api_key")
        safe = {}
        for k, v in log_entry.items():
            if any(s in k.lower() for s in sensitive):
                safe[k] = "[redacted]"
            else:
                safe[k] = v

        return json.dumps(safe, default=str)
