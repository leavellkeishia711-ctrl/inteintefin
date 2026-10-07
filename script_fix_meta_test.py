import re
import os

target_file = '04-backend/tests/test_meta_ads_connector.py'
with open(target_file, 'r') as f:
    content = f.read()

# Add date_stop to missing ones
content = content.replace(
    '{"campaign_id": "fx_camp_1", "date_start": "2026-09-01", "spend": "100.00", "_currency": "USD", "clicks": 10, "impressions": 100}',
    '{"campaign_id": "fx_camp_1", "date_start": "2026-09-01", "date_stop": "2026-09-01", "spend": "100.00", "_currency": "USD", "clicks": 10, "impressions": 100}'
)
content = content.replace(
    '{"campaign_id": "fx_camp_2", "date_start": "2026-09-10", "spend": "50.00", "_currency": "USD", "clicks": 10, "impressions": 100}',
    '{"campaign_id": "fx_camp_2", "date_start": "2026-09-10", "date_stop": "2026-09-10", "spend": "50.00", "_currency": "USD", "clicks": 10, "impressions": 100}'
)
content = content.replace(
    '{"campaign_id": "100", "date_start": "2026-09-01", "spend": "10.50", "clicks": 10, "impressions": 100}',
    '{"campaign_id": "100", "date_start": "2026-09-01", "date_stop": "2026-09-01", "spend": "10.50", "clicks": 10, "impressions": 100}'
)

# Fix fetch_metrics missing dates
content = content.replace(
    'metrics = await connector.fetch_metrics()',
    'metrics = await connector.fetch_metrics(datetime(2026, 9, 1, tzinfo=timezone.utc).date(), datetime(2026, 9, 1, tzinfo=timezone.utc).date())'
)

with open(target_file, 'w') as f:
    f.write(content)
