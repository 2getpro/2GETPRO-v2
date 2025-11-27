#!/bin/bash
################################################################################
# Скрипт удаления 2GETPRO v2
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
LOG_FILE="/var/log/2getpro-uninstall.log"
SERVICE_NAME="2getpro-v2.service"

# Флаги
REMOVE_DATABASE=false
REMOVE_USER=false
REMOVE_LOGS=false
FORCE_MODE=false
KEEP_BACKUPS=true

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
    
    local found=false
    
    if [[ -d "$PROJECT_DIR" ]]; then
        print_info "Найдена директория: $PROJECT_DIR"
        found=true
    fi
    
    if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        print_info "Найден сервис: $SERVICE_NAME"
        found=true
    fi
    
    if id "$SYSTEM_USER" &>/dev/null; then
        print_info "Найден пользователь: $SYSTEM_USER"
        found=true
    fi
    
    if [[ "$found" == false ]]; then
        print_warning "2GETPRO v2 не установлен или уже удален"
        exit 0
    fi
    
    print_success "Установка обнаружена"
}

################################################################################
# ФУНКЦИИ УДАЛЕНИЯ
################################################################################

stop_service() {
    print_step "Остановка сервиса..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME" >> "$LOG_FILE" 2>&1
        print_success "Сервис остановлен"
    else
        print_info "Сервис уже остановлен"
    fi
}

disable_service() {
    print_step "Отключение автозапуска сервиса..."
    
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME" >> "$LOG_FILE" 2>&1
        print_success "Автозапуск отключен"
    else
        print_info "Автозапуск уже отключен"
    fi
}

remove_service_file() {
    print_step "Удаление файла сервиса..."
    
    local service_file="/etc/systemd/system/$SERVICE_NAME"
    
    if [[ -f "$service_file" ]]; then
        rm -f "$service_file"
        systemctl daemon-reload >> "$LOG_FILE" 2>&1
        print_success "Файл сервиса удален"
    else
        print_info "Файл сервиса не найден"
    fi
}

create_backup() {
    if [[ "$KEEP_BACKUPS" == false ]]; then
        return
    fi
    
    print_step "Создание резервной копии конфигурации..."
    
    local backup_dir="/opt/2getpro-backups"
    local backup_name="2getpro-backup-$(date +%Y%m%d_%H%M%S)"
    local backup_path="$backup_dir/$backup_name"
    
    mkdir -p "$backup_dir"
    
    if [[ -f "$PROJECT_DIR/.env.production" ]]; then
        mkdir -p "$backup_path"
        cp "$PROJECT_DIR/.env.production" "$backup_path/"
        
        # Создание информационного файла
        cat > "$backup_path/backup_info.txt" << EOF
Резервная копия 2GETPRO v2
Дата создания: $(date)
Директория: $PROJECT_DIR
Пользователь: $SYSTEM_USER
EOF
        
        print_success "Резервная копия создана: $backup_path"
        print_info "Сохраните эту копию для возможного восстановления"
    else
        print_warning "Файл конфигурации не найден, резервная копия не создана"
    fi
}

remove_project_directory() {
    print_step "Удаление директории проекта..."
    
    if [[ ! -d "$PROJECT_DIR" ]]; then
        print_info "Директория проекта не найдена"
        return
    fi
    
    # Показываем размер директории
    local dir_size=$(du -sh "$PROJECT_DIR" 2>/dev/null | cut -f1)
    print_info "Размер директории: $dir_size"
    
    if [[ "$FORCE_MODE" == false ]]; then
        read -p "Удалить директорию $PROJECT_DIR? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Директория проекта сохранена"
            return
        fi
    fi
    
    rm -rf "$PROJECT_DIR"
    print_success "Директория проекта удалена"
}

remove_system_user() {
    if [[ "$REMOVE_USER" == false ]]; then
        print_info "Пропуск удаления пользователя (используйте --remove-user)"
        return
    fi
    
    print_step "Удаление системного пользователя..."
    
    if ! id "$SYSTEM_USER" &>/dev/null; then
        print_info "Пользователь не найден"
        return
    fi
    
    if [[ "$FORCE_MODE" == false ]]; then
        read -p "Удалить пользователя $SYSTEM_USER? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Пользователь сохранен"
            return
        fi
    fi
    
    userdel -r "$SYSTEM_USER" >> "$LOG_FILE" 2>&1 || true
    print_success "Пользователь удален"
}

remove_database() {
    if [[ "$REMOVE_DATABASE" == false ]]; then
        print_info "Пропуск удаления базы данных (используйте --remove-database)"
        return
    fi
    
    print_step "Удаление базы данных..."
    
    # Попытка получить имя БД из конфигурации
    local db_name=""
    local db_user=""
    
    if [[ -f "$PROJECT_DIR/.env.production" ]]; then
        db_name=$(grep "^DB_NAME=" "$PROJECT_DIR/.env.production" | cut -d'=' -f2)
        db_user=$(grep "^DB_USER=" "$PROJECT_DIR/.env.production" | cut -d'=' -f2)
    fi
    
    if [[ -z "$db_name" ]]; then
        print_warning "Не удалось определить имя базы данных"
        read -p "Введите имя базы данных для удаления (или Enter для пропуска): " db_name
        if [[ -z "$db_name" ]]; then
            return
        fi
    fi
    
    print_warning "ВНИМАНИЕ: Будет удалена база данных '$db_name'"
    print_warning "Все данные будут потеряны безвозвратно!"
    
    if [[ "$FORCE_MODE" == false ]]; then
        read -p "Вы уверены? Введите 'DELETE' для подтверждения: " confirmation
        if [[ "$confirmation" != "DELETE" ]]; then
            print_info "Удаление базы данных отменено"
            return
        fi
    fi
    
    # Удаление базы данных
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS $db_name;" >> "$LOG_FILE" 2>&1 || true
    
    # Удаление пользователя БД
    if [[ -n "$db_user" ]]; then
        sudo -u postgres psql -c "DROP USER IF EXISTS $db_user;" >> "$LOG_FILE" 2>&1 || true
    fi
    
    print_success "База данных удалена"
}

remove_logs() {
    if [[ "$REMOVE_LOGS" == false ]]; then
        print_info "Пропуск удаления логов (используйте --remove-logs)"
        return
    fi
    
    print_step "Удаление логов..."
    
    # Удаление логов из journald
    journalctl --vacuum-time=1s --unit="$SERVICE_NAME" >> "$LOG_FILE" 2>&1 || true
    
    # Удаление директории логов
    if [[ -d "/var/log/2getpro" ]]; then
        rm -rf /var/log/2getpro
        print_success "Логи удалены"
    else
        print_info "Директория логов не найдена"
    fi
}

remove_nginx_config() {
    print_step "Удаление конфигурации Nginx..."
    
    local nginx_config="/etc/nginx/sites-available/2getpro-v2"
    local nginx_enabled="/etc/nginx/sites-enabled/2getpro-v2"
    
    if [[ -f "$nginx_enabled" ]]; then
        rm -f "$nginx_enabled"
        print_info "Удалена ссылка из sites-enabled"
    fi
    
    if [[ -f "$nginx_config" ]]; then
        rm -f "$nginx_config"
        print_success "Конфигурация Nginx удалена"
        
        # Перезагрузка Nginx если он запущен
        if systemctl is-active --quiet nginx; then
            nginx -t >> "$LOG_FILE" 2>&1 && systemctl reload nginx >> "$LOG_FILE" 2>&1
            print_info "Nginx перезагружен"
        fi
    else
        print_info "Конфигурация Nginx не найдена"
    fi
}

remove_ssl_certificates() {
    print_step "Проверка SSL сертификатов..."
    
    if ! command -v certbot &> /dev/null; then
        print_info "Certbot не установлен"
        return
    fi
    
    # Попытка получить домен из конфигурации
    local domain=""
    if [[ -f "$PROJECT_DIR/.env.production" ]]; then
        domain=$(grep "^WEBHOOK_DOMAIN=" "$PROJECT_DIR/.env.production" | cut -d'=' -f2)
    fi
    
    if [[ -z "$domain" ]]; then
        print_info "Домен не найден в конфигурации"
        return
    fi
    
    # Проверка наличия сертификата
    if certbot certificates 2>/dev/null | grep -q "$domain"; then
        print_warning "Найден SSL сертификат для домена: $domain"
        
        if [[ "$FORCE_MODE" == false ]]; then
            read -p "Удалить SSL сертификат? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "SSL сертификат сохранен"
                return
            fi
        fi
        
        certbot delete --cert-name "$domain" --non-interactive >> "$LOG_FILE" 2>&1
        print_success "SSL сертификат удален"
    else
        print_info "SSL сертификат не найден"
    fi
}

################################################################################
# ФУНКЦИЯ ВЫВОДА ИНФОРМАЦИИ
################################################################################

show_summary() {
    print_header "ИТОГИ УДАЛЕНИЯ"
    
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${WHITE}2GETPRO v2 успешно удален${NC}                                   ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    echo -e "${CYAN}📋 Что было удалено:${NC}"
    echo -e "   ${CHECK_MARK} Сервис systemd"
    echo -e "   ${CHECK_MARK} Директория проекта"
    
    if [[ "$REMOVE_USER" == true ]]; then
        echo -e "   ${CHECK_MARK} Системный пользователь"
    else
        echo -e "   ${WARN_MARK} Системный пользователь (сохранен)"
    fi
    
    if [[ "$REMOVE_DATABASE" == true ]]; then
        echo -e "   ${CHECK_MARK} База данных"
    else
        echo -e "   ${WARN_MARK} База данных (сохранена)"
    fi
    
    if [[ "$REMOVE_LOGS" == true ]]; then
        echo -e "   ${CHECK_MARK} Логи"
    else
        echo -e "   ${WARN_MARK} Логи (сохранены)"
    fi
    
    echo
    
    if [[ "$KEEP_BACKUPS" == true ]]; then
        echo -e "${CYAN}💾 Резервные копии:${NC}"
        echo -e "   Сохранены в: ${WHITE}/opt/2getpro-backups${NC}"
        echo
    fi
    
    echo -e "${CYAN}📝 Примечания:${NC}"
    echo -e "   • PostgreSQL и Redis остались установленными"
    echo -e "   • Nginx остался установленным (если был)"
    echo -e "   • Системные пакеты не были удалены"
    echo
    
    echo -e "${CYAN}🔄 Повторная установка:${NC}"
    echo -e "   Для повторной установки используйте: ${WHITE}sudo ./install.sh${NC}"
    echo
    
    echo -e "${GREEN}✨ Спасибо за использование 2GETPRO v2!${NC}"
    echo
}

################################################################################
# ОБРАБОТКА ПАРАМЕТРОВ
################################################################################

show_usage() {
    cat << EOF
Использование: $0 [ОПЦИИ]

Скрипт удаления 2GETPRO v2

ОПЦИИ:
    -h, --help              Показать эту справку
    -f, --force             Принудительное удаление без подтверждений
    --remove-database       Удалить базу данных PostgreSQL
    --remove-user           Удалить системного пользователя
    --remove-logs           Удалить все логи
    --no-backup             Не создавать резервную копию конфигурации
    --full                  Полное удаление (все опции выше)

ПРИМЕРЫ:
    # Базовое удаление (с подтверждениями)
    sudo $0

    # Полное удаление без подтверждений
    sudo $0 --full --force

    # Удаление с сохранением базы данных
    sudo $0 --remove-user --remove-logs

    # Удаление только файлов проекта
    sudo $0 --force

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
                FORCE_MODE=true
                shift
                ;;
            --remove-database)
                REMOVE_DATABASE=true
                shift
                ;;
            --remove-user)
                REMOVE_USER=true
                shift
                ;;
            --remove-logs)
                REMOVE_LOGS=true
                shift
                ;;
            --no-backup)
                KEEP_BACKUPS=false
                shift
                ;;
            --full)
                REMOVE_DATABASE=true
                REMOVE_USER=true
                REMOVE_LOGS=true
                shift
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
    log "INFO" "Начало удаления 2GETPRO v2"
    log "INFO" "=========================================="
    
    # Заголовок
    clear
    echo -e "${RED}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              2GETPRO v2 - Скрипт удаления                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
    
    # Проверки
    check_root
    check_installation
    
    # Предупреждение
    print_warning "ВНИМАНИЕ: Вы собираетесь удалить 2GETPRO v2"
    echo
    echo -e "${YELLOW}Будет удалено:${NC}"
    echo -e "  • Сервис systemd"
    echo -e "  • Директория проекта ($PROJECT_DIR)"
    
    if [[ "$REMOVE_DATABASE" == true ]]; then
        echo -e "  • ${RED}База данных PostgreSQL${NC}"
    fi
    
    if [[ "$REMOVE_USER" == true ]]; then
        echo -e "  • Системный пользователь ($SYSTEM_USER)"
    fi
    
    if [[ "$REMOVE_LOGS" == true ]]; then
        echo -e "  • Все логи"
    fi
    
    echo
    
    if [[ "$FORCE_MODE" == false ]]; then
        read -p "Продолжить удаление? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Удаление отменено"
            exit 0
        fi
    fi
    
    # Создание резервной копии
    create_backup
    
    # Удаление компонентов
    print_header "УДАЛЕНИЕ КОМПОНЕНТОВ"
    
    stop_service
    disable_service
    remove_service_file
    remove_nginx_config
    remove_ssl_certificates
    remove_project_directory
    remove_system_user
    remove_database
    remove_logs
    
    # Итоги
    show_summary
    
    log "INFO" "Удаление завершено успешно"
}

################################################################################
# ТОЧКА ВХОДА
################################################################################

parse_arguments "$@"
main

exit 0