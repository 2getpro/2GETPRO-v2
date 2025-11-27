#!/bin/bash
#
# Скрипт для создания резервной копии PostgreSQL базы данных
# Использование: ./backup.sh [full|incremental]
#

set -e  # Выход при ошибке
set -u  # Выход при использовании неопределенных переменных

# Загрузка переменных окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Конфигурация
BACKUP_TYPE="${1:-full}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_ID="${BACKUP_TYPE}_${TIMESTAMP}"
LOG_FILE="${BACKUP_DIR}/logs/backup_${TIMESTAMP}.log"

# Создание директорий
mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}/logs"
mkdir -p "${BACKUP_DIR}/metadata"

# Функция логирования
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Функция обработки ошибок
error_exit() {
    log "ERROR: $1"
    exit 1
}

log "========================================="
log "Начало создания резервной копии"
log "Тип: ${BACKUP_TYPE}"
log "ID: ${BACKUP_ID}"
log "========================================="

# Проверка переменных окружения
if [ -z "${DB_HOST:-}" ] || [ -z "${DB_NAME:-}" ] || [ -z "${DB_USER:-}" ] || [ -z "${DB_PASSWORD:-}" ]; then
    error_exit "Не заданы обязательные переменные окружения (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD)"
fi

# Экспорт пароля для PostgreSQL
export PGPASSWORD="${DB_PASSWORD}"

if [ "${BACKUP_TYPE}" = "full" ]; then
    log "Создание полного бэкапа..."
    
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_ID}.sql"
    
    # Создание дампа базы данных
    log "Выполнение pg_dump..."
    pg_dump -h "${DB_HOST}" \
            -p "${DB_PORT:-5432}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            -F c \
            -f "${BACKUP_FILE}" || error_exit "Ошибка pg_dump"
    
    log "Дамп создан: ${BACKUP_FILE}"
    
    # Сжатие
    if [ "${COMPRESSION_ENABLED:-true}" = "true" ]; then
        log "Сжатие бэкапа..."
        gzip -${COMPRESSION_LEVEL:-6} "${BACKUP_FILE}" || error_exit "Ошибка сжатия"
        BACKUP_FILE="${BACKUP_FILE}.gz"
        log "Бэкап сжат: ${BACKUP_FILE}"
    fi
    
    # Шифрование
    if [ "${ENCRYPTION_ENABLED:-true}" = "true" ]; then
        log "Шифрование бэкапа..."
        if [ -z "${ENCRYPTION_KEY:-}" ]; then
            error_exit "ENCRYPTION_KEY не задан"
        fi
        
        openssl enc -aes-256-cbc -salt \
                -in "${BACKUP_FILE}" \
                -out "${BACKUP_FILE}.enc" \
                -k "${ENCRYPTION_KEY}" || error_exit "Ошибка шифрования"
        
        rm "${BACKUP_FILE}"
        BACKUP_FILE="${BACKUP_FILE}.enc"
        log "Бэкап зашифрован: ${BACKUP_FILE}"
    fi
    
    # Расчет контрольной суммы
    log "Расчет контрольной суммы..."
    CHECKSUM=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')
    log "Контрольная сумма: ${CHECKSUM}"
    
    # Размер файла
    BACKUP_SIZE=$(stat -f%z "${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_FILE}")
    log "Размер бэкапа: ${BACKUP_SIZE} байт"
    
    # Сохранение метаданных
    METADATA_FILE="${BACKUP_DIR}/metadata/${BACKUP_ID}.json"
    cat > "${METADATA_FILE}" <<EOF
{
    "backup_id": "${BACKUP_ID}",
    "type": "full",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S)Z",
    "size": ${BACKUP_SIZE},
    "checksum": "${CHECKSUM}",
    "compressed": ${COMPRESSION_ENABLED:-true},
    "encrypted": ${ENCRYPTION_ENABLED:-true},
    "status": "completed",
    "db_host": "${DB_HOST}",
    "db_name": "${DB_NAME}"
}
EOF
    log "Метаданные сохранены: ${METADATA_FILE}"
    
    # Загрузка в S3
    if [ "${S3_ENABLED:-false}" = "true" ]; then
        log "Загрузка в S3..."
        
        if [ -z "${S3_ENDPOINT:-}" ] || [ -z "${S3_BUCKET:-}" ]; then
            log "WARNING: S3 настройки не полные, пропуск загрузки"
        else
            S3_KEY="backups/${BACKUP_ID}/$(basename ${BACKUP_FILE})"
            
            aws s3 cp "${BACKUP_FILE}" \
                "s3://${S3_BUCKET}/${S3_KEY}" \
                --endpoint-url "${S3_ENDPOINT}" || log "WARNING: Ошибка загрузки в S3"
            
            log "Бэкап загружен в S3: ${S3_KEY}"
        fi
    fi
    
elif [ "${BACKUP_TYPE}" = "incremental" ]; then
    log "Создание инкрементального бэкапа (WAL архивы)..."
    
    WAL_ARCHIVE_DIR="${WAL_ARCHIVE_DIR:-${BACKUP_DIR}/wal}"
    mkdir -p "${WAL_ARCHIVE_DIR}"
    
    # Архивирование WAL файлов
    # Примечание: требует настройки archive_command в postgresql.conf
    log "Архивирование WAL файлов из ${WAL_ARCHIVE_DIR}..."
    
    WAL_COUNT=$(find "${WAL_ARCHIVE_DIR}" -name "*.wal" 2>/dev/null | wc -l)
    log "Найдено WAL файлов: ${WAL_COUNT}"
    
    if [ ${WAL_COUNT} -eq 0 ]; then
        log "Нет новых WAL файлов для архивирования"
    else
        # Сжатие и шифрование WAL файлов
        for WAL_FILE in "${WAL_ARCHIVE_DIR}"/*.wal; do
            if [ -f "${WAL_FILE}" ]; then
                log "Обработка WAL файла: $(basename ${WAL_FILE})"
                
                if [ "${COMPRESSION_ENABLED:-true}" = "true" ]; then
                    gzip "${WAL_FILE}"
                    WAL_FILE="${WAL_FILE}.gz"
                fi
                
                if [ "${ENCRYPTION_ENABLED:-true}" = "true" ]; then
                    openssl enc -aes-256-cbc -salt \
                            -in "${WAL_FILE}" \
                            -out "${WAL_FILE}.enc" \
                            -k "${ENCRYPTION_KEY}"
                    rm "${WAL_FILE}"
                fi
            fi
        done
        
        # Сохранение метаданных
        METADATA_FILE="${BACKUP_DIR}/metadata/${BACKUP_ID}.json"
        cat > "${METADATA_FILE}" <<EOF
{
    "backup_id": "${BACKUP_ID}",
    "type": "incremental",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S)Z",
    "wal_files": ${WAL_COUNT},
    "status": "completed"
}
EOF
        log "Метаданные сохранены: ${METADATA_FILE}"
    fi
    
else
    error_exit "Неизвестный тип бэкапа: ${BACKUP_TYPE}. Используйте 'full' или 'incremental'"
fi

log "========================================="
log "Резервная копия создана успешно"
log "ID: ${BACKUP_ID}"
log "========================================="

# Очистка переменной пароля
unset PGPASSWORD

exit 0