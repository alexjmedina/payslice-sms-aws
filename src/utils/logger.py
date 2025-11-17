import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class JsonFormatter(logging.Formatter):
    """
    Simple JSON formatter for Lambda logs.
    Produces one JSON object per log line. Easy to parse in CloudWatch / tools.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S,%f%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # You can add more structured fields here if desired
        return json.dumps(payload)


def get_logger(name: str = "app") -> logging.Logger:
    """
    Returns a singleton JSON-logging logger for the given name.
    Safe to call many times; it will only configure the logger once.
    """
    logger = logging.getLogger(name)

    # Avoid reconfiguring handlers on repeated calls
    if getattr(logger, "_configured", False):
        return logger

    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    # Do not propagate to the root logger; we emit JSON ourselves.
    logger.propagate = False

    # Mark as configured
    logger._configured = True  # type: ignore[attr-defined]

    return logger


# Convenience helper for “fire-and-forget” logging
_base_logger = get_logger("root")


def log(message: str, **fields: Any) -> None:
    """
    Convenience function for quick logs without manually grabbing a logger.
    Example:
        log("twilio.status", message_sid="SMxxx", status="delivered")
    """
    if fields:
        _base_logger.info(message, extra={"fields": fields})
    else:
        _base_logger.info(message)
