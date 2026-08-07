# FinanceIntel — Task Tracker (Stage 1 "Financial Core")

## История Stage 1 (Выполнено)

### Базовая инфраструктура и БД
- [x] Инициализация проекта (FastAPI, Next.js, Postgres)
- [x] Настройка Alembic, SQLAlchemy 2.0 (asyncio)
- [x] Проектирование схемы БД (`03-database`)
- [x] Настройка RLS (Row-Level Security) на уровне Postgres
- [x] Подключение TanStack Query на фронтенде

### Финансовое Ядро (Инварианты)
- [x] Жёсткий контроль типов `Numeric(20,4)` вместо `float`
- [x] Написание `check_floats.py` для защиты от float в коде
- [x] Реализация Soft Delete (`deleted_at`) для финансовых транзакций
- [x] UTC `TIMESTAMPTZ` для всех дат (`created_at`, `updated_at`)
- [x] Идемпотентность импортов (`UNIQUE(company_id, source, external_id)`)

### Безопасность и Тенанты
- [x] Изоляция данных на основе `company_id` через JWT
- [x] RLS полностью функционирует, запросы без `company_id` падают
- [x] Маскирование PII (номера карт, пароли прокси)
- [x] Секреты не логируются и не передаются в LLM

### AI Analyst (CR-1)
- [x] Интеграция Anthropic Claude API (`tool_use` / `tool_result`)
- [x] Гарантия: AI отвечает только через Tool Use (вызов SQL к БД)
- [x] Ошибки Anthropic корректно обрабатываются, не отдаются пользователю как успешный анализ
- [x] Финальная проверка `04-backend/app/ai/client.py`
- [x] Финальная проверка `04-backend/app/ai/analyst.py`
- [x] Финальная проверка `04-backend/app/ai/tools.py`

### Преддеплойный аудит Stage 1 (Hardening)
- [x] Очистка Git-индекса от запрещённых файлов (`.env`, `__pycache__`, `pgsql`, `node_modules`)
- [x] Telegram rate limiter: внедрён режим fail-closed (503/429) для `/link` при недоступном Redis. Для некритичных команд оставлен Bounded In-Memory Limiter
- [x] Негативные тесты на Tenant Isolation: подтверждены HTTP, Celery (утечки контекста) и повторное использование `/link` токена.
- [x] AI Analyst (IDOR/Утечки): LLM получает только общую заглушку `Internal error during tool execution.`, payload полностью очищен от ORM-полей и ID.
- [x] `pytest tests/ -q`: 48 passed, 0 failed;
- [x] `alembic upgrade head`: passed;
- [x] `npm run lint`: 0 errors, 0 warnings;
- [x] `npm run build`: passed;
- [x] `check_floats.py`: passed;
- [x] Вердикт по деплою: **STAGING ACCEPTED**, **PRODUCTION BLOCKED** (причина: отсутствует подтверждённый Linux/Docker-прогон с двумя worker’ами, Celery и нагрузкой asyncpg/SQLAlchemy).

## Текущий Backlog (Вне скоупа Stage 1)

### Ожидают проверки (Блокируют Production)
- [ ] Linux/Docker Compose production-gate;
- [ ] PostgreSQL/asyncpg нагрузочный прогон;
- [ ] Redis outage при двух worker’ах;
- [ ] Celery worker/beat smoke;
- [ ] повторная проверка логов и tenant isolation.

### Ожидают реализации (Stage 2+)
- [ ] Market Intelligence (Сбор данных о рынке и бенчмарках)
- [ ] Парсинг Telegram (Чтение сообщений из партнёрок/чатов для автоматизации)
- [ ] `06-admin-frontend` (Панель суперадмина)
- [ ] Коннекторы к рекламным API (Facebook, Google Ads, TikTok API)
- [ ] Forecasting (Прогнозирование Cash Runway на ML)
- [ ] Scenario Modeling (Моделирование "Что если поднимем бюджет на 20%")
- [ ] Свой инференс (Отказ от Anthropic в пользу self-hosted моделей)

> **Внимание:** Все задачи из Backlog находятся вне текущего скоупа. Не предлагать и не писать код для них.
