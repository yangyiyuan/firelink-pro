import copy
import json
import os
import uuid
from typing import Any, Dict, List, Optional

from protocol.scene_catalog import SCENE_CATALOG
from protocol.simulator import FireAlarmSimulator
from protocol.core import GBT26875Packet
from protocol.packet_view import build_packet_view
from services.utils import now_str, parse_int


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
                'updated_at': now_str(),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )


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
                normalized[key] = parse_int(val)
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


def _patch_packet_addrs(packet: bytes, source_addr: int, dest_addr: int, addr_byte_order: str = 'little') -> bytes:
    pkt = bytearray(packet)
    source_bytes = source_addr.to_bytes(6, byteorder=addr_byte_order)
    dest_bytes = dest_addr.to_bytes(6, byteorder=addr_byte_order)
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
    return copy.deepcopy(item) if item else None


def list_instances() -> List[Dict[str, Any]]:
    instances = _load_instances()
    instances.sort(key=lambda x: x.get('lastUsedAt') or x.get('updatedAt') or x.get('createdAt') or '', reverse=True)
    return copy.deepcopy(instances)


def get_instance(instance_id: str) -> Optional[Dict[str, Any]]:
    for inst in _load_instances():
        if inst.get('id') == instance_id:
            return copy.deepcopy(inst)
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

    now = now_str()
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
    return copy.deepcopy(instance)


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

    existing['updatedAt'] = now_str()
    instances[target_index] = existing
    _save_instances(instances)
    return copy.deepcopy(existing)


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
            inst['lastUsedAt'] = now_str()
            inst['useCount'] = inst.get('useCount', 0) + 1
            break
    _save_instances(instances)


_PATCH_FIELD_DEFS = {
    1: [
        ('systemType', 0, 1), ('systemAddr', 1, 1), ('systemStatus', 2, 2),
    ],
    2: [
        ('systemType', 0, 1), ('systemAddr', 1, 1), ('componentType', 2, 1),
        ('zoneNo', 3, 2), ('bitNo', 5, 2), ('componentStatus', 7, 2),
    ],
    3: [
        ('systemType', 0, 1), ('systemAddr', 1, 1), ('componentType', 2, 1),
        ('zoneNo', 3, 2), ('bitNo', 5, 2),
    ],
    4: [
        ('systemType', 0, 1), ('systemAddr', 1, 1),
    ],
    5: [
        ('systemType', 0, 1), ('systemAddr', 1, 1),
    ],
    7: [
        ('systemType', 0, 1), ('systemAddr', 1, 1), ('componentType', 2, 1),
        ('zoneNo', 3, 2), ('bitNo', 5, 2),
    ],
    8: [
        ('systemType', 0, 1), ('systemAddr', 1, 1),
    ],
    21: [
        ('statusByte', 0, 1),
    ],
}

_PATCH_OBJ_SIZES = {
    1: 2 + 2 + 6,
    2: 8 + 4 + 2 + 31 + 6,
    3: 10 + 6,
    4: 2 + 2 + 6,
    5: 2 + 6 + 2,
    7: 8 + 31 + 6,
    8: 2 + 6 + 6,
    21: 1 + 6 + 6,
}

# 部件地址子字段：这些字段需要按部件地址字节序写入
_COMPONENT_ADDR_FIELDS = {'zoneNo', 'bitNo'}


def _patch_packet_adu(packet: bytes, template_id: str, device: Dict[str, Any], component_addr_byteorder: str = 'little') -> bytes:
    pkt = bytearray(packet)
    control_unit = pkt[2:27]
    adu_length = int.from_bytes(control_unit[22:24], byteorder='little')
    adu_start = 27
    adu = pkt[adu_start:adu_start + adu_length]
    if len(adu) < 2:
        return packet
    type_flag = adu[0]
    info_count = adu[1]

    field_defs = _PATCH_FIELD_DEFS.get(type_flag)
    obj_size = _PATCH_OBJ_SIZES.get(type_flag)

    if type_flag == 6:
        field_defs = [('systemType', 0, 1), ('systemAddr', 1, 1)]

    if field_defs is None or obj_size is None:
        if type_flag != 6:
            new_control_unit = bytes(pkt[2:27])
            new_adu = bytes(pkt[adu_start:adu_start + adu_length])
            checksum = GBT26875Packet(0, 0)._calc_checksum(new_control_unit + new_adu)
            pkt[adu_start + adu_length] = checksum
            return bytes(pkt)

    obj_offset = 2
    for _ in range(info_count):
        if type_flag == 6:
            if obj_offset + 3 > len(adu):
                break
            text_len = adu[obj_offset + 2]
            obj_size = 3 + text_len + 6

        min_offset = max((off + size) for _, off, size in field_defs) if field_defs else 0
        if obj_offset + min_offset > len(adu):
            break

        for field_name, rel_off, byte_count in field_defs:
            val = device.get(field_name)
            if val is not None:
                iv = int(val)
                field_byteorder = component_addr_byteorder if field_name in _COMPONENT_ADDR_FIELDS else 'little'
                iv_bytes = iv.to_bytes(byte_count, byteorder=field_byteorder)
                for b in range(byte_count):
                    pkt[adu_start + obj_offset + rel_off + b] = iv_bytes[b]

        obj_offset += obj_size

    new_control_unit = bytes(pkt[2:27])
    new_adu = bytes(pkt[adu_start:adu_start + adu_length])
    checksum = GBT26875Packet(0, 0)._calc_checksum(new_control_unit + new_adu)
    pkt[adu_start + adu_length] = checksum
    return bytes(pkt)


def resolve_instance_packet(instance: Dict[str, Any], simulator: FireAlarmSimulator, addr_byte_order: str = 'little', component_addr_byteorder: str = 'little') -> bytes:
    template_id = instance.get('templateId', '')
    catalog_item = get_scene_catalog_item(template_id)
    if catalog_item is None:
        snapshot = instance.get('templateSnapshot', {})
        if snapshot and snapshot.get('id'):
            raise ValueError(
                f'实例依赖的信号模板 {template_id} 已不存在（快照名称: {snapshot.get("name", "未知")}），请重新绑定模板'
            )
        raise ValueError(f'实例依赖的信号模板 {template_id} 不存在')

    packet = simulator.get_scene_packet(template_id)

    device = instance.get('deviceParams', {})
    source_addr = device.get('sourceAddr')
    dest_addr = device.get('destAddr')
    if source_addr or dest_addr:
        src = _parse_addr(source_addr) if source_addr else int.from_bytes(packet[12:18], byteorder=addr_byte_order)
        dst = _parse_addr(dest_addr) if dest_addr else int.from_bytes(packet[18:24], byteorder=addr_byte_order)
        packet = _patch_packet_addrs(packet, src, dst, addr_byte_order=addr_byte_order)

    packet = _patch_packet_adu(packet, template_id, device, component_addr_byteorder=component_addr_byteorder)

    return packet


def preview_instance(instance_id: str, simulator: FireAlarmSimulator, addr_byte_order: str = 'little', component_addr_byteorder: str = 'little') -> Dict[str, Any]:
    instance = get_instance(instance_id)
    if instance is None:
        raise ValueError(f'实例 {instance_id} 不存在')

    packet = resolve_instance_packet(instance, simulator, addr_byte_order=addr_byte_order, component_addr_byteorder=component_addr_byteorder)
    packet_view = build_packet_view(packet, addr_byte_order=addr_byte_order, component_addr_byteorder=component_addr_byteorder, scene=instance.get('templateId', ''), timestamp=now_str())

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
