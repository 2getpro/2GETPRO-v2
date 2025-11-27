"""
Конфигурация логирования для приложения.

Настраивает:
- Структурированное логирование (JSON)
- Разные уровни логирования для разных модулей
- Ротацию логов
- Форматирование для ELK Stack
"""

from typing import Optional, Dict, Any
import logging
import logging.config
from pathlib import Path
import sys


# Конфигурация логирования по умолчанию
DEFAULT_LOG_CONFIG: Dict[str, Any] = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'filters': {
        'sensitive_data': {
            '()': 'monitoring.logging.log_handlers.SensitiveDataFilter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
            'filters': ['sensitive_data']
        },
        'console_json': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'json',
            'stream': 'ext://sys.stdout',
            'filters': ['sensitive_data']
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'encoding': 'utf-8',
            'filters': ['sensitive_data']
        },
        'file_json': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'json',
            'filename': 'logs/app.json',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'encoding': 'utf-8',
            'filters': ['sensitive_data']
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': 'logs/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'encoding': 'utf-8',
            'filters': ['sensitive_data']
        }
    },
    'loggers': {
        '': {  # Root logger
            'level': 'INFO',
            'handlers': ['console', 'file', 'error_file']
        },
        'bot': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_json', 'error_file'],
            'propagate': False
        },
        'monitoring': {
            'level': 'DEBUG',
            'handlers': ['console', 'file_json', 'error_file'],
            'propagate': False
        },
        'db': {
            'level': 'INFO',
            'handlers': ['console', 'file_json', 'error_file'],
            'propagate': False
        },
        'sqlalchemy': {
            'level': 'WARNING',
            'handlers': ['file'],
            'propagate': False
        },
        'aiohttp': {
            'level': 'WARNING',
            'handlers': ['file'],
            'propagate': False
        },
        'aiogram': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    }
}


def setup_logging(
    log_level: str = 'INFO',
    log_dir: str = 'logs',
    use_json: bool = True,
    use_syslog: bool = False,
    syslog_address: Optional[tuple] = None,
    config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Настройка логирования для приложения.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Директория для логов
        use_json: Использовать JSON формат для логов
        use_syslog: Использовать syslog
        syslog_address: Адрес syslog сервера (host, port)
        config: Пользовательская конфигурация логирования
    """
    # Создаем директорию для логов если её нет
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Используем пользовательскую конфигурацию или конфигурацию по умолчанию
    log_config = config or DEFAULT_LOG_CONFIG.copy()
    
    # Обновляем пути к файлам логов
    if 'handlers' in log_config:
        for handler_name, handler_config in log_config['handlers'].items():
            if 'filename' in handler_config:
                handler_config['filename'] = str(log_path / Path(handler_config['filename']).name)
    
    # Обновляем уровень логирования
    if 'loggers' in log_config:
        for logger_config in log_config['loggers'].values():
            if 'level' in logger_config:
                logger_config['level'] = log_level
    
    # Добавляем JSON handler если нужно
    if use_json and 'handlers' in log_config:
        if 'console_json' in log_config['handlers']:
            log_config['loggers']['']['handlers'].append('console_json')
    
    # Добавляем syslog handler если нужно
    if use_syslog and syslog_address:
        if 'handlers' not in log_config:
            log_config['handlers'] = {}
        
        log_config['handlers']['syslog'] = {
            'class': 'logging.handlers.SysLogHandler',
            'level': 'INFO',
            'formatter': 'json' if use_json else 'standard',
            'address': syslog_address,
            'filters': ['sensitive_data']
        }
        
        # Добавляем syslog handler ко всем логгерам
        for logger_config in log_config['loggers'].values():
            if 'handlers' in logger_config:
                logger_config['handlers'].append('syslog')
    
    # Применяем конфигурацию
    logging.config.dictConfig(log_config)
    
    # Логируем успешную инициализацию
    logger = logging.getLogger(__name__)
    logger.info(
        f'Logging configured: level={log_level}, '
        f'log_dir={log_dir}, use_json={use_json}, use_syslog={use_syslog}'
    )


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер по имени.
    
    Args:
        name: Имя логгера
    
    Returns:
        Логгер
    """
    return logging.getLogger(name)


def set_log_level(logger_name: str, level: str) -> None:
    """
    Установить уровень логирования для конкретного логгера.
    
    Args:
        logger_name: Имя логгера
        level: Уровень логирования
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.info(f'Log level for {logger_name} set to {level}')


def add_handler(
    logger_name: str,
    handler: logging.Handler
) -> None:
    """
    Добавить handler к логгеру.
    
    Args:
        logger_name: Имя логгера
        handler: Handler для добавления
    """
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)


def remove_handler(
    logger_name: str,
    handler: logging.Handler
) -> None:
    """
    Удалить handler из логгера.
    
    Args:
        logger_name: Имя логгера
        handler: Handler для удаления
    """
    logger = logging.getLogger(logger_name)
    logger.removeHandler(handler)


def get_log_config() -> Dict[str, Any]:
    """
    Получить текущую конфигурацию логирования.
    
    Returns:
        Конфигурация логирования
    """
    return DEFAULT_LOG_CONFIG.copy()