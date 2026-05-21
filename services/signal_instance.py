import copy
import datetime
import json
import os
import uuid
from typing import Any, Dict, List, Optional

try:
    from fire_alarm_simulator.protocol.core import (
        SCENE_CATALOG,
        FireAlarmSimulator,
        GBT26875Packet,
        build_packet_view,
    )
except ModuleNotFoundError:
    from protocol.core import (
        SCENE_CATALOG,
        FireAlarmSimulator,
        GBT26875Packet,
        build_packet_view,
    )


SERVICE_DIR = os.path.dirname(os.path.dirname(__file__))
INSTANCE_FILE = os.path.join(SERVICE_DIR, 'signal_instances.json')

INSTANCE_NAME_MAX = 80
INSTANCE_DESC_MAX = 300
TAG_MAX_COUNT = 5
TAG_MAX_LENGTH = 20

DEVICE_PARAM_KEYS = [
    'sourceAddr', 'destAddr', 'systemType', 'systemAddr',
    'componentType', 'zoneNo', 'bitNo',
    'componentStatus', 'systemStatus', 'statusByte',
]

DEVICE_REQUIRED_KEYS = ['sourceAddr', 'destAddr']

TEMPLATE_STATUS_MAP = {
    'component_status': 'componentStatus',
    'system_status': 'systemStatus',
    'device_status': 'statusByte',
}

_SCENE_MAP = {item['id']: item for item in SCENE_CATALOG}

_simulator = None


def _get_simulator() -> FireAlarmSimulator:
    global _simulator
    if _simulator is None:
        _simulator = FireAlarmSimulator()
    return _simulator


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _now_str() -> str:
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _load_instances() -> List[Dict[str, Any]]:
    if not os.path.exists(INSTANCE_FILE):
        return []
    try:
        with open(INSTANCE_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        return data.get('instances', [])
    except Exception:
        return []


def _save_instances(instances: List[Dict[str, Any]]) -> None:
    with open(INSTANCE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(
            {
                'instances': instances,
                'updated_at': _now_str(),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )


def _parse_int(value: Any, default: Optional[int] = None) -> int:
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


def _validate_device_params(params: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(params, dict):
        raise ValueError('deviceParams 必须是对象')

    for key in DEVICE_REQUIRED_KEYS:
        if key not in params or params[key] in (None, ''):
            raise ValueError(f'deviceParams.{key} 为必填字段')

    normalized: Dict[str, Any] = {}
    for key in DEVICE_PARAM_KEYS:
        val = params.get(key)
        if val is None or val == '':
            continue
        if key in ('sourceAddr', 'destAddr'):
            normalized[key] = str(val).strip()
            if not normalized[key]:
                raise ValueError(f'deviceParams.{key} 不能为空字符串')
        else:
            try:
                normalized[key] = _parse_int(val)
            except (ValueError, TypeError):
                raise ValueError(f'deviceParams.{key} 必须是整数')
    return normalized


def _validate_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise ValueError('tags 必须是数组')
    if len(tags) > TAG_MAX_COUNT:
        raise ValueError(f'标签数量不能超过 {TAG_MAX_COUNT}')
    result = []
    for tag in tags:
        text = str(tag).strip()
        if not text:
            continue
        if len(text) > TAG_MAX_LENGTH:
            raise ValueError(f'单个标签长度不能超过 {TAG_MAX_LENGTH}')
        result.append(text)
    return result


def _build_snapshot(catalog_item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': catalog_item.get('id', ''),
        'name': catalog_item.get('name', ''),
        'group': catalog_item.get('group', ''),
        'description': catalog_item.get('description', ''),
    }


def _patch_packet_addrs(packet: bytes, source_addr: int, dest_addr: int) -> bytes:
    pkt = bytearray(packet)
    source_bytes = source_addr.to_bytes(6, byteorder='little')
    dest_bytes = dest_addr.to_bytes(6, byteorder='little')
    pkt[12:18] = source_bytes
    pkt[18:24] = dest_bytes
    control_unit = bytes(pkt[2:27])
    adu_length = int.from_bytes(control_unit[22:24], byteorder='little')
    adu = bytes(pkt[27:27 + adu_length])
    checksum = GBT26875Packet(0, 0)._calc_checksum(control_unit + adu)
    pkt[27 + adu_length] = checksum
    return bytes(pkt)


def _parse_addr(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.startswith('0x') or text.startswith('0X'):
        return int(text, 16)
    return int(text)


def get_scene_catalog_item(template_id: str) -> Optional[Dict[str, Any]]:
    item = _SCENE_MAP.get(template_id)
    return _copy(item) if item else None


def list_instances() -> List[Dict[str, Any]]:
    instances = _load_instances()
    instances.sort(key=lambda x: x.get('lastUsedAt') or x.get('updatedAt') or x.get('createdAt') or '', reverse=True)
    return _copy(instances)


def get_instance(instance_id: str) -> Optional[Dict[str, Any]]:
    for inst in _load_instances():
        if inst.get('id') == instance_id:
            return _copy(inst)
    return None


def create_instance(data: Dict[str, Any]) -> Dict[str, Any]:
    name = str(data.get('name') or '').strip()
    if not name:
        raise ValueError('实例名称不能为空')
    if len(name) > INSTANCE_NAME_MAX:
        raise ValueError(f'实例名称不能超过 {INSTANCE_NAME_MAX} 字符')

    template_id = str(data.get('templateId') or '').strip()
    if not template_id:
        raise ValueError('templateId 不能为空')

    catalog_item = get_scene_catalog_item(template_id)
    if catalog_item is None:
        raise ValueError(f'信号模板 {template_id} 不存在')

    device_params = _validate_device_params(data.get('deviceParams') or {})
    tags = _validate_tags(data.get('tags'))
    description = str(data.get('description') or '').strip()
    if len(description) > INSTANCE_DESC_MAX:
        raise ValueError(f'描述不能超过 {INSTANCE_DESC_MAX} 字符')

    now = _now_str()
    instance: Dict[str, Any] = {
        'id': f'inst_{uuid.uuid4().hex[:8]}',
        'name': name,
        'description': description,
        'templateId': template_id,
        'templateSnapshot': _build_snapshot(catalog_item),
        'source': 'user',
        'tags': tags,
        'deviceParams': device_params,
        'stepOverrides': [],
        'createdAt': now,
        'updatedAt': now,
        'lastUsedAt': None,
        'useCount': 0,
    }

    instances = _load_instances()
    instances.append(instance)
    _save_instances(instances)
    return _copy(instance)


def update_instance(instance_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    instances = _load_instances()
    target_index = None
    for i, inst in enumerate(instances):
        if inst.get('id') == instance_id:
            target_index = i
            break

    if target_index is None:
        raise ValueError(f'实例 {instance_id} 不存在')

    existing = instances[target_index]

    if 'name' in data:
        name = str(data['name'] or '').strip()
        if not name:
            raise ValueError('实例名称不能为空')
        if len(name) > INSTANCE_NAME_MAX:
            raise ValueError(f'实例名称不能超过 {INSTANCE_NAME_MAX} 字符')
        existing['name'] = name

    if 'description' in data:
        description = str(data['description'] or '').strip()
        if len(description) > INSTANCE_DESC_MAX:
            raise ValueError(f'描述不能超过 {INSTANCE_DESC_MAX} 字符')
        existing['description'] = description

    if 'deviceParams' in data:
        existing['deviceParams'] = _validate_device_params(data['deviceParams'])

    if 'tags' in data:
        existing['tags'] = _validate_tags(data['tags'])

    if 'templateId' in data:
        template_id = str(data['templateId'] or '').strip()
        if not template_id:
            raise ValueError('templateId 不能为空')
        catalog_item = get_scene_catalog_item(template_id)
        if catalog_item is None:
            raise ValueError(f'信号模板 {template_id} 不存在')
        existing['templateId'] = template_id
        existing['templateSnapshot'] = _build_snapshot(catalog_item)

    existing['updatedAt'] = _now_str()
    instances[target_index] = existing
    _save_instances(instances)
    return _copy(existing)


def delete_instance(instance_id: str) -> bool:
    instances = _load_instances()
    filtered = [item for item in instances if item.get('id') != instance_id]
    if len(filtered) == len(instances):
        return False
    _save_instances(filtered)
    return True


def touch_instance(instance_id: str) -> None:
    instances = _load_instances()
    for inst in instances:
        if inst.get('id') == instance_id:
            inst['lastUsedAt'] = _now_str()
            inst['useCount'] = inst.get('useCount', 0) + 1
            break
    _save_instances(instances)


def _patch_packet_adu(packet: bytes, template_id: str, device: Dict[str, Any]) -> bytes:
    pkt = bytearray(packet)
    control_unit = pkt[2:27]
    adu_length = int.from_bytes(control_unit[22:24], byteorder='little')
    adu_start = 27
    adu = pkt[adu_start:adu_start + adu_length]
    if len(adu) < 2:
        return packet
    type_flag = adu[0]
    info_count = adu[1]

    obj_offset = 2
    for _ in range(info_count):
        if type_flag == 2:
            if obj_offset + 8 > len(adu):
                break
            if 'systemType' in device and device['systemType'] is not None:
                pkt[adu_start + obj_offset] = int(device['systemType']) & 0xFF
            if 'systemAddr' in device and device['systemAddr'] is not None:
                pkt[adu_start + obj_offset + 1] = int(device['systemAddr']) & 0xFF
            if 'componentType' in device and device['componentType'] is not None:
                pkt[adu_start + obj_offset + 2] = int(device['componentType']) & 0xFF
            if 'zoneNo' in device and device['zoneNo'] is not None:
                zone_no = int(device['zoneNo'])
                pkt[adu_start + obj_offset + 3] = zone_no & 0xFF
                pkt[adu_start + obj_offset + 4] = (zone_no >> 8) & 0xFF
            if 'bitNo' in device and device['bitNo'] is not None:
                bit_no = int(device['bitNo'])
                pkt[adu_start + obj_offset + 5] = bit_no & 0xFF
                pkt[adu_start + obj_offset + 6] = (bit_no >> 8) & 0xFF
            if 'componentStatus' in device and device['componentStatus'] is not None:
                sv = int(device['componentStatus'])
                pkt[adu_start + obj_offset + 7] = sv & 0xFF
                pkt[adu_start + obj_offset + 8] = (sv >> 8) & 0xFF
            obj_offset += 8 + 4 + 2 + 31 + 6
        elif type_flag == 1:
            if obj_offset + 4 > len(adu):
                break
            if 'systemType' in device and device['systemType'] is not None:
                pkt[adu_start + obj_offset] = int(device['systemType']) & 0xFF
            if 'systemAddr' in device and device['systemAddr'] is not None:
                pkt[adu_start + obj_offset + 1] = int(device['systemAddr']) & 0xFF
            if 'systemStatus' in device and device['systemStatus'] is not None:
                sv = int(device['systemStatus'])
                pkt[adu_start + obj_offset + 2] = sv & 0xFF
                pkt[adu_start + obj_offset + 3] = (sv >> 8) & 0xFF
            obj_offset += 2 + 2 + 6
        elif type_flag == 3:
            if obj_offset + 10 > len(adu):
                break
            if 'systemType' in device and device['systemType'] is not None:
                pkt[adu_start + obj_offset] = int(device['systemType']) & 0xFF
            if 'systemAddr' in device and device['systemAddr'] is not None:
                pkt[adu_start + obj_offset + 1] = int(device['systemAddr']) & 0xFF
            if 'componentType' in device and device['componentType'] is not None:
                pkt[adu_start + obj_offset + 2] = int(device['componentType']) & 0xFF
            if 'zoneNo' in device and device['zoneNo'] is not None:
                zone_no = int(device['zoneNo'])
                pkt[adu_start + obj_offset + 3] = zone_no & 0xFF
                pkt[adu_start + obj_offset + 4] = (zone_no >> 8) & 0xFF
            if 'bitNo' in device and device['bitNo'] is not None:
                bit_no = int(device['bitNo'])
                pkt[adu_start + obj_offset + 5] = bit_no & 0xFF
                pkt[adu_start + obj_offset + 6] = (bit_no >> 8) & 0xFF
            obj_offset += 10 + 6
        elif type_flag == 4:
            if obj_offset + 4 > len(adu):
                break
            if 'systemType' in device and device['systemType'] is not None:
                pkt[adu_start + obj_offset] = int(device['systemType']) & 0xFF
            if 'systemAddr' in device and device['systemAddr'] is not None:
                pkt[adu_start + obj_offset + 1] = int(device['systemAddr']) & 0xFF
            obj_offset += 2 + 2 + 6
        elif type_flag in (5, 8):
            if obj_offset + 2 > len(adu):
                break
            if 'systemType' in device and device['systemType'] is not None:
                pkt[adu_start + obj_offset] = int(device['systemType']) & 0xFF
            if 'systemAddr' in device and device['systemAddr'] is not None:
                pkt[adu_start + obj_offset + 1] = int(device['systemAddr']) & 0xFF
            obj_offset += 2 + 6 + (6 if type_flag == 8 else 2)
        elif type_flag == 6:
            if obj_offset + 3 > len(adu):
                break
            if 'systemType' in device and device['systemType'] is not None:
                pkt[adu_start + obj_offset] = int(device['systemType']) & 0xFF
            if 'systemAddr' in device and device['systemAddr'] is not None:
                pkt[adu_start + obj_offset + 1] = int(device['systemAddr']) & 0xFF
            text_len = adu[obj_offset + 2]
            obj_offset += 3 + text_len + 6
        elif type_flag == 7:
            if obj_offset + 8 > len(adu):
                break
            if 'systemType' in device and device['systemType'] is not None:
                pkt[adu_start + obj_offset] = int(device['systemType']) & 0xFF
            if 'systemAddr' in device and device['systemAddr'] is not None:
                pkt[adu_start + obj_offset + 1] = int(device['systemAddr']) & 0xFF
            if 'componentType' in device and device['componentType'] is not None:
                pkt[adu_start + obj_offset + 2] = int(device['componentType']) & 0xFF
            if 'zoneNo' in device and device['zoneNo'] is not None:
                zone_no = int(device['zoneNo'])
                pkt[adu_start + obj_offset + 3] = zone_no & 0xFF
                pkt[adu_start + obj_offset + 4] = (zone_no >> 8) & 0xFF
            if 'bitNo' in device and device['bitNo'] is not None:
                bit_no = int(device['bitNo'])
                pkt[adu_start + obj_offset + 5] = bit_no & 0xFF
                pkt[adu_start + obj_offset + 6] = (bit_no >> 8) & 0xFF
            obj_offset += 8 + 31 + 6
        elif type_flag == 21:
            if obj_offset + 1 > len(adu):
                break
            if 'statusByte' in device and device['statusByte'] is not None:
                pkt[adu_start + obj_offset] = int(device['statusByte']) & 0xFF
            obj_offset += 1 + 6 + 6
        else:
            break

    new_control_unit = bytes(pkt[2:27])
    new_adu = bytes(pkt[adu_start:adu_start + adu_length])
    checksum = GBT26875Packet(0, 0)._calc_checksum(new_control_unit + new_adu)
    pkt[adu_start + adu_length] = checksum
    return bytes(pkt)


def resolve_instance_packet(instance: Dict[str, Any]) -> bytes:
    template_id = instance.get('templateId', '')
    catalog_item = get_scene_catalog_item(template_id)
    if catalog_item is None:
        snapshot = instance.get('templateSnapshot', {})
        if snapshot and snapshot.get('id'):
            raise ValueError(
                f'实例依赖的信号模板 {template_id} 已不存在（快照名称: {snapshot.get("name", "未知")}），请重新绑定模板'
            )
        raise ValueError(f'实例依赖的信号模板 {template_id} 不存在')

    sim = _get_simulator()
    packet = sim.get_scene_packet(template_id)

    device = instance.get('deviceParams', {})
    source_addr = device.get('sourceAddr')
    dest_addr = device.get('destAddr')
    if source_addr or dest_addr:
        src = _parse_addr(source_addr) if source_addr else int.from_bytes(packet[12:18], byteorder='little')
        dst = _parse_addr(dest_addr) if dest_addr else int.from_bytes(packet[18:24], byteorder='little')
        packet = _patch_packet_addrs(packet, src, dst)

    packet = _patch_packet_adu(packet, template_id, device)

    return packet


def preview_instance(instance_id: str) -> Dict[str, Any]:
    instance = get_instance(instance_id)
    if instance is None:
        raise ValueError(f'实例 {instance_id} 不存在')

    packet = resolve_instance_packet(instance)
    packet_view = build_packet_view(packet, scene=instance.get('templateId', ''), timestamp=_now_str())

    return {
        'success': True,
        'instanceId': instance_id,
        'instanceName': instance.get('name', ''),
        'templateId': instance.get('templateId', ''),
        'sceneName': instance.get('name', ''),
        'loop': True,
        'steps': [
            {
                'id': 'step_1',
                'name': instance.get('name', '信号实例'),
                'delayAfterSec': 5,
                'typeFlag': packet_view.get('type_flag', 0),
                'command': packet_view.get('command', 2),
                'packetHex': packet.hex(),
                'packetLength': len(packet),
                'packetView': packet_view,
                'objectCount': packet_view.get('object_count', 1),
            }
        ],
    }
