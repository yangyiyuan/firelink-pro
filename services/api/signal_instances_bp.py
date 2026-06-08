#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: signal instance routes"""

from flask import Blueprint, jsonify, request

from protocol.packet_view import build_packet_view
from protocol.shared import (
    get_addr_byte_order_for_profile,
    get_component_addr_byte_order_for_profile,
)
from services.signal_instance import (
    create_instance,
    delete_instance,
    get_instance,
    list_instances as list_signal_instances,
    preview_instance,
    resolve_instance_packet,
    update_instance,
)
from services.utils import now_ms_str as now_ms


def create_signal_instances_bp(profile_state):
    """Create and return the signal instances Blueprint.

    Parameters
    ----------
    profile_state : dict
        Mutable dict holding ``{'key': current_profile_key}``.
        Used to compute addr byte orders at runtime.
    """
    bp = Blueprint('signal_instances', __name__, url_prefix='/api')

    def _addr_byte_order():
        return get_addr_byte_order_for_profile(profile_state['key'])

    def _component_addr_byte_order():
        return get_component_addr_byte_order_for_profile(profile_state['key'])

    @bp.route('/signal_instances', methods=['GET'])
    def get_signal_instances():
        return jsonify(list_signal_instances())

    @bp.route('/signal_instances', methods=['POST'])
    def create_signal_instance():
        data = request.get_json() or {}
        try:
            instance = create_instance(data)
            return jsonify(instance), 201
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except Exception as exc:
            return jsonify({'error': str(exc)}), 500

    @bp.route('/signal_instances/<instance_id>', methods=['GET'])
    def get_signal_instance_detail(instance_id):
        instance = get_instance(instance_id)
        if instance is None:
            return jsonify({'error': '实例不存在'}), 404
        return jsonify(instance)

    @bp.route('/signal_instances/<instance_id>', methods=['PUT'])
    def update_signal_instance(instance_id):
        data = request.get_json() or {}
        try:
            instance = update_instance(instance_id, data)
            return jsonify(instance)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except Exception as exc:
            return jsonify({'error': str(exc)}), 500

    @bp.route('/signal_instances/<instance_id>', methods=['DELETE'])
    def delete_signal_instance(instance_id):
        if delete_instance(instance_id):
            return jsonify({'success': True})
        return jsonify({'error': '实例不存在'}), 404

    @bp.route('/signal_instances/<instance_id>/preview', methods=['POST'])
    def preview_signal_instance(instance_id):
        try:
            result = preview_instance(
                instance_id,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
        except Exception as exc:
            return jsonify({'success': False, 'error': str(exc)}), 500

    @bp.route('/signal_instances/<instance_id>/resolve', methods=['GET'])
    def resolve_signal_instance(instance_id):
        instance = get_instance(instance_id)
        if instance is None:
            return jsonify({'error': '实例不存在'}), 404
        try:
            packet = resolve_instance_packet(
                instance,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
            )
            packet_view = build_packet_view(
                packet,
                addr_byte_order=_addr_byte_order(),
                component_addr_byteorder=_component_addr_byte_order(),
                scene=instance.get('templateId', ''),
                timestamp=now_ms(),
            )
            return jsonify({
                'instanceId': instance_id,
                'templateId': instance.get('templateId', ''),
                'packetHex': packet.hex(),
                'packetLength': len(packet),
                'packetView': packet_view,
            })
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    return bp