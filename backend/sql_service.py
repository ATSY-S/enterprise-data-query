"""SQL 服务层：生成、纠错、错误分类、失败建议。

对外接口保持兼容（generate / generate_and_execute / classify_error / failure_advice），
新增的开关参数都有默认值，不影响既有调用方和评测脚本。
"""
import logging
import time
from typing import Any

import config
from cache_service import get_cached, set_cached
from llm_client import chat, build_messages, clean_sql
from tools import execute_sql

logger = logging.getLogger('sql_service')

RETRYABLE = ('no such column', 'no such table', 'ambiguous column', 'near ', 'syntax error')
FATAL = ('only select', 'not allowed', '不允许多条', '只允许 select', '检测到写操作')


def classify_error(msg: str) -> str:
    """错误分类：安全类立即拒绝，语法/字段类可重试。"""
    low = msg.lower()
    if any(k in low or k in msg for k in FATAL):
        return 'security'
    if any(k in low for k in RETRYABLE):
        return 'syntax_or_schema'
    return 'unknown'


def failure_advice(question: str, error_type: str, message: str) -> str:
    """给用户可操作的失败建议，不扔裸报错。"""
    if error_type == 'security':
        return '系统拒绝了这条查询，因为包含写操作或多条语句。本系统只允许读取数据，请换一个查询类问题。'
    if error_type == 'syntax_or_schema':
        return (f'模型生成的 SQL 多次执行失败（{message}）。建议：'
                '①把问题说得更具体，例如指明"按地区"或"按月份"；'
                '②在「指标口径」页面确认字段名；③打开"先确认 SQL"开关手动核对。')
    return f'查询未能完成：{message}。建议换一种问法，或联系管理员确认数据源配置。'


def generate(question: str, prune_schema: bool = False) -> dict[str, Any]:
    """只生成 SQL，不执行。"""
    t0 = time.time()
    sql = clean_sql(chat(build_messages(question, prune_schema=prune_schema)))
    return {'question': question, 'sql': sql, 'elapsed': round(time.time() - t0, 2)}


def execute_sql_cached(sql: str) -> dict[str, Any]:
    """先查缓存，未命中再执行并回填。"""
    hit = get_cached(sql)
    if hit is not None:
        return {**hit, 'from_cache': True}
    result = execute_sql(sql)
    if result['success']:
        set_cached(sql, result)
    return {**result, 'from_cache': False}


def generate_and_execute(
    question: str,
    enable_retry: bool = True,
    prune_schema: bool = False,
    use_cache: bool = True,
) -> dict[str, Any]:
    """完整闭环：生成 → 执行 → 分类重试。

    enable_retry=False 用于纠错消融实验（关掉自动修正）；
    prune_schema 默认关闭——实测裁剪会掉正确率（100%→86.7%），
    仅作为可开关的实验特性保留；use_cache 默认开启。
    """
    t0 = time.time()
    messages = build_messages(question, prune_schema=prune_schema)
    max_retries = config.MAX_SQL_RETRIES if enable_retry else 0
    sql = ''
    result: dict[str, Any] = {
        'success': False, 'data': [], 'columns': [], 'row_count': 0, 'message': ''
    }
    retries = 0
    error_type = None
    used_cache = False

    for attempt in range(max_retries + 1):
        sql = clean_sql(chat(messages))
        if use_cache:
            result = execute_sql_cached(sql)
            used_cache = result.get('from_cache', False)
        else:
            result = execute_sql(sql)
        if result['success']:
            break
        error_type = classify_error(result['message'])
        if error_type == 'security' or not enable_retry:
            break
        if attempt == max_retries:
            break
        # 只有真正要回灌模型重试时才计数
        retries = attempt + 1
        messages.append({'role': 'assistant', 'content': sql})
        messages.append({
            'role': 'user',
            'content': f'上一条 SQL 执行失败：{result["message"]}。请根据错误修正 SQL，只输出修正后的 SQL。',
        })

    return {
        'sql': sql,
        'success': result['success'],
        'columns': result['columns'],
        'data': result['data'],
        'row_count': result['row_count'],
        'retries': retries,
        'error_type': error_type,
        'elapsed': round(time.time() - t0, 2),
        'message': result['message'],
        'advice': '' if result['success'] else failure_advice(question, error_type, result['message']),
        'from_cache': used_cache,
    }
