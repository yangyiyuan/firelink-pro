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
from typing import Any

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

try:
    from fire_alarm_simulator.protocol.core import (
        SCENE_CATALOG,
        FireAlarmSimulator,
        build_packet_view,
    )
except ModuleNotFoundError:
    # 兼容在 fire_alarm_simulator 目录下直接执行 `python app.py`
    from protocol.core import (
        SCENE_CATALOG,
        FireAlarmSimulator,
        build_packet_view,
    )


def now_ms() -> str:
    now = datetime.datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S.') + f'{now.microsecond // 1000:03d}'


def is_reloader_process() -> bool:
    return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'


def is_main_process() -> bool:
    return not os.environ.get('WERKZEUG_RUN_MAIN')


app = Flask(__name__)
app.config['SECRET_KEY'] = 'fire-alarm-simulator-secret-key'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

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
send_history = []
max_history = 1000


def push_history(entry: dict[str, Any]) -> None:
    send_history.append(entry)
    if len(send_history) > max_history:
        send_history.pop(0)


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


CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'network_configs.json')


def _load_configs() -> tuple[list[dict[str, Any]], int]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            return data.get('configs', []), data.get('next_id', 1)
        except Exception:
            pass
    return [
        {
            'id': 1,
            'name': '本地测试',
            'host': '127.0.0.1',
            'port': 8080,
            'protocol': 'tcp',
            'description': '本地开发测试服务器',
        }
    ], 2


def _save_configs() -> None:
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as fh:
            json.dump({'configs': network_configs, 'next_id': next_config_id}, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f'保存配置文件失败: {exc}')


network_configs, next_config_id = _load_configs()
target_connection = None
target_lock = threading.Lock()


def send_packet_network(packet: bytes, host: str, port: int, protocol: str, extra_fields: dict[str, Any] | None = None) -> dict[str, Any]:
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
                    parsed = build_packet_view(packet)
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
    socketio.emit('target_disconnected', {})


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
        emit('packet_generated', build_packet_view(packet, scene=scene, timestamp=now_ms()))
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


@socketio.on('connect_target')
def handle_connect_target(data: dict[str, Any]) -> None:
    global target_connection
    host = data.get('host', '127.0.0.1')
    port = int(data.get('port', 8080))
    protocol = data.get('protocol', 'tcp')

    try:
        with target_lock:
            if target_connection is not None:
                _close_target_connection()

            if protocol == 'tcp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((host, port))
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
    except Exception as exc:
        with target_lock:
            target_connection = None
        emit('target_connection_error', {'error': str(exc)})


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
        parsed = build_packet_view(packet)
        parsed['raw_hex'] = hex_str.replace(' ', '')
        return jsonify({'success': True, 'parsed': parsed})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/scenes')
def get_scenes():
    return jsonify(SCENE_CATALOG)


@app.route('/api/stats')
def get_stats():
    return jsonify(
        {
            'total_sent': simulator.stats['total_sent'],
            'running': simulator.running,
            'start_time': simulator.stats['start_time'],
            'history_count': len(send_history),
        }
    )


@app.route('/api/history')
def get_history():
    limit = request.args.get('limit', 50, type=int)
    return jsonify(send_history[-limit:])


@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    global send_history
    send_history = []
    return jsonify({'success': True})


@app.route('/api/network_configs', methods=['GET'])
def get_network_configs():
    return jsonify(network_configs)


@app.route('/api/network_configs/<int:config_id>', methods=['GET'])
def get_network_config(config_id: int):
    config = next((c for c in network_configs if c['id'] == config_id), None)
    if config:
        return jsonify(config)
    return jsonify({'error': '配置不存在'}), 404


@app.route('/api/network_configs', methods=['POST'])
def create_network_config():
    global next_config_id
    data = request.get_json()
    if not data.get('name') or not data.get('host') or not data.get('port'):
        return jsonify({'error': '缺少必要参数'}), 400

    new_config = {
        'id': next_config_id,
        'name': data['name'],
        'host': data['host'],
        'port': int(data['port']),
        'protocol': data.get('protocol', 'tcp'),
        'description': data.get('description', ''),
    }
    network_configs.append(new_config)
    next_config_id += 1
    _save_configs()
    return jsonify(new_config), 201


@app.route('/api/network_configs/<int:config_id>', methods=['PUT'])
def update_network_config(config_id: int):
    data = request.get_json()
    config = next((c for c in network_configs if c['id'] == config_id), None)
    if not config:
        return jsonify({'error': '配置不存在'}), 404

    if 'name' in data:
        config['name'] = data['name']
    if 'host' in data:
        config['host'] = data['host']
    if 'port' in data:
        config['port'] = int(data['port'])
    if 'protocol' in data:
        config['protocol'] = data['protocol']
    if 'description' in data:
        config['description'] = data['description']

    _save_configs()
    return jsonify(config)


@app.route('/api/network_configs/<int:config_id>', methods=['DELETE'])
def delete_network_config(config_id: int):
    global network_configs
    config = next((c for c in network_configs if c['id'] == config_id), None)
    if not config:
        return jsonify({'error': '配置不存在'}), 404

    network_configs = [c for c in network_configs if c['id'] != config_id]
    _save_configs()
    return jsonify({'success': True})


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
    socketio.run(app, host='0.0.0.0', port=5001, debug=debug_mode, use_reloader=debug_mode)
