#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: connection status and test routes"""

from flask import Blueprint, jsonify, request


def create_connection_bp(connection_mgr):
    """Create and return the connection Blueprint.

    Parameters
    ----------
    connection_mgr : ConnectionManager
    """
    bp = Blueprint('connection', __name__, url_prefix='/api')

    @bp.route('/connection_status')
    def get_connection_status():
        return jsonify({'connected': connection_mgr.is_connected()})

    @bp.route('/test_connection', methods=['POST'])
    def test_connection():
        data = request.get_json()
        host = data.get('host', '').strip()
        port = data.get('port', 8080)
        protocol = data.get('protocol', 'tcp')
        result = connection_mgr.test_connection(host, port, protocol)
        if not result.get('success') and (result.get('error') == '主机地址不能为空' or result.get('error') == '端口号无效'):
            return jsonify(result), 400
        return jsonify(result)

    return bp