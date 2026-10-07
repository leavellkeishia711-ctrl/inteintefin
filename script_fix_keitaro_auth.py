import re

target_file = '04-backend/tests/test_pr_a_data_integrity.py'
with open(target_file, 'r') as f:
    content = f.read()

content = content.replace('def test_keitaro_create_blocked(auth_client, company_b_fixtures):', 'def test_keitaro_create_blocked(client_b):')
content = content.replace('await auth_client.post', 'await client_b.post')

with open(target_file, 'w') as f:
    f.write(content)
