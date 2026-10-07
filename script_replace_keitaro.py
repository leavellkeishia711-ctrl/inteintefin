import re

for target_file in ['04-backend/tests/test_connectors.py', '04-backend/tests/test_connectors_persistence.py']:
    with open(target_file, 'r') as f:
        content = f.read()

    content = content.replace('"connector_name": "keitaro"', '"connector_name": "meta"')
    content = content.replace('== "keitaro"', '== "meta"')
    
    with open(target_file, 'w') as f:
        f.write(content)
