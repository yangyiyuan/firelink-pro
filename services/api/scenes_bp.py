#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: scenes, stats, sequence"""

import json
import logging

from flask import Blueprint, jsonify, request

from protocol.scene_catalog import SCENE_CATALOG
from protocol.sequence import sequence_manager

logger = logging.getLogger(__name__)


def create_scenes_bp(simulator, history_mgr):
    """Create and return the scenes Blueprint.

    Parameters
    ----------
    simulator : FireAlarmSimulator
    history_mgr : HistoryManager
    """
    bp = Blueprint('scenes', __name__, url_prefix='/api')

    @bp.route('/scenes')
    def get_scenes():
        return jsonify(SCENE_CATALOG)

    @bp.route('/stats')
    def get_stats():
        result = {
            'total_sent': simulator.stats['total_sent'],
            'running': simulator.running,
            'start_time': simulator.stats['start_time'],
            'history_count': history_mgr.count(),
            'sequence': sequence_manager.current(),
        }
        logger.debug('/api/stats => %s', json.dumps(result, ensure_ascii=False))
        return jsonify(result)

    @bp.route('/sequence')
    def get_sequence():
        """获取当前业务流水号状态"""
        return jsonify({
            'current': sequence_manager.current(),
            'next': sequence_manager.current(),
        })

    @bp.route('/sequence/reset', methods=['POST'])
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

    return bp