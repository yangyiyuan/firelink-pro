#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scene_catalog — 场景目录与支持的类型标志"""

from .adu import PARSER_REGISTRY

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