#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBT 26875.3-2011 消防报警数据模拟器 - Web可视化版本
后端服务 (Flask)
"""

import datetime
import json
import os
import socket
import threading
import time
import traceback
from collections import deque
from typing import Any
from urllib.parse import quote

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

try:
    from fire_alarm_simulator.protocol.core import (
        SCENE_CATALOG,
        FireAlarmSimulator,
        build_packet_view,
        sequence_manager,
    )
    from fire_alarm_simulator.protocol.shared import (
        AVAILABLE_PROFILES,
        get_addr_byte_order_for_profile,
    )
    from fire_alarm_simulator.services.auto_send_scene import (
        build_scene_plan,
        delete_template as delete_auto_scene_template,
        get_auto_send_meta,
        list_templates as list_auto_send_templates,
        rebuild_step_packet,
        save_template as save_auto_scene_template,
    )
    from fire_alarm_simulator.services.signal_instance import (
        create_instance,
        delete_instance,
        get_instance,
        list_instances as list_signal_instances,
        preview_instance,
        resolve_instance_packet,
        touch_instance,
        update_instance,
    )
    from fire_alarm_simulator.services.common import now_ms_str as now_ms
    from fire_alarm_simulator.services.network_config import NetworkConfigStore
except ModuleNotFoundError:
    from protocol.core import (
        SCENE_CATALOG,
        FireAlarmSimulator,
        build_packet_view,
        sequence_manager,
    )
    from protocol.shared import (
        AVAILABLE_PROFILES,
        get_addr_byte_order_for_profile,
    )
    from services.auto_send_scene import (
        build_scene_plan,
        delete_template as delete_auto_scene_template,
        get_auto_send_meta,
        list_templates as list_auto_send_templates,
        rebuild_step_packet,
        save_template as save_auto_scene_template,
    )
    from services.signal_instance import (
        create_instance,
        delete_instance,
        get_instance,
        list_instances as list_signal_instances,
        preview_instance,
        resolve_instance_packet,
        touch_instance,
        update_instance,
    )
    from services.common import now_ms_str as now_ms
    from services.network_config import NetworkConfigStore


def is_reloader_process() -> bool:
    return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'


def is_main_process() -> bool:
    return not os.environ.get('WERKZEUG_RUN_MAIN')


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'fire-alarm-simulator-secret-key'
socketio = SocketIO(app, cors_allowed_origins=os.environ.get('CORS_ORIGINS', '*'), async_mode='threading')

template_last_modified = {}


def watch_templates() -> None:
    import glob

    template_dir = os.path.join(app.root_path, 'templates')
    while True:
        try:
            for filepath in glob.glob(os.path.join(template_dir, '*.html')):
                mtime = os.path.getmtime(filepath)
                filename = os.path.basename(filepath)
                if filename in template_last_modified:
                    if mtime > template_last_modified[filename]:
                        template_last_modified[filename] = mtime
                        socketio.emit('template_changed', {'file': filename})
                else:
                    template_last_modified[filename] = mtime
            time.sleep(1)
        except Exception:
            pass


if is_reloader_process():
    watcher_thread = threading.Thread(target=watch_templates, daemon=True)
    watcher_thread.start()


simulator = FireAlarmSimulator()
send_history = deque(maxlen=1000)
send_history_lock = threading.Lock()
send_lock = threading.Lock()
HISTORY_DIR = os.path.join(os.path.dirname(__file__), 'data', 'history')
os.makedirs(HISTORY_DIR, exist_ok=True)


def push_history(entry: dict[str, Any]) -> None:
    with send_history_lock:
        send_history.append(entry)


def record_send_history(result: dict[str, Any]) -> None:
    entry = dict(result)
    entry['direction'] = 'send'
    entry['history_type'] = 'send'
    push_history(entry)


def record_receive_history(kind: str, host: str, port: int, timestamp: str, protocol: str = 'tcp', **payload: Any) -> None:
    entry = {
        'direction': 'recv',
        'history_type': kind,
        'host': host,
        'port': port,
        'protocol': protocol,
        'timestamp': timestamp,
    }
    entry.update(payload)
    push_history(entry)


network_config_store = NetworkConfigStore()
current_profile_key = ''


def _current_addr_byte_order() -> str:
    return get_addr_byte_order_for_profile(current_profile_key)
target_connection = None
target_lock = threading.Lock()
auto_scene_runs = {}
auto_scene_lock = threading.Lock()


def new_run_id() -> str:
    return f'run_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}_{int(time.time() * 1000) % 1000:03d}'


def send_packet_network(packet: bytes, host: str, port: int, protocol: str, extra_fields: dict[str, Any] | None = None) -> dict[str, Any]:
    print(f'[DEBUG] send_packet_network => host={host}, port={port}, protocol={protocol}, packet_len={len(packet)}')
    try:
        if protocol == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, int(port)))
            sock.sendall(packet)
            sock.close()
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(packet, (host, int(port)))
            sock.close()

        simulator.stats['total_sent'] += 1
        result = {
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
        record_send_history(result)
        print(f'[DEBUG] send_packet_network OK => length={len(packet)}, hex_preview={packet.hex()[:40]}...')
        return result
    except Exception as exc:
        error_result = {
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
            error_result.update(extra_fields)
        record_send_history(error_result)
        print(f'[DEBUG] send_packet_network FAIL => error={exc}')
        return error_result


def _close_target_connection() -> None:
    global target_connection
    if target_connection is not None:
        try:
            if target_connection.get('socket'):
                target_connection['socket'].close()
        except Exception:
            pass


def _recv_loop(sock: socket.socket, host: str, port: int, protocol: str = 'tcp') -> None:
    buf = b''
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                socketio.emit(
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
            record_receive_history('raw', host, port, received_at, data_hex=data_hex, data_length=len(data))
            socketio.emit(
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
            while len(buf) >= 4:
                start_idx = buf.find(b'\x40\x40')
                if start_idx == -1:
                    buf = b''
                    break
                if start_idx > 0:
                    buf = buf[start_idx:]

                end_idx = buf.find(b'\x23\x23', 2)
                if end_idx == -1:
                    break

                packet = buf[: end_idx + 2]
                buf = buf[end_idx + 2 :]

                try:
                    parsed = build_packet_view(packet, addr_byte_order=_current_addr_byte_order())
                    parsed_at = now_ms()
                    record_receive_history('packet', host, port, parsed_at, parsed=parsed)
                    socketio.emit(
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
                    print(f'[接收] 协议解析失败: {exc}')
        except OSError:
            break
        except Exception as exc:
            socketio.emit('target_data_received', {'type': 'error', 'message': str(exc), 'timestamp': now_ms()})
            break

    global target_connection
    with target_lock:
        if target_connection is not None:
            _close_target_connection()
            target_connection = None

    # 连接断开时联动停止正在运行的自动场景
    stop_events = []
    with auto_scene_lock:
        for run_id, run_info in list(auto_scene_runs.items()):
            if run_info.get('stop_event') is not None:
                stop_events.append(run_info['stop_event'])
    for ev in stop_events:
        ev.set()
    print('[DEBUG] 连接断开，已联动停止自动场景')

    socketio.emit('target_disconnected', {})
    print(f'[DEBUG] _recv_loop 退出 => {host}:{port} 连接已断开')


@socketio.on('connect')
def handle_connect() -> None:
    emit('status', {'message': '已连接到模拟器服务器', 'connected': True})


@socketio.on('disconnect')
def handle_disconnect() -> None:
    pass


@socketio.on('generate_packet')
def handle_generate_packet(data: dict[str, Any]) -> None:
    scene = data.get('scene', 'single_fire')
    try:
        packet = simulator.get_scene_packet(scene)
        emit('packet_generated', build_packet_view(packet, addr_byte_order=_current_addr_byte_order(), scene=scene, timestamp=now_ms()))
    except Exception as exc:
        emit('error', {'message': str(exc)})


@socketio.on('send_packet')
def handle_send_packet(data: dict[str, Any]) -> None:
    scene = data.get('scene', 'single_fire')
    host = data.get('host', '127.0.0.1')
    port = data.get('port', 8080)
    protocol = data.get('protocol', 'tcp')
    try:
        if scene == 'full_fire':
            packets = simulator.scene_full_fire_scenario()
            results = []
            for index, packet in enumerate(packets, start=1):
                result = send_packet_network(packet, host, port, protocol, {'scene': scene})
                result['packet_index'] = index
                result['total_packets'] = len(packets)
                results.append(result)
                time.sleep(0.1)
            emit('send_result', {'success': True, 'results': results, 'scene': scene})
        else:
            packet = simulator.get_scene_packet(scene)
            emit('send_result', send_packet_network(packet, host, port, protocol, {'scene': scene}))
    except Exception as exc:
        emit('error', {'message': str(exc)})


@socketio.on('start_auto_send')
def handle_start_auto_send(data: dict[str, Any]) -> None:
    scene = data.get('scene', 'random')
    interval = data.get('interval', 5)
    host = data.get('host', '127.0.0.1')
    port = data.get('port', 8080)
    protocol = data.get('protocol', 'tcp')

    if simulator.running:
        emit('error', {'message': '自动发送已在运行中'})
        return

    simulator.running = True
    simulator.stats['start_time'] = now_ms()

    def auto_send() -> None:
        while simulator.running:
            try:
                packet = simulator.get_scene_packet(scene)
                result = send_packet_network(packet, host, port, protocol, {'scene': scene, 'mode': 'auto'})
                socketio.emit('auto_send_result', result)
                time.sleep(interval)
            except Exception as exc:
                socketio.emit('error', {'message': str(exc)})
                break

    simulator.send_thread = threading.Thread(target=auto_send, daemon=True)
    simulator.send_thread.start()
    emit('auto_send_started', {'scene': scene, 'interval': interval})


@socketio.on('stop_auto_send')
def handle_stop_auto_send() -> None:
    simulator.running = False
    if simulator.send_thread:
        simulator.send_thread.join(timeout=2)
    emit('auto_send_stopped', {'stats': simulator.stats})


@socketio.on('start_auto_scene')
def handle_start_auto_scene(data: dict[str, Any]) -> None:
    scene = data.get('scene') or {}
    network = data.get('network') or {}
    _start_single_scene(scene, network)


@socketio.on('start_auto_scenes')
def handle_start_auto_scenes(data: dict[str, Any]) -> None:
    scenes = data.get('scenes') or []
    network = data.get('network') or {}
    if not scenes:
        emit('auto_scene_error', {'message': '未选择任何场景'})
        return
    for scene in scenes:
        _start_single_scene(scene, network)


def _start_single_scene(scene: dict, network: dict) -> None:
    host = network.get('host', '127.0.0.1')
    port = network.get('port', 8080)
    protocol = network.get('protocol', 'tcp')
    template_id = scene.get('id', '')
    print(f'[DEBUG] start_auto_scene => scene_name={scene.get("name")}, network={host}:{port}/{protocol}, steps={len(scene.get("steps", []))}')

    with auto_scene_lock:
        for rid, rinfo in auto_scene_runs.items():
            if rinfo.get('template_id') == template_id:
                emit('auto_scene_error', {'message': f'场景 {scene.get("name", "")} 已在运行中'})
                return

    try:
        plan = build_scene_plan(scene, addr_byte_order=_current_addr_byte_order())
    except Exception as exc:
        emit('auto_scene_error', {'message': str(exc)})
        return

    stop_event = threading.Event()
    run_id = new_run_id()
    with auto_scene_lock:
        auto_scene_runs[run_id] = {
            'thread': None,
            'stop_event': stop_event,
            'run_id': run_id,
            'scene_name': plan['scene_name'],
            'template_id': template_id,
        }

    def run_auto_scene() -> None:
        global target_connection
        cycle_index = 0
        try:
            while not stop_event.is_set():
                cycle_index += 1
                print(f'[DEBUG] run_auto_scene => cycle={cycle_index}, steps={len(plan["steps"])}, stop={stop_event.is_set()}')
                for step_index, step in enumerate(plan['steps'], start=1):
                    if stop_event.is_set():
                        break

                    fresh = rebuild_step_packet(step, addr_byte_order=_current_addr_byte_order())
                    step['packet'] = fresh['packet']
                    step['packet_hex'] = fresh['packet_hex']
                    step['packet_view'] = fresh['packet_view']

                    with target_lock:
                        conn = target_connection

                    target_port = int(port) if port is not None else 0
                    use_connection = (
                        conn is not None
                        and conn.get('host') == host
                        and conn.get('port') == target_port
                    )
                    print(f'[DEBUG] run_auto_scene step={step_index} => use_connection={use_connection}, conn_host={conn.get("host") if conn else None}, conn_port={conn.get("port") if conn else None}, target_host={host}, target_port={target_port}')

                    if use_connection:
                        try:
                            with send_lock:
                                if conn['protocol'] == 'tcp' and conn.get('socket'):
                                    conn['socket'].sendall(step['packet'])
                                else:
                                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                    udp_sock.sendto(step['packet'], (conn['host'], conn['port']))
                                    udp_sock.close()
                            simulator.stats['total_sent'] += 1
                            result = {
                                'success': True,
                                'length': len(step['packet']),
                                'hex': step['packet'].hex(),
                                'host': conn['host'],
                                'port': conn['port'],
                                'protocol': conn['protocol'],
                                'timestamp': now_ms(),
                                'scene': plan['scene_id'] or plan['scene_name'],
                                'scene_name': plan['scene_name'],
                                'mode': 'auto_scene',
                                'run_id': run_id,
                                'step_id': step['id'],
                                'step_name': step['name'],
                                'step_index': step_index,
                                'cycle_index': cycle_index,
                                'template_id': template_id,
                                'via_connection': True,
                            }
                            record_send_history(result)
                        except Exception as exc:
                            print(f'[DEBUG] 长连接发送失败 => {exc}')
                            traceback.print_exc()
                            result = {
                                'success': False,
                                'error': str(exc),
                                'hex': step['packet'].hex(),
                                'length': len(step['packet']),
                                'host': host,
                                'port': int(port),
                                'protocol': protocol,
                                'timestamp': now_ms(),
                                'scene': plan['scene_id'] or plan['scene_name'],
                                'scene_name': plan['scene_name'],
                                'mode': 'auto_scene',
                                'run_id': run_id,
                                'step_id': step['id'],
                                'step_name': step['name'],
                                'step_index': step_index,
                                'cycle_index': cycle_index,
                                'template_id': template_id,
                                'via_connection': True,
                            }
                            record_send_history(result)
                            with target_lock:
                                if target_connection is not None:
                                    _close_target_connection()
                                    target_connection = None
                            socketio.emit('target_disconnected', {})
                    else:
                        result = send_packet_network(
                            step['packet'],
                            host,
                            int(port),
                            protocol,
                            {
                                'scene': plan['scene_id'] or plan['scene_name'],
                                'scene_name': plan['scene_name'],
                                'mode': 'auto_scene',
                                'run_id': run_id,
                                'step_id': step['id'],
                                'step_name': step['name'],
                                'step_index': step_index,
                                'cycle_index': cycle_index,
                                'template_id': template_id,
                            },
                        )
                    packet_view = dict(step['packet_view'])
                    packet_view.update(
                        {
                            'run_id': run_id,
                            'step_id': step['id'],
                            'step_name': step['name'],
                            'step_index': step_index,
                            'cycle_index': cycle_index,
                        }
                    )
                    socketio.emit(
                        'auto_scene_step_result',
                        {
                            **result,
                            'packet_view': packet_view,
                            'step_id': step['id'],
                            'step_name': step['name'],
                            'step_index': step_index,
                            'cycle_index': cycle_index,
                            'scene_name': plan['scene_name'],
                            'run_id': run_id,
                            'template_id': template_id,
                        },
                    )
                    print(f'[DEBUG] auto_scene_step_result => step={step_index}/{len(plan["steps"])}, cycle={cycle_index}, success={result.get("success")}, hex_len={result.get("length")}, via={"长连接" if result.get("via_connection") else "短连接"}')
                    if step['delay_after_sec'] > 0:
                        if stop_event.wait(step['delay_after_sec']):
                            break

                socketio.emit(
                    'auto_scene_completed',
                    {
                        'run_id': run_id,
                        'scene_name': plan['scene_name'],
                        'cycle_index': cycle_index,
                        'loop': plan['loop'],
                        'template_id': template_id,
                    },
                )
                if stop_event.is_set() or not plan['loop']:
                    break
        except Exception as exc:
            print(f'[DEBUG] run_auto_scene CRASHED => {exc}')
            traceback.print_exc()
            socketio.emit('auto_scene_error', {'message': str(exc), 'run_id': run_id, 'template_id': template_id})
        finally:
            with auto_scene_lock:
                auto_scene_runs.pop(run_id, None)
            socketio.emit('auto_scene_stopped', {'run_id': run_id, 'scene_name': plan['scene_name'], 'template_id': template_id})

    worker = threading.Thread(target=run_auto_scene, daemon=True)
    with auto_scene_lock:
        auto_scene_runs[run_id]['thread'] = worker
    worker.start()
    emit(
        'auto_scene_started',
        {
            'run_id': run_id,
            'scene_name': plan['scene_name'],
            'step_count': len(plan['steps']),
            'loop': plan['loop'],
            'template_id': template_id,
        },
    )
    print(f'[DEBUG] auto_scene_started => run_id={run_id}, scene_name={plan["scene_name"]}, steps={len(plan["steps"])}, loop={plan["loop"]}')


@socketio.on('stop_auto_scene')
def handle_stop_auto_scene(data: dict | None = None) -> None:
    template_id = None
    if data and isinstance(data, dict):
        template_id = data.get('template_id')

    with auto_scene_lock:
        if template_id:
            targets = {rid: info for rid, info in list(auto_scene_runs.items()) if info.get('template_id') == template_id}
        else:
            targets = dict(auto_scene_runs)

        if not targets:
            emit('auto_scene_stopped', {'run_id': None, 'scene_name': '', 'template_id': template_id})
            return

        threads = []
        for rid, info in targets.items():
            threads.append((rid, info.get('thread'), info.get('scene_name'), info.get('template_id'), info.get('stop_event')))

    for rid, thread, scene_name, tid, stop_ev in threads:
        if stop_ev is not None:
            stop_ev.set()

    for rid, thread, scene_name, tid, _ in threads:
        if thread:
            thread.join(timeout=2)
        emit('auto_scene_stopped', {'run_id': rid, 'scene_name': scene_name or '', 'template_id': tid or ''})


@socketio.on('connect_target')
def handle_connect_target(data: dict[str, Any]) -> None:
    global target_connection
    host = data.get('host', '127.0.0.1')
    port = int(data.get('port', 8080))
    protocol = data.get('protocol', 'tcp')
    print(f'[DEBUG] connect_target => host={host}, port={port}, protocol={protocol}')

    try:
        with target_lock:
            if target_connection is not None:
                _close_target_connection()

            if protocol == 'tcp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((host, port))
                # TCP keepalive: 10秒后开始探测，每次间隔3秒，失败3次判定断开
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                sock.settimeout(None)
                recv_thread = threading.Thread(target=_recv_loop, args=(sock, host, port, protocol), daemon=True)
                recv_thread.start()
            else:
                sock = None
                recv_thread = None

            target_connection = {
                'socket': sock,
                'host': host,
                'port': port,
                'protocol': protocol,
                'recv_thread': recv_thread,
            }

        emit('target_connected', {'host': host, 'port': port, 'protocol': protocol})
        print(f'[DEBUG] target_connected => host={host}, port={port}, protocol={protocol}')
    except Exception as exc:
        with target_lock:
            target_connection = None
        emit('target_connection_error', {'error': str(exc)})
        print(f'[DEBUG] target_connection_error => {exc}')


@socketio.on('disconnect_target')
def handle_disconnect_target() -> None:
    global target_connection
    with target_lock:
        if target_connection is not None:
            _close_target_connection()
            target_connection = None
    emit('target_disconnected', {})


@socketio.on('send_via_connection')
def handle_send_via_connection(data: dict[str, Any]) -> None:
    global target_connection
    scene = data.get('scene', 'single_fire')
    with target_lock:
        conn = target_connection

    if conn is None:
        emit('error', {'message': '未连接到目标服务器'})
        return

    try:
        if scene == 'full_fire':
            packets = simulator.scene_full_fire_scenario()
            results = []
            for index, packet in enumerate(packets, start=1):
                with send_lock:
                    if conn['protocol'] == 'tcp' and conn['socket']:
                        conn['socket'].sendall(packet)
                    else:
                        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        udp_sock.sendto(packet, (conn['host'], conn['port']))
                        udp_sock.close()
                simulator.stats['total_sent'] += 1
                result = {
                    'success': True,
                    'length': len(packet),
                    'hex': packet.hex(),
                    'host': conn['host'],
                    'port': conn['port'],
                    'protocol': conn['protocol'],
                    'timestamp': now_ms(),
                    'packet_index': index,
                    'total_packets': len(packets),
                    'scene': scene,
                }
                record_send_history(result)
                results.append(result)
                time.sleep(0.1)
            emit('send_result', {'success': True, 'results': results, 'scene': scene})
        else:
            packet = simulator.get_scene_packet(scene)
            with send_lock:
                if conn['protocol'] == 'tcp' and conn['socket']:
                    conn['socket'].sendall(packet)
                else:
                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    udp_sock.sendto(packet, (conn['host'], conn['port']))
                    udp_sock.close()
            simulator.stats['total_sent'] += 1
            result = {
                'success': True,
                'length': len(packet),
                'hex': packet.hex(),
                'host': conn['host'],
                'port': conn['port'],
                'protocol': conn['protocol'],
                'timestamp': now_ms(),
                'scene': scene,
            }
            record_send_history(result)
            emit('send_result', result)
    except Exception as exc:
        with target_lock:
            if target_connection is not None:
                _close_target_connection()
                target_connection = None
        emit('target_connection_error', {'error': str(exc)})
        emit('error', {'message': f'发送失败: {exc}'})


@app.route('/api/connection_status')
def get_connection_status():
    with target_lock:
        connected = target_connection is not None
    return jsonify({'connected': connected})


@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    data = request.get_json()
    host = data.get('host', '').strip()
    port = data.get('port', 8080)
    protocol = data.get('protocol', 'tcp')

    if not host:
        return jsonify({'success': False, 'error': '主机地址不能为空'}), 400

    try:
        port = int(port)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': '端口号无效'}), 400

    try:
        if protocol == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.close()
        else:
            socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
        return jsonify({'success': True, 'host': host, 'port': port, 'protocol': protocol})
    except socket.timeout:
        return jsonify({'success': False, 'error': f'连接超时: {host}:{port}'})
    except ConnectionRefusedError:
        return jsonify({'success': False, 'error': f'连接被拒绝: {host}:{port}'})
    except socket.gaierror:
        return jsonify({'success': False, 'error': f'无法解析主机: {host}'})
    except OSError as exc:
        return jsonify({'success': False, 'error': str(exc)})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/parse_hex', methods=['POST'])
def parse_hex():
    data = request.get_json()
    hex_str = data.get('hex', '').strip()
    if not hex_str:
        return jsonify({'success': False, 'error': 'HEX数据不能为空'})
    try:
        packet = bytes.fromhex(hex_str.replace(' ', ''))
        parsed = build_packet_view(packet, addr_byte_order=_current_addr_byte_order())
        parsed['raw_hex'] = hex_str.replace(' ', '')
        return jsonify({'success': True, 'parsed': parsed})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/api/auto_send/meta')
def get_auto_send_scene_meta():
    return jsonify(get_auto_send_meta())


@app.route('/api/auto_send/templates', methods=['GET'])
def get_auto_send_templates():
    return jsonify(list_auto_send_templates())


@app.route('/api/auto_send/templates', methods=['POST'])
def create_auto_send_template():
    data = request.get_json() or {}
    scene = data.get('scene') or data
    try:
        template = save_auto_scene_template(scene)
        return jsonify(template), 201
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.route('/api/auto_send/templates/<template_id>', methods=['PUT'])
def update_auto_send_template(template_id: str):
    data = request.get_json() or {}
    scene = data.get('scene') or data
    try:
        template = save_auto_scene_template(scene, template_id=template_id)
        return jsonify(template)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.route('/api/auto_send/templates/<template_id>', methods=['DELETE'])
def remove_auto_send_template(template_id: str):
    if delete_auto_scene_template(template_id):
        return jsonify({'success': True})
    return jsonify({'error': '模板不存在或不可删除'}), 404


@app.route('/api/auto_send/preview', methods=['POST'])
def preview_auto_send_scene():
    data = request.get_json() or {}
    scene = data.get('scene') or data
    try:
        plan = build_scene_plan(scene, addr_byte_order=_current_addr_byte_order())
        steps = [
            {
                'id': step['id'],
                'name': step['name'],
                'delayAfterSec': step['delay_after_sec'],
                'typeFlag': step['type_flag'],
                'command': step['command'],
                'packetHex': step['packet_hex'],
                'packetLength': len(step['packet']),
                'packetView': step['packet_view'],
                'objectCount': 1,
            }
            for step in plan['steps']
        ]
        return jsonify(
            {
                'success': True,
                'sceneName': plan['scene_name'],
                'loop': plan['loop'],
                'steps': steps,
            }
        )
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400


@app.route('/api/signal_instances', methods=['GET'])
def get_signal_instances():
    return jsonify(list_signal_instances())


@app.route('/api/signal_instances', methods=['POST'])
def create_signal_instance():
    data = request.get_json() or {}
    try:
        instance = create_instance(data)
        return jsonify(instance), 201
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/signal_instances/<instance_id>', methods=['GET'])
def get_signal_instance_detail(instance_id: str):
    instance = get_instance(instance_id)
    if instance is None:
        return jsonify({'error': '实例不存在'}), 404
    return jsonify(instance)


@app.route('/api/signal_instances/<instance_id>', methods=['PUT'])
def update_signal_instance(instance_id: str):
    data = request.get_json() or {}
    try:
        instance = update_instance(instance_id, data)
        return jsonify(instance)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/signal_instances/<instance_id>', methods=['DELETE'])
def delete_signal_instance(instance_id: str):
    if delete_instance(instance_id):
        return jsonify({'success': True})
    return jsonify({'error': '实例不存在'}), 404


@app.route('/api/signal_instances/<instance_id>/preview', methods=['POST'])
def preview_signal_instance(instance_id: str):
    try:
        result = preview_instance(instance_id, addr_byte_order=_current_addr_byte_order())
        return jsonify(result)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/signal_instances/<instance_id>/resolve', methods=['GET'])
def resolve_signal_instance(instance_id: str):
    instance = get_instance(instance_id)
    if instance is None:
        return jsonify({'error': '实例不存在'}), 404
    try:
        packet = resolve_instance_packet(instance, addr_byte_order=_current_addr_byte_order())
        packet_view = build_packet_view(packet, addr_byte_order=_current_addr_byte_order(), scene=instance.get('templateId', ''), timestamp=now_ms())
        return jsonify({
            'instanceId': instance_id,
            'templateId': instance.get('templateId', ''),
            'packetHex': packet.hex(),
            'packetLength': len(packet),
            'packetView': packet_view,
        })
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@socketio.on('start_signal_instance')
def handle_start_signal_instance(data: dict[str, Any]) -> None:
    global target_connection
    instance_id = data.get('instanceId', '')
    network = data.get('network') or {}
    host = network.get('host', data.get('host', '127.0.0.1'))
    port = network.get('port', data.get('port', 8080))
    protocol = network.get('protocol', data.get('protocol', 'tcp'))

    instance = get_instance(instance_id)
    if instance is None:
        emit('signal_instance_error', {'message': f'实例 {instance_id} 不存在'})
        emit('error', {'message': f'实例 {instance_id} 不存在'})
        return

    try:
        packet = resolve_instance_packet(instance, addr_byte_order=_current_addr_byte_order())
    except ValueError as exc:
        emit('signal_instance_error', {'message': str(exc)})
        emit('error', {'message': str(exc)})
        return

    touch_instance(instance_id)

    try:
        with target_lock:
            conn = target_connection

        if conn is not None:
            with send_lock:
                if conn['protocol'] == 'tcp' and conn['socket']:
                    conn['socket'].sendall(packet)
                else:
                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    udp_sock.sendto(packet, (conn['host'], conn['port']))
                    udp_sock.close()
            simulator.stats['total_sent'] += 1
            result = {
                'success': True,
                'length': len(packet),
                'hex': packet.hex(),
                'host': conn['host'],
                'port': conn['port'],
                'protocol': conn['protocol'],
                'timestamp': now_ms(),
                'scene': instance.get('templateId', ''),
            }
            record_send_history(result)
        else:
            result = send_packet_network(packet, host, int(port), protocol, {'scene': instance.get('templateId', '')})

        packet_view = build_packet_view(packet, addr_byte_order=_current_addr_byte_order(), scene=instance.get('templateId', ''), timestamp=now_ms())
        emit('auto_scene_step_result', {
            **result,
            'packet_view': packet_view,
            'step_index': 0,
            'total_steps': 1,
            'scene_name': instance.get('name', ''),
        })
    except Exception as exc:
        with target_lock:
            if target_connection is not None:
                _close_target_connection()
                target_connection = None
        emit('signal_instance_error', {'message': str(exc)})
        emit('error', {'message': str(exc)})


@socketio.on('stop_signal_instance')
def handle_stop_signal_instance() -> None:
    pass


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/scenes')
def get_scenes():
    return jsonify(SCENE_CATALOG)


@app.route('/api/stats')
def get_stats():
    with send_history_lock:
        history_count = len(send_history)
    result = {
        'total_sent': simulator.stats['total_sent'],
        'running': simulator.running,
        'start_time': simulator.stats['start_time'],
        'history_count': history_count,
        'sequence': sequence_manager.current(),
    }
    print(f'[DEBUG] /api/stats => {json.dumps(result, ensure_ascii=False)}')
    return jsonify(result)


@app.route('/api/sequence')
def get_sequence():
    """获取当前业务流水号状态"""
    return jsonify({
        'current': sequence_manager.current(),
        'next': sequence_manager.current(),  # 下一个将要使用的序号
    })


@app.route('/api/sequence/reset', methods=['POST'])
def reset_sequence():
    """重置业务流水号"""
    data = request.get_json(silent=True) or {}
    value = data.get('value', 0)
    try:
        value = int(value)
    except (ValueError, TypeError):
        return jsonify({'error': '无效的序号值'}), 400
    sequence_manager.reset(value)
    return jsonify({'success': True, 'current': sequence_manager.current()})


@app.route('/api/history')
def get_history():
    limit = request.args.get('limit', 50, type=int)
    with send_history_lock:
        result = list(send_history[-limit:])
    print(f'[DEBUG] /api/history (limit={limit}) => {len(result)} 条记录')
    return jsonify(result)


@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    with send_history_lock:
        send_history.clear()
    return jsonify({'success': True})


@app.route('/api/history/save', methods=['POST'])
def save_history():
    with send_history_lock:
        snapshot = list(send_history)
    if not snapshot:
        return jsonify({'success': False, 'error': '暂无记录可保存'})

    packet_hex_set = set()
    for r in snapshot:
        if r.get('history_type') == 'packet' and r.get('parsed', {}).get('raw_hex'):
            packet_hex_set.add(r['parsed']['raw_hex'])

    deduped = []
    for r in snapshot:
        if r.get('history_type') == 'raw' and r.get('data_hex') and r['data_hex'] in packet_hex_set:
            continue
        deduped.append(r)

    timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    history_id = f'history_{timestamp_str}'

    send_count = sum(1 for r in deduped if r.get('direction') == 'send')
    recv_count = len(deduped) - send_count

    payload = {
        'metadata': {
            'save_time': now_ms(),
            'total_count': len(deduped),
            'send_count': send_count,
            'recv_count': recv_count,
            'source': '消防协议模拟器 v2.1',
        },
        'records': deduped,
    }

    filepath = os.path.join(HISTORY_DIR, f'{history_id}.json')
    try:
        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        return jsonify({'success': False, 'error': f'保存失败: {exc}'})

    return jsonify({
        'success': True,
        'id': history_id,
        'save_time': payload['metadata']['save_time'],
        'total_count': len(deduped),
        'send_count': send_count,
        'recv_count': recv_count,
    })


@app.route('/api/history/list')
def list_saved_history():
    histories = []
    if not os.path.isdir(HISTORY_DIR):
        return jsonify({'histories': histories})

    for filename in sorted(os.listdir(HISTORY_DIR), reverse=True):
        if not filename.startswith('history_') or not filename.endswith('.json'):
            continue
        filepath = os.path.join(HISTORY_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            meta = data.get('metadata', {})
            histories.append({
                'id': filename[:-5],
                'save_time': meta.get('save_time', ''),
                'total_count': meta.get('total_count', 0),
                'send_count': meta.get('send_count', 0),
                'recv_count': meta.get('recv_count', 0),
            })
        except Exception:
            histories.append({
                'id': filename[:-5],
                'save_time': '',
                'total_count': 0,
                'send_count': 0,
                'recv_count': 0,
                'corrupted': True,
            })

    return jsonify({'histories': histories})


@app.route('/api/history/saved/<history_id>')
def get_saved_history(history_id):
    safe_id = os.path.basename(history_id)
    filepath = os.path.join(HISTORY_DIR, f'{safe_id}.json')

    if not os.path.isfile(filepath):
        return jsonify({'success': False, 'error': '历史记录不存在'}), 404

    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': '历史记录文件已损坏'}), 500

    return jsonify(data)


@app.route('/api/history/saved/<history_id>', methods=['DELETE'])
def delete_saved_history(history_id):
    safe_id = os.path.basename(history_id)
    filepath = os.path.join(HISTORY_DIR, f'{safe_id}.json')

    if not os.path.isfile(filepath):
        return jsonify({'success': False, 'error': '历史记录不存在'}), 404

    try:
        os.remove(filepath)
    except Exception as exc:
        return jsonify({'success': False, 'error': f'删除失败: {exc}'}), 500

    return jsonify({'success': True})


def _build_json_export(records):
    send_count = sum(1 for r in records if r.get('direction') == 'send')
    recv_count = len(records) - send_count

    payload = {
        'metadata': {
            'export_time': now_ms(),
            'total_count': len(records),
            'send_count': send_count,
            'recv_count': recv_count,
            'source': '消防协议模拟器 v2.1',
        },
        'records': records,
    }

    filename = f'通信记录_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
    ascii_name = quote(filename)
    response = app.response_class(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype='application/json',
    )
    response.headers['Content-Disposition'] = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"
    return response


def _build_csv_export(records):
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        '序号', '方向', '类型', '源', '目标', '协议',
        '时间', '长度', '场景/类型', '状态', 'HEX',
    ])

    for idx, item in enumerate(records, start=1):
        direction = item.get('direction', '')
        direction_label = '发送' if direction == 'send' else '接收'

        scene_or_type = (
            item.get('scene_name')
            or item.get('step_name')
            or (item.get('parsed', {}).get('adu_summary') if isinstance(item.get('parsed'), dict) else None)
            or (item.get('parsed', {}).get('type_flag_name') if isinstance(item.get('parsed'), dict) else None)
            or ('原始数据' if item.get('data_hex') else '-')
        )

        status = (
            '成功' if item.get('success', True) else '失败'
        ) if direction == 'send' else '-'

        hex_data = item.get('hex', '') or item.get('data_hex', '') or ''

        writer.writerow([
            idx,
            direction_label,
            item.get('history_type', direction),
            item.get('source', '本机') if direction == 'send' else f"{item.get('host', '')}:{item.get('port', '')}",
            item.get('target', '本机') if direction == 'send' else '本机',
            (item.get('protocol', '') or '').upper(),
            item.get('timestamp', ''),
            item.get('length', 0) or item.get('data_length', 0),
            scene_or_type,
            status,
            hex_data,
        ])

    csv_content = output.getvalue()
    filename = f'通信记录_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
    ascii_name = quote(filename)

    response = app.response_class(
        '\ufeff' + csv_content,
        mimetype='text/csv; charset=utf-8',
    )
    response.headers['Content-Disposition'] = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"
    return response


@app.route('/api/history/export')
def export_history():
    fmt = request.args.get('format', 'json')
    with send_history_lock:
        snapshot = list(send_history)
    if not snapshot:
        return '', 204
    if fmt == 'json':
        return _build_json_export(snapshot)
    elif fmt == 'csv':
        return _build_csv_export(snapshot)
    else:
        return jsonify({'error': '无效的导出格式，支持 json 或 csv'}), 400


@app.route('/api/history/saved/<history_id>/export')
def export_saved_history(history_id):
    fmt = request.args.get('format', 'json')
    safe_id = os.path.basename(history_id)
    filepath = os.path.join(HISTORY_DIR, f'{safe_id}.json')

    if not os.path.isfile(filepath):
        return jsonify({'error': '历史记录不存在'}), 404

    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except json.JSONDecodeError:
        return jsonify({'error': '历史记录文件已损坏'}), 500

    records = data.get('records', [])
    if not records:
        return '', 204

    if fmt == 'json':
        return _build_json_export(records)
    elif fmt == 'csv':
        return _build_csv_export(records)
    else:
        return jsonify({'error': '无效的导出格式，支持 json 或 csv'}), 400


@app.route('/api/network_configs', methods=['GET'])
def get_network_configs():
    return jsonify(network_config_store.list_all())


@app.route('/api/network_configs/<int:config_id>', methods=['GET'])
def get_network_config(config_id: int):
    config = network_config_store.get(config_id)
    if config:
        return jsonify(config)
    return jsonify({'error': '配置不存在'}), 404


@app.route('/api/network_configs', methods=['POST'])
def create_network_config():
    data = request.get_json()
    if not data.get('name') or not data.get('host') or not data.get('port'):
        return jsonify({'error': '缺少必要参数'}), 400
    new_config = network_config_store.create(data)
    return jsonify(new_config), 201


@app.route('/api/network_configs/<int:config_id>', methods=['PUT'])
def update_network_config(config_id: int):
    data = request.get_json()
    config = network_config_store.update(config_id, data)
    if not config:
        return jsonify({'error': '配置不存在'}), 404
    return jsonify(config)


@app.route('/api/network_configs/<int:config_id>', methods=['DELETE'])
def delete_network_config(config_id: int):
    if network_config_store.delete(config_id):
        return jsonify({'success': True})
    return jsonify({'error': '配置不存在'}), 404


@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    return jsonify(AVAILABLE_PROFILES)


@app.route('/api/profile', methods=['GET'])
def get_current_profile():
    addr_order = get_addr_byte_order_for_profile(current_profile_key)
    return jsonify({'key': current_profile_key, 'addr_byte_order': addr_order})


@app.route('/api/profile', methods=['PUT'])
def set_current_profile():
    global current_profile_key
    data = request.get_json(silent=True) or {}
    key = data.get('key', '')
    valid_keys = [p['key'] for p in AVAILABLE_PROFILES]
    if key not in valid_keys:
        return jsonify({'error': f'无效的 profile key: {key}'}), 400
    current_profile_key = key
    addr_order = _current_addr_byte_order()
    # 更新 simulator 的 packet_builder 以适配新字节序
    simulator.packet_builder = GBT26875Packet(
        source_addr=simulator.packet_builder.source_addr,
        dest_addr=simulator.packet_builder.dest_addr,
        command=simulator.packet_builder.command,
        addr_byte_order=addr_order,
    )
    socketio.emit('profile_changed', {'key': current_profile_key, 'addr_byte_order': addr_order})
    return jsonify({'key': current_profile_key, 'addr_byte_order': addr_order})


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() in ('true', '1', 'yes')
    if is_main_process():
        print('=' * 60)
        print('GBT 26875.3-2011 消防报警数据模拟器')
        print('=' * 60)
        print('访问地址: http://127.0.0.1:5001')
        print(f"热重载模式: {'开启' if debug_mode else '关闭'}")
        if debug_mode:
            print('提示: 修改 app.py 或 templates/*.html 后服务将自动重启')
        print('=' * 60)
    socketio.run(app, host='0.0.0.0', port=5001, debug=debug_mode, use_reloader=debug_mode, allow_unsafe_werkzeug=True)
