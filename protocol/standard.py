from enum import IntEnum


# 命令字节定义 (C=控制单元, L=信息对象数)
# 0=预留, 1=控制命令, 2=发送数据, 3=确认(ACK), 4=请求, 5=应答, 6=否认(NAK)
class CommandType(IntEnum):
    RESERVED = 0
    CONTROL = 1
    SEND_DATA = 2
    ACK = 3
    REQUEST = 4
    RESPONSE = 5
    NAK = 6


COMMAND_CN = {
    0: '预留',
    1: '控制命令',
    2: '发送数据',
    3: '确认',
    4: '请求',
    5: '应答',
    6: '否认',
}


# 类型标志定义 (1字节, 标识信息对象数据类型)
# 上行(1~8): 建筑消防设施系统状态/部件状态/模拟量/操作信息/软件版本/系统配置/部件配置/系统时间
# 上行(21~28): 用户信息传输装置运行状态/操作信息/软件版本/配置情况/系统时间
# 下行(61~68): 读建筑消防设施系统状态/部件状态/模拟量/操作信息/软件版本/系统配置/部件配置/系统时间
# 下行(81~91): 读传输装置运行状态/操作信息/软件版本/配置/系统时间, 初始化, 同步时钟, 查岗
class TypeFlag(IntEnum):
    UP_SYSTEM_STATUS = 1
    UP_COMPONENT_STATUS = 2
    UP_ANALOG_VALUE = 3
    UP_OPERATION_INFO = 4
    UP_SOFTWARE_VERSION = 5
    UP_SYSTEM_CONFIG = 6
    UP_COMPONENT_CONFIG = 7
    UP_SYSTEM_TIME = 8
    UP_DEVICE_STATUS = 21
    UP_DEVICE_OPERATION = 24
    UP_DEVICE_VERSION = 25
    UP_DEVICE_CONFIG = 26
    UP_DEVICE_TIME = 28
    DOWN_READ_SYSTEM_STATUS = 61
    DOWN_READ_COMPONENT_STATUS = 62
    DOWN_READ_ANALOG = 63
    DOWN_READ_OPERATION = 64
    DOWN_READ_VERSION = 65
    DOWN_READ_SYS_CONFIG = 66
    DOWN_READ_COMP_CONFIG = 67
    DOWN_READ_SYS_TIME = 68
    DOWN_READ_DEVICE_STATUS = 81
    DOWN_READ_DEVICE_OP = 84
    DOWN_READ_DEVICE_VER = 85
    DOWN_READ_DEVICE_CFG = 86
    DOWN_READ_DEVICE_TIME = 88
    DOWN_INIT_DEVICE = 89
    DOWN_SYNC_TIME = 90
    DOWN_CHECK_DUTY = 91


TYPE_FLAG_CN = {
    0: '预留',
    1: '上传建筑消防设施系统状态',
    2: '上传建筑消防设施部件运行状态',
    3: '上传建筑消防设施部件模拟量值',
    4: '上传建筑消防设施操作信息',
    5: '上传建筑消防设施软件版本',
    6: '上传建筑消防设施系统配置情况',
    7: '上传建筑消防设施部件配置情况',
    8: '上传建筑消防设施系统时间',
    21: '上传用户信息传输装置运行状态',
    24: '上传用户信息传输装置操作信息',
    25: '上传用户信息传输装置软件版本',
    26: '上传用户信息传输装置配置情况',
    28: '上传用户信息传输装置系统时间',
    61: '读建筑消防设施系统状态',
    62: '读建筑消防设施部件运行状态',
    63: '读建筑消防设施部件模拟量值',
    64: '读建筑消防设施操作信息',
    65: '读建筑消防设施软件版本',
    66: '读建筑消防设施系统配置情况',
    67: '读建筑消防设施部件配置情况',
    68: '读建筑消防设施系统时间',
    81: '读用户信息传输装置运行状态',
    84: '读用户信息传输装置操作信息记录',
    85: '读用户信息传输装置软件版本',
    86: '读用户信息传输装置配置情况',
    88: '读用户信息传输装置系统时间',
    89: '初始化用户信息传输装置',
    90: '同步用户信息传输装置时钟',
    91: '查岗命令',
}

STANDARD_TYPE_FLAGS = tuple(sorted(TYPE_FLAG_CN))


# 系统类型定义 (1字节, 标识建筑消防设施系统类型)
# 0=通用, 1=火灾报警系统, 10~24=各类消防子系统
class SystemType(IntEnum):
    GENERAL = 0
    FIRE_ALARM = 1
    FIRE_LINKAGE = 10
    HYDRANT = 11
    SPRINKLER = 12
    GAS_EXTINGUISH = 13
    WATER_SPRAY_PUMP = 14
    WATER_SPRAY_PRESSURE = 15
    FOAM = 16
    DRY_POWDER = 17
    SMOKE_EXHAUST = 18
    FIRE_DOOR_SHUTTER = 19
    FIRE_ELEVATOR = 20
    EMERGENCY_BROADCAST = 21
    EMERGENCY_LIGHTING = 22
    FIRE_POWER = 23
    FIRE_PHONE = 24


SYSTEM_TYPE_CN = {
    0: '通用',
    1: '火灾报警系统',
    10: '消防联动控制器',
    11: '消火栓系统',
    12: '自动喷水灭火系统',
    13: '气体灭火系统',
    14: '水喷雾灭火系统(泵启动方式)',
    15: '水喷雾灭火系统(压力容器启动方式)',
    16: '泡沫灭火系统',
    17: '干粉灭火系统',
    18: '防烟排烟系统',
    19: '防火门及卷帘系统',
    20: '消防电梯',
    21: '消防应急广播',
    22: '消防应急照明和疏散指示系统',
    23: '消防电源',
    24: '消防电话',
}


# 部件类型定义 (1字节, 标识消防设施部件类型)
# 0=通用, 1=火灾报警控制器, 10~13=可燃气体探测器, 16~18=电气火灾监控
# 21=探测回路, 22=火灾显示盘, 23=手动报警按钮, 24=消火栓按钮
# 25=火灾探测器, 30~37=感温探测器, 40~44=感烟探测器, 50~51=复合探测器
# 61~69=火焰探测器, 74=气体探测器, 78=图像探测器, 79=感声探测器
# 81~88=控制/模块类, 91~99=水系统, 101~118=防火/防烟类, 121=警报装置
class ComponentType(IntEnum):
    GENERAL = 0
    FIRE_ALARM_CONTROLLER = 1
    COMBUSTIBLE_GAS_DETECTOR = 10
    POINT_COMBUSTIBLE_GAS = 11
    INDEPENDENT_COMBUSTIBLE_GAS = 12
    LINE_COMBUSTIBLE_GAS = 13
    ELECTRICAL_FIRE_MONITOR = 16
    RESIDUAL_CURRENT_DETECTOR = 17
    TEMPERATURE_DETECTOR_EF = 18
    DETECTION_LOOP = 21
    FIRE_DISPLAY_PANEL = 22
    MANUAL_ALARM_BUTTON = 23
    HYDRANT_BUTTON = 24
    FIRE_DETECTOR = 25
    HEAT_DETECTOR = 30
    POINT_HEAT_DETECTOR = 31
    POINT_HEAT_S_TYPE = 32
    POINT_HEAT_R_TYPE = 33
    LINE_HEAT_DETECTOR = 34
    LINE_HEAT_S_TYPE = 35
    LINE_HEAT_R_TYPE = 36
    FIBER_HEAT_DETECTOR = 37
    SMOKE_DETECTOR = 40
    POINT_ION_SMOKE = 41
    POINT_PHOTO_SMOKE = 42
    LINE_BEAM_SMOKE = 43
    ASPIRATION_SMOKE = 44
    COMPOUND_DETECTOR = 50
    COMPOUND_SMOKE_HEAT = 51
    UV_FLAME_DETECTOR = 61
    IR_FLAME_DETECTOR = 62
    FLAME_DETECTOR = 69
    GAS_DETECTOR_COMPONENT = 74
    IMAGE_CAMERA_DETECTOR = 78
    SOUND_DETECTOR = 79
    GAS_EXTINGUISH_CONTROLLER = 81
    FIRE_ELECTRICAL_CONTROL = 82
    GRAPHIC_DISPLAY = 83
    MODULE = 84
    INPUT_MODULE = 85
    OUTPUT_MODULE = 86
    IO_MODULE = 87
    RELAY_MODULE = 88
    FIRE_PUMP = 91
    FIRE_WATER_TANK = 92
    SPRINKLER_PUMP = 95
    WATER_FLOW_INDICATOR = 96
    SIGNAL_VALVE = 97
    ALARM_VALVE = 98
    PRESSURE_SWITCH = 99
    VALVE_DRIVE = 101
    FIRE_DOOR = 102
    FIRE_DAMPER = 103
    VENTILATION_AC = 104
    FOAM_LIQUID_PUMP = 105
    PIPE_ELECTROMAGNETIC_VALVE = 106
    SMOKE_EXHAUST_FAN = 111
    SMOKE_FIRE_DAMPER = 113
    CLOSED_AIR_SUPPLY = 114
    SMOKE_OUTLET = 115
    ELECTRIC_SMOKE_BARRIER = 116
    FIRE_SHUTTER_CONTROLLER = 117
    FIRE_DOOR_MONITOR = 118
    ALARM_DEVICE = 121


COMPONENT_TYPE_CN = {
    0: '通用',
    1: '火灾报警控制器',
    10: '可燃气体探测器',
    11: '点型可燃气体探测器',
    12: '独立式可燃气体探测器',
    13: '线型可燃气体探测器',
    16: '电气火灾监控报警器',
    17: '剩余电流式电气火灾监控探测器',
    18: '测温式电气火灾监控探测器',
    21: '探测回路',
    22: '火灾显示盘',
    23: '手动火灾报警按钮',
    24: '消火栓按钮',
    25: '火灾探测器',
    30: '感温火灾探测器',
    31: '点型感温火灾探测器',
    32: '点型感温火灾探测器(S型)',
    33: '点型感温火灾探测器(R型)',
    34: '线型感温火灾探测器',
    35: '线型感温火灾探测器(S型)',
    36: '线型感温火灾探测器(R型)',
    37: '光纤感温火灾探测器',
    40: '感烟火灾探测器',
    41: '点型离子感烟火灾探测器',
    42: '点型光电感烟火灾探测器',
    43: '线型光束感烟火灾探测器',
    44: '吸气式感烟火灾探测器',
    50: '复合式火灾探测器',
    51: '复合式感烟感温火灾探测器',
    61: '紫外火焰探测器',
    62: '红外火焰探测器',
    69: '感光火灾探测器',
    74: '气体探测器',
    78: '图像摄像方式火灾探测器',
    79: '感声火灾探测器',
    81: '气体灭火控制器',
    82: '消防电气控制装置',
    83: '消防控制室图形显示装置',
    84: '模块',
    85: '输入模块',
    86: '输出模块',
    87: '输入/输出模块',
    88: '中继模块',
    91: '消防水泵',
    92: '消防水箱',
    95: '喷淋泵',
    96: '水流指示器',
    97: '信号阀',
    98: '报警阀',
    99: '压力开关',
    101: '阀驱动装置',
    102: '防火门',
    103: '防火阀',
    104: '通风空调',
    105: '泡沫液泵',
    106: '管网电磁阀',
    111: '防烟排烟风机',
    113: '排烟防火阀',
    114: '常闭送风口',
    115: '排烟口',
    116: '电控挡烟垂壁',
    117: '防火卷帘控制器',
    118: '防火门监控器',
    121: '警报装置',
}


# 系统类型 → 可选部件类型映射（GB/T 26875.3-2011 从属关系）
# 每个系统类型下仅展示协议规定的部件类型，0=通用始终可选
SYSTEM_TYPE_TO_COMPONENTS = {
    0:  [0],  # 通用
    1:  [0, 1, 10, 11, 12, 13, 16, 17, 18, 21, 22, 23, 25,
         30, 31, 32, 33, 34, 35, 36, 37,
         40, 41, 42, 43, 44,
         50, 51,
         61, 62, 69,
         74, 78, 79,
         84, 85, 86, 87, 88,
         121],
    10: [0, 81, 82, 83, 84, 85, 86, 87, 88, 121],  # 消防联动控制器
    11: [0, 24, 91, 92],  # 消火栓系统
    12: [0, 95, 96, 97, 98, 99],  # 自动喷水灭火系统
    13: [0, 81, 101, 106],  # 气体灭火系统
    14: [0, 91, 99, 101],  # 水喷雾灭火系统(泵启动)
    15: [0, 99, 101],  # 水喷雾灭火系统(压力容器启动)
    16: [0, 91, 105],  # 泡沫灭火系统
    17: [0, 101],  # 干粉灭火系统
    18: [0, 111, 113, 114, 115, 116],  # 防烟排烟系统
    19: [0, 102, 103, 117, 118],  # 防火门及卷帘系统
    20: [0, 82],  # 消防电梯
    21: [0, 82, 121],  # 消防应急广播
    22: [0, 82],  # 消防应急照明和疏散指示系统
    23: [0, 82],  # 消防电源
    24: [0, 82],  # 消防电话
}


# 模拟量类型定义 (1字节, 标识模拟量数据类型及单位)
# 0=未用, 1=事件计数(件), 2=高度(m), 3=温度(°C), 4=压力(MPa), 5=压力(kPa)
# 6=气体浓度(%LEL), 7=时间(s), 8=电压(V), 9=电流(A), 10=流量(L/s), 11=风量(m3/min), 12=风速(m/s)
class AnalogType(IntEnum):
    UNUSED = 0
    EVENT_COUNT = 1
    HEIGHT = 2
    TEMPERATURE = 3
    PRESSURE_MPA = 4
    PRESSURE_KPA = 5
    GAS_CONCENTRATION = 6
    TIME = 7
    VOLTAGE = 8
    CURRENT = 9
    FLOW_RATE = 10
    AIR_VOLUME = 11
    WIND_SPEED = 12


ANALOG_TYPE_META = {
    0: {'name': '未用', 'unit': '', 'scale': 1},
    1: {'name': '事件计数', 'unit': '件', 'scale': 1},
    2: {'name': '高度', 'unit': 'm', 'scale': 0.01},
    3: {'name': '温度', 'unit': '°C', 'scale': 0.1},
    4: {'name': '压力', 'unit': 'MPa', 'scale': 0.1},
    5: {'name': '压力', 'unit': 'kPa', 'scale': 0.1},
    6: {'name': '气体浓度', 'unit': '%LEL', 'scale': 0.1},
    7: {'name': '时间', 'unit': 's', 'scale': 1},
    8: {'name': '电压', 'unit': 'V', 'scale': 0.1},
    9: {'name': '电流', 'unit': 'A', 'scale': 0.1},
    10: {'name': '流量', 'unit': 'L/s', 'scale': 0.1},
    11: {'name': '风量', 'unit': 'm3/min', 'scale': 0.1},
    12: {'name': '风速', 'unit': 'm/s', 'scale': 1},
}


# 建筑消防设施系统状态（2字节），TypeFlag=1
# 低字节: bit0=运行模式, bit1=火警, bit2=故障, bit3=屏蔽, bit4=监管, bit5=启动, bit6=反馈, bit7=延时
# 高字节: bit8=主电故障, bit9=备电故障, bit10=总线故障, bit11=手动/自动, bit12=配置改变, bit13=复位, bit14~15=预留
SYSTEM_STATUS_BITS = [
    {'label': '运行模式', 'on': '测试运行', 'off': '正常运行'},
    {'label': '火警', 'on': '火警', 'off': '无火警'},
    {'label': '故障', 'on': '故障', 'off': '无故障'},
    {'label': '屏蔽', 'on': '屏蔽', 'off': '未屏蔽'},
    {'label': '监管', 'on': '监管', 'off': '无监管'},
    {'label': '启动', 'on': '启动', 'off': '停止'},
    {'label': '反馈', 'on': '反馈', 'off': '无反馈'},
    {'label': '延时', 'on': '延时', 'off': '无延时'},
    {'label': '主电故障', 'on': '主电故障', 'off': '主电正常'},
    {'label': '备电故障', 'on': '备电故障', 'off': '备电正常'},
    {'label': '总线故障', 'on': '总线故障', 'off': '总线正常'},
    {'label': '手动/自动', 'on': '手动', 'off': '自动'},
    {'label': '配置改变', 'on': '配置改变', 'off': '无配置改变'},
    {'label': '复位', 'on': '复位', 'off': '正常'},
    {'label': '预留位14', 'on': 'bit14=1', 'off': 'bit14=0'},
    {'label': '预留位15', 'on': 'bit15=1', 'off': 'bit15=0'},
]

# 建筑消防设施部件状态（2字节），TypeFlag=2
# 低字节: bit0=运行模式, bit1=火警, bit2=故障, bit3=屏蔽, bit4=监管, bit5=启动, bit6=反馈, bit7=延时
# 高字节: bit8=电源故障, bit9~15=预留
COMPONENT_STATUS_BITS = [
    {'label': '运行模式', 'on': '测试运行', 'off': '正常运行'},
    {'label': '火警', 'on': '火警', 'off': '无火警'},
    {'label': '故障', 'on': '故障', 'off': '无故障'},
    {'label': '屏蔽', 'on': '屏蔽', 'off': '未屏蔽'},
    {'label': '监管', 'on': '监管', 'off': '无监管'},
    {'label': '启动', 'on': '启动', 'off': '停止'},
    {'label': '反馈', 'on': '反馈', 'off': '无反馈'},
    {'label': '延时', 'on': '延时', 'off': '无延时'},
    {'label': '电源故障', 'on': '电源故障', 'off': '电源正常'},
    {'label': '预留位9', 'on': 'bit9=1', 'off': 'bit9=0'},
    {'label': '预留位10', 'on': 'bit10=1', 'off': 'bit10=0'},
    {'label': '预留位11', 'on': 'bit11=1', 'off': 'bit11=0'},
    {'label': '预留位12', 'on': 'bit12=1', 'off': 'bit12=0'},
    {'label': '预留位13', 'on': 'bit13=1', 'off': 'bit13=0'},
    {'label': '预留位14', 'on': 'bit14=1', 'off': 'bit14=0'},
    {'label': '预留位15', 'on': 'bit15=1', 'off': 'bit15=0'},
]

# 用户信息传输装置运行状态（1字节），TypeFlag=21
# bit0=运行模式(反向: 0=测试,1=正常), bit1=火警, bit2=故障, bit3=主电故障, bit4=备电故障, bit5=通信信道故障, bit6=线路故障, bit7=预留
DEVICE_STATUS_BITS = [
    {'label': '运行模式', 'on': '正常', 'off': '测试状态'},
    {'label': '火警', 'on': '火警', 'off': '无火警'},
    {'label': '故障', 'on': '故障', 'off': '无故障'},
    {'label': '主电故障', 'on': '主电故障', 'off': '主电正常'},
    {'label': '备电故障', 'on': '备电故障', 'off': '备电正常'},
    {'label': '通信信道故障', 'on': '与监控中心通信信道故障', 'off': '通信信道正常'},
    {'label': '监测连接线路故障', 'on': '监测连接线路故障', 'off': '监测连接线路正常'},
    {'label': '保留位7', 'on': 'bit7=1', 'off': '预留'},
]

# 建筑消防设施操作标志（1字节），TypeFlag=4
# bit0=复位, bit1=消音, bit2=手动报警, bit3=警情消除, bit4=自检, bit5=确认, bit6=测试, bit7=预留
FACILITY_OPERATION_BITS = [
    {'label': '复位', 'on': '复位', 'off': '无'},
    {'label': '消音', 'on': '消音', 'off': '无'},
    {'label': '手动报警', 'on': '手动报警', 'off': '无'},
    {'label': '警情消除', 'on': '警情消除', 'off': '无'},
    {'label': '自检', 'on': '自检', 'off': '无'},
    {'label': '确认', 'on': '确认', 'off': '无'},
    {'label': '测试', 'on': '测试', 'off': '无'},
    {'label': '预留位7', 'on': 'bit7=1', 'off': '预留'},
]

# 用户信息传输装置操作标志（1字节），TypeFlag=24
# bit0=复位, bit1=消音, bit2=手动报警, bit3=警情消除, bit4=自检, bit5=查岗应答, bit6=测试, bit7=预留
DEVICE_OPERATION_BITS = [
    {'label': '复位', 'on': '复位', 'off': '无'},
    {'label': '消音', 'on': '消音', 'off': '无'},
    {'label': '手动报警', 'on': '手动报警', 'off': '无'},
    {'label': '警情消除', 'on': '警情消除', 'off': '无'},
    {'label': '自检', 'on': '自检', 'off': '无'},
    {'label': '查岗应答', 'on': '查岗应答', 'off': '无'},
    {'label': '测试', 'on': '测试', 'off': '无'},
    {'label': '预留位7', 'on': 'bit7=1', 'off': '预留'},
]
