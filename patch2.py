import re

file_path = '04-backend/tests/test_stage2_hardening.py'
with open(file_path, 'r') as f:
    content = f.read()

content = content.replace(
    '{"campaign_id": "100", "date_start": "2026-09-01", "spend":',
    '{"campaign_id": "100", "date_start": "2026-09-01", "date_stop": "2026-09-01", "spend":'
)

with open(file_path, 'w') as f:
    f.write(content)
