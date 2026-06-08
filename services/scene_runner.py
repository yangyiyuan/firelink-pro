#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SceneRunner — 自动场景的生命周期管理：启动、运行循环、停止联动"""

import datetime
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from services.auto_send_scene import build_scene_plan, rebuild_step_packet

logger = logging.getLogger(__name__)


class SceneRunner:
    """管理自动场景的运行生命周期。

    - start_scene(scene, network): 启动场景，返回结果 dict
    - stop_scene(template_id): 按 template_id 停止，返回已停止列表
    - stop_all(): 停止所有场景（断开联动回调）
    - is_running(template_id): 检查是否运行中

    _lock 保护 _runs 字典（run_id → RunInfo），独立于 ConnectionManager._lock。
    """

    def __init__(
        self,
        connection_manager,
        socketio,
        addr_byte_order_fn: Callable[[], str],
        component_addr_byteorder_fn: Callable[[], str],
    ):
        self._conn = connection_manager
        self._socketio = socketio
        self._addr_byte_order_fn = addr_byte_order_fn
        self._component_addr_byteorder_fn = component_addr_byteorder_fn
        self._lock = threading.Lock()
        self._runs: Dict[str, Dict[str, Any]] = {}

    # ── 启动 ──────────────────────────────────────────────

    def start_scene(self, scene: Dict[str, Any], network: Dict[str, Any]) -> Dict[str, Any]:
        """启动一个自动场景。返回结果 dict（含 event 字段用于 handler 判断 emit 类型）。"""
        host = network.get('host', '127.0.0.1')
        port = network.get('port', 8080)
        protocol = network.get('protocol', 'tcp')
        template_id = scene.get('id', '')
        logger.debug('start_auto_scene => scene_name=%s, network=%s:%s/%s, steps=%d',
                     scene.get('name'), host, port, protocol, len(scene.get('steps', [])))

        # 检查是否已在运行
        with self._lock:
            for rid, rinfo in self._runs.items():
                if rinfo.get('template_id') == template_id:
                    return {
                        'success': False,
                        'error': f'场景 {scene.get("name", "")} 已在运行中',
                        'event': 'auto_scene_error',
                    }

        # 构建场景计划
        try:
            plan = build_scene_plan(
                scene,
                addr_byte_order=self._addr_byte_order_fn(),
                component_addr_byteorder=self._component_addr_byteorder_fn(),
            )
        except Exception as exc:
            return {'success': False, 'error': str(exc), 'event': 'auto_scene_error'}

        # 创建运行记录
        stop_event = threading.Event()
        run_id = self._new_run_id()
        with self._lock:
            self._runs[run_id] = {
                'thread': None,
                'stop_event': stop_event,
                'run_id': run_id,
                'scene_name': plan['scene_name'],
                'template_id': template_id,
            }

        # 启动工作线程
        worker = threading.Thread(
            target=self._run_loop,
            args=(run_id, plan, template_id, stop_event, host, int(port), protocol),
            daemon=True,
        )
        with self._lock:
            self._runs[run_id]['thread'] = worker
        worker.start()

        logger.debug('auto_scene_started => run_id=%s, scene_name=%s, steps=%d, loop=%s',
                     run_id, plan['scene_name'], len(plan['steps']), plan['loop'])
        return {
            'success': True,
            'event': 'auto_scene_started',
            'run_id': run_id,
            'scene_name': plan['scene_name'],
            'step_count': len(plan['steps']),
            'loop': plan['loop'],
            'template_id': template_id,
        }

    # ── 停止 ──────────────────────────────────────────────

    def stop_scene(self, template_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """停止指定 template_id 的场景，或全部场景（template_id 为 None）。返回已停止的运行列表。"""
        with self._lock:
            if template_id:
                targets = {rid: info for rid, info in list(self._runs.items())
                           if info.get('template_id') == template_id}
            else:
                targets = dict(self._runs)

            if not targets:
                return [{'run_id': None, 'scene_name': '', 'template_id': template_id}]

            threads_info = []
            for rid, info in targets.items():
                threads_info.append((
                    rid,
                    info.get('thread'),
                    info.get('scene_name'),
                    info.get('template_id'),
                    info.get('stop_event'),
                ))

        # 通知停止
        for rid, thread, scene_name, tid, stop_ev in threads_info:
            if stop_ev is not None:
                stop_ev.set()

        # 等待线程结束
        results = []
        for rid, thread, scene_name, tid, _ in threads_info:
            if thread:
                thread.join(timeout=2)
            results.append({'run_id': rid, 'scene_name': scene_name or '', 'template_id': tid or ''})

        return results

    def stop_all(self) -> None:
        """停止所有运行中的自动场景（作为 ConnectionManager 断开联动回调）。"""
        with self._lock:
            all_stop_events = [
                (rid, info.get('stop_event'))
                for rid, info in list(self._runs.items())
            ]

        for rid, stop_ev in all_stop_events:
            if stop_ev is not None:
                stop_ev.set()

        logger.info('连接断开，已联动停止自动场景')

    # ── 查询 ──────────────────────────────────────────────

    def is_running(self, template_id: str) -> bool:
        """检查指定 template_id 的场景是否运行中"""
        with self._lock:
            for rid, info in self._runs.items():
                if info.get('template_id') == template_id:
                    return True
        return False

    # ── 内部方法 ──────────────────────────────────────────

    def _new_run_id(self) -> str:
        """生成唯一运行 ID"""
        return f'run_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}_{int(time.time() * 1000) % 1000:03d}'

    def _run_loop(
        self,
        run_id: str,
        plan: Dict[str, Any],
        template_id: str,
        stop_event: threading.Event,
        host: str,
        port: int,
        protocol: str,
    ) -> None:
        """自动场景工作线程主循环"""
        cycle_index = 0
        try:
            while not stop_event.is_set():
                cycle_index += 1
                logger.debug('run_auto_scene => cycle=%d, steps=%d, stop=%s',
                             cycle_index, len(plan['steps']), stop_event.is_set())
                for step_index, step in enumerate(plan['steps'], start=1):
                    if stop_event.is_set():
                        break

                    # 每轮刷新数据包（序号递增）
                    fresh = rebuild_step_packet(
                        step,
                        addr_byte_order=self._addr_byte_order_fn(),
                        component_addr_byteorder=self._component_addr_byteorder_fn(),
                    )
                    step['packet'] = fresh['packet']
                    step['packet_hex'] = fresh['packet_hex']
                    step['packet_view'] = fresh['packet_view']

                    # 统一发送（自动选择长/短连接）
                    result = self._conn.send(
                        step['packet'], host, port, protocol,
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
                    logger.debug('auto_scene_step_result => step=%d/%d, cycle=%d, success=%s, hex_len=%s, via=%s',
                                 step_index, len(plan['steps']), cycle_index, result.get('success'),
                                 result.get('length'), '长连接' if result.get('via_connection') else '短连接')

                    # 构建 packet_view 并 emit
                    packet_view = dict(step['packet_view'])
                    packet_view.update({
                        'run_id': run_id,
                        'step_id': step['id'],
                        'step_name': step['name'],
                        'step_index': step_index,
                        'cycle_index': cycle_index,
                    })
                    self._socketio.emit('auto_scene_step_result', {
                        **result,
                        'packet_view': packet_view,
                        'step_id': step['id'],
                        'step_name': step['name'],
                        'step_index': step_index,
                        'cycle_index': cycle_index,
                        'scene_name': plan['scene_name'],
                        'run_id': run_id,
                        'template_id': template_id,
                    })

                    # 步间延迟
                    if step['delay_after_sec'] > 0:
                        if stop_event.wait(step['delay_after_sec']):
                            break

                # 一轮完成
                self._socketio.emit('auto_scene_completed', {
                    'run_id': run_id,
                    'scene_name': plan['scene_name'],
                    'cycle_index': cycle_index,
                    'loop': plan['loop'],
                    'template_id': template_id,
                })
                if stop_event.is_set() or not plan['loop']:
                    break

        except Exception as exc:
            logger.error('run_auto_scene CRASHED => %s', exc, exc_info=True)
            self._socketio.emit('auto_scene_error',
                                {'message': str(exc), 'run_id': run_id, 'template_id': template_id})
        finally:
            with self._lock:
                self._runs.pop(run_id, None)
            self._socketio.emit('auto_scene_stopped',
                                {'run_id': run_id, 'scene_name': plan['scene_name'], 'template_id': template_id})