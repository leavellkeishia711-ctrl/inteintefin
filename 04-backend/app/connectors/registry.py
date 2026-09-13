import importlib
from typing import Type
from app.connectors.base import Connector

_REGISTRY_MAP = {
    'keitaro': ('app.connectors.keitaro', 'KeitaroConnector'),
    'binom': ('app.connectors.binom', 'BinomConnector'),
    'voluum': ('app.connectors.voluum', 'VoluumConnector'),
    'affise': ('app.connectors.affise', 'AffiseConnector'),
    'meta': ('app.connectors.meta_ads', 'MetaAdsConnector'),
    'google_ads': ('app.connectors.google_ads', 'GoogleAdsConnector'),
    'tiktok_ads': ('app.connectors.tiktok_ads', 'TikTokAdsConnector'),
}

class LazyConnectorRegistry(dict):
    def __getitem__(self, key: str) -> Type[Connector]:
        if key in _REGISTRY_MAP:
            mod_path, cls_name = _REGISTRY_MAP[key]
            module = importlib.import_module(mod_path)
            return getattr(module, cls_name)
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return key in _REGISTRY_MAP

    def get(self, key: str, default=None):
        if key in self:
            return self[key]
        return default
        
    def keys(self):
        return _REGISTRY_MAP.keys()

CONNECTOR_REGISTRY = LazyConnectorRegistry()
