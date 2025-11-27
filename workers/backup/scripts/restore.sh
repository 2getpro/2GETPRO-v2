#!/bin/bash
#
# Скрипт для восстановления PostgreSQL базы данных из резервной копии
# Использование: ./restore.sh <backup_id> [target_db]
#

set -e  # Выход при ошибке
set -u  # Выход при использовании неопределенных переменных

# Загрузка переменных окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Конфигурация
BACKUP_ID="${1:-}"
TARGET_DB="${2:-${DB_NAME}}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RESTORE_DIR="${BACKUP_DIR}/restore"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/logs/restore_${TIMESTAMP}.log"

# Создание директорий
mkdir -p "${RESTORE_DIR}"
mkdir -p "${BACKUP_DIR}/logs"

# Функция логирования
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Функция обработки ошибок
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Проверка аргументов
if [ -z "${BACKUP_ID}" ]; then
    error_exit "Не указан BACKUP_ID. Использование: ./restore.sh <backup_id> [target_db]"
fi

log "========================================="
log "Начало восстановления из резервной копии"
log "Backup ID: ${BACKUP_ID}"
log "Целевая БД: ${TARGET_DB}"
log "========================================="

# Проверка переменных окружения
if [ -z "${DB_HOST:-}" ] || [ -z "${DB_USER:-}" ] || [ -z "${DB_PASSWORD:-}" ]; then
    error_exit "Не заданы обязательные переменные окружения (DB_HOST, DB_USER, DB_PASSWORD)"
fi

# Экспорт пароля для PostgreSQL
export PGPASSWORD="${DB_PASSWORD}"

# Поиск файла бэкапа
log "Поиск файла бэкапа..."
BACKUP_FILE=$(find "${BACKUP_DIR}" -name "${BACKUP_ID}*" -type f | head -n 1)

if [ -z "${BACKUP_FILE}" ]; then
    # Попытка скачать из S3
    if [ "${S3_ENABLED:-false}" = "true" ]; then
        log "Файл не найден локально, попытка скачать из S3..."
        
        if [ -z "${S3_ENDPOINT:-}" ] || [ -z "${S3_BUCKET:-}" ]; then
            error_exit "S3 настройки не полные"
        fi
        
        # Поиск файла в S3
        S3_KEY=$(aws s3 ls "s3://${S3_BUCKET}/backups/${BACKUP_ID}/" \
                --endpoint-url "${S3_ENDPOINT}" \
                --recursive | awk '{print $4}' | head -n 1)
        
        if [ -z "${S3_KEY}" ]; then
            error_exit "Файл бэкапа не найден в S3: ${BACKUP_ID}"
        fi
        
        BACKUP_FILE="${RESTORE_DIR}/$(basename ${S3_KEY})"
        
        log "Скачивание из S3: ${S3_KEY}"
        aws s3 cp "s3://${S3_BUCKET}/${S3_KEY}" \
            "${BACKUP_FILE}" \
            --endpoint-url "${S3_ENDPOINT}" || error_exit "Ошибка скачивания из S3"
        
        log "Файл скачан: ${BACKUP_FILE}"
    else
        error_exit "Файл бэкапа не найден: ${BACKUP_ID}"
    fi
fi

log "Найден файл бэкапа: ${BACKUP_FILE}"

# Копирование файла в restore директорию для обработки
WORK_FILE="${RESTORE_DIR}/$(basename ${BACKUP_FILE})"
if [ "${BACKUP_FILE}" != "${WORK_FILE}" ]; then
    cp "${BACKUP_FILE}" "${WORK_FILE}"
    BACKUP_FILE="${WORK_FILE}"
fi

# Расшифровка
if [[ "${BACKUP_FILE}" == *.enc ]]; then
    log "Расшифровка бэкапа..."
    
    if [ -z "${ENCRYPTION_KEY:-}" ]; then
        error_exit "ENCRYPTION_KEY не задан"
    fi
    
    DECRYPTED_FILE="${BACKUP_FILE%.enc}"
    
    openssl enc -aes-256-cbc -d \
            -in "${BACKUP_FILE}" \
            -out "${DECRYPTED_FILE}" \
            -k "${ENCRYPTION_KEY}" || error_exit "Ошибка расшифровки"
    
    rm "${BACKUP_FILE}"
    BACKUP_FILE="${DECRYPTED_FILE}"
    log "Бэкап расшифрован: ${BACKUP_FILE}"
fi

# Распаковка
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    log "Распаковка бэкапа..."
    
    gunzip "${BACKUP_FILE}" || error_exit "Ошибка распаковки"
    BACKUP_FILE="${BACKUP_FILE%.gz}"
    log "Бэкап распакован: ${BACKUP_FILE}"
fi

# Создание snapshot перед восстановлением
if [ "${RESTORE_SNAPSHOT_ENABLED:-true}" = "true" ] && [ "${TARGET_DB}" = "${DB_NAME}" ]; then
    log "Создание snapshot текущей БД..."
    SNAPSHOT_DB="${DB_NAME}_snapshot_${TIMESTAMP}"
    
    createdb -h "${DB_HOST}" \
             -p "${DB_PORT:-5432}" \
             -U "${DB_USER}" \
             -T "${DB_NAME}" \
             "${SNAPSHOT_DB}" || log "WARNING: Не удалось создать snapshot"
    
    if [ $? -eq 0 ]; then
        log "Snapshot создан: ${SNAPSHOT_DB}"
        echo "${SNAPSHOT_DB}" > "${RESTORE_DIR}/last_snapshot.txt"
    fi
fi

# Проверка формата файла
FILE_TYPE=$(file -b "${BACKUP_FILE}")
log "Тип файла: ${FILE_TYPE}"

# Восстановление базы данных
log "Восстановление базы данных ${TARGET_DB}..."

if [[ "${BACKUP_FILE}" == *.sql ]]; then
    # SQL формат
    log "Использование psql для восстановления..."
    
    psql -h "${DB_HOST}" \
         -p "${DB_PORT:-5432}" \
         -U "${DB_USER}" \
         -d "${TARGET_DB}" \
         -f "${BACKUP_FILE}" || error_exit "Ошибка восстановления через psql"
    
else
    # Custom формат (pg_dump -Fc)
    log "Использование pg_restore для восстановления..."
    
    pg_restore -h "${DB_HOST}" \
               -p "${DB_PORT:-5432}" \
               -U "${DB_USER}" \
               -d "${TARGET_DB}" \
               --clean \
               --if-exists \
               "${BACKUP_FILE}" || error_exit "Ошибка восстановления через pg_restore"
fi

log "База данных восстановлена"

# Проверка восстановленной БД
if [ "${RESTORE_VERIFY_ENABLED:-true}" = "true" ]; then
    log "Проверка восстановленной БД..."
    
    psql -h "${DB_HOST}" \
         -p "${DB_PORT:-5432}" \
         -U "${DB_USER}" \
         -d "${TARGET_DB}" \
         -c "SELECT 1;" > /dev/null || error_exit "Проверка БД не прошла"
    
    log "Проверка БД успешна"
fi

# Очистка временных файлов
log "Очистка временных файлов..."
rm -f "${BACKUP_FILE}"

log "========================================="
log "Восстановление завершено успешно"
log "Backup ID: ${BACKUP_ID}"
log "Целевая БД: ${TARGET_DB}"
log "========================================="

# Очистка переменной пароля
unset PGPASSWORD

exit 0