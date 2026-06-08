import copy
import random
from typing import Any, Dict, List, Optional

from . import standard as st
from .core import ADUBuilder, GBT26875Packet
from .scene_catalog import SCENE_CATALOG

CommandType = st.CommandType
TypeFlag = st.TypeFlag
SystemType = st.SystemType
ComponentType = st.ComponentType
AnalogType = st.AnalogType


class FireAlarmSimulator:
    def __init__(self, source_addr: int = 0x000000000001, dest_addr: int = 0x000000000002, addr_byte_order: str = 'little'):
        self.packet_builder = GBT26875Packet(source_addr=source_addr, dest_addr=dest_addr, command=CommandType.SEND_DATA, addr_byte_order=addr_byte_order)
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