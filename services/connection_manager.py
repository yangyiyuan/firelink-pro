#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ConnectionManager — 统一管理目标设备的长/短连接与数据收发"""

import logging
import socket
import threading
from typing import Any, Callable, Dict, List, Optional

from protocol.packet_view import build_packet_view
from services.utils import now_ms_str as now_ms

logger = logging.getLogger(__name__)


class ConnectionManager:
    """管理目标设备的长/短连接，统一发送接口。

    - send():       自动选择长/短连接发送
    - send_via_connection(): 仅通过长连接发送（无匹配则返回错误）
    - connect()/disconnect():  长连接生命周期管理
    - _recv_loop():  TCP 长连接接收线程，解析协议帧并 emit 事件
    - add_disconnect_callback(): 注册断开联动回调（如停止自动场景）

    锁策略：
    - _lock: 保护 _target（连接状态）
    - _send_lock: 保护 socket 写操作
    - 两锁永不同时持有
    """

    def __init__(
        self,
        socketio,
        history_manager,
        addr_byte_order_fn: Callable[[], str],
        component_addr_byteorder_fn: Callable[[], str],
    ):
        self._socketio = socketio
        self._history = history_manager
        self._addr_byte_order_fn = addr_byte_order_fn
        self._component_addr_byteorder_fn = component_addr_byteorder_fn

        self._lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._target: Optional[Dict[str, Any]] = None
        self._disconnect_callbacks: List[Callable] = []
        self._stats: Optional[Dict[str, Any]] = None

    # ── 配置注入 ──────────────────────────────────────────

    def set_simulator_stats(self, stats_dict: Dict[str, Any]) -> None:
        """注入 simulator.stats 引用（避免循环导入）"""
        self._stats = stats_dict

    def add_disconnect_callback(self, cb: Callable) -> None:
        """注册连接断开时的联动回调（如 scene_runner.stop_all）"""
        self._disconnect_callbacks.append(cb)

    # ── 状态查询 ──────────────────────────────────────────

    def is_connected(self) -> bool:
        """是否已建立长连接"""
        with self._lock:
            return self._target is not None

    def get_target_info(self) -> Optional[Dict[str, Any]]:
        """获取当前长连接信息（浅拷贝）"""
        with self._lock:
            if self._target is None:
                return None
            return dict(self._target)

    # ── 长连接生命周期 ────────────────────────────────────

    def connect(self, host: str, port: int, protocol: str) -> Dict[str, Any]:
        """建立到目标设备的长连接。成功返回 info dict，失败抛异常。"""
        with self._lock:
            if self._target is not None:
                self._close_target_socket()

            try:
                if protocol == 'tcp':
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    sock.connect((host, port))
                    # TCP keepalive: 10秒后开始探测，间隔3秒，失败3次判定断开
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    if hasattr(socket, 'TCP_KEEPIDLE'):
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
                    if hasattr(socket, 'TCP_KEEPINTVL'):
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
                    if hasattr(socket, 'TCP_KEEPCNT'):
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                    sock.settimeout(None)
                    recv_thread = threading.Thread(
                        target=self._recv_loop,
                        args=(sock, host, port, protocol),
                        daemon=True,
                    )
                    recv_thread.start()
                else:
                    sock = None
                    recv_thread = None

                self._target = {
                    'socket': sock,
                    'host': host,
                    'port': port,
                    'protocol': protocol,
                    'recv_thread': recv_thread,
                }
            except Exception:
                self._target = None
                raise

        return {'host': host, 'port': port, 'protocol': protocol}

    def disconnect(self) -> None:
        """断开长连接"""
        with self._lock:
            if self._target is not None:
                self._close_target_socket()
                self._target = None

    # ── 统一发送 ──────────────────────────────────────────

    def send(
        self,
        packet: bytes,
        host: str,
        port: int,
        protocol: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """统一发送：自动匹配长连接，否则走短连接。"""
        with self._lock:
            target = self._target

        target_port = int(port) if port is not None else 0
        use_long = (
            target is not None
            and target.get('host') == host
            and target.get('port') == target_port
        )

        if use_long:
            result = self._send_via_long(packet, target, extra_fields)
        else:
            result = self._send_via_short(packet, host, target_port, protocol, extra_fields)

        logger.debug(
            'ConnectionManager.send => use_long=%s, success=%s, length=%d',
            use_long, result.get('success'), result.get('length', 0),
        )
        return result

    def send_via_connection(
        self,
        packet: bytes,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """仅通过长连接发送。未连接时返回 error 结果。"""
        with self._lock:
            target = self._target

        if target is None:
            return {
                'success': False,
                'error': '未连接到目标服务器',
                'hex': packet.hex(),
                'length': len(packet),
                'timestamp': now_ms(),
            }

        return self._send_via_long(packet, target, extra_fields)

    # ── 连接测试 ──────────────────────────────────────────

    def test_connection(self, host: str, port: int, protocol: str) -> Dict[str, Any]:
        """测试目标连通性（不建立长连接）"""
        if not host:
            return {'success': False, 'error': '主机地址不能为空'}

        try:
            port = int(port)
        except (ValueError, TypeError):
            return {'success': False, 'error': '端口号无效'}

        try:
            if protocol == 'tcp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                try:
                    sock.connect((host, port))
                finally:
                    sock.close()
            else:
                socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
            return {'success': True, 'host': host, 'port': port, 'protocol': protocol}
        except socket.timeout:
            return {'success': False, 'error': f'连接超时: {host}:{port}'}
        except ConnectionRefusedError:
            return {'success': False, 'error': f'连接被拒绝: {host}:{port}'}
        except socket.gaierror:
            return {'success': False, 'error': f'无法解析主机: {host}'}
        except OSError as exc:
            return {'success': False, 'error': str(exc)}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    # ── 内部方法 ──────────────────────────────────────────

    def _send_via_short(
        self,
        packet: bytes,
        host: str,
        port: int,
        protocol: str,
        extra_fields: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """短连接：新建 socket → 发送 → 关闭"""
        try:
            if protocol == 'tcp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                try:
                    sock.connect((host, port))
                    sock.sendall(packet)
                finally:
                    sock.close()
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(5)
                try:
                    sock.sendto(packet, (host, port))
                finally:
                    sock.close()

            if self._stats:
                self._stats['total_sent'] += 1

            result: Dict[str, Any] = {
                'success': True,
                'length': len(packet),
                'hex': packet.hex(),
                'host': host,
                'port': port,
                'protocol': protocol,
                'timestamp': now_ms(),
            }
            if extra_fields:
                result.update(extra_fields)
            self._history.record_send(result)
            return result

        except Exception as exc:
            result = {
                'success': False,
                'error': str(exc),
                'hex': packet.hex(),
                'length': len(packet),
                'host': host,
                'port': port,
                'protocol': protocol,
                'timestamp': now_ms(),
            }
            if extra_fields:
                result.update(extra_fields)
            self._history.record_send(result)
            logger.debug('ConnectionManager._send_via_short FAIL => %s', exc)
            return result

    def _send_via_long(
        self,
        packet: bytes,
        target: Dict[str, Any],
        extra_fields: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """通过长连接发送。失败时自动关闭连接并 emit 断开事件。"""
        try:
            with self._send_lock:
                if target['protocol'] == 'tcp' and target.get('socket'):
                    target['socket'].sendall(packet)
                else:
                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    udp_sock.sendto(packet, (target['host'], target['port']))
                    udp_sock.close()

            if self._stats:
                self._stats['total_sent'] += 1

            result: Dict[str, Any] = {
                'success': True,
                'length': len(packet),
                'hex': packet.hex(),
                'host': target['host'],
                'port': target['port'],
                'protocol': target['protocol'],
                'timestamp': now_ms(),
                'via_connection': True,
            }
            if extra_fields:
                result.update(extra_fields)
            self._history.record_send(result)
            return result

        except Exception as exc:
            logger.warning('长连接发送失败 => %s', exc, exc_info=True)
            result = {
                'success': False,
                'error': str(exc),
                'hex': packet.hex(),
                'length': len(packet),
                'host': target['host'],
                'port': target['port'],
                'protocol': target['protocol'],
                'timestamp': now_ms(),
                'via_connection': True,
            }
            if extra_fields:
                result.update(extra_fields)
            self._history.record_send(result)
            # 关闭已损坏的连接
            self._close_and_clear_target()
            self._socketio.emit('target_disconnected', {})
            return result

    def _close_target_socket(self) -> None:
        """关闭 target socket（必须在 _lock 内调用）"""
        if self._target and self._target.get('socket'):
            try:
                self._target['socket'].close()
            except Exception:
                pass

    def _close_and_clear_target(self) -> None:
        """关闭并清空 target（内部获取 _lock）"""
        with self._lock:
            if self._target is not None:
                self._close_target_socket()
                self._target = None

    def _recv_loop(self, sock: socket.socket, host: str, port: int, protocol: str = 'tcp') -> None:
        """TCP 长连接接收循环：解析 GB/T 26875.3 协议帧并 emit 事件"""
        buf = b''
        while True:
            try:
                data = sock.recv(4096)
                if not data:
                    self._socketio.emit(
                        'target_data_received',
                        {
                            'type': 'disconnected',
                            'message': f'{host}:{port} 对端已关闭连接',
                            'host': host,
                            'port': port,
                            'protocol': protocol,
                            'timestamp': now_ms(),
                        },
                    )
                    break

                data_hex = data.hex()
                received_at = now_ms()
                self._history.record_receive(
                    'raw', host, port, received_at,
                    protocol=protocol, data_hex=data_hex, data_length=len(data),
                )
                self._socketio.emit(
                    'target_data_received',
                    {
                        'type': 'raw',
                        'data_hex': data_hex,
                        'data_length': len(data),
                        'host': host,
                        'port': port,
                        'protocol': protocol,
                        'timestamp': received_at,
                    },
                )

                buf += data
                # 基于帧结构的精确解析，而非盲标记扫描
                # 帧格式: @@(2B) + control_unit(25B) + ADU(adu_length B) + checksum(1B) + ##(2B)
                # 最小帧长度 = 2 + 25 + 1 + 1 + 2 = 31 字节
                MIN_FRAME_LEN = 31
                CONTROL_UNIT_START = 2
                CONTROL_UNIT_LEN = 25
                ADU_LENGTH_OFFSET = CONTROL_UNIT_START + 22  # control_unit 内 adu_length 的起始位置

                while len(buf) >= MIN_FRAME_LEN:
                    start_idx = buf.find(b'\x40\x40')
                    if start_idx == -1:
                        buf = b''
                        break
                    if start_idx > 0:
                        buf = buf[start_idx:]

                    # 从 control unit 中读取 adu_length
                    if len(buf) < CONTROL_UNIT_START + CONTROL_UNIT_LEN:
                        break  # control unit 未收齐，等更多数据

                    adu_length = int.from_bytes(
                        buf[ADU_LENGTH_OFFSET:ADU_LENGTH_OFFSET + 2],
                        byteorder='little',
                    )

                    # 计算完整帧的总长度
                    frame_len = 2 + CONTROL_UNIT_LEN + adu_length + 1 + 2

                    if len(buf) < frame_len:
                        break  # 帧未收齐，等更多数据

                    # 验证结束标记
                    if buf[frame_len - 2:frame_len] != b'\x23\x23':
                        # 结束标记不对 — 跳过当前 @@，继续扫描下一个
                        logger.warning(
                            '帧结束标记校验失败: 期望 ##, 实际 %s (adu_length=%d)',
                            buf[frame_len - 2:frame_len].hex(),
                            adu_length,
                        )
                        buf = buf[2:]
                        continue

                    frame = buf[:frame_len]
                    buf = buf[frame_len:]

                    try:
                        parsed = build_packet_view(
                            frame,
                            addr_byte_order=self._addr_byte_order_fn(),
                            component_addr_byteorder=self._component_addr_byteorder_fn(),
                        )
                        parsed_at = now_ms()
                        self._history.record_receive(
                            'packet', host, port, parsed_at,
                            protocol=protocol, parsed=parsed,
                        )
                        self._socketio.emit(
                            'target_data_received',
                            {
                                'type': 'packet',
                                'parsed': parsed,
                                'host': host,
                                'port': port,
                                'protocol': protocol,
                                'timestamp': parsed_at,
                            },
                        )
                    except Exception as exc:
                        logger.warning('协议解析失败: %s', exc)
            except OSError:
                break
            except Exception as exc:
                self._socketio.emit(
                    'target_data_received',
                    {'type': 'error', 'message': str(exc), 'timestamp': now_ms()},
                )
                break

        # 清理连接状态
        with self._lock:
            if self._target is not None:
                self._close_target_socket()
                self._target = None

        # 触发断开联动回调（如停止自动场景）
        for cb in self._disconnect_callbacks:
            try:
                cb()
            except Exception:
                pass

        self._socketio.emit('target_disconnected', {})
        logger.debug('_recv_loop 退出 => %s:%s 连接已断开', host, port)