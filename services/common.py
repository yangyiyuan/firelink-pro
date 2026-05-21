import copy
import datetime
from typing import Any, Optional


def deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def parse_int(value: Any, default: Optional[int] = None) -> int:
    if value is None or value == '':
        if default is None:
            raise ValueError('不能为空')
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        if default is None:
            raise ValueError('不能为空')
        return default
    return int(text, 0)


def now_str() -> str:
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def now_ms_str() -> str:
    now = datetime.datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S.') + f'{now.microsecond // 1000:03d}'
