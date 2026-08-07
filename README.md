# FinanceIntel

![Backend CI](https://github.com/leavellkeishia711-ctrl/inteintefin/actions/workflows/backend.yml/badge.svg)
![Frontend CI](https://github.com/leavellkeishia711-ctrl/inteintefin/actions/workflows/frontend.yml/badge.svg)
![Production Gate](https://github.com/leavellkeishia711-ctrl/inteintefin/actions/workflows/prod-gate.yml/badge.svg)
SaaS финансового учёта для медиабаинговых команд. Виртуальный CFO поверх трекеров.

👉 **[Текущий статус готовности MVP (Stage 1)](02-product-docs/MVP_STATUS.md)** 👈

## Главные документы
- [Большой план проекта (новая версия v4)](<Большой план проекта (новая версия v4)_ FinanceIntel после Stage 1-20260807.txt>)
- [КОНТЕКСТ-ОПИСАНИЕ ПРОЕКТА (самая новая 6 версия)](<КОНТЕКСТ-ОПИСАНИЕ ПРОЕКТА (самая новая 6 версия).txt>)
- [Большой план проекта (прошлая версия v3)](<Большой план проекта (прошлая версия v3)_ FinanceIntel после Stage 1-20260807.txt>)
- [КОНТЕКСТ-ОПИСАНИЕ ПРОЕКТА (прошлая 5 версия)](<КОНТЕКСТ-ОПИСАНИЕ ПРОЕКТА (прошлая 5 версия).txt>)

## Структура проекта

- `01-design/`: Дизайн-материалы, макеты.
- `02-product-docs/`: Источник правды по требованиям (PRD, MVP, ROADMAP, DB_SCHEMA, OPEN_QUESTIONS)
- `03-database/`: Инициализационные скрипты БД (пусто)
- `04-backend/`: Бэкенд на FastAPI, SQLAlchemy 2.0, Alembic, Celery
- `05-frontend/`: Фронтенд на Next.js 16 (App Router), React 19, Tailwind v4, next-intl
- `08-devops/`: Конфигурации для развертывания, docker-compose
- `09-reference/`: Справочные материалы.
- `scripts/`: Вспомогательные скрипты.
- `scratch/`: Временная папка.
- `archive/`: Старые логи и переписки агентов. НЕ ЧИТАТЬ КАК ИСТОЧНИК ПРАВДЫ.

Примечание: Папок 06-market-intelligence и 07-integrations в текущем скоупе (Stage 1) нет, они удалены или не создавались.