#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: connection status and test routes"""

from flask import Blueprint, jsonify, request

from services.api.response_utils import error_response
from services.api.validators import validate_host, validate_port


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
        valid, msg = validate_host(host)
        if not valid:
            return error_response(msg)
        valid, msg = validate_port(port)
        if not valid:
            return error_response(msg)
        result = connection_mgr.test_connection(host, port, protocol)
        return jsonify(result)

    return bp