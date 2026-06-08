#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sequence — 业务流水号全局自增管理器"""

import threading


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