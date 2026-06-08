#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: network config CRUD routes"""

from flask import Blueprint, jsonify, request


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
        return jsonify({'error': '配置不存在'}), 404

    @bp.route('/network_configs', methods=['POST'])
    def create_network_config():
        data = request.get_json()
        if not data.get('name') or not data.get('host') or not data.get('port'):
            return jsonify({'error': '缺少必要参数'}), 400
        new_config = network_config_store.create(data)
        return jsonify(new_config), 201

    @bp.route('/network_configs/<int:config_id>', methods=['PUT'])
    def update_network_config(config_id):
        data = request.get_json()
        config = network_config_store.update(config_id, data)
        if not config:
            return jsonify({'error': '配置不存在'}), 404
        return jsonify(config)

    @bp.route('/network_configs/<int:config_id>', methods=['DELETE'])
    def delete_network_config(config_id):
        if network_config_store.delete(config_id):
            return jsonify({'success': True})
        return jsonify({'error': '配置不存在'}), 404

    return bp