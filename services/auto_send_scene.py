import datetime
import json
import os
import uuid
from typing import Any, Dict, List

try:
    from fire_alarm_simulator.protocol.core import ADUBuilder, GBT26875Packet, build_packet_view
    from fire_alarm_simulator.protocol.shared import (
        COMMAND_CN,
        TYPE_FLAG_CN,
        COMPONENT_TYPE_CN,
        SYSTEM_TYPE_CN,
        SYSTEM_TYPE_TO_COMPONENTS,
        ANALOG_TYPE_META,
    )
    from fire_alarm_simulator.protocol.standard import (
        COMPONENT_STATUS_BITS,
        DEVICE_STATUS_BITS,
        SYSTEM_STATUS_BITS,
    )
    from fire_alarm_simulator.services.common import deep_copy, now_str, parse_int
except ModuleNotFoundError:
    from protocol.core import ADUBuilder, GBT26875Packet, build_packet_view
    from protocol.shared import (
        COMMAND_CN,
        TYPE_FLAG_CN,
        COMPONENT_TYPE_CN,
        SYSTEM_TYPE_CN,
        SYSTEM_TYPE_TO_COMPONENTS,
        ANALOG_TYPE_META,
    )
    from protocol.standard import (
        COMPONENT_STATUS_BITS,
        DEVICE_STATUS_BITS,
        SYSTEM_STATUS_BITS,
    )
    from services.common import deep_copy, now_str, parse_int


OBJECT_TYPE_META = {
    'component_status': {'label': '部件状态对象'},
    'system_status': {'label': '系统状态对象'},
    'analog_value': {'label': '模拟量对象'},
    'device_status': {'label': '装置状态对象'},
}

TYPE_FLAG_OBJECT_COMPATIBILITY = {
    1: ['system_status'],
    2: ['component_status'],
    3: ['analog_value'],
    21: ['device_status'],
    134: ['system_status'],
    135: ['component_status'],
    136: ['device_status'],
}

COMPONENT_STATUS_PRESETS = [
    {'value': 0, 'label': '正常'},
    {'value': 2, 'label': '火警'},
    {'value': 4, 'label': '故障'},
    {'value': 8, 'label': '屏蔽'},
    {'value': 16, 'label': '监管'},
    {'value': 32, 'label': '启动'},
    {'value': 64, 'label': '反馈'},
    {'value': 128, 'label': '延时'},
    {'value': 256, 'label': '电源故障'},
]

SYSTEM_STATUS_PRESETS = [
    {'value': 0, 'label': '正常'},
    {'value': 2, 'label': '火警'},
    {'value': 4, 'label': '故障'},
    {'value': 8, 'label': '屏蔽'},
    {'value': 16, 'label': '监管'},
    {'value': 32, 'label': '启动'},
    {'value': 64, 'label': '反馈'},
    {'value': 128, 'label': '延时'},
    {'value': 256, 'label': '主电故障'},
    {'value': 512, 'label': '备电故障'},
    {'value': 1024, 'label': '总线故障'},
    {'value': 8192, 'label': '复位'},
]

DEVICE_STATUS_PRESETS = [
    {'value': 1, 'label': '正常监视'},
    {'value': 3, 'label': '火警'},
    {'value': 5, 'label': '故障'},
    {'value': 7, 'label': '火警+故障'},
    {'value': 9, 'label': '主电故障'},
    {'value': 17, 'label': '备电故障'},
    {'value': 33, 'label': '通信信道故障'},
    {'value': 65, 'label': '线路故障'},
]

SERVICE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_FILE = os.path.join(SERVICE_DIR, 'auto_send_templates.json')


def _field_error(step_index: int, field_path: str, message: str) -> ValueError:
    prefix = f'步骤{step_index + 1}'
    return ValueError(f'{prefix} {message} ({field_path})')


def _parse_occured_at(fields: Dict[str, Any]) -> datetime.datetime | None:
    mode = fields.get('occurredAtMode', 'now')
    if mode in ('', 'now', None):
        return None
    if mode == 'fixed':
        fixed_value = fields.get('occurredAt')
        if not fixed_value:
            raise ValueError('固定时间不能为空')
        return datetime.datetime.fromisoformat(str(fixed_value))
    return None


def _enum_options(mapping: Dict[int, str], allow: List[int] | None = None) -> List[Dict[str, Any]]:
    options = []
    for value, label in sorted(mapping.items()):
        if value == 0:
            continue
        if allow is not None and value not in allow:
            continue
        options.append({'value': value, 'label': label})
    return options


def _analog_options() -> List[Dict[str, Any]]:
    options = []
    for value, meta in sorted(ANALOG_TYPE_META.items()):
        if value == 0:
            continue
        unit = meta.get('unit', '')
        label = meta.get('name', str(value))
        options.append({'value': value, 'label': f'{label}{f" ({unit})" if unit else ""}'})
    return options


def _default_header(type_flag: int) -> Dict[str, Any]:
    return {
        'sourceAddr': '0x000000000001',
        'destAddr': '0x000000000002',
        'command': 2,
        'typeFlag': type_flag,
    }


def _default_fields(object_type: str) -> Dict[str, Any]:
    if object_type == 'system_status':
        return {
            'systemType': 1,
            'systemAddr': 1,
            'systemStatus': 0,
            'occurredAtMode': 'now',
            'occurredAt': '',
        }
    if object_type == 'analog_value':
        return {
            'systemType': 1,
            'systemAddr': 1,
            'componentType': 31,
            'bitNo': 1,
            'zoneNo': 1,
            'analogType': 3,
            'analogValue': 850,
            'occurredAtMode': 'now',
            'occurredAt': '',
        }
    if object_type == 'device_status':
        return {
            'statusByte': 0,
            'occurredAtMode': 'now',
            'occurredAt': '',
        }
    return {
        'systemType': 1,
        'systemAddr': 1,
        'componentType': 42,
        'bitNo': 1,
        'zoneNo': 1,
        'componentStatus': 2,
        'description': '',
        'occurredAtMode': 'now',
        'occurredAt': '',
    }


def _create_object(object_type: str, fields: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = _default_fields(object_type)
    if fields:
        payload.update(fields)
    return {
        'id': f'obj_{uuid.uuid4().hex[:8]}',
        'objectType': object_type,
        'fields': payload,
    }


def _create_step(name: str, type_flag: int, obj: Dict[str, Any], delay_after_sec: int = 5) -> Dict[str, Any]:
    return {
        'id': f'step_{uuid.uuid4().hex[:8]}',
        'name': name,
        'delayAfterSec': delay_after_sec,
        'packetHeader': _default_header(type_flag),
        'object': obj,
    }


def _system_templates() -> List[Dict[str, Any]]:
    templates = [
        {
            'id': 'system_dual_fire',
            'name': '两点报警',
            'category': 'fire',
            'description': '烟感+手报确认火警，两个报警信号快速连续上报',
            'source': 'system',
            'version': 2,
            'loop': True,
            'steps': [
                _create_step(
                    '烟感火警',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 2, 'bitNo': 1001, 'zoneNo': 1, 'description': 'A区1层大厅烟感01'}),
                    delay_after_sec=5,
                ),
                _create_step(
                    '手报火警',
                    2,
                    _create_object('component_status', {'componentType': 23, 'componentStatus': 2, 'bitNo': 1002, 'zoneNo': 1, 'description': 'A区1层大厅手报02'}),
                    delay_after_sec=30,
                ),
            ],
        },
        {
            'id': 'system_fault_restore',
            'name': '故障-恢复',
            'category': 'fault',
            'description': '烟感故障上报后延时恢复，验证故障处理完整流程',
            'source': 'system',
            'version': 2,
            'loop': True,
            'steps': [
                _create_step(
                    '烟感故障',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 4, 'description': '2号楼5层烟感故障'}),
                    delay_after_sec=5,
                ),
                _create_step(
                    '烟感恢复',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 0, 'description': '2号楼5层烟感恢复'}),
                    delay_after_sec=5,
                ),
            ],
        },
        {
            'id': 'system_fire_feedback',
            'name': '报警-反馈',
            'category': 'linkage',
            'description': '烟感火警后联动模块反馈，验证报警联动响应',
            'source': 'system',
            'version': 2,
            'loop': True,
            'steps': [
                _create_step(
                    '烟感火警',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 2, 'description': 'A区1层大厅烟感01'}),
                    delay_after_sec=3,
                ),
                _create_step(
                    '联动反馈',
                    2,
                    _create_object('component_status', {'componentType': 86, 'componentStatus': 64, 'description': '联动模块反馈'}),
                    delay_after_sec=5,
                ),
            ],
        },
        {
            'id': 'system_start_feedback',
            'name': '启动-反馈',
            'category': 'linkage',
            'description': '联动启动信号后接收反馈，验证控制输出闭环',
            'source': 'system',
            'version': 2,
            'loop': True,
            'steps': [
                _create_step(
                    '联动启动',
                    2,
                    _create_object('component_status', {'componentType': 86, 'componentStatus': 32, 'description': '联动模块启动'}),
                    delay_after_sec=3,
                ),
                _create_step(
                    '联动反馈',
                    2,
                    _create_object('component_status', {'componentType': 86, 'componentStatus': 64, 'description': '联动模块反馈'}),
                    delay_after_sec=5,
                ),
            ],
        },
        {
            'id': 'system_fire_feedback_recovery',
            'name': '报警-反馈-恢复',
            'category': 'restore',
            'description': '火警后联动反馈，再上报恢复，完整演示报警处置流程',
            'source': 'system',
            'version': 2,
            'loop': True,
            'steps': [
                _create_step(
                    '烟感火警',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 2, 'description': 'A区1层大厅烟感01'}),
                    delay_after_sec=3,
                ),
                _create_step(
                    '联动反馈',
                    2,
                    _create_object('component_status', {'componentType': 86, 'componentStatus': 64, 'description': '联动模块反馈'}),
                    delay_after_sec=5,
                ),
                _create_step(
                    '烟感恢复',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 0, 'description': 'A区1层大厅烟感01恢复'}),
                    delay_after_sec=5,
                ),
            ],
        },
        {
            'id': 'system_supervise_restore',
            'name': '监管-恢复',
            'category': 'supervise',
            'description': '部件监管报警后延时恢复，验证监管事件处理流程',
            'source': 'system',
            'version': 2,
            'loop': True,
            'steps': [
                _create_step(
                    '部件监管',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 16, 'description': 'A区1层烟感监管'}),
                    delay_after_sec=5,
                ),
                _create_step(
                    '部件恢复',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 0, 'description': 'A区1层烟感恢复'}),
                    delay_after_sec=5,
                ),
            ],
        },
        {
            'id': 'system_full_linkage',
            'name': '完整联动链路',
            'category': 'sequence',
            'description': '两点确认火警→联动反馈→烟感恢复，演示最完整的报警处置链路',
            'source': 'system',
            'version': 2,
            'loop': False,
            'steps': [
                _create_step(
                    '烟感火警',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 2, 'bitNo': 1001, 'zoneNo': 1, 'description': 'A区1层大厅烟感01'}),
                    delay_after_sec=5,
                ),
                _create_step(
                    '手报火警',
                    2,
                    _create_object('component_status', {'componentType': 23, 'componentStatus': 2, 'bitNo': 1002, 'zoneNo': 1, 'description': 'A区1层大厅手报02'}),
                    delay_after_sec=5,
                ),
                _create_step(
                    '联动反馈',
                    2,
                    _create_object('component_status', {'componentType': 86, 'componentStatus': 64, 'description': '联动模块反馈'}),
                    delay_after_sec=5,
                ),
                _create_step(
                    '烟感恢复',
                    2,
                    _create_object('component_status', {'componentType': 42, 'componentStatus': 0, 'description': 'A区1层大厅烟感01恢复'}),
                    delay_after_sec=5,
                ),
            ],
        },
    ]
    return templates


def _default_scene() -> Dict[str, Any]:
    return {
        'id': '',
        'name': '未命名场景',
        'category': 'custom',
        'description': '',
        'source': 'draft',
        'version': 2,
        'loop': True,
        'steps': [
            _create_step(
                '步骤1',
                2,
                _create_object('component_status', {'componentType': 42, 'componentStatus': 2, 'description': '默认烟感火警'}),
            ),
            _create_step(
                '步骤2',
                2,
                _create_object('component_status', {'componentType': 23, 'componentStatus': 2, 'description': '默认手报火警'}),
            ),
        ],
    }


def _migrate_step(step: Dict[str, Any]) -> Dict[str, Any]:
    if 'object' not in step and 'objects' in step:
        objects = step['objects']
        if isinstance(objects, list) and len(objects) > 0:
            step['object'] = objects[0]
        else:
            step['object'] = _create_object('component_status')
        del step['objects']
    elif 'object' not in step:
        step['object'] = _create_object('component_status')
    return step


def _migrate_template(template: Dict[str, Any]) -> Dict[str, Any]:
    steps = template.get('steps') or []
    template['steps'] = [_migrate_step(s) for s in steps]
    if 'version' not in template:
        template['version'] = 2
    return template


def _load_user_templates() -> List[Dict[str, Any]]:
    if not os.path.exists(TEMPLATE_FILE):
        return []
    try:
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        templates = data.get('templates', [])
        return [_migrate_template(t) for t in templates]
    except Exception:
        return []


def _save_user_templates(templates: List[Dict[str, Any]]) -> None:
    with open(TEMPLATE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(
            {
                'templates': templates,
                'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )


def get_auto_send_meta() -> Dict[str, Any]:
    CATEGORY_OPTIONS = [
        {'value': 'fire', 'label': '火警报警', 'desc': '类型标志2·部件状态火警'},
        {'value': 'fault', 'label': '故障报警', 'desc': '类型标志2·部件状态故障'},
        {'value': 'restore', 'label': '状态恢复', 'desc': '类型标志2·部件状态恢复'},
        {'value': 'linkage', 'label': '联动控制', 'desc': '类型标志2·启动/反馈'},
        {'value': 'supervise', 'label': '监管报警', 'desc': '类型标志2·部件状态监管'},
        {'value': 'analog', 'label': '模拟量监控', 'desc': '类型标志3·温度/烟雾/压力'},
        {'value': 'device', 'label': '传输装置', 'desc': '类型标志21·装置运行状态'},
        {'value': 'shield', 'label': '屏蔽管理', 'desc': '类型标志2·部件状态屏蔽'},
        {'value': 'sequence', 'label': '序列编排', 'desc': '多步骤时序组合'},
        {'value': 'custom', 'label': '自定义', 'desc': '用户自定义编排'},
    ]

    CATEGORY_DEFAULTS = {
        'fire':     {'typeFlag': 2, 'command': 2, 'objectType': 'component_status'},
        'fault':    {'typeFlag': 2, 'command': 2, 'objectType': 'component_status'},
        'restore':  {'typeFlag': 2, 'command': 2, 'objectType': 'component_status'},
        'linkage':  {'typeFlag': 2, 'command': 2, 'objectType': 'component_status'},
        'supervise': {'typeFlag': 2, 'command': 2, 'objectType': 'component_status'},
        'analog':   {'typeFlag': 3, 'command': 2, 'objectType': 'analog_value'},
        'device':   {'typeFlag': 21, 'command': 2, 'objectType': 'device_status'},
        'shield':   {'typeFlag': 2, 'command': 2, 'objectType': 'component_status'},
    }

    supported_type_flags = sorted(TYPE_FLAG_OBJECT_COMPATIBILITY.keys())
    return {
        'commands': _enum_options(COMMAND_CN),
        'typeFlags': _enum_options(TYPE_FLAG_CN, allow=supported_type_flags),
        'systemTypes': _enum_options(SYSTEM_TYPE_CN),
        'componentTypes': _enum_options(COMPONENT_TYPE_CN),
        'systemTypeComponentMap': {str(k): v for k, v in SYSTEM_TYPE_TO_COMPONENTS.items()},
        'analogTypes': _analog_options(),
        'objectTypes': [
            {'value': key, 'label': meta['label']}
            for key, meta in OBJECT_TYPE_META.items()
        ],
        'compatibility': deep_copy(TYPE_FLAG_OBJECT_COMPATIBILITY),
        'statusPresets': {
            'component_status': deep_copy(COMPONENT_STATUS_PRESETS),
            'system_status': deep_copy(SYSTEM_STATUS_PRESETS),
            'device_status': deep_copy(DEVICE_STATUS_PRESETS),
        },
        'statusBits': {
            'component_status': deep_copy(COMPONENT_STATUS_BITS),
            'system_status': deep_copy(SYSTEM_STATUS_BITS),
            'device_status': deep_copy(DEVICE_STATUS_BITS),
        },
        'categories': CATEGORY_OPTIONS,
        'categoryDefaults': CATEGORY_DEFAULTS,
        'defaultScene': _default_scene(),
    }


def list_templates() -> List[Dict[str, Any]]:
    templates = _system_templates() + _load_user_templates()
    return deep_copy(templates)


def get_template(template_id: str) -> Dict[str, Any] | None:
    for template in list_templates():
        if template.get('id') == template_id:
            return template
    return None


def save_template(scene: Dict[str, Any], template_id: str | None = None) -> Dict[str, Any]:
    user_templates = _load_user_templates()
    payload = deep_copy(scene)
    payload['steps'] = payload.get('steps') or []
    payload['name'] = (payload.get('name') or '').strip() or '未命名模板'
    payload['category'] = payload.get('category') or 'custom'
    payload['description'] = payload.get('description', '')
    payload['version'] = int(payload.get('version') or 2)
    payload['source'] = 'user'

    if template_id:
        for index, template in enumerate(user_templates):
            if template.get('id') == template_id:
                payload['id'] = template_id
                user_templates[index] = payload
                _save_user_templates(user_templates)
                return deep_copy(payload)

    payload['id'] = f'user_{uuid.uuid4().hex[:10]}'
    user_templates.append(payload)
    _save_user_templates(user_templates)
    return deep_copy(payload)


def delete_template(template_id: str) -> bool:
    user_templates = _load_user_templates()
    filtered = [item for item in user_templates if item.get('id') != template_id]
    if len(filtered) == len(user_templates):
        return False
    _save_user_templates(filtered)
    return True


def _component_addr_from_fields(fields: Dict[str, Any]) -> int:
    """从位号+区号计算部件地址(4B LE): 位号(2B) + 区号(2B)"""
    bit_no = parse_int(fields.get('bitNo'), 1)
    zone_no = parse_int(fields.get('zoneNo'), 1)
    # 兼容旧数据: 如果直接传了 componentAddr 则优先使用
    if 'componentAddr' in fields and fields.get('componentAddr') not in (None, ''):
        return parse_int(fields.get('componentAddr'), 1)
    return bit_no | (zone_no << 16)


def _build_object_bytes(object_type: str, fields: Dict[str, Any], step_index: int, component_addr_byteorder: str = 'little') -> bytes:
    builder = ADUBuilder()
    occurred_at = _parse_occured_at(fields)
    if object_type == 'system_status':
        return builder.build_system_status(
            parse_int(fields.get('systemType'), 1),
            parse_int(fields.get('systemAddr'), 1),
            parse_int(fields.get('systemStatus'), 0),
            occurred_at,
        )
    if object_type == 'analog_value':
        return builder.build_analog_value(
            parse_int(fields.get('systemType'), 1),
            parse_int(fields.get('systemAddr'), 1),
            parse_int(fields.get('componentType'), 31),
            _component_addr_from_fields(fields),
            parse_int(fields.get('analogType'), 3),
            parse_int(fields.get('analogValue'), 0),
            occurred_at,
            component_addr_byteorder=component_addr_byteorder,
        )
    if object_type == 'device_status':
        return builder.build_device_status(
            parse_int(fields.get('statusByte'), 0),
            occurred_at,
        )
    if object_type == 'component_status':
        return builder.build_component_status(
            parse_int(fields.get('systemType'), 1),
            parse_int(fields.get('systemAddr'), 1),
            parse_int(fields.get('componentType'), 42),
            _component_addr_from_fields(fields),
            parse_int(fields.get('componentStatus'), 0),
            str(fields.get('description') or ''),
            occurred_at,
            component_addr_byteorder=component_addr_byteorder,
        )
    raise _field_error(step_index, 'objectType', f'不支持的对象类型: {object_type}')


def _normalize_step(step: Dict[str, Any], step_index: int, scene_name: str, addr_byte_order: str = 'little', component_addr_byteorder: str = 'little') -> Dict[str, Any]:
    header = step.get('packetHeader') or {}
    type_flag = parse_int(header.get('typeFlag'), 2)
    if type_flag not in TYPE_FLAG_OBJECT_COMPATIBILITY:
        raise _field_error(step_index, f'steps[{step_index}].packetHeader.typeFlag', f'暂不支持的类型标志 {type_flag}')

    allowed_object_types = TYPE_FLAG_OBJECT_COMPATIBILITY[type_flag]
    command = parse_int(header.get('command'), 2)
    source_addr = parse_int(header.get('sourceAddr'), 0x000000000001)
    dest_addr = parse_int(header.get('destAddr'), 0x000000000002)
    delay_after_sec = max(0, parse_int(step.get('delayAfterSec'), 5))
    name = (step.get('name') or '').strip() or f'步骤{step_index + 1}'

    obj = step.get('object')
    if not obj:
        raise _field_error(step_index, f'steps[{step_index}].object', '步骤缺少信息对象')

    object_type = obj.get('objectType') or ''
    if object_type not in allowed_object_types:
        raise _field_error(
            step_index,
            f'steps[{step_index}].object.objectType',
            f'对象类型 {object_type} 与类型标志 {type_flag} 不兼容',
        )
    fields = obj.get('fields') or {}
    try:
        payload = _build_object_bytes(object_type, fields, step_index, component_addr_byteorder=component_addr_byteorder)
    except ValueError as exc:
        raise _field_error(
            step_index,
            f'steps[{step_index}].object',
            str(exc),
        ) from exc

    normalized_object = {
        'id': obj.get('id') or f'obj_1',
        'objectType': object_type,
        'fields': deep_copy(fields),
    }

    adu = ADUBuilder.build_adu(type_flag, [payload])
    packet_builder = GBT26875Packet(source_addr=source_addr, dest_addr=dest_addr, command=command, addr_byte_order=addr_byte_order)
    packet = packet_builder.build_packet(adu)
    packet_view = build_packet_view(
        packet,
        addr_byte_order=addr_byte_order,
        scene_name=scene_name,
        step_id=step.get('id') or f'step_{step_index + 1}',
        step_name=name,
    )
    return {
        'id': step.get('id') or f'step_{step_index + 1}',
        'name': name,
        'delay_after_sec': delay_after_sec,
        'type_flag': type_flag,
        'command': command,
        'source_addr': source_addr,
        'dest_addr': dest_addr,
        'scene_name': scene_name,
        'object': normalized_object,
        'packet': packet,
        'packet_hex': packet.hex(),
        'packet_view': packet_view,
    }


def build_scene_plan(scene: Dict[str, Any], addr_byte_order: str = 'little', component_addr_byteorder: str = 'little') -> Dict[str, Any]:
    payload = deep_copy(scene or {})
    scene_name = (payload.get('name') or '').strip() or '未命名场景'
    steps = payload.get('steps') or []
    if not steps:
        raise ValueError('场景至少需要 1 个步骤')
    normalized_steps = [_normalize_step(step, index, scene_name, addr_byte_order=addr_byte_order, component_addr_byteorder=component_addr_byteorder) for index, step in enumerate(steps)]
    return {
        'scene_id': payload.get('id') or '',
        'scene_name': scene_name,
        'category': payload.get('category') or 'custom',
        'description': payload.get('description') or '',
        'source': payload.get('source') or 'draft',
        'loop': bool(payload.get('loop', True)),
        'steps': normalized_steps,
    }


def rebuild_step_packet(step: Dict[str, Any], addr_byte_order: str = 'little', component_addr_byteorder: str = 'little') -> Dict[str, Any]:
    type_flag = step['type_flag']
    command = step['command']
    source_addr = step['source_addr']
    dest_addr = step['dest_addr']
    scene_name = step.get('scene_name', '')

    obj = step.get('object', {})
    object_bytes = [_build_object_bytes(obj['objectType'], obj['fields'], 0, component_addr_byteorder=component_addr_byteorder)]

    adu = ADUBuilder.build_adu(type_flag, object_bytes)
    packet_builder = GBT26875Packet(source_addr=source_addr, dest_addr=dest_addr, command=command, addr_byte_order=addr_byte_order)
    packet = packet_builder.build_packet(adu)
    packet_view = build_packet_view(
        packet,
        addr_byte_order=addr_byte_order,
        component_addr_byteorder=component_addr_byteorder,
        scene_name=scene_name,
        step_id=step['id'],
        step_name=step['name'],
    )

    return {
        'packet': packet,
        'packet_hex': packet.hex(),
        'packet_view': packet_view,
    }
