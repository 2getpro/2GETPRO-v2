# Исправления критических проблем развертывания

## Обзор исправлений

Исправлены три критические проблемы, препятствующие развертыванию приложения:

1. ✅ **Nginx монтирование файла конфигурации**
2. ✅ **Несоответствие имени базы данных PostgreSQL**
3. ✅ **Валидация пустого значения FREEKASSA_PAYMENT_METHOD_ID**

---

## Изменённые файлы

### 1. [`docker-compose.yml`](docker-compose.yml)

**Проблема:** Nginx монтировал конфигурацию неправильно, что приводило к ошибке "Is a directory"

**Исправления:**
- Изменено монтирование основного конфига Nginx: `./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf:ro`
- Изменено монтирование конфига бота: `./infrastructure/nginx/telegram-bot.conf:/etc/nginx/conf.d/default.conf:ro`
- Исправлены значения по умолчанию для PostgreSQL:
  - `POSTGRES_DB: ${POSTGRES_DB:-vpn_shop_db}` (вместо 2getpro_v2_db)
  - `POSTGRES_USER: ${POSTGRES_USER:-user}` (вместо 2getpro_user)
- Добавлено монтирование скрипта инициализации БД: `./infrastructure/docker/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro`

### 2. [`config/settings.py`](config/settings.py)

**Проблема:** Валидация Pydantic требовала целочисленное значение для `FREEKASSA_PAYMENT_METHOD_ID`, но получала пустую строку

**Исправления:**
- Добавлено описание к полю `FREEKASSA_PAYMENT_METHOD_ID` с указанием, что оно опциональное
- Добавлен `FREEKASSA_PAYMENT_METHOD_ID` в валидатор `validate_optional_int_fields` для автоматической конвертации пустых строк в `None`

### 3. [`.env.example`](.env.example)

**Проблема:** Отсутствовали комментарии о том, какие поля обязательны, а какие опциональны

**Исправления:**
- Добавлены секции с понятными заголовками
- Добавлены комментарии для опциональных полей
- Указаны правильные значения по умолчанию для PostgreSQL
- Добавлены примеры для всех платёжных систем с пометкой "опционально"
- Добавлена документация по всем функциям бота

### 4. [`infrastructure/docker/init-db.sh`](infrastructure/docker/init-db.sh) (новый файл)

**Назначение:** Автоматическая инициализация базы данных PostgreSQL при первом запуске

**Функции:**
- Проверяет существование базы данных
- Создаёт БД если её нет
- Выдаёт права пользователю

---

## Инструкции по развертыванию

### Шаг 1: Остановка и очистка (если запущено)

```bash
# Остановить все контейнеры
docker-compose down

# Опционально: удалить volume PostgreSQL для чистой установки
docker volume rm 2getpro-v2_postgres_data

# Удалить директорию /etc/nginx/conf.d/telegram-bot.conf на хосте, если была создана
# В Windows:
rd /s /q "C:\path\to\etc\nginx\conf.d\telegram-bot.conf" 2>nul
```

### Шаг 2: Настройка .env файла

Скопируйте [`.env.example`](.env.example) в `.env` и заполните обязательные параметры:

```bash
cp .env.example .env
```

**Обязательные параметры:**
```env
# Бот
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789

# База данных (значения по умолчанию совпадают с docker-compose.yml)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=vpn_shop_db
POSTGRES_USER=user
POSTGRES_PASSWORD=strong_password_here

# Panel API
PANEL_API_URL=https://your-panel-api.com
PANEL_API_KEY=your_api_key

# Webhook
WEBHOOK_BASE_URL=https://togettest.2get.pro

# Цены (хотя бы одна)
RUB_PRICE_1_MONTH=199
```

**Опциональные параметры (можно оставить пустыми):**
```env
FREEKASSA_ENABLED=false
FREEKASSA_MERCHANT_ID=
FREEKASSA_PAYMENT_METHOD_ID=
LOG_CHAT_ID=
LOG_THREAD_ID=
SENTRY_DSN=
```

### Шаг 3: Установка прав на скрипт (Linux/macOS)

```bash
chmod +x infrastructure/docker/init-db.sh
```

В Windows это не требуется, так как скрипт будет выполняться внутри Linux-контейнера.

### Шаг 4: Запуск

```bash
# Сборка и запуск всех сервисов
docker-compose up -d --build

# Проверка логов
docker-compose logs -f bot
docker-compose logs -f postgres
docker-compose logs -f nginx
```

### Шаг 5: Проверка работоспособности

1. **Проверка PostgreSQL:**
```bash
docker-compose exec postgres psql -U user -d vpn_shop_db -c "SELECT version();"
```

2. **Проверка Nginx:**
```bash
curl http://localhost/health
```

3. **Проверка бота:**
```bash
docker-compose logs bot | grep "Bot started successfully"
```

4. **Проверка вебхука (если настроен):**
```bash
curl https://togettest.2get.pro/health
```

---

## Решение проблем

### Проблема: Nginx всё ещё показывает "Is a directory"

**Решение:**
```bash
# Удалите созданную директорию на хосте
docker-compose down
sudo rm -rf ./infrastructure/nginx/conf.d/  # Если была создана

# Пересоздайте контейнер
docker-compose up -d --force-recreate nginx
```

### Проблема: PostgreSQL показывает "database does not exist"

**Решение:**
```bash
# Проверьте переменные окружения
docker-compose exec postgres env | grep POSTGRES

# Проверьте, что скрипт инициализации выполнился
docker-compose logs postgres | grep "init-db"

# При необходимости пересоздайте volume
docker-compose down -v
docker-compose up -d
```

### Проблема: Ошибка валидации FREEKASSA_PAYMENT_METHOD_ID

**Решение:**
Убедитесь, что в `.env` либо указано числовое значение, либо поле вообще отсутствует:

```env
# Правильно (опущено):
# FREEKASSA_PAYMENT_METHOD_ID=

# Правильно (с значением):
FREEKASSA_PAYMENT_METHOD_ID=123

# Неправильно:
FREEKASSA_PAYMENT_METHOD_ID=
```

Или оставьте строку пустой в `.env`, валидатор автоматически преобразует её в `None`.

---

## Верификация исправлений

### Тест 1: Nginx конфигурация
```bash
docker-compose exec nginx nginx -t
# Ожидаемый результат: "configuration file /etc/nginx/nginx.conf test is successful"
```

### Тест 2: PostgreSQL подключение
```bash
docker-compose exec postgres psql -U user -d vpn_shop_db -c "\dt"
# Ожидаемый результат: список таблиц или пустой список если миграции не выполнялись
```

### Тест 3: Загрузка настроек бота
```bash
docker-compose exec bot python -c "from config.settings import settings; print(f'DB: {settings.POSTGRES_DB}'); print(f'FreeKassa ID: {settings.FREEKASSA_PAYMENT_METHOD_ID}')"
# Ожидаемый результат: 
# DB: vpn_shop_db
# FreeKassa ID: None
```

---

## Контрольный список перед развертыванием

- [ ] Скопирован и настроен `.env` файл
- [ ] Указаны все обязательные параметры в `.env`
- [ ] Проверено, что SSL сертификаты существуют (`remnabot_privkey.key`, `remnabot_fullchain.pem`)
- [ ] Выполнена команда `docker-compose down` для остановки старых контейнеров
- [ ] Удалены старые volumes PostgreSQL (если требуется чистая установка)
- [ ] Выполнена команда `docker-compose up -d --build`
- [ ] Проверены логи всех сервисов
- [ ] Выполнены тесты верификации (см. выше)
- [ ] Webhook настроен в Telegram Bot API (если используется webhook режим)

---

## Дополнительная информация

### Структура монтирования Nginx

```
Host                                    →  Container
./infrastructure/nginx/nginx.conf       →  /etc/nginx/nginx.conf
./infrastructure/nginx/telegram-bot.conf →  /etc/nginx/conf.d/default.conf
./remnabot_privkey.key                  →  /etc/nginx/ssl/privkey.key
./remnabot_fullchain.pem                →  /etc/nginx/ssl/fullchain.pem
./logs/nginx                            →  /var/log/nginx
```

### Порты и сервисы

| Сервис     | Внутренний порт | Внешний порт | Доступен извне |
|------------|----------------|--------------|----------------|
| Bot        | 8080           | -            | Нет            |
| PostgreSQL | 5432           | 5432         | Да             |
| Redis      | 6379           | 6379         | Да             |
| Nginx      | 80, 443        | 80, 443      | Да             |
| Prometheus | 9090           | 9090         | Да             |
| Grafana    | 3000           | 3000         | Да             |

### Полезные команды

```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Перезапуск конкретного сервиса
docker-compose restart bot

# Проверка статуса
docker-compose ps

# Вход в контейнер
docker-compose exec bot bash

# Просмотр переменных окружения
docker-compose exec bot env

# Очистка всего
docker-compose down -v --remove-orphans
```

---

## Обратная связь

Если после применения исправлений возникают проблемы:

1. Проверьте логи: `docker-compose logs`
2. Проверьте статус сервисов: `docker-compose ps`
3. Убедитесь, что все файлы находятся в правильных местах
4. Проверьте права доступа к файлам
5. Убедитесь, что порты не заняты другими приложениями

---

**Дата создания:** 2025-11-28  
**Версия:** 1.0