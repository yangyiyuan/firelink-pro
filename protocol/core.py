import datetime
from typing import Any, Dict, List, Optional

from . import standard as st
from .scene_catalog import SCENE_CATALOG, SUPPORTED_TYPE_FLAGS
from .sequence import SequenceManager, sequence_manager
from .shared import decode_time_tag

CommandType = st.CommandType
TypeFlag = st.TypeFlag
SystemType = st.SystemType
ComponentType = st.ComponentType
AnalogType = st.AnalogType


class GBT26875Packet:
    START_FLAG = b'\x40\x40'
    END_FLAG = b'\x23\x23'
    MAX_ADU_LENGTH = 1024

    def __init__(self, source_addr: int = 0x000000000001, dest_addr: int = 0x000000000002, command: CommandType = CommandType.SEND_DATA, version_major: int = 1, version_minor: int = 0, addr_byte_order: str = 'little'):
        self.source_addr = source_addr
        self.dest_addr = dest_addr
        self.command = command
        self.version_major = version_major
        self.version_minor = version_minor
        self.addr_byte_order = addr_byte_order

    def _int_to_bytes(self, value: int, length: int, signed: bool = False, byteorder_override: str = '') -> bytes:
        order = byteorder_override or 'little'
        return value.to_bytes(length, byteorder=order, signed=signed)

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
            + self._int_to_bytes(self.source_addr, 6, byteorder_override=self.addr_byte_order)
            + self._int_to_bytes(self.dest_addr, 6, byteorder_override=self.addr_byte_order)
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
            'source_addr': f"0x{int.from_bytes(control_unit[10:16], byteorder=self.addr_byte_order):012x}",
            'dest_addr': f"0x{int.from_bytes(control_unit[16:22], byteorder=self.addr_byte_order):012x}",
            'adu_length': adu_length,
            'command': control_unit[24],
            'adu': adu.hex(),
            'checksum': f"0x{checksum:02x}",
        }


class ADUBuilder:
    @staticmethod
    def _int_to_bytes(value: int, length: int, signed: bool = False, byteorder: str = 'little') -> bytes:
        return value.to_bytes(length, byteorder=byteorder, signed=signed)

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
    def build_component_status(cls, system_type: int, system_addr: int, component_type: int, component_addr: int, component_status: int, component_desc: str = '', dt: Optional[datetime.datetime] = None, component_addr_byteorder: str = 'little') -> bytes:
        return bytes([system_type, system_addr, component_type]) + cls._int_to_bytes(component_addr, 4, byteorder=component_addr_byteorder) + cls._int_to_bytes(component_status, 2) + cls._str_to_bytes(component_desc, 31) + cls._get_time_tag(dt)

    @classmethod
    def build_analog_value(cls, system_type: int, system_addr: int, component_type: int, component_addr: int, analog_type: int, analog_value: int, dt: Optional[datetime.datetime] = None, component_addr_byteorder: str = 'little') -> bytes:
        return bytes([system_type, system_addr, component_type]) + cls._int_to_bytes(component_addr, 4, byteorder=component_addr_byteorder) + bytes([analog_type]) + cls._int_to_bytes(analog_value, 2, signed=True) + cls._get_time_tag(dt)

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
    def build_component_config(cls, system_type: int, system_addr: int, component_type: int, component_addr: int, component_desc: str = '', dt: Optional[datetime.datetime] = None, component_addr_byteorder: str = 'little') -> bytes:
        """构建消防设施部件配置信息对象（TF=7）

        信息对象结构：
        - 系统类型标志（1字节）
        - 系统地址（1字节）
        - 部件类型（1字节）
        - 部件地址（4字节）
        - 部件说明（31字节）
        - 时间标签（6字节）
        """
        return bytes([system_type, system_addr, component_type]) + cls._int_to_bytes(component_addr, 4, byteorder=component_addr_byteorder) + cls._str_to_bytes(component_desc, 31) + cls._get_time_tag(dt)

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


# 从新模块重新导入（向后兼容）
from .packet_view import parse_adu, enrich_packet_parse, build_packet_view  # noqa: E402
from .simulator import FireAlarmSimulator, get_scene_catalog  # noqa: E402