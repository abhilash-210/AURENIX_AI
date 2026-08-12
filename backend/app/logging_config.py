"""
Structured logging configuration for the Aurenix AI backend.

Provides two formatters:
  - TEXT: human-readable for local development
  - JSON: machine-parseable for production log aggregators (e.g. Cloud Logging)

Every log record emits: timestamp, level, logger name, message, and any extra
context fields (trace_id, request_id, etc.) passed via LoggerAdapter or
``logging.getLogger(...).info(..., extra={...})``.

Usage:
    from app.logging_config import configure_logging

    configure_logging(level="INFO", fmt="json")
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, Literal


class _JsonFormatter(logging.Formatter):
    """
    Emit each log record as a single-line JSON object.

    Standard fields always present:
        timestamp  — ISO-8601 UTC
        level      — DEBUG / INFO / WARNING / ERROR / CRITICAL
        logger     — dotted module name
        message    — formatted log message

    Any extra keyword arguments passed to the logging call are merged into the
    root of the JSON object, making it easy to attach trace_id, request_id, etc.
    """

    _RESERVED: frozenset[str] = frozenset(
        {
            "args",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "taskName",
            "thread",
            "threadName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }

        # Merge any extra context fields (e.g. trace_id, request_id)
        for key, value in record.__dict__.items():
            if key not in self._RESERVED:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class _TextFormatter(logging.Formatter):
    """
    Human-readable formatter for local development.

    Format: YYYY-MM-DD HH:MM:SS  LEVEL     logger_name  message
    """

    _FMT = "%(asctime)s  %(levelname)-8s  %(name)-30s  %(message)s"
    _DATEFMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATEFMT)


def configure_logging(
    level: str = "INFO",
    fmt: Literal["json", "text"] = "text",
) -> None:
    """
    Configure the root logger for the application.

    Should be called exactly once at application startup (inside the FastAPI
    lifespan handler) before any other logging calls are made.

    Args:
        level: Python logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        fmt:   Output format — "json" for production, "text" for development.
    """
    formatter: logging.Formatter = (
        _JsonFormatter() if fmt == "json" else _TextFormatter()
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Remove any handlers added by libraries before ours
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = True
