#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blueprint: profile read / update routes"""

from flask import Blueprint, jsonify, request

from protocol.core import GBT26875Packet
from protocol.shared import (
    AVAILABLE_PROFILES,
    get_addr_byte_order_for_profile,
    get_component_addr_byte_order_for_profile,
)
from services.api.response_utils import error_response


def create_profiles_bp(profile_state, simulator, socketio):
    """Create and return the profiles Blueprint.

    Parameters
    ----------
    profile_state : dict
        Mutable dict ``{'key': current_profile_key}``.
        Mutated in-place on PUT so app.py sees the change.
    simulator : FireAlarmSimulator
        Its ``packet_builder`` is rebuilt on profile change.
    socketio : SocketIO
        Used to broadcast ``profile_changed`` event.
    """
    bp = Blueprint('profiles', __name__, url_prefix='/api')

    def _addr_byte_order():
        return get_addr_byte_order_for_profile(profile_state['key'])

    def _component_addr_byte_order():
        return get_component_addr_byte_order_for_profile(profile_state['key'])

    @bp.route('/profiles', methods=['GET'])
    def get_profiles():
        return jsonify(AVAILABLE_PROFILES)

    @bp.route('/profile', methods=['GET'])
    def get_current_profile():
        addr_order = _addr_byte_order()
        component_addr_order = _component_addr_byte_order()
        return jsonify({
            'key': profile_state['key'],
            'addr_byte_order': addr_order,
            'component_addr_byte_order': component_addr_order,
        })

    @bp.route('/profile', methods=['PUT'])
    def set_current_profile():
        data = request.get_json(silent=True) or {}
        key = data.get('key', '')
        valid_keys = [p['key'] for p in AVAILABLE_PROFILES]
        if key not in valid_keys:
            return error_response(f'无效的 profile key: {key}')

        # Mutate the shared profile_state dict in-place so app.py
        # (and the addr_byte_order closures) pick up the new value.
        profile_state['key'] = key

        addr_order = _addr_byte_order()
        component_addr_order = _component_addr_byte_order()

        # Rebuild simulator.packet_builder with the new byte order
        simulator.packet_builder = GBT26875Packet(
            source_addr=simulator.packet_builder.source_addr,
            dest_addr=simulator.packet_builder.dest_addr,
            command=simulator.packet_builder.command,
            addr_byte_order=addr_order,
        )

        socketio.emit('profile_changed', {
            'key': profile_state['key'],
            'addr_byte_order': addr_order,
            'component_addr_byte_order': component_addr_order,
        })

        return jsonify({
            'key': profile_state['key'],
            'addr_byte_order': addr_order,
            'component_addr_byte_order': component_addr_order,
        })

    return bp