"""统一日志配置：结构化格式、请求 ID 上下文、可配置级别。

用法：
    from logging_config import get_logger, request_id_var
    logger = get_logger(__name__)
    logger.info('query received', extra={'request_id': request_id_var.get()})
"""
import logging
import sys
import uuid
from contextvars import ContextVar

import config

request_id_var: ContextVar[str] = ContextVar('request_id', default='-')

LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s] [rid=%(request_id)s] %(message)s'


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid
