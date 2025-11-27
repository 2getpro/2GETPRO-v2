"""
Конфигурация системы резервного копирования базы данных.

Этот модуль содержит настройки для создания, хранения и восстановления
резервных копий PostgreSQL базы данных.
"""

from typing import Optional
from pydantic import BaseSettings, Field, validator


class BackupConfig(BaseSettings):
    """Конфигурация системы резервного копирования."""
    
    # PostgreSQL настройки
    DB_HOST: str = Field(..., description="Хост PostgreSQL")
    DB_PORT: int = Field(5432, description="Порт PostgreSQL")
    DB_NAME: str = Field(..., description="Имя базы данных")
    DB_USER: str = Field(..., description="Пользователь БД")
    DB_PASSWORD: str = Field(..., description="Пароль БД")
    
    # Настройки резервного копирования
    BACKUP_DIR: str = Field("/backups", description="Директория для локальных бэкапов")
    BACKUP_SCHEDULE: str = Field("0 2 * * *", description="Расписание полных бэкапов (cron)")
    INCREMENTAL_SCHEDULE: str = Field("0 * * * *", description="Расписание инкрементальных бэкапов (cron)")
    
    # S3/MinIO настройки
    S3_ENABLED: bool = Field(True, description="Включить загрузку в S3")
    S3_ENDPOINT: Optional[str] = Field(None, description="Endpoint S3/MinIO")
    S3_BUCKET: str = Field("backups", description="S3 bucket для бэкапов")
    S3_ACCESS_KEY: Optional[str] = Field(None, description="S3 access key")
    S3_SECRET_KEY: Optional[str] = Field(None, description="S3 secret key")
    S3_REGION: str = Field("us-east-1", description="S3 регион")
    S3_USE_SSL: bool = Field(True, description="Использовать SSL для S3")
    
    # Настройки шифрования
    ENCRYPTION_ENABLED: bool = Field(True, description="Включить шифрование бэкапов")
    ENCRYPTION_KEY: Optional[str] = Field(None, description="Ключ шифрования (AES-256)")
    ENCRYPTION_ALGORITHM: str = Field("AES-256-CBC", description="Алгоритм шифрования")
    
    # Политика хранения (retention policy)
    DAILY_RETENTION_DAYS: int = Field(7, description="Хранить ежедневные бэкапы (дней)")
    WEEKLY_RETENTION_WEEKS: int = Field(4, description="Хранить еженедельные бэкапы (недель)")
    MONTHLY_RETENTION_MONTHS: int = Field(12, description="Хранить ежемесячные бэкапы (месяцев)")
    YEARLY_RETENTION_YEARS: int = Field(5, description="Хранить годовые бэкапы (лет)")
    
    # Настройки сжатия
    COMPRESSION_ENABLED: bool = Field(True, description="Включить сжатие бэкапов")
    COMPRESSION_LEVEL: int = Field(6, description="Уровень сжатия gzip (1-9)")
    
    # Настройки мониторинга
    MONITORING_ENABLED: bool = Field(True, description="Включить мониторинг бэкапов")
    ALERT_EMAIL: Optional[str] = Field(None, description="Email для алертов")
    ALERT_TELEGRAM_CHAT_ID: Optional[str] = Field(None, description="Telegram chat ID для алертов")
    ALERT_TELEGRAM_BOT_TOKEN: Optional[str] = Field(None, description="Telegram bot token")
    
    # Настройки производительности
    MAX_PARALLEL_UPLOADS: int = Field(3, description="Максимум параллельных загрузок в S3")
    MULTIPART_THRESHOLD: int = Field(100 * 1024 * 1024, description="Порог для multipart upload (байты)")
    MULTIPART_CHUNKSIZE: int = Field(10 * 1024 * 1024, description="Размер части для multipart upload (байты)")
    
    # Настройки восстановления
    RESTORE_VERIFY_ENABLED: bool = Field(True, description="Проверять восстановленную БД")
    RESTORE_SNAPSHOT_ENABLED: bool = Field(True, description="Создавать snapshot перед восстановлением")
    RESTORE_TIMEOUT: int = Field(3600, description="Таймаут восстановления (секунды)")
    
    # Настройки логирования
    LOG_LEVEL: str = Field("INFO", description="Уровень логирования")
    LOG_FILE: str = Field("/var/log/backup/backup.log", description="Файл логов")
    
    # WAL архивирование (для инкрементальных бэкапов)
    WAL_ARCHIVE_DIR: str = Field("/backups/wal", description="Директория для WAL архивов")
    WAL_ARCHIVE_ENABLED: bool = Field(True, description="Включить WAL архивирование")
    
    @validator("COMPRESSION_LEVEL")
    def validate_compression_level(cls, v):
        """Проверка уровня сжатия."""
        if not 1 <= v <= 9:
            raise ValueError("Уровень сжатия должен быть от 1 до 9")
        return v
    
    @validator("ENCRYPTION_KEY")
    def validate_encryption_key(cls, v, values):
        """Проверка ключа шифрования."""
        if values.get("ENCRYPTION_ENABLED") and not v:
            raise ValueError("ENCRYPTION_KEY обязателен при включенном шифровании")
        if v and len(v) < 32:
            raise ValueError("ENCRYPTION_KEY должен быть минимум 32 символа")
        return v
    
    @validator("S3_ACCESS_KEY", "S3_SECRET_KEY")
    def validate_s3_credentials(cls, v, values, field):
        """Проверка S3 credentials."""
        if values.get("S3_ENABLED") and not v:
            raise ValueError(f"{field.name} обязателен при включенном S3")
        return v
    
    class Config:
        """Настройки Pydantic."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Глобальный экземпляр конфигурации
_config: Optional[BackupConfig] = None


def get_backup_config() -> BackupConfig:
    """
    Получить глобальный экземпляр конфигурации.
    
    Returns:
        BackupConfig: Конфигурация системы резервного копирования
    """
    global _config
    if _config is None:
        _config = BackupConfig()
    return _config


def set_backup_config(config: BackupConfig) -> None:
    """
    Установить глобальный экземпляр конфигурации.
    
    Args:
        config: Новая конфигурация
    """
    global _config
    _config = config