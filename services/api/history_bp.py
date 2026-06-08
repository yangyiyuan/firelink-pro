#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: history routes"""

import json
import logging
from urllib.parse import quote

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)


def create_history_bp(history_mgr, app):
    """Create and return the history Blueprint.

    Parameters
    ----------
    history_mgr : HistoryManager
    app : Flask
        Needed for ``app.response_class`` on export routes.
    """
    bp = Blueprint('history', __name__, url_prefix='/api')

    @bp.route('/history')
    def get_history():
        limit = request.args.get('limit', 50, type=int)
        result = history_mgr.get_recent(limit)
        logger.debug('/api/history (limit=%d) => %d 条记录', limit, len(result))
        return jsonify(result)

    @bp.route('/clear_history', methods=['POST'])
    def clear_history():
        history_mgr.clear()
        return jsonify({'success': True})

    @bp.route('/history/save', methods=['POST'])
    def save_history():
        return jsonify(history_mgr.save_to_file())

    @bp.route('/history/list')
    def list_saved_history():
        return jsonify({'histories': history_mgr.list_saved()})

    @bp.route('/history/saved/<history_id>')
    def get_saved_history(history_id):
        data = history_mgr.get_saved(history_id)
        if data is None:
            return jsonify({'success': False, 'error': '历史记录不存在'}), 404
        return jsonify(data)

    @bp.route('/history/saved/<history_id>', methods=['DELETE'])
    def delete_saved_history(history_id):
        if history_mgr.delete_saved(history_id):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '历史记录不存在'}), 404

    @bp.route('/history/export')
    def export_history():
        fmt = request.args.get('format', 'json')
        snapshot = history_mgr.snapshot()
        if not snapshot:
            return '', 204
        if fmt == 'json':
            payload, filename = history_mgr.export_json(snapshot)
            ascii_name = quote(filename)
            response = app.response_class(
                json.dumps(payload, ensure_ascii=False, indent=2),
                mimetype='application/json',
            )
            response.headers['Content-Disposition'] = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"
            return response
        elif fmt == 'csv':
            csv_content, filename = history_mgr.export_csv(snapshot)
            ascii_name = quote(filename)
            response = app.response_class(
                '\ufeff' + csv_content,
                mimetype='text/csv; charset=utf-8',
            )
            response.headers['Content-Disposition'] = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"
            return response
        else:
            return jsonify({'error': '无效的导出格式，支持 json 或 csv'}), 400

    @bp.route('/history/saved/<history_id>/export')
    def export_saved_history(history_id):
        fmt = request.args.get('format', 'json')
        try:
            data = history_mgr.get_saved(history_id)
        except ValueError:
            return jsonify({'error': '历史记录文件已损坏'}), 500

        if data is None:
            return jsonify({'error': '历史记录不存在'}), 404

        records = data.get('records', [])
        if not records:
            return '', 204

        if fmt == 'json':
            payload, filename = history_mgr.export_json(records)
            ascii_name = quote(filename)
            response = app.response_class(
                json.dumps(payload, ensure_ascii=False, indent=2),
                mimetype='application/json',
            )
            response.headers['Content-Disposition'] = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"
            return response
        elif fmt == 'csv':
            csv_content, filename = history_mgr.export_csv(records)
            ascii_name = quote(filename)
            response = app.response_class(
                '\ufeff' + csv_content,
                mimetype='text/csv; charset=utf-8',
            )
            response.headers['Content-Disposition'] = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{ascii_name}"
            return response
        else:
            return jsonify({'error': '无效的导出格式，支持 json 或 csv'}), 400

    return bp