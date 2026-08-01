# DB_SCHEMA — нормализованная схема для MVP (Stage 1)

> Покрывает только **Financial Core** (`MVP.md`). Таблицы Market Intelligence и коннекторов добавляются на своих стадиях (см. `ROADMAP.md`).
> СУБД: PostgreSQL. Все денежные суммы — `NUMERIC(20,4)` (никогда не `float`). Время — `TIMESTAMPTZ` (UTC).

---

## Принципы

1. **Мультитенантность:** каждая доменная таблица содержит `company_id`. Все запросы фильтруются по нему (Row-Level Security или обязательный фильтр в repository-слое).
2. **Деньги — decimal.** `NUMERIC(20,4)`. Валюта хранится рядом с суммой.
3. **Мультивалютность:** сумма всегда в исходной валюте + обязательно курс на дату операции (`fx_rate_to_base`). Для базовой валюты компании курс = 1. Курс фиксируется на дату операции.
4. **Аудит времени:** `created_at`, `updated_at` во всех таблицах.
5. **Мягкое удаление:** `deleted_at NULL` вместо физического удаления.
6. **Идемпотентность импорта:** `external_id` + `source` с уникальным индексом.
7. **Источники правды:** P&L и фактические деньги = `transactions`; рекламная статистика = `campaign_run_stats`; `campaigns` и `campaign_runs` = сущности и агрегаты.
8. **Безопасность:** Запрещены связи между разными компаниями. Использовать составные FK или триггеры.
9. **Контроль типов:** Добавить `CHECK` или `enum` для всех `type`, `status`, `role`, `category`, `source`.

---

## Таблицы

### companies
```sql
id              UUID PK
name            TEXT NOT NULL
base_currency   CHAR(3) NOT NULL          -- ISO 4217, базовая валюта отчётности
budget_requests_frozen BOOLEAN NOT NULL DEFAULT false -- Отложено до Stage 5
default_language TEXT NOT NULL DEFAULT 'en' -- en | ru
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL
```
*(Примечание: `cash_balance` удалён, вычисляется из `transactions`)*

### fx_rates
```sql
id              UUID PK
rate_date       DATE NOT NULL
from_currency   CHAR(3) NOT NULL
to_currency     CHAR(3) NOT NULL
rate            NUMERIC(20,8) NOT NULL
source          TEXT NOT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

CHECK (rate > 0)
CHECK (from_currency <> to_currency)

UNIQUE (rate_date, from_currency, to_currency, source)
```

### users
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
name            TEXT NOT NULL
email           CITEXT NOT NULL
password_hash   TEXT NOT NULL             -- Argon2id: m=65536, t=3, p=4
role            TEXT NOT NULL             -- owner|cfo|team_lead|media_buyer|farmer|processor|creative|admin
preferred_language TEXT NULL               -- en | ru
telegram_user_id BIGINT NULL UNIQUE        -- идентификатор пользователя в Telegram
telegram_chat_id BIGINT NULL UNIQUE        -- ID чата для отправки уведомлений
telegram_linked_at TIMESTAMPTZ NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL

UNIQUE (company_id, email) WHERE deleted_at IS NULL
CHECK (role IN ('owner','cfo','team_lead','media_buyer','farmer','processor','creative','admin'))
```

### telegram_link_tokens
```sql
id              UUID PK
user_id         UUID FK -> users(id) NOT NULL
token_hash      TEXT NOT NULL UNIQUE
expires_at      TIMESTAMPTZ NOT NULL
used_at         TIMESTAMPTZ NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

CHECK (expires_at > created_at)
INDEX (user_id, expires_at)
```

### invites
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
email           CITEXT NOT NULL
role            TEXT NOT NULL
token_hash      TEXT NOT NULL UNIQUE
invited_by      UUID FK -> users(id) NOT NULL
expires_at      TIMESTAMPTZ NOT NULL
accepted_at     TIMESTAMPTZ NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

CHECK (role IN ('owner','cfo','team_lead','media_buyer','farmer','processor','creative','admin'))
INDEX (company_id, email)
INDEX (email, expires_at) WHERE accepted_at IS NULL
```

### teams
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
name            TEXT NOT NULL
lead_user_id    UUID FK -> users(id) NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL
```

### import_batches
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
filename        TEXT NOT NULL
row_count       INTEGER NOT NULL DEFAULT 0
error_count     INTEGER NOT NULL DEFAULT 0
status          TEXT NOT NULL
created_by      UUID FK -> users(id) NOT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
completed_at    TIMESTAMPTZ NULL

CHECK (row_count >= 0)
CHECK (error_count >= 0)
CHECK (status IN ('pending','processing','completed','completed_with_errors','failed','rolled_back'))
INDEX (company_id, created_at)
```

### transactions
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
import_batch_id UUID FK -> import_batches(id) NULL
type            TEXT NOT NULL             -- income | expense
category        TEXT NOT NULL             -- ad_spend, salary, infra, tax, payout_incoming, payout_outgoing, consumables, depreciation, interest, other
amount          NUMERIC(20,4) NOT NULL    -- в валюте currency
currency        CHAR(3) NOT NULL
fx_rate_to_base NUMERIC(20,8) NOT NULL    -- курс к base_currency на occurred_on
occurred_on     DATE NOT NULL             -- дата операции
team_id         UUID FK -> teams(id) NULL
description     TEXT NULL
source          TEXT NOT NULL DEFAULT 'manual'  -- manual | csv | derived | <connector>
external_id     TEXT NULL
created_by      UUID FK -> users(id) NOT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL

UNIQUE (company_id, source, external_id) WHERE external_id IS NOT NULL
INDEX (company_id, occurred_on)
INDEX (company_id, type, category)
CHECK (type IN ('income', 'expense'))
CHECK (category IN ('ad_spend', 'salary', 'infra', 'tax', 'payout_incoming', 'payout_outgoing', 'consumables', 'depreciation', 'interest', 'other'))
```
*(Примечание: `transactions` не создаются автоматически из `campaign_run_stats`. Если создаются, то с `source='derived'` и исключаются из P&L при наличии оригинала)*

### ad_accounts
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
platform        TEXT NOT NULL
external_account_id TEXT NULL
status          TEXT NOT NULL             -- active | warming | banned | suspended
prepared_by_user_id UUID FK -> users(id) NULL
assigned_buyer_id   UUID FK -> users(id) NULL
vertical        TEXT NULL
geo             TEXT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
banned_at       TIMESTAMPTZ NULL
deleted_at      TIMESTAMPTZ NULL

INDEX (company_id, platform, status)
INDEX (company_id, prepared_by_user_id, created_at)
CHECK (status IN ('active', 'warming', 'banned', 'suspended'))
```

### campaigns
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
team_id         UUID FK -> teams(id) NULL
assigned_user_id UUID FK -> users(id) NULL
ad_account_id   UUID FK -> ad_accounts(id) NULL
source          TEXT NULL                 
platform        TEXT NULL                 
geo             TEXT NULL
vertical        TEXT NULL                 
funding_status  TEXT NOT NULL DEFAULT 'active' -- Отложено до Stage 5
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL
```

### campaign_runs (заливы)
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
campaign_id     UUID FK -> campaigns(id) NULL
ad_account_id   UUID FK -> ad_accounts(id) NULL
buyer_id        UUID FK -> users(id) NOT NULL   
started_at      TIMESTAMPTZ NOT NULL
ended_at        TIMESTAMPTZ NULL               
status          TEXT NOT NULL DEFAULT 'active' -- active | stopped | banned
note            TEXT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL

INDEX (company_id, buyer_id, started_at)
INDEX (company_id, ad_account_id, started_at)
CHECK (status IN ('active', 'stopped', 'banned'))
```

### campaign_run_stats
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
campaign_run_id UUID FK -> campaign_runs(id) NOT NULL
stat_date       DATE NOT NULL
spend           NUMERIC(20,4) NOT NULL DEFAULT 0
revenue         NUMERIC(20,4) NOT NULL DEFAULT 0
currency        CHAR(3) NOT NULL
fx_rate_to_base NUMERIC(20,8) NOT NULL
source          TEXT NOT NULL
external_id     TEXT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()

UNIQUE (company_id, campaign_run_id, stat_date, source, external_id)
INDEX (company_id, campaign_run_id, stat_date)
```

### consumables (расходники)
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
type            TEXT NOT NULL             -- proxy | card | account_service | other
ad_account_id   UUID FK -> ad_accounts(id) NULL
identifier      TEXT NULL                 -- маскированный идентификатор
cost            NUMERIC(20,4) NOT NULL DEFAULT 0
currency        CHAR(3) NOT NULL
fx_rate_to_base NUMERIC(20,8) NOT NULL
purchased_on    DATE NOT NULL
expires_on      DATE NULL
status          TEXT NOT NULL DEFAULT 'active' -- active | expired | burned
transaction_id  UUID FK -> transactions(id) NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL

INDEX (company_id, type, status)
INDEX (company_id, ad_account_id)
CHECK (type IN ('proxy', 'card', 'account_service', 'other'))
CHECK (status IN ('active', 'expired', 'burned'))
```
> ⚠️ **Security note:** Полные данные карт и пароли не хранятся, только маскированные.

### affiliate_networks
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
name            TEXT NOT NULL
payment_terms   TEXT NOT NULL             
payout_model    TEXT NOT NULL             
typical_hold_days INT NOT NULL DEFAULT 14
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL
```

### partner_payouts
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
network_id      UUID FK -> affiliate_networks(id) NOT NULL
campaign_id     UUID FK -> campaigns(id) NULL
buyer_id        UUID FK -> users(id) NULL
amount          NUMERIC(20,4) NOT NULL    -- legacy field for backwards comp, or use expected_amount/actual_amount
expected_amount NUMERIC(20,4) NOT NULL
scrubbed_amount NUMERIC(20,4) NOT NULL DEFAULT 0
actual_amount   NUMERIC(20,4) NOT NULL DEFAULT 0
currency        CHAR(3) NOT NULL
fx_rate_to_base NUMERIC(20,8) NOT NULL
status          TEXT NOT NULL             -- booked | in_hold | scrubbed | paid
booked_on       DATE NOT NULL             
hold_until      DATE NULL                 
paid_on         DATE NULL                 
transaction_id  UUID FK -> transactions(id) NULL 
note            TEXT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL

INDEX (company_id, network_id, status)
INDEX (company_id, hold_until)
CHECK (status IN ('booked', 'in_hold', 'scrubbed', 'paid'))
```

### alerts
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NULL   
type            TEXT NOT NULL             
risk_level      TEXT NOT NULL             -- low | medium | high
message         TEXT NOT NULL
dedup_key       TEXT NOT NULL
cooldown_until  TIMESTAMPTZ NULL
triggered_at    TIMESTAMPTZ NOT NULL DEFAULT now()
acknowledged_by UUID FK -> users(id) NULL
acknowledged_at TIMESTAMPTZ NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

INDEX (company_id, triggered_at)
UNIQUE (company_id, dedup_key, (triggered_at::date))
CHECK (risk_level IN ('low', 'medium', 'high'))
```

### audit_log
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
actor_user_id   UUID FK -> users(id) NULL   
entity_type     TEXT NOT NULL             
entity_id       UUID NULL
action          TEXT NOT NULL             -- create | update | delete
diff            JSONB NULL                
request_id      UUID NULL
ip_address      INET NULL
user_agent      TEXT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

INDEX (company_id, created_at)
INDEX (entity_type, entity_id)
```

### compensation_plans
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
user_id         UUID FK -> users(id) NOT NULL
base_salary     NUMERIC(20,4) NOT NULL DEFAULT 0
bonus_percent   NUMERIC(5,2) NOT NULL DEFAULT 0  
bonus_basis     TEXT NOT NULL             -- profit | revenue | net_profit | quota | piece_rate
quota_target    NUMERIC(20,4) NULL        
rate_per_unit   NUMERIC(20,4) NULL        
currency        CHAR(3) NOT NULL
fx_rate_to_base NUMERIC(20,8) NOT NULL
effective_from  DATE NOT NULL
effective_to    DATE NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL

-- PostgreSQL EXCLUDE USING gist (user_id WITH =, daterange(effective_from, effective_to) WITH &&)
CHECK (bonus_basis IN ('profit', 'revenue', 'net_profit', 'quota', 'piece_rate'))
```

### payroll_runs
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
period_start    DATE NOT NULL
period_end      DATE NOT NULL
status          TEXT NOT NULL             -- draft | approved | paid
total_amount    NUMERIC(20,4) NOT NULL DEFAULT 0
currency        CHAR(3) NOT NULL
fx_rate_to_base NUMERIC(20,8) NOT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL

CHECK (status IN ('draft', 'approved', 'paid'))
```

### payroll_line_items
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
payroll_run_id  UUID FK -> payroll_runs(id) NOT NULL
user_id         UUID FK -> users(id) NOT NULL
base_amount     NUMERIC(20,4) NOT NULL DEFAULT 0
bonus_amount    NUMERIC(20,4) NOT NULL DEFAULT 0
total_amount    NUMERIC(20,4) NOT NULL DEFAULT 0
currency        CHAR(3) NOT NULL
fx_rate_to_base NUMERIC(20,8) NOT NULL
status          TEXT NOT NULL DEFAULT 'draft' -- draft | approved | paid | held
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()

CHECK (status IN ('draft', 'approved', 'paid', 'held'))
```

### decision_recommendations
```sql
recommendation_id UUID PK
company_id      UUID FK -> companies(id) NOT NULL
campaign_id     UUID FK -> campaigns(id) NULL
type            TEXT NOT NULL
vertical        TEXT NULL
geo             TEXT NULL
field           TEXT NOT NULL
current_value   NUMERIC(20,4) NULL
recommended_value NUMERIC(20,4) NOT NULL
change_percent  NUMERIC(10,2) NULL
reasoning       TEXT NOT NULL
confidence_score NUMERIC(5,2) NOT NULL
status          TEXT NOT NULL DEFAULT 'recommended' -- recommended | approved | executed | rejected
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at      TIMESTAMPTZ NULL
created_by      TEXT NULL

INDEX (company_id, created_at)
CHECK (status IN ('recommended', 'approved', 'executed', 'rejected'))
```
*(Примечание: Stage 5 - мультитенантная)*

### chat_messages
```sql
id              UUID PK
company_id      UUID FK -> companies(id) NOT NULL
user_id         UUID FK -> users(id) NOT NULL
role            TEXT NOT NULL             -- user | assistant
content         TEXT NOT NULL
tool_calls_used JSONB NULL                
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

INDEX (company_id, user_id, created_at)
CHECK (role IN ('user', 'assistant'))
```
> ⚠️ **Data Policy:** История чатов и вызовы инструментов логируются для контекста. Финансовые секреты маскируются на уровне бэкенда.

---

## Производные метрики (вычисляются, не хранятся)

| Метрика | Формула |
|---|---|
| Gross Profit | `revenue − ad_spend` |
| EBITDA | `gross_profit − (salary + infra + other + consumables)` |
| EBIT | `EBITDA − depreciation` |
| EBT | `EBIT − interest` |
| Net Profit | `EBT − tax` |
| Margin % | `(Прибыль уровня / revenue) * 100` (если `revenue=0` возвращает `NULL`) |
| ROI | `(revenue − spend) / spend * 100` (если `spend=0` возвращает `NULL`) |
| ROAS | `revenue / spend` (если `spend=0` возвращает `NULL`) |
| Cash Runway (дней) | Окно 30 дней: `avg_daily_spend = expenses_last_30_days / 30`. Формула: `available_balance / avg_daily_spend`. Если расходов нет — `NULL`. |
| Available Balance | `cash_balance (из transactions) - SUM(partner_payouts.amount WHERE status IN ('booked','in_hold'))` |
| Finance Health Score | Формула: `0.4 * MarginScore + 0.4 * RunwayScore + 0.2 * TrendScore`. Ограничение диапазона `0..100`. |

Хранить только исходные суммы; метрики считать на лету или в materialized view.

### P&L Mapping
*   `payout_incoming` = Revenue
*   `ad_spend`, `consumables` = Direct Costs (Cost of Goods Sold)
*   `salary`, `infra`, `other`, `payout_outgoing` = Operating Expenses
*   `depreciation` = EBIT Adjustment
*   `interest` = EBT Adjustment
*   `tax` = Net Profit Adjustment

**Примечание:** Для корректного подсчёта EBITDA `consumables` должны учитываться отдельной статьёй, а не входить в `ad_spend`.

---

## Что добавится позже (ссылки на стадии)

- **Stage 2:** таблица `connectors` (credentials, статус синка, last_synced_at).
- **Stage 4:** `intelligence_sources`, `raw_signals`, `detected_patterns`, `moderation_log`, `forecast_accuracy`, `company_vertical_watchlist`, `ai_generated_posts`, `impact_briefs`.

---
