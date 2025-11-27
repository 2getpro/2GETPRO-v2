# Руководство разработчика

## Обзор

Руководство для разработчиков, работающих над проектом 2GETPRO v2.

## Содержание

- [Начало работы](#начало-работы)
- [Структура проекта](#структура-проекта)
- [Стандарты кода](#стандарты-кода)
- [Тестирование](#тестирование)
- [Git Workflow](#git-workflow)

## Начало работы

### Требования

- Python 3.11+
- Docker и Docker Compose
- Git
- IDE (рекомендуется VS Code или PyCharm)

### Настройка окружения разработки

```bash
# 1. Клонирование репозитория
git clone https://github.com/your-repo/2GETPRO_v2.git
cd 2GETPRO_v2

# 2. Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установка зависимостей
pip install -r requirements.txt
pip install -r requirements-dev.txt  # dev зависимости

# 4. Настройка pre-commit hooks
pre-commit install

# 5. Копирование конфигурации
cp .env.example .env
nano .env  # Настройте для разработки

# 6. Запуск сервисов
docker-compose up -d postgres redis

# 7. Применение миграций
alembic upgrade head

# 8. Запуск бота
python main.py
```

### VS Code настройка

Создайте `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

## Структура проекта

```
2GETPRO_v2/
├── bot/                    # Основной код бота
│   ├── handlers/          # Обработчики команд
│   │   ├── admin/        # Админ команды
│   │   └── user/         # Пользовательские команды
│   ├── keyboards/        # Клавиатуры
│   ├── middlewares/      # Middleware
│   ├── services/         # Бизнес-логика
│   ├── states/           # FSM состояния
│   └── utils/            # Утилиты
├── config/               # Конфигурация
│   └── settings.py       # Настройки приложения
├── db/                   # База данных
│   ├── models.py         # SQLAlchemy модели
│   ├── dal/              # Data Access Layer
│   └── migrations/       # Alembic миграции
├── docs/                 # Документация
├── tests/                # Тесты
│   ├── unit/            # Unit тесты
│   └── integration/     # Integration тесты
└── main.py              # Точка входа
```

## Стандарты кода

### Python Style Guide

Следуем [PEP 8](https://pep8.org/) с некоторыми дополнениями:

- Максимальная длина строки: 100 символов
- Используем type hints
- Docstrings в формате Google Style

### Пример кода

```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_subscriptions(
    session: AsyncSession,
    user_id: int,
    active_only: bool = True
) -> List[Subscription]:
    """
    Получить подписки пользователя.
    
    Args:
        session: Асинхронная сессия БД
        user_id: ID пользователя
        active_only: Только активные подписки
        
    Returns:
        Список подписок
        
    Raises:
        ValueError: Если пользователь не найден
    """
    query = select(Subscription).where(Subscription.user_id == user_id)
    
    if active_only:
        query = query.where(Subscription.is_active == True)
    
    result = await session.execute(query)
    return result.scalars().all()
```

### Форматирование

```bash
# Black для форматирования
black bot/ --line-length 100

# isort для импортов
isort bot/

# flake8 для проверки
flake8 bot/ --max-line-length 100
```

### Pre-commit hooks

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        args: [--line-length=100]
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]
```

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=bot --cov-report=html

# Конкретный файл
pytest tests/unit/test_services.py

# Конкретный тест
pytest tests/unit/test_services.py::test_balance_service
```

### Написание тестов

```python
import pytest
from bot.services.balance_service import BalanceService


@pytest.mark.asyncio
async def test_add_balance(db_session, test_user):
    """Тест пополнения баланса"""
    service = BalanceService(db_session)
    
    # Arrange
    initial_balance = test_user.balance_kopeks
    amount = 10000
    
    # Act
    transaction = await service.add_balance(
        user_id=test_user.user_id,
        amount_kopeks=amount,
        description="Test"
    )
    
    # Assert
    assert transaction.amount_kopeks == amount
    assert test_user.balance_kopeks == initial_balance + amount
```

### Fixtures

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


@pytest.fixture
async def db_session():
    """Создание тестовой сессии БД"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with AsyncSession(engine) as session:
        yield session


@pytest.fixture
async def test_user(db_session):
    """Создание тестового пользователя"""
    user = User(
        user_id=123456,
        username="testuser",
        first_name="Test"
    )
    db_session.add(user)
    await db_session.commit()
    return user
```

## Git Workflow

### Ветки

- `main` - продакшн код
- `develop` - разработка
- `feature/*` - новые функции
- `bugfix/*` - исправления
- `hotfix/*` - срочные исправления

### Процесс разработки

```bash
# 1. Создание ветки
git checkout develop
git pull origin develop
git checkout -b feature/new-feature

# 2. Разработка
# ... делаем изменения ...
git add .
git commit -m "feat: add new feature"

# 3. Push
git push origin feature/new-feature

# 4. Создание Pull Request
# Через GitHub/GitLab interface

# 5. Code Review
# Ожидание ревью и внесение правок

# 6. Merge
# После одобрения
```

### Commit Messages

Следуем [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: Новая функция
- `fix`: Исправление бага
- `docs`: Документация
- `style`: Форматирование
- `refactor`: Рефакторинг
- `test`: Тесты
- `chore`: Рутинные задачи

**Примеры:**

```bash
feat(payments): add FreeKassa integration
fix(subscriptions): correct end date calculation
docs(api): update webhook documentation
refactor(services): extract common logic
test(balance): add unit tests for balance service
```

## Создание миграций

```bash
# Создание новой миграции
alembic revision --autogenerate -m "add new table"

# Применение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1

# История
alembic history

# Текущая версия
alembic current
```

## Отладка

### Локальная отладка

```python
# Добавьте в код
import pdb; pdb.set_trace()

# Или используйте breakpoint()
breakpoint()
```

### VS Code Debug Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Bot",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

## Code Review Guidelines

### Что проверять

- [ ] Код следует стандартам проекта
- [ ] Есть тесты для новой функциональности
- [ ] Документация обновлена
- [ ] Нет hardcoded значений
- [ ] Обработка ошибок корректна
- [ ] Нет SQL injection уязвимостей
- [ ] Логирование добавлено где необходимо

### Комментарии

Используйте конструктивные комментарии:

✅ **Хорошо:**
```
Предлагаю использовать list comprehension для улучшения читаемости:
`result = [x for x in items if x.is_active]`
```

❌ **Плохо:**
```
Этот код ужасен, переписывай.
```

## Полезные команды

```bash
# Проверка типов
mypy bot/

# Проверка безопасности
bandit -r bot/

# Проверка зависимостей
pip-audit

# Генерация requirements
pip freeze > requirements.txt

# Обновление зависимостей
pip install --upgrade -r requirements.txt
```

## Дополнительные ресурсы

- [API Documentation](../api/README.md)
- [Deployment Guide](../deployment/README.md)
- [Operations Guide](../operations/README.md)
- [Python Best Practices](https://docs.python-guide.org/)
- [aiogram Documentation](https://docs.aiogram.dev/)