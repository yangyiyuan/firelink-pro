#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Blueprint registry — registers all Flask blueprints and SocketIO handlers."""

from services.api.scenes_bp import create_scenes_bp
from services.api.history_bp import create_history_bp
from services.api.signal_instances_bp import create_signal_instances_bp
from services.api.auto_send_bp import create_auto_send_bp
from services.api.network_configs_bp import create_network_configs_bp
from services.api.profiles_bp import create_profiles_bp
from services.api.connection_bp import create_connection_bp
from services.api.socketio_events import register_socketio_events


def register_all(app, socketio, services):
    """Register every Blueprint on *app* and every SocketIO handler on *socketio*.

    Parameters
    ----------
    app : Flask
    socketio : SocketIO
    services : dict
        Expected keys (all required):

        - ``simulator``             — FireAlarmSimulator
        - ``connection_mgr``        — ConnectionManager
        - ``history_mgr``           — HistoryManager
        - ``scene_runner``          — SceneRunner
        - ``network_config_store``  — NetworkConfigStore
        - ``profile_state``         — dict ``{'key': current_profile_key}``
                                      (mutable — the PUT /api/profile handler
                                      updates it in-place so app.py stays
                                      synchronised)
    """
    # --- Flask Blueprints ---
    app.register_blueprint(create_scenes_bp(
        simulator=services['simulator'],
        history_mgr=services['history_mgr'],
    ))

    app.register_blueprint(create_history_bp(
        history_mgr=services['history_mgr'],
        app=app,
    ))

    app.register_blueprint(create_signal_instances_bp(
        profile_state=services['profile_state'],
        simulator=services['simulator'],
    ))

    app.register_blueprint(create_auto_send_bp(
        profile_state=services['profile_state'],
    ))

    app.register_blueprint(create_network_configs_bp(
        network_config_store=services['network_config_store'],
    ))

    app.register_blueprint(create_profiles_bp(
        profile_state=services['profile_state'],
        simulator=services['simulator'],
        socketio=socketio,
    ))

    app.register_blueprint(create_connection_bp(
        connection_mgr=services['connection_mgr'],
    ))

    # --- SocketIO event handlers ---
    register_socketio_events(socketio, services)