import json
import os
from typing import Any, Dict, List, Optional, Tuple

_DEFAULT_CONFIGS: List[Dict[str, Any]] = [
    {
        'id': 1,
        'name': '本地测试',
        'host': '127.0.0.1',
        'port': 8080,
        'protocol': 'tcp',
        'description': '本地开发测试服务器',
    }
]
_DEFAULT_NEXT_ID = 2

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'network_configs.json')


class NetworkConfigStore:
    def __init__(self) -> None:
        self._configs: List[Dict[str, Any]] = []
        self._next_id: int = 1
        self._load()

    def _load(self) -> None:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                self._configs = data.get('configs', list(_DEFAULT_CONFIGS))
                self._next_id = data.get('next_id', _DEFAULT_NEXT_ID)
                return
            except Exception:
                pass
        self._configs = list(_DEFAULT_CONFIGS)
        self._next_id = _DEFAULT_NEXT_ID

    def _save(self) -> None:
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as fh:
                json.dump({'configs': self._configs, 'next_id': self._next_id}, fh, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error('保存配置文件失败: %s', exc)

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._configs)

    def get(self, config_id: int) -> Optional[Dict[str, Any]]:
        return next((c for c in self._configs if c['id'] == config_id), None)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        new_config = {
            'id': self._next_id,
            'name': data['name'],
            'host': data['host'],
            'port': int(data['port']),
            'protocol': data.get('protocol', 'tcp'),
            'description': data.get('description', ''),
        }
        self._configs.append(new_config)
        self._next_id += 1
        self._save()
        return new_config

    def update(self, config_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        config = self.get(config_id)
        if not config:
            return None
        for key in ('name', 'host', 'port', 'protocol', 'description'):
            if key in data:
                if key == 'port':
                    config[key] = int(data[key])
                else:
                    config[key] = data[key]
        self._save()
        return config

    def delete(self, config_id: int) -> bool:
        config = self.get(config_id)
        if not config:
            return False
        self._configs = [c for c in self._configs if c['id'] != config_id]
        self._save()
        return True
