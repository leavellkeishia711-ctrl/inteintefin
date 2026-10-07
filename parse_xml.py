import xml.etree.ElementTree as ET
import sys

tree = ET.parse(r'C:\Users\fylht\Desktop\temp_pytest_extract\pytest-results.xml')
root = tree.getroot()
testsuite = root.find('testsuite')
if testsuite is None:
    testsuite = root

print('SUMMARY:')
print(f"Tests: {testsuite.get('tests')}")
print(f"Failures: {testsuite.get('failures')}")
print(f"Errors: {testsuite.get('errors')}")
print(f"Skipped: {testsuite.get('skipped')}")

print('\nTARGET TESTS:')
targets = [
    'test_patch_connector_settings_semantics',
    'test_connector_settings_tenant_isolation',
    'test_connector_settings_patch_validate_true',
    'test_connector_settings_audit'
]
found = {}
for case in testsuite.findall('.//testcase'):
    name = case.get('name')
    if name in targets:
        if case.find('failure') is not None:
            found[name] = 'failed'
        elif case.find('error') is not None:
            found[name] = 'error'
        elif case.find('skipped') is not None:
            found[name] = 'skipped'
        else:
            found[name] = 'passed'

for t in targets:
    print(f'{t}: {found.get(t, "absent")}')

print('\nFAILURES/ERRORS:')
for case in testsuite.findall('.//testcase'):
    failure = case.find('failure')
    error = case.find('error')
    problem = failure if failure is not None else error
    if problem is not None:
        print(f"--- NODEID: {case.get('classname')}.{case.get('name')} ---")
        print(f"Message: {problem.get('message')}")
        print(f"Text:\n{problem.text.strip()}\n")
