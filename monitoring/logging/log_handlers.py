"""
Обработчики логов для различных целей.

Включает:
- FileHandler с ротацией
- StreamHandler для консоли
- SysLogHandler для централизованного логирования
- Фильтры для чувствительных данных
"""

from typing import Optional, List
import logging
import logging.handlers
import re
from pathlib import Path


# Список полей с чувствительными данными
SENSITIVE_PATTERNS = [
    r'password["\']?\s*[:=]\s*["\']?[\w\d]+',
    r'token["\']?\s*[:=]\s*["\']?[\w\d\-_]+',
    r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w\d\-_]+',
    r'secret["\']?\s*[:=]\s*["\']?[\w\d\-_]+',
    r'authorization["\']?\s*[:=]\s*["\']?[\w\d\-_\s]+',
    r'bearer\s+[\w\d\-_\.]+',
    r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}',  # Credit card
    r'\d{3}-\d{2}-\d{4}',  # SSN
]


class SensitiveDataFilter(logging.Filter):
    """Фильтр для удаления чувствительных данных из логов."""
    
    def __init__(self, name: str = ''):
        """
        Инициализация фильтра.
        
        Args:
            name: Имя фильтра
        """
        super().__init__(name)
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SENSITIVE_PATTERNS]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Фильтрация записи лога.
        
        Args:
            record: Запись лога
        
        Returns:
            True если запись должна быть залогирована
        """
        # Фильтруем сообщение
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern in self.patterns:
                record.msg = pattern.sub('[FILTERED]', record.msg)
        
        # Фильтруем args
        if hasattr(record, 'args') and record.args:
            filtered_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern in self.patterns:
                        arg = pattern.sub('[FILTERED]', arg)
                filtered_args.append(arg)
            record.args = tuple(filtered_args)
        
        return True


def get_file_handler(
    filename: str,
    level: str = 'DEBUG',
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 10,
    encoding: str = 'utf-8',
    formatter: Optional[logging.Formatter] = None,
    use_json: bool = False
) -> logging.handlers.RotatingFileHandler:
    """
    Создать file handler с ротацией.
    
    Args:
        filename: Путь к файлу лога
        level: Уровень логирования
        max_bytes: Максимальный размер файла в байтах
        backup_count: Количество резервных копий
        encoding: Кодировка файла
        formatter: Форматтер для логов
        use_json: Использовать JSON формат
    
    Returns:
        RotatingFileHandler
    """
    # Создаем директорию если её нет
    log_path = Path(filename)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Создаем handler
    handler = logging.handlers.RotatingFileHandler(
        filename=filename,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding
    )
    
    # Устанавливаем уровень
    handler.setLevel(getattr(logging, level.upper()))
    
    # Устанавливаем форматтер
    if formatter:
        handler.setFormatter(formatter)
    elif use_json:
        try:
            from pythonjsonlogger import jsonlogger
            json_formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
            )
            handler.setFormatter(json_formatter)
        except ImportError:
            # Fallback to standard formatter
            standard_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(standard_formatter)
    else:
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(standard_formatter)
    
    # Добавляем фильтр для чувствительных данных
    handler.addFilter(SensitiveDataFilter())
    
    return handler


def get_stream_handler(
    level: str = 'INFO',
    formatter: Optional[logging.Formatter] = None,
    use_json: bool = False
) -> logging.StreamHandler:
    """
    Создать stream handler для консоли.
    
    Args:
        level: Уровень логирования
        formatter: Форматтер для логов
        use_json: Использовать JSON формат
    
    Returns:
        StreamHandler
    """
    # Создаем handler
    handler = logging.StreamHandler()
    
    # Устанавливаем уровень
    handler.setLevel(getattr(logging, level.upper()))
    
    # Устанавливаем форматтер
    if formatter:
        handler.setFormatter(formatter)
    elif use_json:
        try:
            from pythonjsonlogger import jsonlogger
            json_formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s'
            )
            handler.setFormatter(json_formatter)
        except ImportError:
            # Fallback to standard formatter
            standard_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(standard_formatter)
    else:
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(standard_formatter)
    
    # Добавляем фильтр для чувствительных данных
    handler.addFilter(SensitiveDataFilter())
    
    return handler


def get_syslog_handler(
    address: tuple,
    level: str = 'INFO',
    formatter: Optional[logging.Formatter] = None,
    use_json: bool = True
) -> logging.handlers.SysLogHandler:
    """
    Создать syslog handler для централизованного логирования.
    
    Args:
        address: Адрес syslog сервера (host, port)
        level: Уровень логирования
        formatter: Форматтер для логов
        use_json: Использовать JSON формат
    
    Returns:
        SysLogHandler
    """
    # Создаем handler
    handler = logging.handlers.SysLogHandler(address=address)
    
    # Устанавливаем уровень
    handler.setLevel(getattr(logging, level.upper()))
    
    # Устанавливаем форматтер
    if formatter:
        handler.setFormatter(formatter)
    elif use_json:
        try:
            from pythonjsonlogger import jsonlogger
            json_formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
            )
            handler.setFormatter(json_formatter)
        except ImportError:
            # Fallback to standard formatter
            standard_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(standard_formatter)
    else:
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(standard_formatter)
    
    # Добавляем фильтр для чувствительных данных
    handler.addFilter(SensitiveDataFilter())
    
    return handler


class TimedRotatingFileHandlerWithCompression(logging.handlers.TimedRotatingFileHandler):
    """
    TimedRotatingFileHandler с автоматическим сжатием старых логов.
    """
    
    def __init__(
        self,
        filename: str,
        when: str = 'midnight',
        interval: int = 1,
        backup_count: int = 30,
        encoding: Optional[str] = 'utf-8',
        delay: bool = False,
        utc: bool = False,
        at_time: Optional[object] = None
    ):
        """
        Инициализация handler.
        
        Args:
            filename: Путь к файлу лога
            when: Интервал ротации (S, M, H, D, midnight, W0-W6)
            interval: Интервал между ротациями
            backup_count: Количество резервных копий
            encoding: Кодировка файла
            delay: Отложить открытие файла
            utc: Использовать UTC время
            at_time: Время для ротации
        """
        super().__init__(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=at_time
        )
    
    def doRollover(self) -> None:
        """Выполнить ротацию с сжатием."""
        super().doRollover()
        
        # Сжимаем старые логи
        import gzip
        import shutil
        from pathlib import Path
        
        log_dir = Path(self.baseFilename).parent
        log_name = Path(self.baseFilename).stem
        
        # Находим все несжатые ротированные логи
        for log_file in log_dir.glob(f'{log_name}.*'):
            if not log_file.suffix == '.gz' and log_file != Path(self.baseFilename):
                # Сжимаем файл
                with open(log_file, 'rb') as f_in:
                    with gzip.open(f'{log_file}.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Удаляем оригинальный файл
                log_file.unlink()


def get_timed_rotating_handler(
    filename: str,
    when: str = 'midnight',
    interval: int = 1,
    backup_count: int = 30,
    level: str = 'DEBUG',
    encoding: str = 'utf-8',
    formatter: Optional[logging.Formatter] = None,
    use_json: bool = False,
    compress: bool = True
) -> logging.Handler:
    """
    Создать timed rotating file handler.
    
    Args:
        filename: Путь к файлу лога
        when: Интервал ротации (S, M, H, D, midnight, W0-W6)
        interval: Интервал между ротациями
        backup_count: Количество резервных копий
        level: Уровень логирования
        encoding: Кодировка файла
        formatter: Форматтер для логов
        use_json: Использовать JSON формат
        compress: Сжимать старые логи
    
    Returns:
        TimedRotatingFileHandler
    """
    # Создаем директорию если её нет
    log_path = Path(filename)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Создаем handler
    if compress:
        handler = TimedRotatingFileHandlerWithCompression(
            filename=filename,
            when=when,
            interval=interval,
            backup_count=backup_count,
            encoding=encoding
        )
    else:
        handler = logging.handlers.TimedRotatingFileHandler(
            filename=filename,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding=encoding
        )
    
    # Устанавливаем уровень
    handler.setLevel(getattr(logging, level.upper()))
    
    # Устанавливаем форматтер
    if formatter:
        handler.setFormatter(formatter)
    elif use_json:
        try:
            from pythonjsonlogger import jsonlogger
            json_formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
            )
            handler.setFormatter(json_formatter)
        except ImportError:
            # Fallback to standard formatter
            standard_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(standard_formatter)
    else:
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(standard_formatter)
    
    # Добавляем фильтр для чувствительных данных
    handler.addFilter(SensitiveDataFilter())
    
    return handler