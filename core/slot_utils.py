import re
from datetime import datetime

def extract_slot_from_message(slot, message):
    if slot == 'city':
        city_match = re.search(r'(?:in|kat|di)\s+([a-zA-Z ]+)', message.lower())
        if city_match:
            return city_match.group(1).strip().title()
        return None
    elif slot in ['check_in', 'check_out']:
        # Try YYYY-MM-DD
        match = re.search(r"(\d{4}-\d{2}-\d{2})", message)
        if match:
            return match.group(1)
        # Try DD/MM/YYYY
        match = re.search(r"(\d{2}/\d{2}/\d{4})", message)
        if match:
            try:
                dt = datetime.strptime(match.group(1), "%d/%m/%Y")
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        # Try DD MMM YYYY (e.g., 29 Mei 2025)
        match = re.search(r"(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})", message)
        if match:
            day, month, year = match.groups()
            month_map = {
                'januari': '01', 'februari': '02', 'mac': '03', 'april': '04', 'mei': '05', 'jun': '06',
                'julai': '07', 'ogos': '08', 'september': '09', 'oktober': '10', 'november': '11', 'disember': '12',
                'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
                'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12',
            }
            m = month_map.get(month.lower())
            if m:
                return f"{year}-{m}-{int(day):02d}"
        return None
    return None 