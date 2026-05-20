from typing import Any, Dict, List

from . import standard as st
from .profiles import jk_gh2013g as jk

COMMAND_CN = dict(st.COMMAND_CN)
TYPE_FLAG_CN = {**st.TYPE_FLAG_CN, **jk.CUSTOM_TYPE_FLAG_CN}
SYSTEM_TYPE_CN = dict(st.SYSTEM_TYPE_CN)
COMPONENT_TYPE_CN = dict(st.COMPONENT_TYPE_CN)
SYSTEM_TYPE_TO_COMPONENTS = dict(st.SYSTEM_TYPE_TO_COMPONENTS)
ANALOG_TYPE_META = dict(st.ANALOG_TYPE_META)

SYSTEM_ADDRESS_RELEVANT = {1, 2, 3, 4, 5, 6, 7, 8, 61, 62, 63, 64, 65, 66, 67, 68, 132, 133, 134, 135}


def field(label: str, value: Any, mono: bool = False, accent: str = '') -> Dict[str, Any]:
    return {'label': label, 'value': '' if value is None else str(value), 'mono': mono, 'accent': accent}


def safe_name(mapping: Dict[int, str], value: int, unknown_prefix: str = '未知') -> str:
    return mapping.get(value, f'{unknown_prefix}({value})')


def format_bytes_hex(raw: bytes) -> str:
    return ' '.join(f'{b:02X}' for b in raw)


def decode_text(raw: bytes) -> str:
    return raw.rstrip(b'\x00').decode('gb18030', errors='ignore').strip()


def decode_time_tag(raw: bytes) -> str:
    if len(raw) != 6:
        raise ValueError('时间标签长度必须为6字节')
    second, minute, hour, day, month, year = raw
    return f'20{year:02d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}'


def decode_flag_bits(value: int, definitions: List[Dict[str, str]], width: int) -> Dict[str, Any]:
    flags = []
    active = []
    for bit in range(width):
        meta = definitions[bit] if bit < len(definitions) else {}
        enabled = bool(value & (1 << bit))
        on_text = meta.get('on', f'bit{bit}=1')
        off_text = meta.get('off', f'bit{bit}=0')
        label = meta.get('label', f'bit{bit}')
        item = {
            'bit': bit,
            'label': label,
            'active': enabled,
            'on': on_text,
            'off': off_text,
            'text': on_text if enabled else off_text,
        }
        flags.append(item)
        if enabled:
            active.append(on_text)
    return {'flags': flags, 'active_labels': active}


class ByteReader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read(self, size: int, label: str) -> bytes:
        if self.remaining() < size:
            raise ValueError(f'{label}长度不足，需要{size}字节，剩余{self.remaining()}字节')
        chunk = self.data[self.offset:self.offset + size]
        self.offset += size
        return chunk

    def read_u8(self, label: str) -> int:
        return self.read(1, label)[0]

    def read_u16(self, label: str) -> int:
        return int.from_bytes(self.read(2, label), byteorder='little')

    def read_s16(self, label: str) -> int:
        return int.from_bytes(self.read(2, label), byteorder='little', signed=True)

    def read_time(self, label: str) -> str:
        return decode_time_tag(self.read(6, label))


def direction_for_type(type_flag: int) -> str:
    if 61 <= type_flag <= 127 or type_flag in {188, 189}:
        return '下行'
    return '上行'


def type_origin_for_flag(type_flag: int) -> str:
    if type_flag in jk.CUSTOM_TYPE_FLAG_CN:
        return 'vendor_custom'
    if type_flag in st.TYPE_FLAG_CN:
        return 'standard'
    return 'reserved'


def type_origin_label(type_origin: str) -> str:
    if type_origin == 'vendor_custom':
        return jk.TYPE_ORIGIN_LABEL
    if type_origin == 'standard':
        return '标准'
    return '未知/保留'


def build_summary(name: str, active_labels: List[str], fallback: str) -> str:
    return f'{name} / {", ".join(active_labels)}' if active_labels else f'{name} / {fallback}'


def common_profile_notes(type_flag: int) -> List[str]:
    notes = []
    if type_flag in jk.CUSTOM_TYPE_FLAG_CN:
        notes.append(f'该类型来自 {jk.PROFILE_NAME} 厂商扩展定义。')
    if type_flag in SYSTEM_ADDRESS_RELEVANT:
        notes.append(jk.SYSTEM_ADDRESS_SEMANTICS)
    return notes
