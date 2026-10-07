with open('04-backend/app/connectors/meta_ads.py', 'r') as f:
    content = f.read()

import re

old_norm = '''    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []
            
        for row in raw_data:
            if not isinstance(row, dict):
                continue
                
            external_id = row.get("campaign_id")
            if external_id is None:
                continue
                
            date_str = row.get("date_start")
            if not date_str:
                continue
            try:
                stat_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
            except ValueError:
                continue'''

new_norm = '''    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []
        dropped_aggregates = 0
            
        for row in raw_data:
            if not isinstance(row, dict):
                continue
                
            external_id = row.get("campaign_id")
            if external_id is None:
                continue
                
            date_start = row.get("date_start")
            date_stop = row.get("date_stop")
            
            if not date_start or not date_stop or date_start != date_stop:
                dropped_aggregates += 1
                continue
                
            try:
                stat_date = datetime.strptime(date_start, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
            except ValueError:
                continue'''

content = content.replace(old_norm, new_norm)

old_return = '''        unique_records = {}
        for rec in normalized:
            key = (rec.external_id, rec.stat_date)
            unique_records[key] = rec
            
        return list(unique_records.values())'''

new_return = '''        unique_records = {}
        for rec in normalized:
            key = (rec.external_id, rec.stat_date)
            unique_records[key] = rec
            
        if dropped_aggregates > 0:
            logger.warning(f"MetaAds normalize dropped {dropped_aggregates} rows with invalid date_stop != date_start")
            
        return list(unique_records.values())'''

content = content.replace(old_return, new_return)

with open('04-backend/app/connectors/meta_ads.py', 'w') as f:
    f.write(content)
