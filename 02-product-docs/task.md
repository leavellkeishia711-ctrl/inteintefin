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
- [x] Telegram rate limiter: внедрён Bounded In-Memory Limiter (TTL 60s, asyncio.Lock(), max 10000 записей) как fallback при `ConnectionError`/`TimeoutError`
- [x] Негативные тесты на Tenant Isolation: подтверждены HTTP, Celery (утечки контекста) и повторное использование `/link` токена.
- [x] AI Analyst (IDOR/Утечки): LLM получает только общую заглушку `Internal error during tool execution.`, payload полностью очищен от ORM-полей и ID.
- [x] Успешный запуск `pytest -q` (48 passed)
- [x] Успешный запуск `alembic upgrade head`
- [x] Успешный запуск `npm run lint` (0 ошибок, 0 предупреждений)
- [x] Успешный запуск `npm run build`
- [x] Успешный запуск `check_floats.py`

## Текущий Backlog (Вне скоупа Stage 1)

### Ожидает реализации (Stage 2+)
- [ ] Market Intelligence (Сбор данных о рынке и бенчмарках)
- [ ] Парсинг Telegram (Чтение сообщений из партнёрок/чатов для автоматизации)
- [ ] `06-admin-frontend` (Панель суперадмина)
- [ ] Коннекторы к рекламным API (Facebook, Google Ads, TikTok API)
- [ ] Forecasting (Прогнозирование Cash Runway на ML)
- [ ] Scenario Modeling (Моделирование "Что если поднимем бюджет на 20%")
- [ ] Свой инференс (Отказ от Anthropic в пользу self-hosted моделей)

> **Внимание:** Все задачи из Backlog находятся вне текущего скоупа. Не предлагать и не писать код для них.
