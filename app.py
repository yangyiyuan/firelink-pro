#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GBT 26875.3-2011 消防报警数据模拟器 - Web可视化版本
后端服务 (Flask)
"""

import logging
import os
import threading
import time

from flask import Flask, render_template
from flask_socketio import SocketIO

from protocol.simulator import FireAlarmSimulator
from protocol.shared import (
    get_addr_byte_order_for_profile,
    get_component_addr_byte_order_for_profile,
)
from services.api import register_all
from services.history_manager import HistoryManager
from services.connection_manager import ConnectionManager
from services.scene_runner import SceneRunner
from services.network_config import NetworkConfigStore


def is_reloader_process() -> bool:
    return os.environ.get('WERKZEUG_RUN_MAIN') == 'true'


def is_main_process() -> bool:
    return not os.environ.get('WERKZEUG_RUN_MAIN')


logger = logging.getLogger(__name__)

app = Flask(__name__)
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    logger.warning('SECRET_KEY 未通过环境变量设置，使用硬编码后备值 — 生产环境请务必设置 SECRET_KEY')
    _secret_key = 'fire-alarm-simulator-secret-key'
app.config['SECRET_KEY'] = _secret_key
socketio = SocketIO(app, cors_allowed_origins=os.environ.get('CORS_ORIGINS', '*'), async_mode='threading')

# --- Template watcher (dev only) ---
template_last_modified = {}


def watch_templates() -> None:
    import glob

    template_dir = os.path.join(app.root_path, 'templates')
    while True:
        try:
            for filepath in glob.glob(os.path.join(template_dir, '*.html')):
                mtime = os.path.getmtime(filepath)
                filename = os.path.basename(filepath)
                if filename in template_last_modified:
                    if mtime > template_last_modified[filename]:
                        template_last_modified[filename] = mtime
                        socketio.emit('template_changed', {'file': filename})
                else:
                    template_last_modified[filename] = mtime
            time.sleep(1)
        except Exception:
            pass


if is_reloader_process():
    watcher_thread = threading.Thread(target=watch_templates, daemon=True)
    watcher_thread.start()

# --- Service instantiation ---
simulator = FireAlarmSimulator()
history_mgr = HistoryManager(
    maxlen=1000,
    history_dir=os.path.join(os.path.dirname(__file__), 'data', 'history'),
)
network_config_store = NetworkConfigStore()

profile_state = {'key': ''}


def _current_addr_byte_order() -> str:
    return get_addr_byte_order_for_profile(profile_state['key'])


def _current_component_addr_byte_order() -> str:
    return get_component_addr_byte_order_for_profile(profile_state['key'])


connection_mgr = ConnectionManager(
    socketio, history_mgr,
    addr_byte_order_fn=_current_addr_byte_order,
    component_addr_byteorder_fn=_current_component_addr_byte_order,
)
connection_mgr.set_simulator_stats(simulator.stats)

scene_runner = SceneRunner(
    connection_mgr, socketio,
    addr_byte_order_fn=_current_addr_byte_order,
    component_addr_byteorder_fn=_current_component_addr_byte_order,
)
connection_mgr.add_disconnect_callback(scene_runner.stop_all)

# --- Register all API routes and SocketIO handlers ---
services = {
    'simulator': simulator,
    'connection_mgr': connection_mgr,
    'history_mgr': history_mgr,
    'scene_runner': scene_runner,
    'network_config_store': network_config_store,
    'profile_state': profile_state,
}
register_all(app, socketio, services)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() in ('true', '1', 'yes')
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )
    if is_main_process():
        logger.info('=' * 60)
        logger.info('GBT 26875.3-2011 消防报警数据模拟器')
        logger.info('=' * 60)
        logger.info('访问地址: http://127.0.0.1:5001')
        logger.info('热重载模式: %s', '开启' if debug_mode else '关闭')
        if debug_mode:
            logger.info('提示: 修改 app.py 或 templates/*.html 后服务将自动重启')
        logger.info('=' * 60)
    socketio.run(app, host='0.0.0.0', port=5001, debug=debug_mode, use_reloader=debug_mode, allow_unsafe_werkzeug=True)