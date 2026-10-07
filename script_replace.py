with open('04-backend/app/connectors/meta_ads.py', 'r') as f:
    content = f.read()

import re

# 1. Replace fetch_metrics start
old_fetch = '''async def fetch_metrics(self, start_date=None, end_date=None) -> List[Dict[str, Any]]:
        time_range_str = ""
        if start_date and end_date:
            time_range_str = f".time_range({{'since':'{start_date.strftime('%Y-%m-%d')}','until':'{end_date.strftime('%Y-%m-%d')}'}}).time_increment(1)"
        
        url = f"{self.base_url}/me/adaccounts?fields=account_id,currency,insights.level(campaign){time_range_str}{{campaign_id,spend,action_values,clicks,impressions,reach,actions,date_start}}"'''

new_fetch = '''async def fetch_metrics(self, start_date=None, end_date=None) -> List[Dict[str, Any]]:
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date are required for fetch_metrics")

        time_range_str = f".time_range({{'since':'{start_date.strftime('%Y-%m-%d')}','until':'{end_date.strftime('%Y-%m-%d')}'}}).time_increment(1)"
        url = f"{self.base_url}/me/adaccounts?fields=account_id,currency,insights.level(campaign){time_range_str}{{campaign_id,spend,action_values,clicks,impressions,reach,actions,date_start,date_stop}}"'''

content = content.replace(old_fetch, new_fetch)

# 2. Replace fetch()
old_fetch2 = '''    async def fetch(self) -> List[Dict[str, Any]]:
        return await self.fetch_metrics()'''

new_fetch2 = '''    async def fetch(self) -> List[Dict[str, Any]]:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=self.lookback_days - 1)
        return await self.fetch_metrics(start_date, end_date)'''

content = content.replace(old_fetch2, new_fetch2)

with open('04-backend/app/connectors/meta_ads.py', 'w') as f:
    f.write(content)
