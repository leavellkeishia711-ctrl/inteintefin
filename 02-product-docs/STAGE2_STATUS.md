# Stage 2: Data Connectors Status

## Текущий статус: PARTIAL (In Progress)

| Requirement | Status | Evidence / Notes |
|-------------|--------|------------------|
| **Connector Configuration & Encrypted Credentials** | ✅ Done | 	est_api_persistence_create, 	est_api_create_connector (Backend CI Run 33848386533). Рендеринг замаскированного ключа, шифрование на стороне БД. |
| **Celery Beat Sync Scheduling** | ✅ Done | Успешное выполнение celery_smoke_ci.py в Production Gate (Run 33848386451), расписание настроено в celery.py. |
| **Keitaro Tracker** | ✅ Done | Интеграционные мок-тесты в 	est_connectors.py (Backend CI Run 33848386533). |
| **Data Quality (DQ) metrics** | ✅ Done | Частично имплементировано и валидируется на базовом уровне в schemas/connectors.py (поля last_attempted_sync, last_successful_sync). |
| **Binom, Voluum, Affise (Трекеры)** | ⬜ Open | В ожидании реализации (намечено на следующие итерации). |
| **Meta Ads, Google Ads, TikTok Ads** | ⬜ Open | В ожидании реализации (намечено на следующие итерации). |
| **ad_accounts (Управление кабинетами)** | ⬜ Open | Модель и маппинг d_accounts -> campaigns не реализованы. |
| **Ротация ключей, Rate Limits, Backoff** | ⬜ Open | Требует внедрения единой политики через connectors/base.py. |
