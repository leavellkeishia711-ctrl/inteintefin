import re

target_file = '04-backend/tests/test_meta_ads_connector.py'
with open(target_file, 'r') as f:
    content = f.read()

content = content.replace(
    '"date_start": "2026-09-01", "spend"',
    '"date_start": "2026-09-01", "date_stop": "2026-09-01", "spend"'
)
content = content.replace(
    '"date_start": "2026-09-02", "spend"',
    '"date_start": "2026-09-02", "date_stop": "2026-09-02", "spend"'
)
content = content.replace(
    '"date_start": "2026-09-03", "spend"',
    '"date_start": "2026-09-03", "date_stop": "2026-09-03", "spend"'
)

with open(target_file, 'w') as f:
    f.write(content)
