"""
Модуль структурированного логирования.
"""

from .logger_config import setup_logging, get_logger
from .structured_logger import StructuredLogger
from .log_handlers import get_file_handler, get_stream_handler, get_syslog_handler

__all__ = [
    'setup_logging',
    'get_logger',
    'StructuredLogger',
    'get_file_handler',
    'get_stream_handler',
    'get_syslog_handler'
]