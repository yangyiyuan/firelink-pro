from typing import Any, Dict, List

from .. import standard as st
from ..profiles import jk_gh2013g as jk
from ..shared import (
    ANALOG_TYPE_META,
    COMPONENT_TYPE_CN,
    SYSTEM_TYPE_CN,
    ByteReader,
    build_summary,
    decode_flag_bits,
    field,
    format_bytes_hex,
    safe_name,
)


def parse_system_status_objects(reader: ByteReader, info_count: int, type_flag: int = 1, type_flag_name: str = '') -> List[Dict[str, Any]]:
    is_restore = type_flag == 134
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        status = reader.read_u16('系统状态')
        occurred_at = reader.read_time('状态发生时间')
        decoded = decode_flag_bits(status, st.SYSTEM_STATUS_BITS, 16)
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        fallback = '正常运行' if not decoded['active_labels'] else ('恢复正常' if is_restore else '正常/无激活状态位')
        status_accent = 'success' if not decoded['active_labels'] else 'primary'
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': build_summary(system_name, decoded['active_labels'], fallback),
            'occurred_at': occurred_at,
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('系统状态值', f'0x{status:04X} / {status}', mono=True, accent=status_accent),
                field('状态时间', occurred_at, mono=True),
            ],
            'status_flags': decoded['flags'],
        })
    return objects


def parse_component_status_objects(reader: ByteReader, info_count: int, type_flag: int = 2, type_flag_name: str = '') -> List[Dict[str, Any]]:
    is_restore = type_flag in (135, 134)
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        component_type = reader.read_u8('部件类型')
        component_addr_raw, component_addr = reader.read_component_addr()
        status = reader.read_u16('部件状态')
        desc = reader.read(31, '部件说明')
        occurred_at = reader.read_time('状态发生时间')
        decoded = decode_flag_bits(status, st.COMPONENT_STATUS_BITS, 16)
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        component_name = safe_name(COMPONENT_TYPE_CN, component_type, '未知部件')
        fallback = '正常运行' if not decoded['active_labels'] else ('恢复正常' if is_restore else '无激活状态位')
        status_accent = 'success' if not decoded['active_labels'] else 'primary'
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': build_summary(component_name, decoded['active_labels'], fallback),
            'occurred_at': occurred_at,
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('部件类型', f'{component_type} / {component_name}'),
                field('部件地址', f'0x{component_addr:08X} / {format_bytes_hex(component_addr_raw)}', mono=True),
                field('部件状态值', f'0x{status:04X} / {status}', mono=True, accent=status_accent),
                field('部件说明', desc.rstrip(b'\x00').decode('gb18030', errors='ignore').strip() or '-'),
                field('状态时间', occurred_at, mono=True),
            ],
            'status_flags': decoded['flags'],
        })
    return objects


def parse_analog_objects(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        component_type = reader.read_u8('部件类型')
        component_addr_raw, component_addr = reader.read_component_addr()
        analog_type = reader.read_u8('模拟量类型')
        analog_value = reader.read_s16('模拟量值')
        sampled_at = reader.read_time('采样时间')
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        component_name = safe_name(COMPONENT_TYPE_CN, component_type, '未知部件')
        analog_meta = ANALOG_TYPE_META.get(analog_type, {'name': f'未知模拟量({analog_type})', 'unit': '', 'scale': 1})
        scaled_value = analog_value * analog_meta.get('scale', 1)
        unit = analog_meta.get('unit', '')
        value_display = f'{scaled_value:g}{unit}' if unit else f'{scaled_value:g}'
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{component_name} / {analog_meta["name"]} = {value_display}',
            'occurred_at': sampled_at,
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('部件类型', f'{component_type} / {component_name}'),
                field('部件地址', f'0x{component_addr:08X} / {format_bytes_hex(component_addr_raw)}', mono=True),
                field('模拟量类型', f'{analog_type} / {analog_meta["name"]}'),
                field('模拟量原始值', analog_value, mono=True),
                field('换算值', value_display, accent='primary'),
                field('采样时间', sampled_at, mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_operation_objects(reader: ByteReader, info_count: int, bit_defs: List[Dict[str, str]], include_system: bool) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        fields = []
        prefix = ''
        if include_system:
            system_type = reader.read_u8('系统类型')
            system_addr = reader.read_u8('系统地址')
            system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
            fields.extend([
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
            ])
            prefix = f'{system_name} / '
        op_value = reader.read_u8('操作信息')
        operator_no = reader.read_u8('操作员编号')
        occurred_at = reader.read_time('操作记录时间')
        decoded = decode_flag_bits(op_value, bit_defs, 8)
        fields.extend([
            field('操作信息值', f'0x{op_value:02X} / {op_value}', mono=True, accent='primary'),
            field('操作员编号', operator_no),
            field('记录时间', occurred_at, mono=True),
        ])
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': prefix + (', '.join(decoded['active_labels']) if decoded['active_labels'] else '无激活操作位'),
            'occurred_at': occurred_at,
            'fields': fields,
            'status_flags': decoded['flags'],
        })
    return objects


def parse_device_operation_objects(reader: ByteReader, info_count: int, bit_defs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """解析传输装置操作信息（TF=24）

    与TF=4不同，TF=24每个信息对象不含系统类型/系统地址，
    且在所有信息对象之后，ADU末尾有一个时间标签。
    """
    objects = []
    for idx in range(info_count):
        op_value = reader.read_u8('操作信息')
        operator_no = reader.read_u8('操作员编号')
        occurred_at = reader.read_time('操作记录时间')
        decoded = decode_flag_bits(op_value, bit_defs, 8)
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': ', '.join(decoded['active_labels']) if decoded['active_labels'] else '无激活操作位',
            'occurred_at': occurred_at,
            'fields': [
                field('操作信息值', f'0x{op_value:02X} / {op_value}', mono=True, accent='primary'),
                field('操作员编号', operator_no),
                field('记录时间', occurred_at, mono=True),
            ],
            'status_flags': decoded['flags'],
        })
    # ADU末尾时间标签
    if reader.remaining() >= 6:
        time_tag = reader.read_time('时间标签')
        for obj in objects:
            obj['fields'].append(field('时间标签', time_tag, mono=True))
        # 将时间标签记录到第一个对象的occurred_at（如果尚未设置）
        if objects and not objects[0].get('occurred_at'):
            objects[0]['occurred_at'] = time_tag
    return objects


def parse_system_version_objects(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        major = reader.read_u8('主版本号')
        minor = reader.read_u8('次版本号')
        version_time = reader.read_time('版本时间')
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{system_name} / V{major}.{minor}',
            'occurred_at': version_time,
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('软件版本', f'V{major}.{minor}', mono=True, accent='primary'),
                field('版本时间', version_time, mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_system_config_objects(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        text_len = reader.read_u8('系统说明长度')
        text = reader.read(text_len, '系统配置说明').rstrip(b'\x00').decode('gb18030', errors='ignore').strip()
        config_time = reader.read_time('配置时间')
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{system_name} / 配置说明',
            'occurred_at': config_time,
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('说明长度', text_len, mono=True),
                field('系统配置说明', text or '-'),
                field('配置时间', config_time, mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_component_config_objects(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        component_type = reader.read_u8('部件类型')
        component_addr_raw, component_addr = reader.read_component_addr()
        desc = reader.read(31, '部件说明').rstrip(b'\x00').decode('gb18030', errors='ignore').strip()
        config_time = reader.read_time('配置时间')
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        component_name = safe_name(COMPONENT_TYPE_CN, component_type, '未知部件')
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{component_name} / 配置',
            'occurred_at': config_time,
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('部件类型', f'{component_type} / {component_name}'),
                field('部件地址', f'0x{component_addr:08X} / {format_bytes_hex(component_addr_raw)}', mono=True),
                field('部件说明', desc or '-'),
                field('配置时间', config_time, mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_system_time_objects(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        system_time = reader.read_time('系统时间')
        reported_at = reader.read_time('上报时间')
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{system_name} / {system_time}',
            'occurred_at': reported_at,
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('系统时间', system_time, mono=True, accent='primary'),
                field('上报时间', reported_at, mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_device_status_objects(reader: ByteReader, info_count: int, title_prefix: str = '运行状态') -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        status = reader.read_u8('装置状态')
        occurred_at = reader.read_time('状态发生时间')
        time_tag = reader.read_time('时间标签')
        decoded = decode_flag_bits(status, st.DEVICE_STATUS_BITS, 8)
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': build_summary(title_prefix, decoded['active_labels'], '正常监视/无激活状态位'),
            'occurred_at': occurred_at,
            'fields': [
                field('状态值', f'0x{status:02X} / {status}', mono=True, accent='primary'),
                field('状态发生时间', occurred_at, mono=True),
                field('时间标签', time_tag, mono=True),
            ],
            'status_flags': decoded['flags'],
        })
    return objects


def parse_device_version_objects(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        major = reader.read_u8('主版本号')
        minor = reader.read_u8('次版本号')
        version_time = reader.read_time('版本时间')
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'传输装置软件版本 / V{major}.{minor}',
            'occurred_at': version_time,
            'fields': [
                field('软件版本', f'V{major}.{minor}', mono=True, accent='primary'),
                field('版本时间', version_time, mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_device_config_objects(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        text_len = reader.read_u8('配置说明长度')
        text = reader.read(text_len, '配置说明').rstrip(b'\x00').decode('gb18030', errors='ignore').strip()
        config_time = reader.read_time('配置时间')
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': '传输装置配置说明',
            'occurred_at': config_time,
            'fields': [
                field('说明长度', text_len, mono=True),
                field('配置说明', text or '-'),
                field('配置时间', config_time, mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_device_time_objects(reader: ByteReader, info_count: int, label: str = '传输装置系统时间') -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        time_text = reader.read_time(label)
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{label} / {time_text}',
            'fields': [field(label, time_text, mono=True, accent='primary')],
            'status_flags': [],
        })
    return objects


def parse_query_system_targets(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        objects.append({
            'index': idx + 1,
            'title': f'查询对象 {idx + 1}',
            'summary': f'{system_name} / 地址 {system_addr}',
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
            ],
            'status_flags': [],
        })
    return objects


def parse_query_component_targets(reader: ByteReader, info_count: int) -> List[Dict[str, Any]]:
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        component_addr_raw, component_addr = reader.read_component_addr()
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        objects.append({
            'index': idx + 1,
            'title': f'查询对象 {idx + 1}',
            'summary': f'{system_name} / 部件地址 0x{component_addr:08X}',
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field('部件地址', f'0x{component_addr:08X} / {format_bytes_hex(component_addr_raw)}', mono=True),
            ],
            'status_flags': [],
        })
    return objects


def parse_query_operation(reader: ByteReader, include_system: bool, label: str) -> List[Dict[str, Any]]:
    fields = []
    if include_system:
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        fields.extend([
            field('系统类型', f'{system_type} / {system_name}'),
            field('系统地址', system_addr),
        ])
    query_count = reader.read_u8('查询记录数')
    start_time = reader.read_time('起始时间')
    return [{
        'index': 1,
        'title': label,
        'summary': f'从 {start_time} 开始查询 {query_count} 条',
        'fields': fields + [
            field('查询记录数', query_count, mono=True, accent='primary'),
            field('指定起始时间', start_time, mono=True),
        ],
        'status_flags': [],
    }]


def parse_reserved_payload(reader: ByteReader, label: str) -> List[Dict[str, Any]]:
    remaining = reader.read(reader.remaining(), label) if reader.remaining() else b''
    return [{
        'index': 1,
        'title': label,
        'summary': '保留或固定负载',
        'fields': [
            field('负载长度', len(remaining), mono=True),
            field('负载HEX', format_bytes_hex(remaining) if remaining else '空', mono=True),
        ],
        'status_flags': [],
    }]


def parse_custom_time_payload(reader: ByteReader, info_count: int, type_flag: int, type_flag_name: str) -> List[Dict[str, Any]]:
    label = jk.CUSTOM_TIME_TYPE_NAMES.get(type_flag, type_flag_name or '自定义时间信息')
    objects = []
    for idx in range(info_count):
        time_text = reader.read_time(label)
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{label} / {time_text}',
            'fields': [field(label, time_text, mono=True, accent='primary')],
            'status_flags': [],
        })
    return objects


def parse_custom_system_time_payload(reader: ByteReader, info_count: int, type_flag: int, type_flag_name: str) -> List[Dict[str, Any]]:
    label = jk.CUSTOM_SYSTEM_TIME_TYPE_NAMES.get(type_flag, type_flag_name or '系统时间信息')
    objects = []
    for idx in range(info_count):
        system_type = reader.read_u8('系统类型')
        system_addr = reader.read_u8('系统地址')
        time_text = reader.read_time(label)
        system_name = safe_name(SYSTEM_TYPE_CN, system_type, '未知系统')
        objects.append({
            'index': idx + 1,
            'title': f'信息对象 {idx + 1}',
            'summary': f'{system_name} / {label}',
            'fields': [
                field('系统类型', f'{system_type} / {system_name}'),
                field('系统地址', system_addr),
                field(label, time_text, mono=True, accent='primary'),
            ],
            'status_flags': [],
        })
    return objects


def parse_check_duty(reader: ByteReader) -> List[Dict[str, Any]]:
    timeout_minutes = reader.read_u8('查岗超时分钟')
    return [{
        'index': 1,
        'title': '查岗命令',
        'summary': f'查岗应答超时 {timeout_minutes} 分钟',
        'fields': [field('查岗应答超时(分钟)', timeout_minutes, mono=True, accent='primary')],
        'status_flags': [],
    }]
