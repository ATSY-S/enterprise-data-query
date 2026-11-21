"""SQL 服务层：生成、纠错、错误分类、失败建议。"""
import logging
import time
import config
from llm_client import chat, build_messages, clean_sql
from tools import execute_sql

logger = logging.getLogger('sql_service')

RETRYABLE = ('no such column', 'no such table', 'ambiguous column', 'near ', 'syntax error')
FATAL = ('only select', 'not allowed', '不允许多条', '只允许 select', '检测到写操作')


def classify_error(msg: str) -> str:
    low = msg.lower()
    if any(k in low or k in msg for k in FATAL):
        return 'security'
    if any(k in low for k in RETRYABLE):
        return 'syntax_or_schema'
    return 'unknown'


def failure_advice(question: str, error_type: str, message: str) -> str:
    if error_type == 'security':
        return '系统拒绝了这条查询，因为包含写操作或多条语句。本系统只允许读取数据，请换一个查询类问题。'
    if error_type == 'syntax_or_schema':
        return (f'模型生成的 SQL 多次执行失败（{message}）。建议：'
                '①把问题说得更具体，例如指明"按地区"或"按月份"；'
                '②在「指标口径」页面确认字段名；③打开"先确认 SQL"开关手动核对。')
    return f'查询未能完成：{message}。建议换一种问法，或联系管理员确认数据源配置。'


def generate(question: str) -> dict:
    """只生成 SQL，不执行。"""
    t0 = time.time()
    sql = clean_sql(chat(build_messages(question)))
    return {'question': question, 'sql': sql, 'elapsed': round(time.time() - t0, 2)}


def generate_and_execute(question: str) -> dict:
    """完整纠错闭环：生成 → 执行 → 分类重试。"""
    t0 = time.time()
    messages = build_messages(question)
    sql = ''
    result = {'success': False, 'data': [], 'columns': [], 'row_count': 0, 'message': ''}
    retries = 0
    error_type = None

    for attempt in range(config.MAX_SQL_RETRIES + 1):
        sql = clean_sql(chat(messages))
        result = execute_sql(sql)
        if result['success']:
            break
        retries = attempt + 1
        error_type = classify_error(result['message'])
        if error_type == 'security':
            logger.warning('安全拦截，停止重试: %s | %s', sql, result['message'])
            break
        if attempt == config.MAX_SQL_RETRIES:
            break
        messages.append({'role': 'assistant', 'content': sql})
        messages.append({'role': 'user', 'content':
                         f'上一条 SQL 执行失败：{result["message"]}。请根据错误修正 SQL，只输出修正后的 SQL。'})

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
    }
