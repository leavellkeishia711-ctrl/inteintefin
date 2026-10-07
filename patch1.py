import re

file_path = '04-backend/tests/test_normalized_record_metrics.py'
with open(file_path, 'r') as f:
    content = f.read()

# For test_meta_normalize_metrics
content = content.replace(
    '"campaign_id": "123",\n        "date_start": "2026-01-01",',
    '"campaign_id": "123",\n        "date_start": "2026-01-01",\n        "date_stop": "2026-01-01",'
)

with open(file_path, 'w') as f:
    f.write(content)
