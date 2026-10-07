import re

target_file = '04-backend/tests/test_stage2_hardening.py'
with open(target_file, 'r') as f:
    content = f.read()

content = content.replace(
    'await connector.fetch_metrics()',
    'await connector.fetch_metrics(date(2026, 9, 1), date(2026, 9, 1))'
)
# Ensure date is imported
if 'from datetime import date' not in content:
    content = 'from datetime import date\n' + content

with open(target_file, 'w') as f:
    f.write(content)
