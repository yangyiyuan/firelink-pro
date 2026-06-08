#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: network config CRUD routes"""

from flask import Blueprint, jsonify, request

from services.api.response_utils import success_response, error_response
from services.api.validators import validate_host, validate_port


def create_network_configs_bp(network_config_store):
    """Create and return the network configs Blueprint.

    Parameters
    ----------
    network_config_store : NetworkConfigStore
    """
    bp = Blueprint('network_configs', __name__, url_prefix='/api')

    @bp.route('/network_configs', methods=['GET'])
    def get_network_configs():
        return jsonify(network_config_store.list_all())

    @bp.route('/network_configs/<int:config_id>', methods=['GET'])
    def get_network_config(config_id):
        config = network_config_store.get(config_id)
        if config:
            return jsonify(config)
        return error_response('配置不存在', status_code=404)

    @bp.route('/network_configs', methods=['POST'])
    def create_network_config():
        data = request.get_json()
        if not data.get('name') or not data.get('host') or not data.get('port'):
            return error_response('缺少必要参数')
        valid, msg = validate_host(data['host'])
        if not valid:
            return error_response(msg)
        valid, msg = validate_port(data['port'])
        if not valid:
            return error_response(msg)
        new_config = network_config_store.create(data)
        return success_response(new_config, status_code=201)

    @bp.route('/network_configs/<int:config_id>', methods=['PUT'])
    def update_network_config(config_id):
        data = request.get_json()
        config = network_config_store.update(config_id, data)
        if not config:
            return error_response('配置不存在', status_code=404)
        return jsonify(config)

    @bp.route('/network_configs/<int:config_id>', methods=['DELETE'])
    def delete_network_config(config_id):
        if network_config_store.delete(config_id):
            return success_response()
        return error_response('配置不存在', status_code=404)

    return bp