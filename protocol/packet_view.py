from typing import Any, Dict, List

from .adu import PARSER_REGISTRY
from .profiles import jk_gh2013g as jk
from .shared import (
    ByteReader,
    COMMAND_CN,
    common_profile_notes,
    direction_for_type,
    field,
    format_bytes_hex,
    type_origin_for_flag,
    type_origin_label,
    TYPE_FLAG_CN,
)


def parse_adu(adu_bytes: bytes, component_addr_byteorder: str = 'little') -> Dict[str, Any]:
    if len(adu_bytes) < 2:
        raise ValueError('ADU长度不足，至少需要2字节')

    type_flag = adu_bytes[0]
    info_count = adu_bytes[1]
    payload = adu_bytes[2:]
    reader = ByteReader(payload, component_addr_byteorder=component_addr_byteorder)
    type_name = TYPE_FLAG_CN.get(type_flag, f'未知类型({type_flag})')
    direction = direction_for_type(type_flag)
    type_origin = type_origin_for_flag(type_flag)
    notes = common_profile_notes(type_flag)

    parser = PARSER_REGISTRY.get(type_flag)
    parse_error = None
    objects: List[Dict[str, Any]] = []

    try:
        if parser is None:
            raw_payload = reader.read(reader.remaining(), '自定义负载') if reader.remaining() else b''
            objects = [{
                'index': 1,
                'title': '未适配类型',
                'summary': '当前类型未定义结构化解析规则',
                'fields': [
                    field('类型标志', f'{type_flag} / {type_name}', mono=True),
                    field('负载长度', len(raw_payload), mono=True),
                    field('负载HEX', format_bytes_hex(raw_payload) if raw_payload else '空', mono=True),
                ],
                'status_flags': [],
            }]
            notes.append('该类型暂按原始负载展示，可继续补充新的厂商 profile。')
        else:
            objects = parser(reader, info_count, type_flag, type_name)
    except Exception as exc:
        parse_error = str(exc)

    trailing = payload[reader.offset:]
    if trailing:
        notes.append(f'存在未消费负载 {len(trailing)} 字节：{format_bytes_hex(trailing)}')
    if parse_error:
        notes.append(f'ADU解析异常：{parse_error}')

    summary_short = f'{type_name} / {len(objects)} 个信息对象'
    if parse_error:
        summary_short += ' / 部分解析失败'

    return {
        'profile_key': jk.PROFILE_KEY,
        'profile_name': jk.PROFILE_NAME,
        'type_flag': type_flag,
        'type_flag_name': type_name,
        'type_origin': type_origin,
        'type_origin_label': type_origin_label(type_origin),
        'direction': direction,
        'info_count': info_count,
        'payload_length': len(payload),
        'payload_hex': payload.hex(),
        'adu_full_hex': adu_bytes.hex(),
        'summary_short': summary_short,
        'objects': objects,
        'notes': notes,
        'parse_error': parse_error,
        'trailing_hex': trailing.hex(),
    }


def enrich_packet_parse(parsed: Dict[str, Any], component_addr_byteorder: str = 'little') -> Dict[str, Any]:
    adu_hex = parsed.get('adu', '')
    adu_bytes = bytes.fromhex(adu_hex) if adu_hex else b''
    adu_parsed = parse_adu(adu_bytes, component_addr_byteorder=component_addr_byteorder) if adu_bytes else None
    parsed['command_name'] = COMMAND_CN.get(parsed['command'], f'未知({parsed["command"]})')
    parsed['adu_parsed'] = adu_parsed
    parsed['adu_hex'] = adu_hex
    if adu_parsed:
        parsed['type_flag'] = adu_parsed['type_flag']
        parsed['type_flag_name'] = adu_parsed['type_flag_name']
        parsed['type_origin'] = adu_parsed['type_origin']
        parsed['type_origin_label'] = adu_parsed['type_origin_label']
        parsed['profile_key'] = adu_parsed['profile_key']
        parsed['profile_name'] = adu_parsed['profile_name']
        parsed['info_count'] = adu_parsed['info_count']
        parsed['direction_name'] = adu_parsed['direction']
        parsed['adu_summary'] = adu_parsed['summary_short']
    return parsed


def build_packet_view(packet: bytes, addr_byte_order: str = 'little', component_addr_byteorder: str = 'little', **extra_fields: Any) -> Dict[str, Any]:
    # Lazy import to avoid circular dependency with protocol.core
    from .core import GBT26875Packet
    packet_builder = GBT26875Packet(addr_byte_order=addr_byte_order)
    parsed = packet_builder.parse_packet(packet)
    parsed['raw_hex'] = packet.hex()
    parsed['raw_length'] = len(packet)
    parsed.update(extra_fields)
    return enrich_packet_parse(parsed, component_addr_byteorder=component_addr_byteorder)