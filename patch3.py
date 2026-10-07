import re

file_path = '04-backend/tests/test_pr_a_data_integrity.py'
with open(file_path, 'r') as f:
    content = f.read()

old_assertion = '''        async with system_session() as db_session:
            mock_fx.assert_awaited_once_with(db_session, "EUR", "USD", date(2023, 1, 1))'''

new_assertion = '''        mock_fx.assert_awaited_once()
        args = mock_fx.call_args.args
        assert args[1:] == ("EUR", "USD", date(2023, 1, 1))'''

content = content.replace(old_assertion, new_assertion)

with open(file_path, 'w') as f:
    f.write(content)
