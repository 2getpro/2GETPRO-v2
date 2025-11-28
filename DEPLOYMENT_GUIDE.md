# 📘 Подробное руководство по развертыванию 2GETPRO v2 на Ubuntu 24.04 LTS

Полное руководство по развертыванию Telegram-бота для продажи VPN-подписок с использованием Docker Compose на Ubuntu 24.04 LTS.

---

## 📋 Содержание

1. [Введение и архитектура](#1-введение-и-архитектура)
2. [Детальный разбор зависимостей](#2-детальный-разбор-зависимостей)
3. [Настройка переменных окружения](#3-настройка-переменных-окружения)
4. [Оптимизированный Docker Compose](#4-оптимизированный-docker-compose)
5. [Пошаговая инструкция по развертыванию](#5-пошаговая-инструкция-по-развертыванию)
6. [Чек-лист функциональности](#6-чек-лист-функциональности)
7. [Troubleshooting](#7-troubleshooting)
8. [Мониторинг и поддержка](#8-мониторинг-и-поддержка)

---

## 1. Введение и архитектура

### 1.1 Описание компонентов

**2GETPRO v2** - автоматизированная система продажи VPN-подписок через Telegram с интеграцией платежных систем и панелей управления.

#### Основные компоненты:

- **Telegram Bot** - основное приложение на Python 3.11+
- **PostgreSQL 15** - реляционная база данных для хранения пользователей, подписок, платежей
- **Redis 7** - кэширование и очереди задач
- **Prometheus** - сбор метрик и мониторинг
- **Grafana** - визуализация метрик и дашборды
- **Nginx** - reverse proxy для webhook'ов (опционально)

### 1.2 Схема взаимодействия сервисов

```mermaid
graph TB
    subgraph "Внешние сервисы"
        TG[Telegram API]
        YK[YooKassa]
        CP[CryptoPay]
        FK[FreeKassa]
        Panel[VPN Panel API]
    end
    
    subgraph "Docker Compose Stack"
        Nginx[Nginx :80,:443]
        Bot1[Bot Instance 1 :8080]
        Bot2[Bot Instance 2 :8080]
        Bot3[Bot Instance 3 :8080]
        PG[(PostgreSQL :5432)]
        RD[(Redis :6379)]
        Prom[Prometheus :9090]
        Graf[Grafana :3000]
    end
    
    subgraph "Мониторинг"
        PGE[PostgreSQL Exporter]
        RDE[Redis Exporter]
        NGE[Nginx Exporter]
    end
    
    TG <-->|Polling/Webhook| Nginx
    Nginx -->|Load Balance| Bot1
    Nginx -->|Load Balance| Bot2
    Nginx -->|Load Balance| Bot3
    
    Bot1 <-->|SQL| PG
    Bot2 <-->|SQL| PG
    Bot3 <-->|SQL| PG
    
    Bot1 <-->|Cache| RD
    Bot2 <-->|Cache| RD
    Bot3 <-->|Cache| RD
    
    Bot1 <-->|Payments| YK
    Bot1 <-->|Payments| CP
    Bot1 <-->|Payments| FK
    Bot1 <-->|API| Panel
    
    Bot1 -->|Metrics| Prom
    Bot2 -->|Metrics| Prom
    Bot3 -->|Metrics| Prom
    PGE -->|Metrics| Prom
    RDE -->|Metrics| Prom
    NGE -->|Metrics| Prom
    
    Graf -->|Query| Prom
    
    style Bot1 fill:#4CAF50
    style Bot2 fill:#4CAF50
    style Bot3 fill:#4CAF50
    style PG fill:#336791
    style RD fill:#DC382D
    style Prom fill:#E6522C
    style Graf fill:#F46800
```

### 1.3 Архитектура потока данных

```mermaid
sequenceDiagram
    participant User as Пользователь
    participant TG as Telegram
    participant Bot as Bot Service
    participant Redis as Redis Cache
    participant DB as PostgreSQL
    participant Payment as Payment Provider
    participant Panel as VPN Panel
    
    User->>TG: /start
    TG->>Bot: Update
    Bot->>Redis: Check cache
    Redis-->>Bot: Cache miss
    Bot->>DB: Get/Create User
    DB-->>Bot: User data
    Bot->>Redis: Cache user
    Bot->>TG: Welcome message
    
    User->>TG: Buy subscription
    TG->>Bot: Callback
    Bot->>Payment: Create payment
    Payment-->>Bot: Payment URL
    Bot->>TG: Payment link
    
    User->>Payment: Pay
    Payment->>Bot: Webhook notification
    Bot->>DB: Create payment record
    Bot->>Panel: Create/Extend subscription
    Panel-->>Bot: Subscription data
    Bot->>DB: Update subscription
    Bot->>TG: Success notification
```

### 1.4 Требования к серверу

#### Минимальные требования:
- **ОС**: Ubuntu 24.04 LTS
- **CPU**: 2 ядра (vCPU)
- **RAM**: 4 GB
- **Диск**: 40 GB SSD
- **Сеть**: 100 Мбит/с

#### Рекомендуемые требования:
- **CPU**: 4 ядра (vCPU)
- **RAM**: 8 GB
- **Диск**: 80 GB NVMe SSD
- **Сеть**: 1 Гбит/с
- **Резервный канал** (для высокой доступности)

#### Требования к сети:
- Открытые порты: 80 (HTTP), 443 (HTTPS)
- Доступ к Telegram API (149.154.160.0/20, 91.108.4.0/22)
- Белый IP-адрес (для webhook'ов)

---

## 2. Детальный разбор зависимостей

### 2.1 Python зависимости

Анализ [`requirements.txt`](requirements.txt):

#### Core Bot Framework
```txt
aiogram>=3.0.0          # Асинхронный фреймворк для Telegram Bot API
aiohttp>=3.9.0          # Асинхронный HTTP клиент/сервер
```
**Назначение**: Основа для работы с Telegram Bot API, обработка запросов.

#### Database
```txt
sqlalchemy>=2.0.0       # ORM для работы с БД
alembic>=1.12.0         # Система миграций БД
asyncpg>=0.29.0         # Асинхронный драйвер PostgreSQL
```
**Назначение**: Работа с PostgreSQL, управление схемой БД.

#### Configuration & Validation
```txt
pydantic>=2.5.0            # Валидация данных
pydantic-settings>=2.1.0   # Управление настройками
python-dotenv>=1.0.0       # Загрузка .env файлов
```
**Назначение**: Валидация конфигурации, типобезопасность.

#### Monitoring & Observability
```txt
prometheus-client>=0.19.0     # Метрики Prometheus
sentry-sdk>=1.39.0            # Отслеживание ошибок
python-json-logger>=2.0.7     # Структурированное логирование
```
**Назначение**: Мониторинг производительности, отслеживание ошибок.

#### Caching
```txt
redis>=5.0.0            # Клиент Redis
aioredis>=2.0.1         # Асинхронный клиент Redis
```
**Назначение**: Кэширование данных, хранение сессий.

#### Security
```txt
cryptography>=41.0.0    # Криптографические операции
python-jose>=3.3.0      # JWT токены
```
**Назначение**: Шифрование данных, валидация webhook'ов.

#### Payment Systems
```txt
aiocryptopay>=0.4.0,<0.5.0   # CryptoPay API
yookassa>=2.3.0              # YooKassa API
```
**Назначение**: Интеграция с платежными системами.

#### Utilities
```txt
python-dateutil>=2.8.2   # Работа с датами
pytz>=2023.3             # Временные зоны
loguru>=0.7.0            # Расширенное логирование
```

### 2.2 Системные зависимости

#### Ubuntu 24.04 LTS (обязательные)
```bash
# Компиляция и сборка
build-essential          # gcc, g++, make
gcc                      # GNU C компилятор
python3-dev              # Заголовочные файлы Python

# Библиотеки
libssl-dev              # OpenSSL для шифрования
libffi-dev              # Foreign Function Interface
libpq-dev               # PostgreSQL клиентские библиотеки

# Утилиты
curl                    # Загрузка файлов
wget                    # Загрузка файлов
git                     # Система контроля версий
```

### 2.3 Docker и Docker Compose

#### Docker Engine
- **Версия**: 24.0+
- **Компоненты**: Docker Engine, containerd, Docker CLI
- **Плагины**: docker-compose-plugin

#### Docker Compose
- **Версия**: 2.20+
- **Формат файла**: версия 3.8

**Установка**:
```bash
# Удаление старых версий
sudo apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Добавление GPG ключа Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавление репозитория
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Проверка
docker --version
docker compose version
```

### 2.4 PostgreSQL конфигурация

**Образ**: `postgres:15-alpine`

#### Оптимальные настройки для production:

```ini
# Память
shared_buffers = 1GB              # 25% от RAM
effective_cache_size = 3GB        # 75% от RAM
work_mem = 16MB                   # RAM / (max_connections * 2)
maintenance_work_mem = 256MB

# Checkpoint
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Query планирование
random_page_cost = 1.1
effective_io_concurrency = 200

# Логирование
log_min_duration_statement = 1000  # Логировать запросы > 1s
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Подключения
max_connections = 100
```

### 2.5 Redis конфигурация

**Образ**: `redis:7-alpine`

#### Оптимальные настройки:

```bash
# Persistence
appendonly yes              # Включить AOF
appendfsync everysec       # Синхронизация каждую секунду
save 900 1                 # Сохранять при 1 изменении за 15 мин
save 300 10                # Сохранять при 10 изменениях за 5 мин
save 60 10000              # Сохранять при 10000 изменений за 1 мин

# Память
maxmemory 768mb            # Максимум памяти
maxmemory-policy allkeys-lru  # Политика вытеснения

# Безопасность
requirepass <strong_password>  # Обязательный пароль

# Производительность
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

---

## 3. Настройка переменных окружения

### 3.1 Структура .env файла

Создайте `.env` файл в корне проекта на основе `.env.example`:

```bash
cp .env.example .env
nano .env
```

### 3.2 ОБЯЗАТЕЛЬНЫЕ переменные

#### 🤖 Telegram Bot
```bash
# Токен бота от @BotFather
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# ID администраторов (через запятую)
# Получить ID: @userinfobot
ADMIN_IDS=123456789,987654321
```

#### 🗄️ База данных PostgreSQL
```bash
# Хост (в Docker всегда postgres)
POSTGRES_HOST=postgres

# Порт по умолчанию
POSTGRES_PORT=5432

# Имя базы данных
POSTGRES_DB=2getpro_v2_db

# Пользователь БД
POSTGRES_USER=2getpro_user

# ВАЖНО: Используйте СИЛЬНЫЙ пароль (минимум 16 символов)
# Пример генерации: openssl rand -base64 24
POSTGRES_PASSWORD=your_very_strong_password_here_change_me
```

#### 🔴 Redis Cache
```bash
# Хост (в Docker всегда redis)
REDIS_HOST=redis

# Порт по умолчанию
REDIS_PORT=6379

# База данных (0-15)
REDIS_DB=0

# Пароль Redis (рекомендуется установить)
REDIS_PASSWORD=your_redis_password_here

# Включен ли Redis
REDIS_ENABLED=true

# TTL для кэша (в секундах)
REDIS_TTL=3600
```

#### 🎛️ VPN Panel API
```bash
# URL API панели (3x-ui, Marzban, и т.д.)
PANEL_API_URL=https://your-panel.example.com/api

# API ключ панели
PANEL_API_KEY=your_panel_api_key_here

# Лимит трафика для пользователей (ГБ, 0 = безлимит)
USER_TRAFFIC_LIMIT_GB=0.0

# Стратегия сброса трафика: NO_RESET, MONTHLY, WEEKLY
USER_TRAFFIC_STRATEGY=NO_RESET

# UUID внутренних squadов (через запятую)
USER_SQUAD_UUIDS=uuid1,uuid2,uuid3

# UUID внешнего squad (опционально)
USER_EXTERNAL_SQUAD_UUID=external-squad-uuid

# Секрет для валидации webhook от панели
PANEL_WEBHOOK_SECRET=your_webhook_secret_here
```

### 3.3 Платежные системы

#### 💳 YooKassa (основная)
```bash
# Включить YooKassa
YOOKASSA_ENABLED=true

# Shop ID из личного кабинета
YOOKASSA_SHOP_ID=123456

# Секретный ключ
YOOKASSA_SECRET_KEY=live_ваш_секретный_ключ

# URL возврата после оплаты
YOOKASSA_RETURN_URL=https://t.me/your_bot

# Email для чеков (опционально)
YOOKASSA_DEFAULT_RECEIPT_EMAIL=

# НДС код (1 = без НДС)
YOOKASSA_VAT_CODE=1

# Режим оплаты (full_prepayment, service)
YOOKASSA_PAYMENT_MODE=full_prepayment

# Предмет расчета (payment, service, full_payment)
YOOKASSA_PAYMENT_SUBJECT=service

# Автоплатежи (сохранение карт)
YOOKASSA_AUTOPAYMENTS_ENABLED=false

# Обязательная привязка карты при автоплатежах
YOOKASSA_AUTOPAYMENTS_REQUIRE_CARD_BINDING=true
```

#### 🪙 CryptoPay (криптовалюта)
```bash
# Включить CryptoPay
CRYPTOPAY_ENABLED=true

# API токен от @CryptoBot
CRYPTOPAY_TOKEN=your_cryptopay_token_here

# Сеть: mainnet или testnet
CRYPTOPAY_NETWORK=mainnet

# Тип валюты: crypto или fiat
CRYPTOPAY_CURRENCY_TYPE=fiat

# Актив: RUB, USD, USDT, TON и т.д.
CRYPTOPAY_ASSET=RUB
```

#### ⭐ Telegram Stars
```bash
# Включить Telegram Stars
STARS_ENABLED=true

# Настройка не требуется - встроено в Telegram
```

#### 💰 FreeKassa (опционально)
```bash
# Включить FreeKassa
FREEKASSA_ENABLED=false

# Merchant ID
FREEKASSA_MERCHANT_ID=your_merchant_id

# Секретные ключи
FREEKASSA_FIRST_SECRET=your_secret_key_1
FREEKASSA_SECOND_SECRET=your_secret_key_2

# API ключ
FREEKASSA_API_KEY=your_api_key

# URL платежной формы
FREEKASSA_PAYMENT_URL=https://pay.freekassa.ru/

# IP для webhook (опционально)
FREEKASSA_PAYMENT_IP=

# ID метода оплаты (опционально)
FREEKASSA_PAYMENT_METHOD_ID=
```

#### 🎁 Tribute (опционально)
```bash
# Включить Tribute
TRIBUTE_ENABLED=true

# API ключ
TRIBUTE_API_KEY=your_tribute_api_key_here

# Ссылки на оплату для каждого периода
TRIBUTE_LINK_1_MONTH=https://tribute.to/your_link_1m
TRIBUTE_LINK_3_MONTHS=https://tribute.to/your_link_3m
TRIBUTE_LINK_6_MONTHS=https://tribute.to/your_link_6m
TRIBUTE_LINK_12_MONTHS=https://tribute.to/your_link_12m

# Пропускать уведомления о продлении
TRIBUTE_SKIP_NOTIFICATIONS=true

# Пропускать уведомления об отмене
TRIBUTE_SKIP_CANCELLATION_NOTIFICATIONS=false
```

### 3.4 Цены подписок

```bash
# Включение/отключение тарифов
1_MONTH_ENABLED=true
3_MONTHS_ENABLED=true
6_MONTHS_ENABLED=true
12_MONTHS_ENABLED=true

# Цены в рублях (в копейках: 1 руб = 100)
RUB_PRICE_1_MONTH=15000     # 150 рублей
RUB_PRICE_3_MONTHS=40000    # 400 рублей
RUB_PRICE_6_MONTHS=75000    # 750 рублей
RUB_PRICE_12_MONTHS=140000  # 1400 рублей

# Цены в Telegram Stars
STARS_PRICE_1_MONTH=150
STARS_PRICE_3_MONTHS=400
STARS_PRICE_6_MONTHS=750
STARS_PRICE_12_MONTHS=1400
```

### 3.5 Реферальная программа

```bash
# Бонусы для пригласившего (в днях)
REFERRAL_BONUS_DAYS_1_MONTH=3
REFERRAL_BONUS_DAYS_3_MONTHS=7
REFERRAL_BONUS_DAYS_6_MONTHS=15
REFERRAL_BONUS_DAYS_12_MONTHS=30

# Бонусы для приглашенного (в днях)
REFEREE_BONUS_DAYS_1_MONTH=1
REFEREE_BONUS_DAYS_3_MONTHS=3
REFEREE_BONUS_DAYS_6_MONTHS=7
REFEREE_BONUS_DAYS_12_MONTHS=15

# Выдавать бонус только за первую покупку
REFERRAL_ONE_BONUS_PER_REFEREE=true

# Поддержка legacy реферальных ссылок
LEGACY_REFS=true
```

### 3.6 Пробный период

```bash
# Включить триал
TRIAL_ENABLED=true

# Длительность (дней)
TRIAL_DURATION_DAYS=3

# Лимит трафика (ГБ)
TRIAL_TRAFFIC_LIMIT_GB=5.0
```

### 3.7 Уведомления

```bash
# Уведомления о подписках
SUBSCRIPTION_NOTIFICATIONS_ENABLED=true
SUBSCRIPTION_NOTIFY_ON_EXPIRE=true
SUBSCRIPTION_NOTIFY_AFTER_EXPIRE=true
SUBSCRIPTION_NOTIFY_DAYS_BEFORE=3

# ID чата для логов (опционально)
LOG_CHAT_ID=
LOG_THREAD_ID=

# Типы уведомлений
LOG_NEW_USERS=true
LOG_PAYMENTS=true
LOG_PROMO_ACTIVATIONS=true
LOG_TRIAL_ACTIVATIONS=true
LOG_SUSPICIOUS_ACTIVITY=true
```

### 3.8 Безопасность

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# Валидация веб-хуков
WEBHOOK_VALIDATION_ENABLED=true

# Секретный токен для webhook (сгенерируйте: openssl rand -hex 32)
WEBHOOK_SECRET_TOKEN=your_generated_secret_token_here
```

### 3.9 Мониторинг (ОПЦИОНАЛЬНО)

#### Sentry (отслеживание ошибок)
```bash
# Включить Sentry
SENTRY_ENABLED=false

# DSN из личного кабинета Sentry
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Окружение
SENTRY_ENVIRONMENT=production

# Процент отслеживаемых транзакций (0.0 - 1.0)
SENTRY_TRACES_SAMPLE_RATE=0.1
```

#### Prometheus (метрики)
```bash
# Включить Prometheus
PROMETHEUS_ENABLED=true

# Порт для метрик
PROMETHEUS_PORT=9090

# Путь к метрикам
PROMETHEUS_METRICS_PATH=/metrics
```

#### Grafana (визуализация)
```bash
# Пароль для Grafana (по умолчанию admin/admin)
GRAFANA_PASSWORD=your_secure_grafana_password
```

### 3.10 Веб-сервер и webhook

```bash
# Хост веб-сервера
WEB_SERVER_HOST=0.0.0.0

# Порт веб-сервера
WEB_SERVER_PORT=8080

# Базовый URL для webhook (с HTTPS!)
WEBHOOK_BASE_URL=https://your-domain.com

# Размер страницы логов
LOGS_PAGE_SIZE=10
```

### 3.11 Дополнительные настройки

```bash
# Язык по умолчанию (ru или en)
DEFAULT_LANGUAGE=ru

# Валюта по умолчанию
DEFAULT_CURRENCY_SYMBOL=RUB

# Поддержка
SUPPORT_LINK=https://t.me/your_support

# Статус серверов
SERVER_STATUS_URL=https://status.example.com

# Условия использования
TERMS_OF_SERVICE_URL=https://example.com/terms

# Обязательная подписка на канал (ID и ссылка)
REQUIRED_CHANNEL_ID=-1001234567890
REQUIRED_CHANNEL_LINK=https://t.me/your_channel

# URL мини-приложения для подписок
SUBSCRIPTION_MINI_APP_URL=

# Описание команды /start
START_COMMAND_DESCRIPTION=

# Отключить приветственное сообщение
DISABLE_WELCOME_MESSAGE=false

# Включить секцию "Мои устройства"
MY_DEVICES_SECTION_ENABLED=false

# Лимит устройств для пользователя (0 = безлимит)
USER_HWID_DEVICE_LIMIT=

# URL миниатюр для inline режима
INLINE_REFERRAL_THUMBNAIL_URL=https://cdn-icons-png.flaticon.com/512/1077/1077114.png
INLINE_USER_STATS_THUMBNAIL_URL=https://cdn-icons-png.flaticon.com/512/681/681494.png
INLINE_FINANCIAL_STATS_THUMBNAIL_URL=https://cdn-icons-png.flaticon.com/512/2769/2769339.png
INLINE_SYSTEM_STATS_THUMBNAIL_URL=https://cdn-icons-png.flaticon.com/512/2920/2920277.png
```

---

## 4. Оптимизированный Docker Compose

### 4.1 Базовая конфигурация (docker-compose.yml)

Основной файл [`docker-compose.yml`](docker-compose.yml) содержит минимальную конфигурацию для развертывания.

### 4.2 Production конфигурация

Для production рекомендуется использовать расширенную конфигурацию из [`infrastructure/docker/docker-compose.prod.yml`](infrastructure/docker/docker-compose.prod.yml:1).

#### Ключевые отличия production:

1. **Несколько инстансов бота** (масштабируемость)
2. **Ограничения ресурсов** (CPU/Memory limits)
3. **Health checks** для всех сервисов
4. **Мониторинг** (Prometheus + Grafana + exporters)
5. **Оптимизированное логирование**
6. **Nginx** как reverse proxy

### 4.3 Полная конфигурация с мониторингом

Создайте `docker-compose.override.yml` для продакшена:

```yaml
version: '3.8'

services:
  # Расширенная конфигурация бота
  bot:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
  
  # PostgreSQL exporter для метрик
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: 2getpro_postgres_exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?sslmode=disable"
    networks:
      - bot_network
    depends_on:
      - postgres
  
  # Redis exporter для метрик
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: 2getpro_redis_exporter
    environment:
      REDIS_ADDR: "redis:6379"
      REDIS_PASSWORD: ${REDIS_PASSWORD}
    networks:
      - bot_network
    depends_on:
      - redis

networks:
  bot_network:
    driver: bridge
```

---

## 5. Пошаговая инструкция по развертыванию

### 5.1 Подготовка сервера Ubuntu 24.04

#### Шаг 1: Обновление системы

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Обновите пакеты
sudo apt update && sudo apt upgrade -y

# Перезагрузка (если требуется)
sudo reboot
```

#### Шаг 2: Установка базовых утилит

```bash
# Установите необходимые пакеты
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    git \
    wget \
    nano \
    htop \
    net-tools
```

#### Шаг 3: Настройка firewall

```bash
# Установите UFW
sudo apt install -y ufw

# Разрешите SSH
sudo ufw allow 22/tcp

# Разрешите HTTP и HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Включите firewall
sudo ufw --force enable

# Проверьте статус
sudo ufw status
```

### 5.2 Установка Docker и Docker Compose

Используйте скрипт автоматической установки:

```bash
# Скачайте официальный скрипт Docker
curl -fsSL https://get.docker.com -o get-docker.sh

# Запустите установку
sudo sh get-docker.sh

# Добавьте пользователя в группу docker
sudo usermod -aG docker $USER

# Примените изменения
newgrp docker

# Проверьте установку
docker --version
docker compose version
```

**Ожидаемый вывод:**
```
Docker version 24.0.7, build afdd53b
Docker Compose version v2.23.0
```

### 5.3 Клонирование и настройка проекта

#### Шаг 1: Клонирование репозитория

```bash
# Перейдите в директорию
cd /opt

# Клонируйте проект
git clone https://github.com/your-username/2GETPRO-v2.git
cd 2GETPRO-v2

# Проверьте структуру
ls -la
```

#### Шаг 2: Создание .env файла

```bash
# Скопируйте пример
cp .env.example .env

# Откройте для редактирования
nano .env
```

**Заполните ВСЕ обязательные переменные** из раздела 3!

#### Шаг 3: Генерация секретных ключей

```bash
# Генерация паролей
openssl rand -base64 32  # Для POSTGRES_PASSWORD
openssl rand -base64 32  # Для REDIS_PASSWORD
openssl rand -hex 32     # Для WEBHOOK_SECRET_TOKEN
openssl rand -base64 24  # Для GRAFANA_PASSWORD
```

Вставьте сгенерированные значения в `.env`.

#### Шаг 4: Проверка конфигурации

```bash
# Проверьте синтаксис docker-compose.yml
docker compose config

# Должны увидеть объединенную конфигурацию без ошибок
```

### 5.4 Первый запуск

#### Шаг 1: Создание сети и volumes

```bash
# Docker Compose автоматически создаст их при запуске
# Но можно создать вручную для контроля

docker network create bot_network
docker volume create postgres_data
docker volume create redis_data
docker volume create prometheus_data
docker volume create grafana_data
```

#### Шаг 2: Запуск сервисов

```bash
# Запустите в фоновом режиме
docker compose up -d

# Проверьте статус
docker compose ps
```

**Ожидаемый вывод:**
```
NAME                      STATUS          PORTS
2getpro_v2_bot            running         
2getpro_v2_postgres       running (healthy)   5432/tcp
2getpro_v2_redis          running (healthy)   6379/tcp
2getpro_v2_prometheus     running         9090/tcp
2getpro_v2_grafana        running         3000/tcp
```

#### Шаг 3: Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Только бот
docker compose logs -f bot

# Последние 100 строк
docker compose logs --tail=100 bot
```

### 5.5 Миграции базы данных

#### Автоматическое применение миграций

```bash
# Войдите в контейнер бота
docker compose exec bot bash

# Примените миграции
python db/migrator.py

# Выйдите
exit
```

#### Проверка миграций

```bash
# Подключитесь к PostgreSQL
docker compose exec postgres psql -U 2getpro_user -d 2getpro_v2_db

# Выведите список таблиц
\dt

# Должны увидеть:
# - users
# - subscriptions
# - payments
# - promo_codes
# - transactions
# и другие

# Выйдите
\q
```

### 5.6 Проверка работоспособности

#### Health checks

```bash
# Проверка health endpoints
curl http://localhost:8080/health

# Ожидаемый ответ: {"status": "ok"}

# Проверка Prometheus
curl http://localhost:9090/-/healthy

# Проверка Grafana
curl http://localhost:3000/api/health
```

#### Проверка бота в Telegram

1. Откройте Telegram
2. Найдите вашего бота по username
3. Отправьте `/start`
4. Бот должен ответить приветственным сообщением

### 5.7 Настройка Nginx (опционально, для webhook)

Если вы хотите использовать webhook вместо polling:

#### Шаг 1: Установка Nginx

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

#### Шаг 2: Конфигурация Nginx

```bash
sudo nano /etc/nginx/sites-available/bot
```

Добавьте:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### Шаг 3: Получение SSL сертификата

```bash
# Активируйте конфигурацию
sudo ln -s /etc/nginx/sites-available/bot /etc/nginx/sites-enabled/

# Проверьте конфигурацию
sudo nginx -t

# Перезапустите Nginx
sudo systemctl restart nginx

# Получите SSL сертификат
sudo certbot --nginx -d your-domain.com

# Следуйте инструкциям
```

#### Шаг 4: Обновите .env

```bash
nano .env
```

Установите:
```bash
WEBHOOK_BASE_URL=https://your-domain.com
```

Перезапустите бота:
```bash
docker compose restart bot
```

---

## 6. Чек-лист функциональности

### 6.1 Базовые функции бота

- [ ] **Регистрация пользователя**: `/start` создает нового пользователя
- [ ] **Профиль пользователя**: Команда "Мой профиль" показывает информацию
- [ ] **Языковая поддержка**: Интерфейс на русском/английском
- [ ] **Обязательная подписка**: Проверка подписки на канал (если настроено)
- [ ] **Inline режим**: Работа inline команд для админов

### 6.2 Платежные системы

#### YooKassa
- [ ] Создание платежа через YooKassa
- [ ] Обработка успешного платежа
- [ ] Обработка отмененного платежа
- [ ] Webhook от YooKassa корректно обрабатывается
- [ ] Создается подписка после успешной оплаты
- [ ] Отправляется уведомление пользователю

#### CryptoPay
- [ ] Создание платежа через CryptoPay
- [ ] Webhook от CryptoPay обрабатывается
- [ ] Оплата в USDT работает
- [ ] Оплата в TON работает

#### Telegram Stars
- [ ] Создание инвойса со Stars
- [ ] Обработка успешной оплаты Stars
- [ ] Создание подписки

#### FreeKassa (если включено)
- [ ] Создание платежа
- [ ] Webhook обрабатывается
- [ ] Валидация подписи

#### Tribute (если включено)
- [ ] Ссылки на Tribute работают
- [ ] Обработка платежей

### 6.3 Административные функции

- [ ] **Статистика**: Команда /stats показывает метрики
- [ ] **Управление пользователями**: Просмотр, бан, разбан
- [ ] **Платежи**: История всех платежей
- [ ] **Синхронизация с панелью**: Команда синхронизации работает
- [ ] **Рассылка**: Отправка сообщений всем пользователям
- [ ] **Логи**: Просмотр логов действий
- [ ] **Рекламные кампании**: Отслеживание источников

### 6.4 Реферальная система

- [ ] Генерация реферальной ссылки для пользователя
- [ ] Учет приглашенных пользователей
- [ ] Начисление бонусов приглашающему
- [ ] Начисление бонусов приглашенному
- [ ] Статистика рефералов
- [ ] Один бонус за реферала (если настроено)

### 6.5 Промокоды

#### Создание промокодов
- [ ] Одиночный промокод
- [ ] Массовое создание промокодов
- [ ] Лимит активаций работает
- [ ] Срок действия учитывается

#### Использование
- [ ] Активация промокода
- [ ] Начисление дней подписки
- [ ] Проверка на повторную активацию
- [ ] Уведомление администратора

#### Управление
- [ ] Просмотр всех промокодов
- [ ] Деактивация промокода
- [ ] Удаление промокода
- [ ] Статистика по промокоду

### 6.6 Подписки

#### Создание и управление
- [ ] Создание подписки после оплаты
- [ ] Продление существующей подписки
- [ ] Отображение даты окончания
- [ ] Расчет оставшихся дней

#### Интеграция с панелью
- [ ] Создание пользователя в панели
- [ ] Создание подписки в панели
- [ ] Синхронизация статуса
- [ ] Обновление трафика
- [ ] Удаление подписки

#### Уведомления
- [ ] За 3 дня до окончания подписки
- [ ] В день окончания подписки
- [ ] После окончания подписки

### 6.7 Тестовый и Production режимы

#### Тестовый режим
- [ ] Создание триальной подписки
- [ ] Лимит трафика для триала
- [ ] Один триал на пользователя
- [ ] Уведомление админа о активации триала

#### Production режим
- [ ] Тестовые платежи работают
- [ ] Production платежи работают
- [ ] Webhook валидация включена
- [ ] Rate limiting работает
- [ ] Логирование ошибок в Sentry (если настроено)

### 6.8 Система балансов

- [ ] Отображение баланса пользователя
- [ ] Пополнение баланса через платежи
- [ ] Оплата подписки с баланса
- [ ] История транзакций
- [ ] Начисление реферальных бонусов на баланс

---

## 7. Troubleshooting

### 7.1 Бот не запускается

#### Проблема: Контейнер постоянно перезапускается

**Диагностика:**
```bash
# Проверьте логи
docker compose logs --tail=100 bot

# Проверьте статус
docker compose ps
```

**Возможные причины и решения:**

1. **Неверный BOT_TOKEN**
```bash
# Проверьте токен
grep BOT_TOKEN .env

# Обновите и перезапустите
nano .env
docker compose restart bot
```

2. **Не может подключиться к БД**
```bash
# Проверьте, что PostgreSQL запущен
docker compose ps postgres

# Проверьте подключение
docker compose exec postgres pg_isready -U 2getpro_user

# Проверьте логи PostgreSQL
docker compose logs postgres
```

3. **Ошибки миграции**
```bash
# Примените миграции вручную
docker compose exec bot python db/migrator.py
```

### 7.2 Проблемы с базой данных

#### Проблема: "too many connections"

**Решение:**
```bash
# Войдите в PostgreSQL
docker compose exec postgres psql -U 2getpro_user -d 2getpro_v2_db

# Увеличьте лимит подключений
ALTER SYSTEM SET max_connections = 200;

# Перезапустите
\q
docker compose restart postgres
```

#### Проблема: Медленные запросы

**Диагностика:**
```sql
-- Подключитесь к БД
docker compose exec postgres psql -U 2getpro_user -d 2getpro_v2_db

-- Найдите медленные запросы
SELECT pid, now() - query_start as duration, query 
FROM pg_stat_activity 
WHERE state = 'active' 
AND now() - query_start > interval '1 second';
```

**Решение:**
```sql
-- Создайте индексы (если отсутствуют)
CREATE INDEX CONCURRENTLY idx_payments_user_id ON payments(user_id);
CREATE INDEX CONCURRENTLY idx_subscriptions_end_date ON subscriptions(end_date);
CREATE INDEX CONCURRENTLY idx_users_panel_uuid ON users(panel_user_uuid);

-- Обновите статистику
VACUUM ANALYZE;
```

### 7.3 Проблемы с Redis

#### Проблема: Redis connection timeout

**Диагностика:**
```bash
# Проверьте статус
docker compose ps redis

# Проверьте подключение
docker compose exec redis redis-cli ping
```

**С паролем:**
```bash
docker compose exec redis redis-cli -a your_redis_password ping
```

**Решение:**
```bash
# Перезапустите Redis
docker compose restart redis

# Проверьте память
docker compose exec redis redis-cli INFO memory
```

### 7.4 Проблемы с платежами

#### Проблема: Webhook не приходят

**Диагностика:**
```bash
# Проверьте доступность endpoint
curl -I https://your-domain.com/webhook/yookassa

# Проверьте логи Nginx (если используете)
sudo tail -f /var/log/nginx/error.log

# Проверьте логи бота
docker compose logs --tail=100 bot | grep webhook
```

**Решение:**

1. **Проверьте firewall**
```bash
sudo ufw status
sudo ufw allow 443/tcp
```

2. **Проверьте SSL сертификат**
```bash
sudo certbot certificates
```

3. **Проверьте webhook URL в .env**
```bash
grep WEBHOOK_BASE_URL .env
# Должно быть: https://your-domain.com (с HTTPS!)
```

#### Проблема: Неверная подпись webhook

**Решение:**
```bash
# Проверьте секретные ключи
grep SECRET .env

# Убедитесь, что используются актуальные ключи из личных кабинетов
# Перезапустите бота после обновления
docker compose restart bot
```

### 7.5 Проблемы с производительностью

#### Проблема: Высокое использование памяти

**Диагностика:**
```bash
# Мониторинг ресурсов
docker stats

# Отсортировать по памяти
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | sort -k 2 -h
```

**Решение:**

Установите лимиты в `docker-compose.override.yml`:
```yaml
services:
  bot:
    deploy:
      resources:
        limits:
          memory: 2G
```

#### Проблема: Медленный отклик бота

**Диагностика:**
```bash
# Проверьте метрики
curl http://localhost:9090/api/v1/query?query=bot_response_time_seconds

# Проверьте логи на медленные операции
docker compose logs bot | grep -i "slow"
```

**Решение:**

1. **Оптимизируйте запросы к БД** (добавьте индексы)
2. **Увеличьте TTL кэша Redis**
3. **Масштабируйте** (добавьте больше инстансов бота)

### 7.6 Проблемы с Docker

#### Проблема: "No space left on device"

**Решение:**
```bash
# Очистите неиспользуемые образы
docker image prune -a

# Очистите volumes
docker volume prune

# Очистите всё
docker system prune -a --volumes
```

#### Проблема: Сеть недоступна

```bash
# Пересоздайте сеть
docker compose down
docker network prune
docker compose up -d
```

### 7.7 Диагностический скрипт

Создайте `diagnose.sh`:

```bash
#!/bin/bash
echo "=== Docker Version ==="
docker --version
docker compose version

echo -e "\n=== Container Status ==="
docker compose ps

echo -e "\n=== Recent Logs (Bot) ==="
docker compose logs --tail=50 bot

echo -e "\n=== Database Status ==="
docker compose exec postgres pg_isready -U 2getpro_user || echo "PostgreSQL not ready"

echo -e "\n=== Redis Status ==="
docker compose exec redis redis-cli ping || echo "Redis not ready"

echo -e "\n=== Disk Usage ==="
df -h

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Docker Stats ==="
docker stats --no-stream
```

Запуск:
```bash
chmod +x diagnose.sh
./diagnose.sh > diagnostic_report.txt
```

---

## 8. Мониторинг и поддержка

### 8.1 Настройка Prometheus

Prometheus уже настроен через [`infrastructure/prometheus/prometheus.yml`](infrastructure/prometheus/prometheus.yml:1).

**Доступ:** `http://your-server-ip:9090`

#### Полезные запросы (PromQL):

```promql
# Количество активных пользователей
count(users{is_active="true"})

# RPS (запросов в секунду)
rate(bot_requests_total[5m])

# Средняя задержка ответа
avg(bot_response_time_seconds)

# Использование памяти контейнером
container_memory_usage_bytes{name="2getpro_v2_bot"}

# CPU usage
rate(container_cpu_usage_seconds_total{name="2getpro_v2_bot"}[5m])
```

### 8.2 Настройка Grafana

**Доступ:** `http://your-server-ip:3000`  
**Логин:** admin  
**Пароль:** Из переменной `GRAFANA_PASSWORD` в .env

#### Импорт дашбордов:

1. Откройте Grafana
2. **Dashboards → Import**
3. Используйте ID дашборда:
   - **Docker Container Metrics**: `193`
   - **PostgreSQL Database**: `9628`
   - **Redis Dashboard**: `11835`
   - **Nginx**: `12708`

#### Создание алертов:

1. **Alerts → Alert rules → New alert rule**
2. Настройте условия, например:
   - Бот не отвечает > 5 минут
   - Использование памяти > 90%
   - Свободное место на диске < 10%

### 8.3 Резервное копирование

#### Автоматический бэкап

Создайте скрипт `backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/2getpro"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Создайте директорию
mkdir -p "$BACKUP_DIR"

# Бэкап PostgreSQL
echo "Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U 2getpro_user 2getpro_v2_db | \
    gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Бэкап Redis
echo "Backing up Redis..."
docker compose exec redis redis-cli SAVE
docker cp 2getpro_v2_redis:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Бэкап конфигурации
echo "Backing up configuration..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env docker-compose.yml

# Удалите старые бэкапы
echo "Cleaning old backups..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

#### Добавьте в cron:

```bash
chmod +x backup.sh

# Ежедневно в 3:00 AM
crontab -e
```

Добавьте строку:
```cron
0 3 * * * cd /opt/2GETPRO-v2 && ./backup.sh >> /var/log/2getpro_backup.log 2>&1
```

#### Восстановление из бэкапа:

```bash
# PostgreSQL
gunzip < /var/backups/2getpro/db_20240101_030000.sql.gz | \
    docker compose exec -T postgres psql -U 2getpro_user 2getpro_v2_db

# Redis
docker cp /var/backups/2getpro/redis_20240101_030000.rdb 2getpro_v2_redis:/data/dump.rdb
docker compose restart redis
```

### 8.4 Обновление системы

```bash
# Остановите бота
docker compose down

# Обновите код
git pull origin main

# Обновите зависимости
docker compose build --no-cache

# Примените миграции
docker compose run --rm bot python db/migrator.py

# Запустите
docker compose up -d

# Проверьте логи
docker compose logs -f bot
```

### 8.5 Полезные команды

```bash
# Просмотр логов в реальном времени
docker compose logs -f

# Перезапуск конкретного сервиса
docker compose restart bot

# Вход в контейнер
docker compose exec bot bash

# Проверка использования ресурсов
docker stats

# Очистка логов
docker compose exec bot sh -c "rm -rf logs/*.log"

# Проверка здоровья
docker compose ps
curl http://localhost:8080/health

# Экспорт метрик
curl http://localhost:9090/metrics

# Резервная копия БД
docker compose exec -T postgres pg_dump -U 2getpro_user 2getpro_v2_db > backup.sql
```

---

## 📞 Поддержка и ресурсы

### Документация проекта

- [README](README.md) - Обзор проекта
- [INSTALLATION_GUIDE](docs/deployment/INSTALLATION_GUIDE.md) - Традиционная установка
- [Docker Guide](docs/deployment/docker.md) - Docker развертывание
- [Production Checklist](docs/deployment/production.md) - Чек-лист для продакшена
- [Troubleshooting](docs/operations/troubleshooting.md) - Решение проблем
- [API Documentation](docs/api/README.md) - API документация

### Полезные ссылки

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [aiogram Documentation](https://docs.aiogram.dev/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

### Получение помощи

1. **Проверьте логи**: `docker compose logs -f bot`
2. **Запустите диагностику**: `./diagnose.sh`
3. **Проверьте документацию** в директории `docs/`
4. **Создайте Issue** на GitHub с:
   - Описанием проблемы
   - Шагами для воспроизведения
   - Логами
   - Версией системы

---

## ✅ Финальный чек-лист

Перед запуском в продакшн убедитесь:

- [ ] Все переменные в .env заполнены
- [ ] Используются СИЛЬНЫЕ пароли (PostgreSQL, Redis, Grafana)
- [ ] SSL сертификаты установлены (для webhook)
- [ ] Firewall настроен правильно
- [ ] Резервное копирование настроено
- [ ] Мониторинг работает (Prometheus + Grafana)
- [ ] Логирование настроено
- [ ] Проведено тестирование всех функций
- [ ] Webhook валидация включена
- [ ] Rate limiting включен
- [ ] Health checks работают
- [ ] Документация актуальна

---

**Версия документа**: 1.0  
**Дата создания**: 2025-11-28  
**Автор**: 2GETPRO Team  
**Лицензия**: MIT

🚀 **Удачного развертывания!**