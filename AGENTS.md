# FinanceIntel — правила для AI-агентов
SaaS финансового учёта для медиабаинга. Виртуальный CFO поверх трекеров.
Стадия: Stage 1 "Financial Core". Всё, чего нет в 02-product-docs/MVP.md, вне скоупа.

## Структура
02-product-docs/ PRD, MVP, ROADMAP, DB_SCHEMA, OPEN_QUESTIONS (источник правды)
03-database/ init-скрипты
04-backend/ FastAPI + SQLAlchemy 2.0 + Alembic + Celery
05-frontend/ Next.js 16.2.10 + React 19 + Tailwind v4 + next-intl
08-devops/ docker-compose, деплой

## Инварианты. Нарушение = блокирующий баг
1. ДЕНЬГИ. Только Decimal / NUMERIC(20,4). float в финансовых расчётах запрещён. Округление ROUND_HALF_UP до 4 знаков. Валюта хранится рядом с суммой.
2. ТЕНАНТЫ. company_id берётся ТОЛЬКО из JWT-сессии. Никогда из тела запроса, query-параметра или аргумента LLM-инструмента. Плюс RLS в Postgres.
3. CR-1. AI Analyst отвечает только через tool use с реальным SQL к БД. Если модель не вызвала ни одного инструмента, ответ пользователю НЕ уходит. Мокать ответы AI запрещено даже временно.
4. PCI. Полные номера карт и пароли прокси не хранятся. Только маскированный идентификатор (последние 4 символа).
5. СЕКРЕТЫ. Не логируются, не попадают в контекст LLM.
6. SOFT DELETE. deleted_at вместо DELETE на всех финансовых таблицах.
7. ВРЕМЯ. TIMESTAMPTZ в UTC. created_at/updated_at везде.
8. ИДЕМПОТЕНТНОСТЬ. UNIQUE (company_id, source, external_id) на импортируемых.

## Backend
- Логика в services/, роутеры тонкие. SQL только в repositories/services.
- Pydantic v2, condecimal(max_digits=20, decimal_places=4) для сумм.
- Каждый новый роут покрывается тестом изоляции тенантов.
- Миграции только через alembic revision --autogenerate, ручная проверка diff.

## Frontend
- Экраны в src/components/screens/, страницы только импортируют их.
- Навигация через Link/usePathname из @/i18n/routing, НЕ из next/link.
- Тексты в messages/en.json и messages/ru.json. Хардкод строк в JSX запрещён.
- Цвета из токенов Tailwind @theme (bg-surface, text-content-secondary). Палитра ai-* только для AI-блоков.
- Деньги через lib/formatters. Иконки lucide-react. Графики recharts.
- Данные через TanStack Query + src/lib/api. Прямой импорт из mockData запрещён.
- Next.js 16 свежее твоих тренировочных данных: перед написанием читай node_modules/next/dist/docs/.

## Вне скоупа сейчас
Market Intelligence, парсинг Telegram, 06-admin-frontend, коннекторы к рекламным API, Forecasting, Scenario Modeling, свой инференс. Не предлагать, не писать.
