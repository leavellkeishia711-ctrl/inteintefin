# Отчёт о Staging Smoke-Тестировании (Stage 1)

## Окружение и Конфигурация (Локально)
- **ОС**: Windows.
- **СУБД**: PostgreSQL 16 (локально, не Docker).
- **Backend**: FastAPI, Python 3.11, SQLAlchemy 2.0. uvicorn --workers 2.
- **Frontend**: Next.js 16.2.10, Node.js.
- **Внимание**: Linux/Docker, PostgreSQL 16 + Redis 7 + Celery worker/beat не запускались.

## Выполненные базовые проверки
- `pytest tests/ -q`: 48 passed, 0 failed;
- `check_floats.py`: passed;
- `alembic upgrade head`: passed;
- `npm run lint`: 0 errors, 0 warnings;
- `npm run build`: passed.

## Проверки функционала и изоляции
- **HTTP**: `reports`, `transactions`, `payroll`, `alerts` возвращают 404/пустые массивы для чужих ID. Попытки подменить `company_id` игнорируются, так как тенант берётся строго из JWT.
- **Celery Worker & Beat**: Утечек контекста нет. Транзакции успешно используют `SET LOCAL app.company_id` и очищают контекст.
- **AI Analyst**: 
  - Успешный `tool_use` заставляет LLM продолжить цикл до финального ответа.
  - Ошибка `tool_use` маскируется под `Internal error during tool execution.`. Тресы, SQL, схемы БД не раскрываются.
  - Инструменты отдают словари без ORM-метаданных, `id`, `company_id`. Кросс-тенантные запросы блокируются на уровне SQL.
- **Безопасность**:
  - Неверный webhook secret отклоняется.
  - Expired и повторно использованный link token отклоняются.
  - В логах отсутствуют bot token, Redis URL, JWT secret, chat_id и link token.

## Выполнение локального нагрузочного Smoke-теста (uvicorn --workers 2)
1. **Тест `/link` (100 параллельных запросов при Redis outage)**:
   - Все 100 запросов получили ответ 503.
   - Токены не использованы.
   - in-memory fallback для `/link` не использовался.
2. **Тест `/status`**:
   - Использован best-effort in-memory limiter.
   
## Вердикт

**STAGING ACCEPTED** 🟢
Тестирование логики и изоляции пройдено в рамках доступного окружения (Windows).

**PRODUCTION BLOCKED** 🔴
Причина: упавшие CI-джобы
- `Production Gate` (Run ID: 31216615005, 31216476017) упал из-за ошибки старта docker-compose стека.
- `Frontend CI` (Run ID: 31216614993, 31216475943) упал на шаге установки зависимостей (npm install).

Необходимо дождаться зелёных CI-пайплайнов.
