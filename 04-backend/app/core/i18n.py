from typing import Dict

# Simple i18n for backend messages
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "alert_cash_runway": "Cash runway is critically low: {days} days remaining.",
        "alert_roi_negative": "Overall ROI is negative ({roi}%).",
        "alert_stalled_data": "No new data (transactions or campaign stats) recorded in the last {days} days.",
    },
    "ru": {
        "alert_cash_runway": "Кассовый разрыв: осталось {days} дней.",
        "alert_roi_negative": "Общий ROI отрицательный ({roi}%).",
        "alert_stalled_data": "Нет новых данных (транзакций или статистики) за последние {days} дней.",
    }
}

def translate(key: str, lang: str = "en", **kwargs) -> str:
    lang = lang if lang in TRANSLATIONS else "en"
    text = TRANSLATIONS[lang].get(key, key)
    try:
        return text.format(**kwargs)
    except KeyError:
        return text
