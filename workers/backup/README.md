# Система резервного копирования базы данных

Полнофункциональная система резервного копирования PostgreSQL базы данных для проекта 2GETPRO_v2.

## Возможности

- ✅ **Полные и инкрементальные бэкапы** - поддержка pg_dump и WAL архивирования
- ✅ **Сжатие и шифрование** - gzip сжатие и AES-256 шифрование
- ✅ **S3/MinIO хранилище** - автоматическая загрузка в облачное хранилище
- ✅ **Автоматическое восстановление** - простое восстановление из любого бэкапа
- ✅ **Retention policy** - автоматическое удаление старых бэкапов
- ✅ **Мониторинг и алерты** - интеграция с Prometheus, email и Telegram
- ✅ **Планирование** - автоматические бэкапы по расписанию

## Архитектура

```
workers/backup/
├── __init__.py              # Экспорт модулей
├── config.py                # Конфигурация системы
├── backup_worker.py         # Основной worker для бэкапов
├── backup_manager.py        # Менеджер управления бэкапами
├── restore_manager.py       # Менеджер восстановления
├── retention_policy.py      # Политика хранения
├── s3_storage.py           # S3/MinIO интеграция
├── monitoring.py           # Мониторинг и алерты
├── scripts/
│   ├── backup.sh           # Bash скрипт для бэкапа
│   └── restore.sh          # Bash скрипт для восстановления
└── README.md               # Документация
```

## Установка

### Зависимости

```bash
pip install boto3 cryptography pydantic aiohttp
```

### PostgreSQL утилиты

Убедитесь, что установлены PostgreSQL клиентские утилиты:

```bash
# Ubuntu/Debian
apt-get install postgresql-client

# CentOS/RHEL
yum install postgresql

# macOS
brew install postgresql
```

### AWS CLI (для S3)

```bash
# Ubuntu/Debian
apt-get install awscli

# macOS
brew install awscli

# Или через pip
pip install awscli
```

## Конфигурация

### Переменные окружения

Создайте файл `.env` с необходимыми настройками:

```env
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=2getpro
DB_USER=postgres
DB_PASSWORD=your_password

# Backup settings
BACKUP_DIR=/backups
BACKUP_SCHEDULE=0 2 * * *
INCREMENTAL_SCHEDULE=0 * * * *

# S3/MinIO
S3_ENABLED=true
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=backups
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_REGION=us-east-1

# Encryption
ENCRYPTION_ENABLED=true
ENCRYPTION_KEY=your_32_character_encryption_key_here

# Retention policy
DAILY_RETENTION_DAYS=7
WEEKLY_RETENTION_WEEKS=4
MONTHLY_RETENTION_MONTHS=12
YEARLY_RETENTION_YEARS=5

# Monitoring
MONITORING_ENABLED=true
ALERT_EMAIL=admin@example.com
ALERT_TELEGRAM_CHAT_ID=your_chat_id
ALERT_TELEGRAM_BOT_TOKEN=your_bot_token
```

## Использование

### Python API

#### Создание полного бэкапа

```python
from workers.backup import BackupWorker

# Инициализация worker
backup_worker = BackupWorker()

# Создание полного бэкапа
backup_id = await backup_worker.create_full_backup()
print(f"Создан бэкап: {backup_id}")
```

#### Создание инкрементального бэкапа

```python
# Создание инкрементального бэкапа (WAL архивы)
backup_id = await backup_worker.create_incremental_backup()
print(f"Создан инкрементальный бэкап: {backup_id}")
```

#### Восстановление из бэкапа

```python
from workers.backup import RestoreManager

# Инициализация restore manager
restore_manager = RestoreManager()

# Восстановление из бэкапа
await restore_manager.restore_from_backup(backup_id)
```

#### Восстановление на момент времени

```python
from datetime import datetime

# Восстановление на определенный момент времени
timestamp = datetime(2024, 1, 15, 12, 0, 0)
await restore_manager.restore_to_point_in_time(timestamp)
```

#### Применение retention policy

```python
from workers.backup import RetentionPolicy

# Инициализация retention policy
retention = RetentionPolicy()

# Применение политики хранения
stats = await retention.apply_retention_policy()
print(f"Удалено бэкапов: {stats['total_deleted']}")
```

#### Мониторинг

```python
from workers.backup import BackupMonitoring

# Инициализация мониторинга
monitoring = BackupMonitoring()

# Проверка статуса
status = await monitoring.check_backup_status()
print(f"Статус: {status['status']}")

# Генерация отчета
report = await monitoring.generate_backup_report(period_days=7)
print(f"Всего бэкапов за неделю: {report['total_backups']}")
```

#### Планирование автоматических бэкапов

```python
# Запуск планировщика
await backup_worker.schedule_backups()
# Планировщик будет работать в фоне
```

### Bash скрипты

#### Создание бэкапа

```bash
# Полный бэкап
./workers/backup/scripts/backup.sh full

# Инкрементальный бэкап
./workers/backup/scripts/backup.sh incremental
```

#### Восстановление

```bash
# Восстановление из бэкапа
./workers/backup/scripts/restore.sh full_20240115_120000

# Восстановление в другую БД
./workers/backup/scripts/restore.sh full_20240115_120000 test_db
```

### Cron задачи

Добавьте в crontab для автоматических бэкапов:

```cron
# Полный бэкап каждый день в 2:00
0 2 * * * /path/to/workers/backup/scripts/backup.sh full >> /var/log/backup/cron.log 2>&1

# Инкрементальный бэкап каждый час
0 * * * * /path/to/workers/backup/scripts/backup.sh incremental >> /var/log/backup/cron.log 2>&1
```

## Политика хранения (Retention Policy)

Система автоматически управляет хранением бэкапов:

- **Ежедневные бэкапы**: хранятся 7 дней
- **Еженедельные бэкапы**: хранятся 4 недели (воскресенье)
- **Ежемесячные бэкапы**: хранятся 12 месяцев (1-е число)
- **Годовые бэкапы**: хранятся 5 лет (1 января)

### Предпросмотр политики

```python
# Посмотреть, какие бэкапы будут удалены
preview = await retention.preview_retention_policy()
print(f"Будет удалено: {preview['total_to_delete']} бэкапов")
```

### Принудительная очистка

```python
# Удалить все бэкапы старше 30 дней
deleted = await retention.force_cleanup(older_than_days=30)
print(f"Удалено: {deleted} бэкапов")
```

## Мониторинг

### Prometheus метрики

Система экспортирует метрики в формате Prometheus:

```python
metrics = await monitoring.get_prometheus_metrics()
print(metrics)
```

Доступные метрики:
- `backup_total_count` - общее количество бэкапов
- `backup_successful_count` - успешные бэкапы
- `backup_failed_count` - неудачные бэкапы
- `backup_full_count` - полные бэкапы
- `backup_incremental_count` - инкрементальные бэкапы
- `backup_total_size_bytes` - общий размер бэкапов
- `backup_health_status` - статус здоровья (1=healthy, 0=unhealthy)
- `backup_last_timestamp` - время последнего бэкапа

### Алерты

Система отправляет алерты при ошибках:

- **Email** - на указанный адрес
- **Telegram** - в указанный чат

### Ежедневные отчеты

```python
# Отправка ежедневного отчета
await monitoring.send_daily_report()
```

## Восстановление

### Тестовое восстановление

Перед восстановлением в продакшен рекомендуется протестировать:

```python
# Тестовое восстановление в отдельную БД
success = await restore_manager.test_restore(backup_id)
if success:
    print("Бэкап валиден и может быть восстановлен")
```

### Snapshot перед восстановлением

Система автоматически создает snapshot текущей БД перед восстановлением:

```python
# Восстановление с автоматическим snapshot
await restore_manager.restore_from_backup(backup_id)
# Snapshot будет создан автоматически
```

### Откат восстановления

```python
# Откат к предыдущему состоянию
await restore_manager.rollback_restore()
```

## S3/MinIO интеграция

### Загрузка в S3

```python
from workers.backup import S3Storage

s3 = S3Storage()

# Загрузка файла
await s3.upload_file(
    local_path="/backups/full_20240115.sql.gz.enc",
    s3_key="backups/full_20240115/full_20240115.sql.gz.enc"
)
```

### Скачивание из S3

```python
# Скачивание файла
await s3.download_file(
    s3_key="backups/full_20240115/full_20240115.sql.gz.enc",
    local_path="/restore/full_20240115.sql.gz.enc"
)
```

### Список файлов

```python
# Получение списка бэкапов в S3
files = await s3.list_files(prefix="backups/")
for file in files:
    print(f"{file['key']}: {file['size']} bytes")
```

## Troubleshooting

### Ошибка: "pg_dump: command not found"

Установите PostgreSQL клиентские утилиты:

```bash
apt-get install postgresql-client
```

### Ошибка: "ENCRYPTION_KEY не задан"

Убедитесь, что в `.env` файле задан `ENCRYPTION_KEY` (минимум 32 символа):

```env
ENCRYPTION_KEY=your_32_character_encryption_key_here
```

### Ошибка: "S3 bucket не существует"

Создайте bucket вручную или убедитесь, что у пользователя есть права на создание:

```bash
aws s3 mb s3://backups --endpoint-url https://your-s3-endpoint
```

### Бэкапы занимают много места

Проверьте настройки сжатия и retention policy:

```python
# Проверка статистики
stats = await backup_manager.get_backup_statistics()
print(f"Общий размер: {stats['total_size'] / (1024**3):.2f} GB")

# Применение retention policy
await retention.apply_retention_policy()
```

### Восстановление занимает слишком много времени

Увеличьте таймаут в конфигурации:

```env
RESTORE_TIMEOUT=7200  # 2 часа
```

## Безопасность

### Шифрование

Все бэкапы шифруются с помощью AES-256:

```python
# Ключ должен быть минимум 32 символа
ENCRYPTION_KEY=your_very_long_and_secure_encryption_key_here_32_chars_minimum
```

### Хранение ключей

**Важно**: Никогда не храните ключи шифрования в репозитории!

Используйте:
- Переменные окружения
- Секреты Kubernetes
- AWS Secrets Manager
- HashiCorp Vault

### Права доступа

Ограничьте доступ к директории бэкапов:

```bash
chmod 700 /backups
chown postgres:postgres /backups
```

## Производительность

### Multipart upload

Для больших файлов (>100MB) автоматически используется multipart upload:

```env
MULTIPART_THRESHOLD=104857600  # 100MB
MULTIPART_CHUNKSIZE=10485760   # 10MB
```

### Параллельные загрузки

Настройте количество параллельных загрузок в S3:

```env
MAX_PARALLEL_UPLOADS=3
```

### Уровень сжатия

Баланс между скоростью и размером:

```env
COMPRESSION_LEVEL=6  # 1-9, где 9 - максимальное сжатие
```

## Интеграция с Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Установка PostgreSQL клиента
RUN apt-get update && apt-get install -y postgresql-client

# Копирование кода
COPY workers/backup /app/workers/backup

# Установка зависимостей
RUN pip install boto3 cryptography pydantic aiohttp

WORKDIR /app
```

### docker-compose.yml

```yaml
services:
  backup:
    build: .
    volumes:
      - ./backups:/backups
      - ./.env:/app/.env
    environment:
      - DB_HOST=postgres
      - DB_NAME=2getpro
    depends_on:
      - postgres
```

## Лицензия

MIT License

## Поддержка

Для вопросов и поддержки создайте issue в репозитории проекта.