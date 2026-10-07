import re

target_file = '04-backend/tests/test_meta_ads_connector.py'
with open(target_file, 'r') as f:
    content = f.read()

# Fix fetch_metrics missing dates for retry/unauthorized tests
content = content.replace(
    'await connector.fetch_metrics()',
    'await connector.fetch_metrics(datetime(2026, 9, 1, tzinfo=timezone.utc).date(), datetime(2026, 9, 1, tzinfo=timezone.utc).date())'
)

with open(target_file, 'w') as f:
    f.write(content)
