#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SocketIO event handlers — registered directly on the socketio instance."""

import logging
import threading
import time
from typing import Any

from flask_socketio import emit

from protocol.packet_view import build_packet_view
from protocol.shared import (
    get_addr_byte_order_for_profile,
    get_component_addr_byte_order_for_profile,
)
from services.signal_instance import (
    get_instance,
    resolve_instance_packet,
    touch_instance,
)
from services.utils import now_ms_str as now_ms

logger = logging.getLogger(__name__)


def register_socketio_events(socketio, services):
    """Register all SocketIO event handlers on the given socketio instance.

    Parameters
    ----------
    socketio : SocketIO
    services : dict
        Must contain keys:
        - ``simulator``       — FireAlarmSimulator
        - ``connection_mgr``  — ConnectionManager
        - ``scene_runner``    — SceneRunner
        - ``profile_state``   — dict ``{'key': current_profile_key}``
    """
    simulator = services['simulator']
    connection_mgr = services['connection_mgr']
    scene_runner = services['scene_runner']
    profile_state = services['profile_state']

    def _addr_byte_order():
        return get_addr_byte_order_for_profile(profile_state['key'])

    def _component_addr_byte_order():
        return get_component_addr_byte_order_for_profile(profile_state['key'])

    @socketio.on('connect')
    def handle_connect():
        emit('status', {'message': '已连接到模拟器服务器', 'connected': True})

    @socketio.on('disconnect')
    def handle_disconnect():
        pass

    @socketio.on('generate_packet')
    def handle_generate_packet(data: dict[str, Any]):
        scene = data.get('scene', 'single_fire')
        try:
            packet = simulator.get_scene_packet(scene)
            emit('packet_generated', build_packet_view(
                packet,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
                scene=scene,
                timestamp=now_ms(),
            ))
        except Exception as exc:
            emit('error', {'message': str(exc)})

    @socketio.on('send_packet')
    def handle_send_packet(data: dict[str, Any]):
        scene = data.get('scene', 'single_fire')
        host = data.get('host', '127.0.0.1')
        port = data.get('port', 8080)
        protocol = data.get('protocol', 'tcp')
        try:
            if scene == 'full_fire':
                packets = simulator.scene_full_fire_scenario()
                results = []
                for index, packet in enumerate(packets, start=1):
                    result = connection_mgr.send(packet, host, int(port), protocol, {'scene': scene})
                    result['packet_index'] = index
                    result['total_packets'] = len(packets)
                    results.append(result)
                    time.sleep(0.1)
                emit('send_result', {'success': True, 'results': results, 'scene': scene})
            else:
                packet = simulator.get_scene_packet(scene)
                emit('send_result', connection_mgr.send(packet, host, int(port), protocol, {'scene': scene}))
        except Exception as exc:
            emit('error', {'message': str(exc)})

    @socketio.on('start_auto_send')
    def handle_start_auto_send(data: dict[str, Any]):
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

        def auto_send():
            while simulator.running:
                try:
                    packet = simulator.get_scene_packet(scene)
                    result = connection_mgr.send(packet, host, int(port), protocol, {'scene': scene, 'mode': 'auto'})
                    socketio.emit('auto_send_result', result)
                    time.sleep(interval)
                except Exception as exc:
                    socketio.emit('error', {'message': str(exc)})
                    break

        simulator.send_thread = threading.Thread(target=auto_send, daemon=True)
        simulator.send_thread.start()
        emit('auto_send_started', {'scene': scene, 'interval': interval})

    @socketio.on('stop_auto_send')
    def handle_stop_auto_send():
        simulator.running = False
        if simulator.send_thread:
            simulator.send_thread.join(timeout=2)
        emit('auto_send_stopped', {'stats': simulator.stats})

    @socketio.on('start_auto_scene')
    def handle_start_auto_scene(data: dict[str, Any]):
        scene = data.get('scene') or {}
        network = data.get('network') or {}
        result = scene_runner.start_scene(scene, network)
        if result.get('event') == 'auto_scene_error':
            emit('auto_scene_error', {'message': result.get('error', '')})
        elif result.get('event') == 'auto_scene_started':
            emit('auto_scene_started', {
                'run_id': result['run_id'],
                'scene_name': result['scene_name'],
                'step_count': result['step_count'],
                'loop': result['loop'],
                'template_id': result['template_id'],
            })

    @socketio.on('start_auto_scenes')
    def handle_start_auto_scenes(data: dict[str, Any]):
        scenes = data.get('scenes') or []
        network = data.get('network') or {}
        if not scenes:
            emit('auto_scene_error', {'message': '未选择任何场景'})
            return
        for scene in scenes:
            result = scene_runner.start_scene(scene, network)
            if result.get('event') == 'auto_scene_error':
                emit('auto_scene_error', {'message': result.get('error', '')})
            elif result.get('event') == 'auto_scene_started':
                emit('auto_scene_started', {
                    'run_id': result['run_id'],
                    'scene_name': result['scene_name'],
                    'step_count': result['step_count'],
                    'loop': result['loop'],
                    'template_id': result['template_id'],
                })

    @socketio.on('stop_auto_scene')
    def handle_stop_auto_scene(data: dict | None = None):
        template_id = None
        if data and isinstance(data, dict):
            template_id = data.get('template_id')
        stopped = scene_runner.stop_scene(template_id)
        for info in stopped:
            emit('auto_scene_stopped', {
                'run_id': info.get('run_id'),
                'scene_name': info.get('scene_name', ''),
                'template_id': info.get('template_id', ''),
            })

    @socketio.on('connect_target')
    def handle_connect_target(data: dict[str, Any]):
        host = data.get('host', '127.0.0.1')
        port = int(data.get('port', 8080))
        protocol = data.get('protocol', 'tcp')
        logger.debug('connect_target => host=%s, port=%d, protocol=%s', host, port, protocol)

        try:
            connection_mgr.connect(host, port, protocol)
            emit('target_connected', {'host': host, 'port': port, 'protocol': protocol})
            logger.info('target_connected => host=%s, port=%s, protocol=%s', host, port, protocol)
        except Exception as exc:
            emit('target_connection_error', {'error': str(exc)})
            logger.error('target_connection_error => %s', exc)

    @socketio.on('disconnect_target')
    def handle_disconnect_target():
        connection_mgr.disconnect()
        emit('target_disconnected', {})

    @socketio.on('send_via_connection')
    def handle_send_via_connection(data: dict[str, Any]):
        scene = data.get('scene', 'single_fire')

        if not connection_mgr.is_connected():
            emit('error', {'message': '未连接到目标服务器'})
            return

        try:
            if scene == 'full_fire':
                packets = simulator.scene_full_fire_scenario()
                results = []
                for index, packet in enumerate(packets, start=1):
                    result = connection_mgr.send_via_connection(packet, {
                        'packet_index': index,
                        'total_packets': len(packets),
                        'scene': scene,
                    })
                    results.append(result)
                    if not result.get('success'):
                        break
                    time.sleep(0.1)
                emit('send_result', {'success': True, 'results': results, 'scene': scene})
            else:
                packet = simulator.get_scene_packet(scene)
                result = connection_mgr.send_via_connection(packet, {'scene': scene})
                emit('send_result', result)
        except Exception as exc:
            emit('error', {'message': f'发送失败: {exc}'})

    @socketio.on('start_signal_instance')
    def handle_start_signal_instance(data: dict[str, Any]):
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
            packet = resolve_instance_packet(
                instance,
                simulator,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
            )
        except ValueError as exc:
            emit('signal_instance_error', {'message': str(exc)})
            emit('error', {'message': str(exc)})
            return

        touch_instance(instance_id)

        try:
            result = connection_mgr.send(packet, host, int(port), protocol, {
                'scene': instance.get('templateId', ''),
            })

            packet_view = build_packet_view(
                packet,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
                scene=instance.get('templateId', ''),
                timestamp=now_ms(),
            )
            emit('auto_scene_step_result', {
                **result,
                'packet_view': packet_view,
                'step_index': 0,
                'total_steps': 1,
                'scene_name': instance.get('name', ''),
            })
        except Exception as exc:
            emit('signal_instance_error', {'message': str(exc)})
            emit('error', {'message': str(exc)})

    @socketio.on('stop_signal_instance')
    def handle_stop_signal_instance():
        pass