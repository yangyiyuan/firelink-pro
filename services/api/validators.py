#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路由输入验证工具"""

import re


def validate_hex_string(hex_str: str, max_len: int = 10000) -> tuple:
    """验证hex字符串格式。

    Returns
    -------
    (bool, str)
        (是否合法, 错误消息)。合法时错误消息为空字符串。
    """
    if not hex_str or not hex_str.strip():
        return False, 'HEX数据不能为空'
    cleaned = hex_str.replace(' ', '')
    if len(cleaned) > max_len:
        return False, f'HEX数据长度不能超过{max_len}字符'
    if not re.match(r'^[0-9a-fA-F]+$', cleaned):
        return False, 'HEX数据仅允许包含0-9a-fA-F字符和空格'
    return True, ''


def validate_port(port_value) -> tuple:
    """验证端口范围。

    Returns
    -------
    (bool, str)
        (是否合法, 错误消息)。
    """
    try:
        port = int(port_value)
        if 1 <= port <= 65535:
            return True, ''
        return False, '端口范围应为1-65535'
    except (TypeError, ValueError):
        return False, '端口应为整数'


def validate_host(host: str) -> tuple:
    """验证host格式（IP或域名）。

    Returns
    -------
    (bool, str)
        (是否合法, 错误消息)。
    """
    if not host or not host.strip():
        return False, '主机地址不能为空'
    if re.match(r'^[a-zA-Z0-9._:-]+$', host.strip()):
        return True, ''
    return False, '主机地址格式不合法'


def validate_scene_structure(scene: dict) -> tuple:
    """验证场景数据结构的基本完整性。

    Returns
    -------
    (bool, str)
        (是否合法, 错误消息)。
    """
    if not scene:
        return False, '场景数据不能为空'
    if not isinstance(scene, dict):
        return False, '场景数据应为JSON对象'
    # steps 存在时须为列表
    steps = scene.get('steps')
    if steps is not None and not isinstance(steps, list):
        return False, 'steps 应为数组'
    return True, ''