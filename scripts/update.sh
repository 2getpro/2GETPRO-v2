#!/bin/bash
################################################################################
# Скрипт обновления 2GETPRO v2
# Версия: 1.0
# Автор: 2GETPRO Team
################################################################################

set -e

################################################################################
# ЦВЕТНОЙ ВЫВОД
################################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

CHECK_MARK="${GREEN}✓${NC}"
CROSS_MARK="${RED}✗${NC}"
INFO_MARK="${BLUE}ℹ${NC}"
WARN_MARK="${YELLOW}⚠${NC}"

################################################################################
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
################################################################################

PROJECT_DIR="/opt/2getpro-v2"
SYSTEM_USER="2getpro"
LOG_FILE="/var/log/2getpro-update.log"
SERVICE_NAME="2getpro-v2.service"
BACKUP_DIR="/opt/2getpro-backups"

# Флаги
SKIP_BACKUP=false
SKIP_MIGRATIONS=false
FORCE_UPDATE=false
AUTO_RESTART=true
GIT_BRANCH="main"

################################################################################
# ФУНКЦИИ ЛОГИРОВАНИЯ
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

print_header() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${WHITE}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
    log "INFO" "$1"
}

print_success() {
    echo -e "${CHECK_MARK} ${GREEN}$1${NC}"
    log "SUCCESS" "$1"
}

print_error() {
    echo -e "${CROSS_MARK} ${RED}$1${NC}"
    log "ERROR" "$1"
}

print_warning() {
    echo -e "${WARN_MARK} ${YELLOW}$1${NC}"
    log "WARNING" "$1"
}

print_info() {
    echo -e "${INFO_MARK} ${CYAN}$1${NC}"
    log "INFO" "$1"
}

################################################################################
# ФУНКЦИИ ПРОВЕРКИ
################################################################################

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Этот скрипт должен быть запущен с правами root"
        print_info "Используйте: sudo $0"
        exit 1
    fi
}

check_installation() {
    print_step "Проверка установки..."
    
    if [[ ! -d "$PROJECT_DIR" ]]; then
        print_error "2GETPRO v2 не установлен"
        print_info "Директория $PROJECT_DIR не найдена"
        exit 1
    fi
    
    if [[ ! -d "$PROJECT_DIR/.git" ]]; then
        print_error "Директория не является git-репозиторием"
        print_info "Обновление невозможно"
        exit 1
    fi
    
    if ! systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        print_warning "Сервис $SERVICE_NAME не найден"
    fi
    
    print_success "Установка обнаружена"
}

check_git_status() {
    print_step "Проверка состояния git-репозитория..."
    
    cd "$PROJECT_DIR"
    
    # Проверка наличия изменений
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        print_warning "Обнаружены локальные изменения в репозитории"
        
        if [[ "$FORCE_UPDATE" == false ]]; then
            echo
            echo -e "${YELLOW}Измененные файлы:${NC}"
            git status --short
            echo
            
            read -p "Сохранить изменения в stash? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git stash save "Auto-stash before update $(date +%Y%m%d_%H%M%S)" >> "$LOG_FILE" 2>&1
                print_success "Изменения сохранены в stash"
            else
                print_warning "Изменения будут перезаписаны при обновлении"
            fi
        fi
    else
        print_success "Локальных изменений не обнаружено"
    fi
}

get_current_version() {
    cd "$PROJECT_DIR"
    local current_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    echo "$current_branch:$current_commit"
}

check_updates_available() {
    print_step "Проверка доступных обновлений..."
    
    cd "$PROJECT_DIR"
    
    # Получение информации о удаленном репозитории
    git fetch origin >> "$LOG_FILE" 2>&1
    
    local local_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse origin/$GIT_BRANCH)
    
    if [[ "$local_commit" == "$remote_commit" ]]; then
        print_info "Установлена последняя версия"
        
        if [[ "$FORCE_UPDATE" == false ]]; then
            read -p "Продолжить обновление зависимостей? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Обновление отменено"
                exit 0
            fi
        fi
    else
        print_success "Доступны обновления"
        
        # Показываем список изменений
        echo
        echo -e "${CYAN}Новые коммиты:${NC}"
        git log --oneline --decorate --graph HEAD..origin/$GIT_BRANCH | head -10
        echo
    fi
}

################################################################################
# ФУНКЦИИ РЕЗЕРВНОГО КОПИРОВАНИЯ
################################################################################

create_backup() {
    if [[ "$SKIP_BACKUP" == true ]]; then
        print_info "Пропуск создания резервной копии"
        return
    fi
    
    print_step "Создание резервной копии..."
    
    local backup_name="2getpro-backup-$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$backup_path"
    
    # Копирование конфигурации
    if [[ -f "$PROJECT_DIR/.env.production" ]]; then
        cp "$PROJECT_DIR/.env.production" "$backup_path/"
    fi
    
    # Копирование пользовательских файлов
    if [[ -d "$PROJECT_DIR/logs" ]]; then
        cp -r "$PROJECT_DIR/logs" "$backup_path/" 2>/dev/null || true
    fi
    
    # Резервная копия базы данных
    if [[ -f "$PROJECT_DIR/.env.production" ]]; then
        source "$PROJECT_DIR/.env.production"
        
        if [[ -n "$DB_NAME" ]]; then
            print_info "Создание резервной копии базы данных..."
            sudo -u postgres pg_dump "$DB_NAME" > "$backup_path/database.sql" 2>> "$LOG_FILE" || {
                print_warning "Не удалось создать резервную копию БД"
            }
        fi
    fi
    
    # Создание информационного файла
    cat > "$backup_path/backup_info.txt" << EOF
Резервная копия 2GETPRO v2
Дата создания: $(date)
Версия до обновления: $(get_current_version)
Директория: $PROJECT_DIR
EOF
    
    # Сжатие резервной копии
    cd "$BACKUP_DIR"
    tar -czf "${backup_name}.tar.gz" "$backup_name" >> "$LOG_FILE" 2>&1
    rm -rf "$backup_name"
    
    print_success "Резервная копия создана: $BACKUP_DIR/${backup_name}.tar.gz"
    
    # Очистка старых резервных копий (оставляем последние 5)
    ls -t "$BACKUP_DIR"/2getpro-backup-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
}

################################################################################
# ФУНКЦИИ ОБНОВЛЕНИЯ
################################################################################

stop_service() {
    print_step "Остановка сервиса..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME" >> "$LOG_FILE" 2>&1
        
        # Ждем полной остановки
        local timeout=30
        local counter=0
        while systemctl is-active --quiet "$SERVICE_NAME"; do
            if [[ $counter -ge $timeout ]]; then
                print_error "Не удалось остановить сервис за ${timeout}с"
                exit 1
            fi
            sleep 1
            counter=$((counter + 1))
        done
        
        print_success "Сервис остановлен"
    else
        print_info "Сервис уже остановлен"
    fi
}

update_code() {
    print_step "Обновление кода из git..."
    
    cd "$PROJECT_DIR"
    
    # Переключение на нужную ветку
    git checkout "$GIT_BRANCH" >> "$LOG_FILE" 2>&1
    
    # Получение обновлений
    git pull origin "$GIT_BRANCH" >> "$LOG_FILE" 2>&1
    
    local new_version=$(get_current_version)
    print_success "Код обновлен до версии: $new_version"
}

update_dependencies() {
    print_step "Обновление Python зависимостей..."
    
    sudo -u "$SYSTEM_USER" bash -c "
        cd '$PROJECT_DIR'
        source venv/bin/activate
        pip install --upgrade pip setuptools wheel >> '$LOG_FILE' 2>&1
        pip install -r requirements.txt --upgrade >> '$LOG_FILE' 2>&1
    "
    
    print_success "Зависимости обновлены"
}

apply_migrations() {
    if [[ "$SKIP_MIGRATIONS" == true ]]; then
        print_info "Пропуск применения миграций"
        return
    fi
    
    print_step "Применение миграций базы данных..."
    
    sudo -u "$SYSTEM_USER" bash -c "
        cd '$PROJECT_DIR'
        source venv/bin/activate
        python db/migrator.py >> '$LOG_FILE' 2>&1
    " || {
        print_error "Ошибка при применении миграций"
        print_info "Проверьте логи: $LOG_FILE"
        return 1
    }
    
    print_success "Миграции применены"
}

update_systemd_service() {
    print_step "Обновление systemd сервиса..."
    
    local service_file="$PROJECT_DIR/infrastructure/systemd/2getpro-v2.service"
    
    if [[ -f "$service_file" ]]; then
        # Проверяем, изменился ли файл сервиса
        if ! cmp -s "$service_file" "/etc/systemd/system/$SERVICE_NAME"; then
            cp "$service_file" "/etc/systemd/system/"
            systemctl daemon-reload >> "$LOG_FILE" 2>&1
            print_success "Файл сервиса обновлен"
        else
            print_info "Файл сервиса не изменился"
        fi
    else
        print_warning "Файл сервиса не найден в репозитории"
    fi
}

update_scripts() {
    print_step "Обновление скриптов..."
    
    local scripts_dir="$PROJECT_DIR/infrastructure/systemd/scripts"
    
    if [[ -d "$scripts_dir" ]]; then
        cp "$scripts_dir"/*.sh "$PROJECT_DIR/scripts/" 2>/dev/null || true
        chmod +x "$PROJECT_DIR/scripts"/*.sh
        print_success "Скрипты обновлены"
    else
        print_info "Директория скриптов не найдена"
    fi
}

start_service() {
    if [[ "$AUTO_RESTART" == false ]]; then
        print_info "Автозапуск отключен"
        return
    fi
    
    print_step "Запуск сервиса..."
    
    systemctl start "$SERVICE_NAME" >> "$LOG_FILE" 2>&1
    
    # Ждем запуска
    sleep 5
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Сервис запущен"
    else
        print_error "Не удалось запустить сервис"
        print_info "Проверьте логи: journalctl -u $SERVICE_NAME -n 50"
        return 1
    fi
}

################################################################################
# ФУНКЦИИ ПРОВЕРКИ ПОСЛЕ ОБНОВЛЕНИЯ
################################################################################

verify_update() {
    print_header "ПРОВЕРКА ОБНОВЛЕНИЯ"
    
    local all_ok=true
    
    # Проверка статуса сервиса
    print_step "Проверка статуса сервиса..."
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Сервис работает"
    else
        print_error "Сервис не запущен"
        all_ok=false
    fi
    
    # Проверка логов на ошибки
    print_step "Проверка логов..."
    if journalctl -u "$SERVICE_NAME" -n 20 --since "5 minutes ago" | grep -qi "error"; then
        print_warning "Обнаружены ошибки в логах"
        echo
        echo -e "${YELLOW}Последние ошибки:${NC}"
        journalctl -u "$SERVICE_NAME" -n 10 --since "5 minutes ago" | grep -i "error"
        echo
        all_ok=false
    else
        print_success "Критических ошибок не обнаружено"
    fi
    
    # Проверка версии
    print_step "Проверка версии..."
    local current_version=$(get_current_version)
    print_info "Текущая версия: $current_version"
    
    if [[ "$all_ok" == true ]]; then
        print_success "Все проверки пройдены успешно!"
        return 0
    else
        print_warning "Некоторые проверки не пройдены"
        return 1
    fi
}

################################################################################
# ФУНКЦИЯ ОТКАТА
################################################################################

rollback_update() {
    print_header "ОТКАТ ОБНОВЛЕНИЯ"
    print_warning "Выполняется откат к предыдущей версии..."
    
    cd "$PROJECT_DIR"
    
    # Остановка сервиса
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Откат git
    git reset --hard HEAD~1 >> "$LOG_FILE" 2>&1
    
    # Восстановление зависимостей
    sudo -u "$SYSTEM_USER" bash -c "
        cd '$PROJECT_DIR'
        source venv/bin/activate
        pip install -r requirements.txt >> '$LOG_FILE' 2>&1
    "
    
    # Запуск сервиса
    systemctl start "$SERVICE_NAME" >> "$LOG_FILE" 2>&1
    
    print_info "Откат завершен"
    print_info "Для восстановления из резервной копии используйте последний backup"
}

################################################################################
# ФУНКЦИЯ ВЫВОДА ИНФОРМАЦИИ
################################################################################

show_summary() {
    print_header "ОБНОВЛЕНИЕ ЗАВЕРШЕНО"
    
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${WHITE}2GETPRO v2 успешно обновлен!${NC}                                ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    echo -e "${CYAN}📋 Информация об обновлении:${NC}"
    echo -e "   Версия: ${WHITE}$(get_current_version)${NC}"
    echo -e "   Дата: ${WHITE}$(date)${NC}"
    echo
    
    if [[ "$SKIP_BACKUP" == false ]]; then
        echo -e "${CYAN}💾 Резервная копия:${NC}"
        echo -e "   Сохранена в: ${WHITE}$BACKUP_DIR${NC}"
        echo
    fi
    
    echo -e "${CYAN}🎮 Управление ботом:${NC}"
    echo -e "   Статус:      ${WHITE}systemctl status $SERVICE_NAME${NC}"
    echo -e "   Перезапуск:  ${WHITE}systemctl restart $SERVICE_NAME${NC}"
    echo -e "   Логи:        ${WHITE}journalctl -u $SERVICE_NAME -f${NC}"
    echo
    
    echo -e "${CYAN}📝 Что было обновлено:${NC}"
    echo -e "   ${CHECK_MARK} Код из git-репозитория"
    echo -e "   ${CHECK_MARK} Python зависимости"
    
    if [[ "$SKIP_MIGRATIONS" == false ]]; then
        echo -e "   ${CHECK_MARK} Миграции базы данных"
    fi
    
    echo -e "   ${CHECK_MARK} Systemd сервис"
    echo -e "   ${CHECK_MARK} Скрипты"
    echo
    
    echo -e "${CYAN}🔄 Откат обновления:${NC}"
    echo -e "   В случае проблем используйте резервную копию"
    echo -e "   или выполните: ${WHITE}git reset --hard HEAD~1${NC}"
    echo
    
    echo -e "${GREEN}✨ Обновление завершено успешно!${NC}"
    echo
}

################################################################################
# ОБРАБОТКА ПАРАМЕТРОВ
################################################################################

show_usage() {
    cat << EOF
Использование: $0 [ОПЦИИ]

Скрипт обновления 2GETPRO v2

ОПЦИИ:
    -h, --help              Показать эту справку
    -f, --force             Принудительное обновление
    -b, --branch BRANCH     Обновить из указанной ветки (по умолчанию: main)
    --skip-backup           Не создавать резервную копию
    --skip-migrations       Не применять миграции
    --no-restart            Не перезапускать сервис автоматически
    --check-only            Только проверить наличие обновлений

ПРИМЕРЫ:
    # Стандартное обновление
    sudo $0

    # Обновление без резервной копии
    sudo $0 --skip-backup

    # Обновление из ветки develop
    sudo $0 --branch develop

    # Проверка обновлений без установки
    sudo $0 --check-only

    # Принудительное обновление без перезапуска
    sudo $0 --force --no-restart

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--force)
                FORCE_UPDATE=true
                shift
                ;;
            -b|--branch)
                GIT_BRANCH="$2"
                shift 2
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --no-restart)
                AUTO_RESTART=false
                shift
                ;;
            --check-only)
                check_root
                check_installation
                check_updates_available
                exit 0
                ;;
            *)
                print_error "Неизвестная опция: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

################################################################################
# ГЛАВНАЯ ФУНКЦИЯ
################################################################################

main() {
    # Инициализация лога
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    
    log "INFO" "=========================================="
    log "INFO" "Начало обновления 2GETPRO v2"
    log "INFO" "=========================================="
    
    # Заголовок
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              2GETPRO v2 - Скрипт обновления                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
    
    # Проверки
    check_root
    check_installation
    
    # Показываем текущую версию
    local old_version=$(get_current_version)
    print_info "Текущая версия: $old_version"
    echo
    
    check_git_status
    check_updates_available
    
    # Подтверждение обновления
    if [[ "$FORCE_UPDATE" == false ]]; then
        echo
        read -p "Продолжить обновление? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Обновление отменено"
            exit 0
        fi
    fi
    
    # Создание резервной копии
    create_backup
    
    # Обновление
    print_header "ОБНОВЛЕНИЕ КОМПОНЕНТОВ"
    
    stop_service
    update_code
    update_dependencies
    apply_migrations || {
        print_error "Ошибка при применении миграций"
        read -p "Продолжить обновление? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            rollback_update
            exit 1
        fi
    }
    update_systemd_service
    update_scripts
    start_service
    
    # Проверка
    if ! verify_update; then
        print_warning "Обнаружены проблемы после обновления"
        
        if [[ "$FORCE_UPDATE" == false ]]; then
            read -p "Выполнить откат? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rollback_update
                exit 1
            fi
        fi
    fi
    
    # Итоги
    show_summary
    
    log "INFO" "Обновление завершено успешно"
}

################################################################################
# ОБРАБОТКА ОШИБОК
################################################################################

trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_number=$2
    
    print_error "Ошибка на строке $line_number (код: $exit_code)"
    log "ERROR" "Ошибка на строке $line_number (код: $exit_code)"
    
    if [[ "$FORCE_UPDATE" == false ]]; then
        read -p "Выполнить откат обновления? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rollback_update
        fi
    fi
    
    exit $exit_code
}

################################################################################
# ТОЧКА ВХОДА
################################################################################

parse_arguments "$@"
main

exit 0