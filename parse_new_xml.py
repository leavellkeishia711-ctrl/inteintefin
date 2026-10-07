import xml.etree.ElementTree as ET

tree = ET.parse(r'C:\Users\fylht\Desktop\new_pytest_extract\pytest-results.xml')
root = tree.getroot()

if root.tag == 'testsuites':
    ts = root.find('testsuite')
else:
    ts = root

print(f'Summary: tests={ts.get("tests")}, failures={ts.get("failures")}, errors={ts.get("errors")}, skipped={ts.get("skipped")}')

target_tests = [
    'test_patch_connector_settings_semantics',
    'test_connector_settings_tenant_isolation',
    'test_connector_settings_patch_validate_true',
    'test_connector_settings_audit'
]

statuses = {t: 'absent' for t in target_tests}

for tc in ts.findall('testcase'):
    name = tc.get('name', '')
    nodeid = tc.get('classname', '') + '.' + name
    
    status = 'passed'
    fail_node = tc.find('failure')
    err_node = tc.find('error')
    skip_node = tc.find('skipped')
    
    if fail_node is not None:
        status = 'failed'
        print(f'\n--- FAILURE: {nodeid} ---')
        print(f'Message: {fail_node.get("message")}')
        print(f'Traceback:\n{fail_node.text}')
    elif err_node is not None:
        status = 'error'
        print(f'\n--- ERROR: {nodeid} ---')
        print(f'Message: {err_node.get("message")}')
        print(f'Traceback:\n{err_node.text}')
    elif skip_node is not None:
        status = 'skipped'
        
    for t in target_tests:
        if t in name:
            statuses[t] = status

print('\n--- STATUSES ---')
for k, v in statuses.items():
    print(f'{k}: {v}')
