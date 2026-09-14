import importlib
from typing import Type
import logging

logger = logging.getLogger(__name__)

CONNECTOR_NAMES = frozenset(['meta', 'google_ads', 'tiktok_ads', 'keitaro'])

_REGISTRY_MAP = {
    'meta': ('app.connectors.meta_ads', 'MetaAdsConnector'),
    'google_ads': ('app.connectors.google_ads', 'GoogleAdsConnector'),
    'tiktok_ads': ('app.connectors.tiktok_ads', 'TikTokAdsConnector'),
    'keitaro': ('app.connectors.keitaro', 'KeitaroConnector')
}

def get_connector_class(name: str):
    if name not in _REGISTRY_MAP:
        return None
        
    module_path, class_name = _REGISTRY_MAP[name]
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls
    except Exception as e:
        logger.error(f"Failed to load connector class for {name}: {e}")
        return None
