#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一 API 响应格式工具"""

from flask import jsonify


def success_response(data=None, status_code=200, **kwargs):
    """统一成功响应格式。

    Parameters
    ----------
    data : dict, optional
        要合并到响应中的数据字段。
    status_code : int
        HTTP 状态码，默认 200。创建资源时可用 201。
    **kwargs
        额外的键值对，直接合并到响应中。

    Returns
    -------
    flask.Response or tuple[flask.Response, int]
        status_code 为 200 时返回 Response，其他状态码返回 (Response, status_code)。
    """
    result = {'success': True}
    if data is not None:
        result.update(data)
    result.update(kwargs)
    if status_code == 200:
        return jsonify(result)
    return jsonify(result), status_code


def error_response(message, status_code=400, **kwargs):
    """统一错误响应格式。

    Parameters
    ----------
    message : str
        错误描述信息。
    status_code : int
        HTTP 状态码，默认 400。
    **kwargs
        额外的键值对，直接合并到响应中。

    Returns
    -------
    tuple[flask.Response, int]
        (JSON 响应, HTTP 状态码)。
    """
    result = {'success': False, 'error': message}
    result.update(kwargs)
    return jsonify(result), status_code