import copy
import datetime
import random
import threading
from typing import Any, Dict, List, Optional

from . import standard as st
from .adu import PARSER_REGISTRY
from .profiles import jk_gh2013g as jk
from .shared import (
    COMMAND_CN,
    ByteReader,
    common_profile_notes,
    decode_time_tag,
    direction_for_type,
    field,
    format_bytes_hex,
    type_origin_for_flag,
    type_origin_label,
    TYPE_FLAG_CN,
)

CommandType = st.CommandType
TypeFlag = st.TypeFlag
SystemType = st.SystemType
ComponentType = st.ComponentType
AnalogType = st.AnalogType

SCENE_CATALOG = [
    # 消防设施状态 (TF 1~8)
    {'id': 'system_status', 'name': '系统状态', 'description': '建筑消防设施系统状态', 'level': 'danger', 'group': 'facility'},
    {'id': 'component_status', 'name': '部件状态', 'description': '部件运行状态（火警/故障/屏蔽/监管/恢复）', 'level': 'warning', 'group': 'facility'},
    {'id': 'analog_value', 'name': '模拟量值', 'description': '部件模拟量值（温度/烟雾/压力）', 'level': 'warning', 'group': 'facility'},
    {'id': 'operation_info', 'name': '操作信息', 'description': '消防设施操作信息（复位/消音/确认）', 'level': 'info', 'group': 'facility'},
    {'id': 'system_version', 'name': '软件版本', 'description': '消防设施软件版本信息', 'level': 'info', 'group': 'facility'},
    {'id': 'system_config', 'name': '系统配置', 'description': '消防设施系统配置情况', 'level': 'info', 'group': 'facility'},
    {'id': 'component_config', 'name': '部件配置', 'description': '消防设施部件配置情况', 'level': 'info', 'group': 'facility'},
    {'id': 'system_time', 'name': '系统时间', 'description': '消防设施系统时间', 'level': 'info', 'group': 'facility'},
    # 传输装置状态 (TF 21~28)
    {'id': 'device_status', 'name': '装置运行状态', 'description': '传输装置运行状态（正常/火警/故障/屏蔽）', 'level': 'info', 'group': 'device'},
    {'id': 'device_operation', 'name': '装置操作信息', 'description': '传输装置操作信息', 'level': 'info', 'group': 'device'},
    {'id': 'device_version', 'name': '装置软件版本', 'description': '传输装置软件版本信息', 'level': 'info', 'group': 'device'},
    {'id': 'device_config', 'name': '装置配置', 'description': '传输装置配置情况', 'level': 'info', 'group': 'device'},
    {'id': 'device_time', 'name': '装置系统时间', 'description': '传输装置系统时间', 'level': 'info', 'group': 'device'},
    # 快捷工具
    {'id': 'random', 'name': '随机模板', 'description': '随机生成一种信号', 'level': 'info', 'group': 'tool'},
]

SUPPORTED_TYPE_FLAGS = tuple(sorted(PARSER_REGISTRY))


class SequenceManager:
    """业务流水号全局自增管理器（线程安全）

    GB/T 26875.3-2011 规定控制单元中业务流水号为2字节无符号整数，
    范围 0~65535，溢出后回绕至0。所有数据包发送共享同一序号源，
    确保连续发送时序号严格递增。
    """

    def __init__(self, start: int = 0):
        self._sequence = start % 65536
        self._lock = threading.Lock()

    def next(self) -> int:
        """获取当前序号并自增（线程安全）"""
        with self._lock:
            seq = self._sequence
            self._sequence = (self._sequence + 1) % 65536
            return seq

    def current(self) -> int:
        """获取当前序号（不自增）"""
        with self._lock:
            return self._sequence

    def reset(self, value: int = 0) -> None:
        """重置序号到指定值"""
        with self._lock:
            self._sequence = value % 65536


# 全局单例：应用级共享的流水号管理器
sequence_manager = SequenceManager()


def parse_adu(adu_bytes: bytes) -> Dict[str, Any]:
    if len(adu_bytes) < 2:
        raise ValueError('ADU长度不足，至少需要2字节')

    type_flag = adu_bytes[0]
    info_count = adu_bytes[1]
    payload = adu_bytes[2:]
    reader = ByteReader(payload)
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
        'summary_short': summary_short,
        'objects': objects,
        'notes': notes,
        'parse_error': parse_error,
        'trailing_hex': trailing.hex(),
    }


class GBT26875Packet:
    START_FLAG = b'\x40\x40'
    END_FLAG = b'\x23\x23'
    MAX_ADU_LENGTH = 1024

    def __init__(self, source_addr: int = 0x000000000001, dest_addr: int = 0x000000000002, command: CommandType = CommandType.SEND_DATA, version_major: int = 1, version_minor: int = 0):
        self.source_addr = source_addr
        self.dest_addr = dest_addr
        self.command = command
        self.version_major = version_major
        self.version_minor = version_minor

    def _int_to_bytes(self, value: int, length: int, signed: bool = False) -> bytes:
        return value.to_bytes(length, byteorder='little', signed=signed)

    def _get_time_tag(self, dt: Optional[datetime.datetime] = None) -> bytes:
        dt = dt or datetime.datetime.now()
        return bytes([dt.second, dt.minute, dt.hour, dt.day, dt.month, dt.year % 100])

    def _calc_checksum(self, data: bytes) -> int:
        return sum(data) & 0xFF

    def build_packet(self, adu: bytes) -> bytes:
        if len(adu) > self.MAX_ADU_LENGTH:
            raise ValueError(f'应用数据单元长度不能超过{self.MAX_ADU_LENGTH}字节')
        seq = sequence_manager.next()
        seq_bytes = self._int_to_bytes(seq, 2)
        version = bytes([self.version_major, self.version_minor])
        control_unit = (
            seq_bytes
            + version
            + self._get_time_tag()
            + self._int_to_bytes(self.source_addr, 6)
            + self._int_to_bytes(self.dest_addr, 6)
            + self._int_to_bytes(len(adu), 2)
            + bytes([self.command])
        )
        checksum = self._calc_checksum(control_unit + adu)
        return self.START_FLAG + control_unit + adu + bytes([checksum]) + self.END_FLAG

    def parse_packet(self, packet: bytes) -> Dict[str, Any]:
        if len(packet) < 30:
            raise ValueError('数据包长度不足')
        if packet[:2] != self.START_FLAG:
            raise ValueError('启动符错误')
        if packet[-2:] != self.END_FLAG:
            raise ValueError('结束符错误')
        control_unit = packet[2:27]
        adu_length = int.from_bytes(control_unit[22:24], byteorder='little')
        adu = packet[27:27 + adu_length]
        checksum = packet[27 + adu_length]
        expected_checksum = self._calc_checksum(control_unit + adu)
        if checksum != expected_checksum:
            raise ValueError(f'校验和错误: 期望{expected_checksum}, 实际{checksum}')
        time_str = decode_time_tag(control_unit[4:10])
        return {
            'sequence': int.from_bytes(control_unit[0:2], byteorder='little'),
            'version_major': control_unit[2],
            'version_minor': control_unit[3],
            'time_tag': time_str,
            'source_addr': f"0x{int.from_bytes(control_unit[10:16], byteorder='little'):012x}",
            'dest_addr': f"0x{int.from_bytes(control_unit[16:22], byteorder='little'):012x}",
            'adu_length': adu_length,
            'command': control_unit[24],
            'adu': adu.hex(),
            'checksum': f"0x{checksum:02x}",
        }


class ADUBuilder:
    @staticmethod
    def _int_to_bytes(value: int, length: int, signed: bool = False) -> bytes:
        return value.to_bytes(length, byteorder='little', signed=signed)

    @staticmethod
    def _get_time_tag(dt: Optional[datetime.datetime] = None) -> bytes:
        dt = dt or datetime.datetime.now()
        return bytes([dt.second, dt.minute, dt.hour, dt.day, dt.month, dt.year % 100])

    @staticmethod
    def _str_to_bytes(text: str, length: int) -> bytes:
        encoded = text.encode('gb18030', errors='ignore')
        if len(encoded) > length:
            encoded = encoded[:length]
        return encoded.ljust(length, b'\x00')

    @classmethod
    def build_system_status(cls, system_type: int, system_addr: int, status: int, dt: Optional[datetime.datetime] = None) -> bytes:
        return bytes([system_type, system_addr]) + cls._int_to_bytes(status, 2) + cls._get_time_tag(dt)

    @classmethod
    def build_component_status(cls, system_type: int, system_addr: int, component_type: int, component_addr: int, component_status: int, component_desc: str = '', dt: Optional[datetime.datetime] = None) -> bytes:
        return bytes([system_type, system_addr, component_type]) + cls._int_to_bytes(component_addr, 4) + cls._int_to_bytes(component_status, 2) + cls._str_to_bytes(component_desc, 31) + cls._get_time_tag(dt)

    @classmethod
    def build_analog_value(cls, system_type: int, system_addr: int, component_type: int, component_addr: int, analog_type: int, analog_value: int, dt: Optional[datetime.datetime] = None) -> bytes:
        return bytes([system_type, system_addr, component_type]) + cls._int_to_bytes(component_addr, 4) + bytes([analog_type]) + cls._int_to_bytes(analog_value, 2, signed=True) + cls._get_time_tag(dt)

    @classmethod
    def build_operation_info(cls, system_type: int, system_addr: int, op_flag: int, operator_no: int, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建消防设施操作信息对象（TF=4）

        信息对象结构：
        - 系统类型标志（1字节）
        - 系统地址（1字节）
        - 操作标志（1字节）
        - 操作员编号（1字节）
        - 时间标签（6字节）
        """
        return bytes([system_type, system_addr, op_flag, operator_no]) + cls._get_time_tag(dt)

    @classmethod
    def build_system_version(cls, system_type: int, system_addr: int, major: int, minor: int, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建消防设施软件版本信息对象（TF=5）

        信息对象结构：
        - 系统类型标志（1字节）
        - 系统地址（1字节）
        - 主版本号（1字节）
        - 次版本号（1字节）
        - 时间标签（6字节）
        """
        return bytes([system_type, system_addr, major, minor]) + cls._get_time_tag(dt)

    @classmethod
    def build_device_version(cls, major: int, minor: int, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建传输装置软件版本信息对象（TF=25）

        信息对象结构：
        - 主版本号（1字节）
        - 次版本号（1字节）
        - 时间标签（6字节）
        """
        return bytes([major, minor]) + cls._get_time_tag(dt)

    @classmethod
    def build_device_config(cls, text: str, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建传输装置配置信息对象（TF=26）

        信息对象结构：
        - 配置说明长度（1字节，L=0~255）
        - 配置说明（L字节）
        - 时间标签（6字节）

        信息对象数目限制为 1。
        """
        encoded = text.encode('gb18030', errors='ignore')
        text_len = min(len(encoded), 255)
        encoded = encoded[:text_len]
        return bytes([text_len]) + encoded + cls._get_time_tag(dt)

    @classmethod
    def build_device_status(cls, status_byte: int, occurred_dt: Optional[datetime.datetime] = None, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建传输装置运行状态信息对象（TF=21）

        信息对象结构：
        - 状态（1字节）
        - 状态发生时间（6字节）
        - 时间标签（6字节）
        """
        return bytes([status_byte]) + cls._get_time_tag(occurred_dt) + cls._get_time_tag(dt)

    @classmethod
    def build_system_config(cls, system_type: int, system_addr: int, text: str, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建消防设施系统配置信息对象（TF=6）

        信息对象结构：
        - 系统类型标志（1字节）
        - 系统地址（1字节）
        - 系统说明长度（1字节，L=0~255）
        - 系统配置说明（L字节）
        - 时间标签（6字节）
        """
        encoded = text.encode('gb18030', errors='ignore')
        text_len = min(len(encoded), 255)
        encoded = encoded[:text_len]
        return bytes([system_type, system_addr, text_len]) + encoded + cls._get_time_tag(dt)

    @classmethod
    def build_component_config(cls, system_type: int, system_addr: int, component_type: int, component_addr: int, component_desc: str = '', dt: Optional[datetime.datetime] = None) -> bytes:
        """构建消防设施部件配置信息对象（TF=7）

        信息对象结构：
        - 系统类型标志（1字节）
        - 系统地址（1字节）
        - 部件类型（1字节）
        - 部件地址（4字节）
        - 部件说明（31字节）
        - 时间标签（6字节）
        """
        return bytes([system_type, system_addr, component_type]) + cls._int_to_bytes(component_addr, 4) + cls._str_to_bytes(component_desc, 31) + cls._get_time_tag(dt)

    @classmethod
    def build_system_time(cls, system_type: int, system_addr: int, reported_dt: Optional[datetime.datetime] = None, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建消防设施系统时间信息对象（TF=8）

        信息对象结构：
        - 系统类型标志（1字节）
        - 系统地址（1字节）
        - 建筑消防设施的系统时间（6字节）
        - 时间标签（6字节）
        """
        return bytes([system_type, system_addr]) + cls._get_time_tag(reported_dt) + cls._get_time_tag(dt)

    @classmethod
    def build_device_time(cls, device_dt: Optional[datetime.datetime] = None, dt: Optional[datetime.datetime] = None) -> bytes:
        """构建传输装置系统时间信息对象（TF=28）

        信息对象结构：
        - 用户信息传输装置的系统时间（6字节）
        - 时间标签（6字节）

        信息对象数目限制为 1。
        """
        return cls._get_time_tag(device_dt) + cls._get_time_tag(dt)

    @classmethod
    def build_adu(cls, type_flag: int, info_objects: List[bytes]) -> bytes:
        adu = bytes([type_flag, len(info_objects)])
        for obj in info_objects:
            adu += obj
        return adu

    @classmethod
    def build_adu_with_time_tag(cls, type_flag: int, info_objects: List[bytes], dt: Optional[datetime.datetime] = None) -> bytes:
        """构建带ADU末尾时间标签的应用数据单元

        用于TF=24等在所有信息对象之后追加时间标签的协议类型
        """
        adu = cls.build_adu(type_flag, info_objects)
        return adu + cls._get_time_tag(dt)


def enrich_packet_parse(parsed: Dict[str, Any]) -> Dict[str, Any]:
    adu_hex = parsed.get('adu', '')
    adu_bytes = bytes.fromhex(adu_hex) if adu_hex else b''
    adu_parsed = parse_adu(adu_bytes) if adu_bytes else None
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


def build_packet_view(packet: bytes, **extra_fields: Any) -> Dict[str, Any]:
    packet_builder = GBT26875Packet()
    parsed = packet_builder.parse_packet(packet)
    parsed['raw_hex'] = packet.hex()
    parsed['raw_length'] = len(packet)
    parsed.update(extra_fields)
    return enrich_packet_parse(parsed)


class FireAlarmSimulator:
    def __init__(self, source_addr: int = 0x000000000001, dest_addr: int = 0x000000000002):
        self.packet_builder = GBT26875Packet(source_addr=source_addr, dest_addr=dest_addr, command=CommandType.SEND_DATA)
        self.adu_builder = ADUBuilder()
        self.running = False
        self.send_thread = None
        self.stats = {'total_sent': 0, 'scenes': {}, 'start_time': None}

    def _generate_random_addr(self) -> int:
        return random.randint(1, 255)

    def _generate_random_component_addr(self) -> int:
        return random.randint(1, 0xFFFFFFFF)

    def scene_device_status(self) -> bytes:
        """传输装置运行状态（TF=21）

        模拟装置正常监视状态（bit0=1表示正常运行模式）
        状态位定义见 standard.DEVICE_STATUS_BITS
        """
        adu = self.adu_builder.build_adu(TypeFlag.UP_DEVICE_STATUS, [self.adu_builder.build_device_status(0x01)])
        return self.packet_builder.build_packet(adu)

    def scene_normal(self) -> bytes:
        adu = self.adu_builder.build_adu(TypeFlag.UP_DEVICE_STATUS, [self.adu_builder.build_device_status(0x01)])
        return self.packet_builder.build_packet(adu)

    def scene_single_fire_alarm(self, system_addr: Optional[int] = None) -> bytes:
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_component_status(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, self._generate_random_component_addr(), 0x0002, '1号楼3层走廊烟感')
        adu = self.adu_builder.build_adu(TypeFlag.UP_COMPONENT_STATUS, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_confirmed_fire_alarm(self, system_addr: Optional[int] = None) -> bytes:
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_component_status(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, 0x00010001, 0x0002, 'A区1层大厅烟感01')
        adu = self.adu_builder.build_adu(TypeFlag.UP_COMPONENT_STATUS, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_fault_alarm(self, system_addr: Optional[int] = None) -> bytes:
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_component_status(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, self._generate_random_component_addr(), 0x0004, '2号楼5层烟感故障')
        adu = self.adu_builder.build_adu(TypeFlag.UP_COMPONENT_STATUS, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_composite_alarm(self, system_addr: Optional[int] = None) -> bytes:
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_component_status(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, 0x00020001, 0x0002, 'B区2层烟感火警')
        adu = self.adu_builder.build_adu(TypeFlag.UP_COMPONENT_STATUS, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_analog_overlimit(self, system_addr: Optional[int] = None) -> bytes:
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_analog_value(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_HEAT_DETECTOR, 0x00030001, AnalogType.TEMPERATURE, 850)
        adu = self.adu_builder.build_adu(TypeFlag.UP_ANALOG_VALUE, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_operation_info(self, system_addr: Optional[int] = None) -> bytes:
        """消防设施操作信息（TF=4）

        模拟确认操作场景
        操作标志位定义见 standard.FACILITY_OPERATION_BITS
        """
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_operation_info(SystemType.FIRE_ALARM, system_addr, 0x20, 1)
        adu = self.adu_builder.build_adu(TypeFlag.UP_OPERATION_INFO, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_system_fire_alarm(self, system_addr: Optional[int] = None) -> bytes:
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_system_status(SystemType.FIRE_ALARM, system_addr, 0x0002)
        adu = self.adu_builder.build_adu(TypeFlag.UP_SYSTEM_STATUS, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_system_version(self, system_addr: Optional[int] = None) -> bytes:
        """消防设施软件版本（TF=5）

        模拟火灾报警系统版本上报
        """
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_system_version(SystemType.FIRE_ALARM, system_addr, 3, 2)
        adu = self.adu_builder.build_adu(TypeFlag.UP_SOFTWARE_VERSION, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_device_version(self) -> bytes:
        """传输装置软件版本（TF=25）"""
        obj = self.adu_builder.build_device_version(4, 0)
        adu = self.adu_builder.build_adu(TypeFlag.UP_DEVICE_VERSION, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_device_config(self) -> bytes:
        """传输装置配置情况（TF=26）

        模拟典型配置上报：传输装置配置说明
        信息对象数目限制为 1。
        """
        obj = self.adu_builder.build_device_config('JK-GH2013G型用户信息传输装置，支持TCP/UDP通信，3路RS232/RS485接口')
        adu = self.adu_builder.build_adu(TypeFlag.UP_DEVICE_CONFIG, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_device_time(self) -> bytes:
        """传输装置系统时间（TF=28）

        模拟传输装置系统时间上报
        信息对象结构：用户信息传输装置的系统时间（6字节）+ 时间标签（6字节）
        信息对象数目限制为 1。
        """
        obj = self.adu_builder.build_device_time()
        adu = self.adu_builder.build_adu(TypeFlag.UP_DEVICE_TIME, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_system_config(self, system_addr: Optional[int] = None) -> bytes:
        """消防设施系统配置（TF=6）

        模拟火灾报警系统配置上报
        """
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_system_config(SystemType.FIRE_ALARM, system_addr, '1号楼火灾报警控制器，3回路，每回路128点')
        adu = self.adu_builder.build_adu(TypeFlag.UP_SYSTEM_CONFIG, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_component_config(self, system_addr: Optional[int] = None) -> bytes:
        """消防设施部件配置（TF=7）

        模拟烟感探测器配置上报
        """
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_component_config(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, 0x00010001, '1号楼3层走廊光电烟感01')
        adu = self.adu_builder.build_adu(TypeFlag.UP_COMPONENT_CONFIG, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_system_time(self, system_addr: Optional[int] = None) -> bytes:
        """消防设施系统时间（TF=8）

        模拟火灾报警系统时间上报
        """
        system_addr = system_addr or self._generate_random_addr()
        obj = self.adu_builder.build_system_time(SystemType.FIRE_ALARM, system_addr)
        adu = self.adu_builder.build_adu(TypeFlag.UP_SYSTEM_TIME, [obj])
        return self.packet_builder.build_packet(adu)

    def scene_device_operation(self) -> bytes:
        """传输装置操作信息（TF=24）

        模拟确认操作，末尾附ADU级时间标签
        操作标志位定义见 standard.DEVICE_OPERATION_BITS
        """
        info_objects = [
            bytes([0x20, 1]) + self.adu_builder._get_time_tag(),
        ]
        adu = self.adu_builder.build_adu_with_time_tag(TypeFlag.UP_DEVICE_OPERATION, info_objects)
        return self.packet_builder.build_packet(adu)

    def scene_device_fire_status(self) -> bytes:
        adu = self.adu_builder.build_adu(TypeFlag.UP_DEVICE_STATUS, [self.adu_builder.build_device_status(0x03)])
        return self.packet_builder.build_packet(adu)

    def scene_full_fire_scenario(self) -> List[bytes]:
        packets = []
        system_addr = self._generate_random_addr()
        packets.append(self.packet_builder.build_packet(self.adu_builder.build_adu(TypeFlag.UP_SYSTEM_STATUS, [self.adu_builder.build_system_status(SystemType.FIRE_ALARM, system_addr, 0x0002)])))
        packets.append(self.packet_builder.build_packet(self.adu_builder.build_adu(TypeFlag.UP_DEVICE_STATUS, [self.adu_builder.build_device_status(0x03)])))
        packets.append(self.packet_builder.build_packet(self.adu_builder.build_adu(TypeFlag.UP_COMPONENT_STATUS, [
            self.adu_builder.build_component_status(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, 0x00010001, 0x0002, '探测器1火警'),
            self.adu_builder.build_component_status(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, 0x00010002, 0x0002, '探测器2火警'),
            self.adu_builder.build_component_status(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_PHOTO_SMOKE, 0x00010003, 0x0002, '探测器3火警'),
        ])))
        packets.append(self.packet_builder.build_packet(self.adu_builder.build_adu(TypeFlag.UP_ANALOG_VALUE, [
            self.adu_builder.build_analog_value(SystemType.FIRE_ALARM, system_addr, ComponentType.POINT_HEAT_DETECTOR, 0x00010001, AnalogType.TEMPERATURE, 920)
        ])))
        return packets

    def generate_random_scene(self) -> bytes:
        return random.choice([
            self.scene_normal,
            self.scene_single_fire_alarm,
            self.scene_confirmed_fire_alarm,
            self.scene_fault_alarm,
            self.scene_composite_alarm,
            self.scene_analog_overlimit,
            self.scene_system_fire_alarm,
            self.scene_device_fire_status,
        ])()

    def get_scene_packet(self, scene_name: str, **kwargs: Any) -> bytes:
        scene_map = {
            # 消防设施状态 (TF 1~8)
            'system_status': self.scene_system_fire_alarm,
            'component_status': self.scene_single_fire_alarm,
            'analog_value': self.scene_analog_overlimit,
            'operation_info': self.scene_operation_info,
            'system_version': self.scene_system_version,
            'system_config': self.scene_system_config,
            'component_config': self.scene_component_config,
            'system_time': self.scene_system_time,
            # 传输装置状态 (TF 21~28)
            'device_status': self.scene_device_status,
            'device_operation': self.scene_device_operation,
            'device_version': self.scene_device_version,
            'device_config': self.scene_device_config,
            'device_time': self.scene_device_time,
            # 快捷工具
            'random': self.generate_random_scene,
            # 兼容旧ID
            'single_fire': self.scene_single_fire_alarm,
            'confirmed_fire': self.scene_confirmed_fire_alarm,
            'fault': self.scene_fault_alarm,
            'composite': self.scene_composite_alarm,
            'analog': self.scene_analog_overlimit,
            'system_fire': self.scene_system_fire_alarm,
            'device_fire': self.scene_device_fire_status,
            'normal': self.scene_normal,
        }
        func = scene_map.get(scene_name, self.scene_single_fire_alarm)
        return func(**kwargs) if kwargs else func()


def get_scene_catalog() -> List[Dict[str, Any]]:
    return copy.deepcopy(SCENE_CATALOG)
