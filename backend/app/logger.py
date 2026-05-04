"""커스텀 로거 - Request ID 포함 로깅 시스템."""

import logging
import sys
from logging.config import dictConfig
from app.middleware.request_id import get_request_id


class RequestIDFilter(logging.Filter):
    """로깅 필터 - 모든 로그에 Request ID 추가"""

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = get_request_id()
        record.request_id = request_id or "N/A"
        return True


def setup_logger(name: str | None = None) -> logging.Logger:
    """로거 설정"""
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s - %(request_id)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "/var/log/chatbot/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "json",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"],
        },
    }

    dictConfig(log_config)

    logger = logging.getLogger(name or __name__)
    logger.addFilter(RequestIDFilter())

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """로거 가져오기"""
    return setup_logger(name)
