# apps/backend/app/core/logging_config.py
"""
Production observability logging configuration.

Implements structured logging with:
- JSON format for production environments
- Request correlation ID propagation
- Secret leakage prevention
- Standardized log fields
"""

import logging
import logging.config
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from pythonjsonlogger import jsonlogger

# Context variable for async-safe request correlation
request_id_context: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_context.get()


def set_request_id(request_id: str) -> None:
    """Set the current request ID in context."""
    request_id_context.set(request_id)


class SecretRedactingFormatter(logging.Formatter):
    """
    Log formatter that redacts sensitive information.

    Prevents accidental logging of:
    - Passwords
    - API keys
    - JWT tokens
    - Authorization headers
    - Database credentials
    """

    SENSITIVE_PATTERNS = [
        # Handle Bearer tokens - MUST come first to catch Authorization: Bearer <token> before authorization pattern
        # Enhanced pattern to handle JWT tokens (with dots), base64, and other token formats
        (r"Bearer\s+[A-Za-z0-9\._\-+/=]+", "Bearer [REDACTED]"),
        (r'password["\s]*[:=]["\s]*[^\s"]+', "password=[REDACTED]"),
        (r'api[_-]?key["\s]*[:=]["\s]*[^\s"]+', "api_key=[REDACTED]"),
        (r'jwt["\s]*[:=]["\s]*[^\s"]+', "jwt=[REDACTED]"),
        (r'token["\s]*[:=]["\s]*[^\s"]+', "token=[REDACTED]"),
        # Authorization pattern - handle Authorization headers with values
        # This catches authorization=anything (after Bearer pattern handles Bearer tokens)
        (r'authorization["\s]*[:=]["\s]*[^\s]+', "authorization=[REDACTED]"),
        (r'secret["\s]*[:=]["\s]*[^\s"]+', "secret=[REDACTED]"),
        (r"sk-[a-zA-Z0-9]{20,}", "sk-[REDACTED]"),  # OpenAI-style API keys
        (r"AIza[a-zA-Z0-9_-]{35}", "AIza[REDACTED]"),  # Google-style API keys
        # URL-based credential patterns - specifically match and redact credentials in URLs
        (r"(postgresql|mysql|mongodb)://[^:/\s]+:[^@/\s]+@", r"\1://[REDACTED]@"),
        (
            r"redis://:[^@/\s]+@",
            "redis://[REDACTED]@",
        ),  # Redis URL with password only (no username)
        (r"://[^:/\s]+:[^@/\s]+@", "://[REDACTED]@"),  # Catch-all for URL credentials
        # Handle generic API key patterns with variations
        (r"sk-[a-zA-Z0-9_-]+", "sk-[REDACTED]"),  # Catch shorter API keys too
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import re

        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.SENSITIVE_PATTERNS
        ]

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        for pattern, replacement in self._compiled_patterns:
            formatted = pattern.sub(replacement, formatted)
        return formatted


class StructuredFormatter(jsonlogger.JsonFormatter):
    """
    Structured JSON formatter for production logging.

    Adds standard fields to all log entries:
    - timestamp (ISO 8601)
    - level
    - logger
    - message
    - service
    - environment
    - request_id (when available)
    """

    def __init__(self, *args, **kwargs):
        # Remove unsupported kwargs for newer python-json-logger versions
        kwargs.pop("timestamp", None)
        kwargs.pop("level", None)
        kwargs.pop("logger", None)
        kwargs.pop("message", None)
        super().__init__(*args, **kwargs)

    def add_fields(
        self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]
    ):
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["service"] = "lumenly-api"
        log_record["environment"] = self._get_environment()

        # Add request ID if available from context
        request_id = get_request_id()
        if request_id:
            log_record["request_id"] = request_id

        # Ensure timestamp is ISO 8601 with timezone
        if "timestamp" in log_record:
            timestamp = log_record["timestamp"]
            if isinstance(timestamp, datetime):
                log_record["timestamp"] = timestamp.astimezone(UTC).isoformat()
        else:
            # Add timestamp if not present
            log_record["timestamp"] = datetime.fromtimestamp(record.created, tz=UTC).isoformat()

    def _get_environment(self) -> str:
        """Get current environment from settings."""
        try:
            from app.core.config import settings

            return settings.APP_ENV
        except Exception:
            return "unknown"


def validate_request_id(request_id: str) -> bool:
    """
    Validate incoming request ID format.

    Args:
        request_id: The request ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not request_id:
        return False

    # Check length (reasonable limit)
    if len(request_id) > 100:
        return False

    # Check if it's a valid UUID v4 format (if it looks like a UUID)
    import re

    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    if re.match(uuid_pattern, request_id.lower()):
        return True

    # Allow non-UUID request IDs if they're reasonable
    # (alphanumeric, hyphens, underscores, reasonable length)
    if re.match(r"^[a-zA-Z0-9_-]+$", request_id):
        return True

    return False


def setup_logging(environment: str = "development") -> None:
    """
    Setup logging configuration based on environment.

    Args:
        environment: The environment (development, staging, production)
    """
    log_level = logging.INFO
    if environment == "development":
        log_level = logging.DEBUG

    # Common logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "structured": {
                "()": "app.core.logging_config.StructuredFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "standard" if environment == "development" else "structured",
                "stream": sys.stdout,
            }
        },
        "root": {"level": log_level, "handlers": ["console"]},
        "loggers": {
            # Reduce noise from external libraries
            "uvicorn": {"level": logging.INFO, "propagate": False, "handlers": ["console"]},
            "uvicorn.access": {
                "level": logging.WARNING,
                "propagate": False,
                "handlers": ["console"],
            },
            "httpx": {"level": logging.WARNING, "propagate": False, "handlers": ["console"]},
            "pymongo": {"level": logging.WARNING, "propagate": False, "handlers": ["console"]},
            "qdrant_client": {
                "level": logging.WARNING,
                "propagate": False,
                "handlers": ["console"],
            },
            "redis": {"level": logging.WARNING, "propagate": False, "handlers": ["console"]},
        },
    }

    logging.config.dictConfig(logging_config)

    # Log that logging has been configured
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for environment: {environment}")


# Convenience function for getting a logger with correlation support
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger that supports request correlation.

    Args:
        name: The logger name (typically __name__)

    Returns:
        A logger instance
    """
    return logging.getLogger(name)
