# Architecture Status

- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Celery.
- **Frontend:** Next.js 16.2.10 + React 19 + Tailwind v4 + next-intl.
- **Database:** PostgreSQL with Row Level Security (RLS) for multi-tenancy. Redis for caching/celery.
- **Tenant Isolation:** Enforced via `company_id` decoded STRICTLY from JWT. RLS policies implemented at the database level.
- **Credentials:** Encrypted at rest via Fernet. Decrypted in memory during connector sync.
- **Connector Interface:** Abstract `BaseConnector` enforces contracts for `test_connection`, `fetch_ad_accounts`, `normalize`, `upsert`, etc.
- **Retry/Backoff:** Centralized wrapper in `base.with_retry` capturing `HTTPStatusError` (429, 502, 503, 504) and providing exponential backoff logic.
- **Scheduler:** Celery beat driving periodic syncs based on individual connector `sync_interval_minutes`.
- **Data Quality:** Explicit stale-source DQ checks (`monitor_stalled_data`) ensuring pipelines don't fail silently.
- **AI Analyst:** Uses real SQL tools.
- **CI/CD:** Github Actions (Backend, Frontend, Production Gate).
- **Known Technical Debt:** Normalization mappings across diverse ad networks not fully generalized.
- **Known Gaps:** Meta/Google/TikTok OAuth lifecycles.
