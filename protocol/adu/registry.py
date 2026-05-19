from typing import Any, Callable, Dict, List

from .. import standard as st
from ..shared import ByteReader
from .common import (
    parse_analog_objects,
    parse_check_duty,
    parse_component_config_objects,
    parse_component_status_objects,
    parse_custom_system_time_payload,
    parse_custom_time_payload,
    parse_device_config_objects,
    parse_device_status_objects,
    parse_device_time_objects,
    parse_device_version_objects,
    parse_operation_objects,
    parse_query_component_targets,
    parse_query_operation,
    parse_query_system_targets,
    parse_reserved_payload,
    parse_system_config_objects,
    parse_system_status_objects,
    parse_system_time_objects,
    parse_system_version_objects,
)

Parser = Callable[[ByteReader, int, int, str], List[Dict[str, Any]]]


def _with_info_count(func: Callable[[ByteReader, int], List[Dict[str, Any]]]) -> Parser:
    return lambda reader, info_count, _type_flag, _type_flag_name: func(reader, info_count)


def _reserved(label: str) -> Parser:
    return lambda reader, _info_count, _type_flag, _type_flag_name: parse_reserved_payload(reader, label)


def _device_time(label: str) -> Parser:
    return lambda reader, info_count, _type_flag, _type_flag_name: parse_device_time_objects(reader, info_count, label)


def _query_operation(include_system: bool, label: str) -> Parser:
    return lambda reader, _info_count, _type_flag, _type_flag_name: parse_query_operation(reader, include_system, label)


def _operation(bit_defs, include_system: bool) -> Parser:
    return lambda reader, info_count, _type_flag, _type_flag_name: parse_operation_objects(reader, info_count, bit_defs, include_system)


def _custom_time() -> Parser:
    return lambda reader, info_count, type_flag, type_flag_name: parse_custom_time_payload(reader, info_count, type_flag, type_flag_name)


def _custom_system_time() -> Parser:
    return lambda reader, info_count, type_flag, type_flag_name: parse_custom_system_time_payload(reader, info_count, type_flag, type_flag_name)


PARSER_REGISTRY: Dict[int, Parser] = {
    1: _with_info_count(parse_system_status_objects),
    2: _with_info_count(parse_component_status_objects),
    3: _with_info_count(parse_analog_objects),
    4: _operation(st.FACILITY_OPERATION_BITS, True),
    5: _with_info_count(parse_system_version_objects),
    6: _with_info_count(parse_system_config_objects),
    7: _with_info_count(parse_component_config_objects),
    8: _with_info_count(parse_system_time_objects),
    21: _with_info_count(parse_device_status_objects),
    24: _operation(st.DEVICE_OPERATION_BITS, False),
    25: _with_info_count(parse_device_version_objects),
    26: _with_info_count(parse_device_config_objects),
    28: _with_info_count(parse_device_time_objects),
    61: _with_info_count(parse_query_system_targets),
    62: _with_info_count(parse_query_component_targets),
    63: _with_info_count(parse_query_component_targets),
    64: _query_operation(True, '读建筑消防设施操作信息'),
    65: _with_info_count(parse_query_system_targets),
    66: _with_info_count(parse_query_system_targets),
    67: _with_info_count(parse_query_component_targets),
    68: _with_info_count(parse_query_system_targets),
    81: _reserved('读传输装置运行状态负载'),
    84: _query_operation(False, '读传输装置操作信息'),
    85: _reserved('读传输装置软件版本负载'),
    86: _reserved('读传输装置配置情况负载'),
    88: _reserved('读传输装置系统时间负载'),
    89: _reserved('初始化传输装置负载'),
    90: _device_time('同步后的中心系统时间'),
    91: lambda reader, _info_count, _type_flag, _type_flag_name: parse_check_duty(reader),
    128: _custom_time(),
    129: _custom_time(),
    130: _custom_time(),
    131: _custom_time(),
    132: _custom_system_time(),
    133: _custom_system_time(),
    134: _with_info_count(parse_system_status_objects),
    135: _with_info_count(parse_component_status_objects),
    136: lambda reader, info_count, _type_flag, _type_flag_name: parse_device_status_objects(reader, info_count, '运行状态恢复'),
    188: _reserved('读取传输装置生产日期负载'),
    189: _device_time('设置报名时间'),
}
