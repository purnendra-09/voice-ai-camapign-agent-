import logging
import json
from datetime import datetime
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def log_request(logger: logging.Logger, endpoint: str, method: str, data: Optional[Any] = None):
    """Log incoming request"""
    extra_data = {
        "endpoint": endpoint,
        "method": method,
    }
    if data:
        extra_data["request_data"] = str(data)

    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "request",
        0,
        f"{method} {endpoint}",
        (),
        None,
    )
    record.extra_data = extra_data
    logger.handle(record)


def log_response(logger: logging.Logger, endpoint: str, status_code: int, response: Any):
    """Log outgoing response"""
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "response",
        0,
        f"Response from {endpoint}",
        (),
        None,
    )
    record.extra_data = {
        "endpoint": endpoint,
        "status_code": status_code,
        "response": str(response),
    }
    logger.handle(record)


def log_error(logger: logging.Logger, error_msg: str, error_type: str, context: Optional[Any] = None):
    """Log error with context"""
    record = logger.makeRecord(
        logger.name,
        logging.ERROR,
        "error",
        0,
        error_msg,
        (),
        None,
    )
    record.extra_data = {
        "error_type": error_type,
    }
    if context:
        record.extra_data["context"] = str(context)
    logger.handle(record)
