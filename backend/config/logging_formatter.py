"""
JSON log formatter for structured audit logging.
Outputs one JSON object per log line for easy SIEM ingestion.
"""

import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON lines."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include audit data if present
        audit = getattr(record, "audit", None)
        if audit:
            log_entry["audit"] = audit

        return json.dumps(log_entry, default=str)
