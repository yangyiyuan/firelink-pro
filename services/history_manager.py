#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HistoryManager — 通信历史记录的 CRUD、去重保存与 JSON/CSV 导出"""

import csv
import datetime
import io
import json
import logging
import os
import threading
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from services.utils import now_ms_str as now_ms

logger = logging.getLogger(__name__)


class HistoryManager:
    """管理发送/接收通信历史记录的内存存储与文件持久化。

    - record_send()/record_receive(): 写入内存 deque（线程安全）
    - get_recent()/snapshot()/count(): 读取内存记录
    - save_to_file(): 去重后持久化到 JSON 文件
    - list_saved()/get_saved()/delete_saved(): 管理已保存文件
    - export_json()/export_csv(): 构建导出数据（不含 Flask response）
    """

    def __init__(self, maxlen: int = 1000, history_dir: Optional[str] = None):
        self._history: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._history_dir = history_dir
        if self._history_dir:
            os.makedirs(self._history_dir, exist_ok=True)

    # ── 写入 ──────────────────────────────────────────────

    def record_send(self, result: Dict[str, Any]) -> None:
        """记录一次发送事件"""
        entry = dict(result)
        entry['direction'] = 'send'
        entry['history_type'] = 'send'
        with self._lock:
            self._history.append(entry)

    def record_receive(self, kind: str, host: str, port: int, timestamp: str,
                       protocol: str = 'tcp', **kwargs: Any) -> None:
        """记录一次接收事件"""
        entry: Dict[str, Any] = {
            'direction': 'recv',
            'history_type': kind,
            'host': host,
            'port': port,
            'protocol': protocol,
            'timestamp': timestamp,
        }
        entry.update(kwargs)
        with self._lock:
            self._history.append(entry)

    # ── 读取 ──────────────────────────────────────────────

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近 limit 条记录"""
        with self._lock:
            return list(self._history)[-limit:]

    def clear(self) -> None:
        """清空内存记录"""
        with self._lock:
            self._history.clear()

    def count(self) -> int:
        """当前内存记录总数"""
        with self._lock:
            return len(self._history)

    def snapshot(self) -> List[Dict[str, Any]]:
        """获取内存记录完整快照"""
        with self._lock:
            return list(self._history)

    # ── 持久化 ────────────────────────────────────────────

    def save_to_file(self) -> Dict[str, Any]:
        """去重后保存到 JSON 文件。返回结果 dict。"""
        if not self._history_dir:
            return {'success': False, 'error': '未配置历史记录保存目录'}

        records = self.snapshot()
        if not records:
            return {'success': False, 'error': '暂无记录可保存'}

        deduped = self._dedup_records(records)
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

        filepath = os.path.join(self._history_dir, f'{history_id}.json')
        try:
            with open(filepath, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        except Exception as exc:
            return {'success': False, 'error': f'保存失败: {exc}'}

        return {
            'success': True,
            'id': history_id,
            'save_time': payload['metadata']['save_time'],
            'total_count': len(deduped),
            'send_count': send_count,
            'recv_count': recv_count,
        }

    def list_saved(self) -> List[Dict[str, Any]]:
        """列出所有已保存的历史文件元信息"""
        histories: List[Dict[str, Any]] = []
        if not self._history_dir or not os.path.isdir(self._history_dir):
            return histories

        for filename in sorted(os.listdir(self._history_dir), reverse=True):
            if not filename.startswith('history_') or not filename.endswith('.json'):
                continue
            filepath = os.path.join(self._history_dir, filename)
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

        return histories

    def get_saved(self, history_id: str) -> Optional[Dict[str, Any]]:
        """读取已保存的历史文件。不存在返回 None，损坏抛 ValueError。"""
        safe_id = os.path.basename(history_id)
        filepath = os.path.join(self._history_dir, f'{safe_id}.json')

        if not os.path.isfile(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            raise ValueError('历史记录文件已损坏')

    def delete_saved(self, history_id: str) -> bool:
        """删除已保存的历史文件。不存在返回 False。"""
        safe_id = os.path.basename(history_id)
        filepath = os.path.join(self._history_dir, f'{safe_id}.json')

        if not os.path.isfile(filepath):
            return False

        os.remove(filepath)
        return True

    # ── 导出 ──────────────────────────────────────────────

    def export_json(self, records: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str]:
        """构建 JSON 导出数据。返回 (payload_dict, filename)。"""
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
        return payload, filename

    def export_csv(self, records: List[Dict[str, Any]]) -> Tuple[str, str]:
        """构建 CSV 导出内容。返回 (csv_content, filename)。"""
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
        return csv_content, filename

    # ── 内部方法 ──────────────────────────────────────────

    def _dedup_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除与 parsed 记录重复的 raw 记录"""
        packet_hex_set = set()
        for r in records:
            if r.get('history_type') == 'packet' and r.get('parsed', {}).get('raw_hex'):
                packet_hex_set.add(r['parsed']['raw_hex'])

        deduped = []
        for r in records:
            if r.get('history_type') == 'raw' and r.get('data_hex') and r['data_hex'] in packet_hex_set:
                continue
            deduped.append(r)
        return deduped