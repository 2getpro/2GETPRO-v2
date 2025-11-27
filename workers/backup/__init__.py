"""
Модуль резервного копирования базы данных.

Этот модуль предоставляет полнофункциональную систему резервного копирования
PostgreSQL базы данных с поддержкой:
- Полных и инкрементальных бэкапов
- Сжатия и шифрования
- Хранения в S3/MinIO
- Автоматического восстановления
- Политики хранения (retention policy)
- Мониторинга и алертов
"""

from .backup_worker import BackupWorker
from .backup_manager import BackupManager
from .restore_manager import RestoreManager
from .retention_policy import RetentionPolicy
from .s3_storage import S3Storage
from .monitoring import BackupMonitoring
from .config import BackupConfig, get_backup_config, set_backup_config

__all__ = [
    'BackupWorker',
    'BackupManager',
    'RestoreManager',
    'RetentionPolicy',
    'S3Storage',
    'BackupMonitoring',
    'BackupConfig',
    'get_backup_config',
    'set_backup_config',
]

__version__ = "1.0.0"