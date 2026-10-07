with open('04-backend/app/connectors/meta_ads.py', 'r') as f:
    content = f.read()

import re

old_init = '''        try:
            self.lookback_days = int(settings.get("lookback_days", DEFAULT_LOOKBACK_DAYS))
        except (ValueError, TypeError):
            self.lookback_days = DEFAULT_LOOKBACK_DAYS
            
        if not (MIN_LOOKBACK <= self.lookback_days <= MAX_LOOKBACK):
            raise ValueError(f"lookback_days must be between {MIN_LOOKBACK} and {MAX_LOOKBACK}")'''

new_init = '''        if "lookback_days" in settings:
            val = settings["lookback_days"]
            if val is None or not str(val).isdigit():
                raise ValueError("lookback_days must be an integer")
            self.lookback_days = int(val)
        else:
            self.lookback_days = DEFAULT_LOOKBACK_DAYS
            
        if not (MIN_LOOKBACK <= self.lookback_days <= MAX_LOOKBACK):
            raise ValueError(f"lookback_days must be between {MIN_LOOKBACK} and {MAX_LOOKBACK}")'''

content = content.replace(old_init, new_init)

with open('04-backend/app/connectors/meta_ads.py', 'w') as f:
    f.write(content)
