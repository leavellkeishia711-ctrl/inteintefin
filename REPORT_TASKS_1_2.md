# Отчёт по задаче 1: ECB FX PR (`feat/ecb-fx-auto-fetch`)

## Причина падения Backend CI
1. **Ошибка:** Падение происходило в тесте `test_csv_import_fx_rate_triangulation`, где `txn is None` (ранее была исправлена ошибка изоляции БД в `test_sync_ecb_rates_idempotent_and_conflict`).
2. **Первопричина:** Неправильный маппинг колонок (CSV Header vs DB Field) в тестовом запросе. Словарь `mapping` в тесте ожидал `{"Date": "transaction_date"}`, тогда как API ожидает ключи в виде колонок БД: `{"occurred_on": "Date"}`. Из-за этого импорт прерывался без создания транзакции.
3. **Вторая ошибка:** В `tests/test_csv_import_coverage.py` assertion проверял `txn.amount_base` — атрибута, которого нет в модели `Transaction`.
4. **Исправление:** 
   - Исправлен `mapping` в `test_csv_import_fx_rate_triangulation` на правильный (`"occurred_on": "Date"`, и т.д.).
   - Добавлены assertions на `imported == 1` и `errors == 0`, чтобы падение импорта отлавливалось сразу.
   - Исправлено свойство для проверки курса в базе: теперь сравнивается `txn.fx_rate_to_base`.
5. **Текущий SHA:** `c1c2779b`
6. **Открытие PR:** У меня нет токена GitHub (отсутствует `GITHUB_TOKEN` и не установлен `gh CLI`), поэтому я физически не могу открыть PR через API (получаю ошибку `rate limit exceeded` и отсутствие прав). Ссылка для самостоятельного создания PR: https://github.com/leavellkeishia711-ctrl/inteintefin/pull/new/feat/ecb-fx-auto-fetch

---

# Отчёт по задаче 2: Stage 1 Bug-Fix PR (`fix/stage1-correctness`)

Ветка `fix/stage1-correctness` обновлена и отправлена (SHA: `6517b498`). Выполнены все 8 подзадач:

- **A. Payroll:** В `app/services/payroll.py` суммы прогоняются через `quantize_money`, `base_currency` берется из таблицы `Company`, `primaryjoin` на `PayrollLineItem` фильтрует `deleted_at IS NULL`.
- **B. Partner KPI:** Обновлены `app/api/v1/partners.py` (теперь используется `app.core.deps` и `UserCtx`) и `app/services/partners.py` (суммы перемножаются на `fx_rate_to_base` и квантуются `quantize_money`).
- **C. Settings Dependency:** Роутер `settings.py` переведён на `UserCtx` и `get_tenant_session`. Устаревший файл `app/api/deps.py` удалён.
- **D. P&L Category:** Из `pnl.py` удалено обращение к мёртвой категории `sales`, доход считается только по `payout_incoming`.
- **E. Audit X-Request-ID:** В `audit.py` парсинг `x-request-id` обернут в `try-except ValueError`, при ошибке `request_id` становится `None`.
- **F. Internal Exception Leaks:** Во всех контроллерах (`campaign_runs.py`, `campaign_run_stats.py`) убрана передача текста исключения `{e}` в 500 ошибках FastAPI. В лог пишется полная ошибка (`logging.error(..., exc_info=True)`), а клиент видит "Internal server error".
- **G. Soft-Delete Filters:** Добавлено условие `deleted_at.is_(None)` во все прямые запросы (`auth.py`, `ad_accounts.py`, `consumables.py`, `campaign_runs.py`, `data_quality.py`, `invites.py`).
- **H. Cross-Tenant FK Validation:** Создан хелпер `app/services/validation.py` -> `validate_fk`, который проверяет `company_id` и `deleted_at.is_(None)`. Он интегрирован в эндпоинты `create_campaign_run`, `update_campaign_run`, `create_tx` и `update_tx`.
