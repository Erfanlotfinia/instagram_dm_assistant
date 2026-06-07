import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.log_masking import mask_dict, mask_string


class JsonFormatter(logging.Formatter):
    """Small dependency-free JSON formatter for container-friendly logs."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        message = mask_string(record.getMessage())
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        if record.exc_info:
            payload["exception"] = mask_string(self.formatException(record.exc_info))
        for field in ("request_id", "ip_address", "shop_id", "user_id", "action"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            payload["data"] = mask_dict(record.extra_data)
        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    for noisy_logger in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
