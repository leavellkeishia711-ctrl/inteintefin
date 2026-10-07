import re
import os

target_file = '04-backend/tests/test_normalized_record_metrics.py'
with open(target_file, 'r') as f:
    content = f.read()

content = content.replace(
    '{"campaign_id": "123",',
    '{"campaign_id": "123", "date_stop": "2026-01-01",'
)
content = content.replace(
    '{"campaign_id": "1", "date_start": "2026-01-01",',
    '{"campaign_id": "1", "date_start": "2026-01-01", "date_stop": "2026-01-01",'
)

with open(target_file, 'w') as f:
    f.write(content)
