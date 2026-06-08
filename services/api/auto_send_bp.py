#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: auto-send scene routes + parse_hex"""

from flask import Blueprint, jsonify, request

from protocol.packet_view import build_packet_view
from protocol.shared import (
    get_addr_byte_order_for_profile,
    get_component_addr_byte_order_for_profile,
)
from services.auto_send_scene import (
    build_scene_plan,
    delete_template as delete_auto_scene_template,
    get_auto_send_meta,
    list_templates as list_auto_send_templates,
    save_template as save_auto_scene_template,
)


def create_auto_send_bp(profile_state):
    """Create and return the auto-send Blueprint.

    Parameters
    ----------
    profile_state : dict
        Mutable dict holding ``{'key': current_profile_key}``.
        Used to compute addr byte orders at runtime.
    """
    bp = Blueprint('auto_send', __name__, url_prefix='/api')

    def _addr_byte_order():
        return get_addr_byte_order_for_profile(profile_state['key'])

    def _component_addr_byte_order():
        return get_component_addr_byte_order_for_profile(profile_state['key'])

    @bp.route('/parse_hex', methods=['POST'])
    def parse_hex():
        data = request.get_json()
        hex_str = data.get('hex', '').strip()
        if not hex_str:
            return jsonify({'success': False, 'error': 'HEX数据不能为空'})
        try:
            packet = bytes.fromhex(hex_str.replace(' ', ''))
            parsed = build_packet_view(
                packet,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
            )
            parsed['raw_hex'] = hex_str.replace(' ', '')
            return jsonify({'success': True, 'parsed': parsed})
        except Exception as exc:
            return jsonify({'success': False, 'error': str(exc)})

    @bp.route('/auto_send/meta')
    def get_auto_send_scene_meta():
        return jsonify(get_auto_send_meta())

    @bp.route('/auto_send/templates', methods=['GET'])
    def get_auto_send_templates():
        return jsonify(list_auto_send_templates())

    @bp.route('/auto_send/templates', methods=['POST'])
    def create_auto_send_template():
        data = request.get_json() or {}
        scene = data.get('scene') or data
        try:
            template = save_auto_scene_template(scene)
            return jsonify(template), 201
        except Exception as exc:
            return jsonify({'error': str(exc)}), 400

    @bp.route('/auto_send/templates/<template_id>', methods=['PUT'])
    def update_auto_send_template(template_id):
        data = request.get_json() or {}
        scene = data.get('scene') or data
        try:
            template = save_auto_scene_template(scene, template_id=template_id)
            return jsonify(template)
        except Exception as exc:
            return jsonify({'error': str(exc)}), 400

    @bp.route('/auto_send/templates/<template_id>', methods=['DELETE'])
    def remove_auto_send_template(template_id):
        if delete_auto_scene_template(template_id):
            return jsonify({'success': True})
        return jsonify({'error': '模板不存在或不可删除'}), 404

    @bp.route('/auto_send/preview', methods=['POST'])
    def preview_auto_send_scene():
        data = request.get_json() or {}
        scene = data.get('scene') or data
        try:
            plan = build_scene_plan(
                scene,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
            )
            steps = [
                {
                    'id': step['id'],
                    'name': step['name'],
                    'delayAfterSec': step['delay_after_sec'],
                    'typeFlag': step['type_flag'],
                    'command': step['command'],
                    'packetHex': step['packet_hex'],
                    'packetLength': len(step['packet']),
                    'packetView': step['packet_view'],
                    'objectCount': 1,
                }
                for step in plan['steps']
            ]
            return jsonify(
                {
                    'success': True,
                    'sceneName': plan['scene_name'],
                    'loop': plan['loop'],
                    'steps': steps,
                }
            )
        except Exception as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

    return bp