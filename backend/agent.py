"""Agent 核心：DeepSeek 生成 SQL → 只读执行 → 分类纠错。

设计取舍：
- 重试不是越多越好。语法/字段错误可自动修，安全类错误立即拒绝，语义问题交回用户。
- 提供 preview_only 模式：只生成 SQL 不执行，供用户在界面上确认（Human-in-the-loop）。
- 失败时返回可操作的建议，而不是一句报错。
"""
import json
import time
import logging
from openai import OpenAI

import config
from semantic import schema_text
from tools import (execute_sql, get_statistics, generate_chart,
                   export_to_excel, save_history)

logger = logging.getLogger('agent')
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)

SYSTEM_PROMPT = '''你是一个企业数据查询助手。用户用中文提问，你只输出一条 SQLite SELECT 语句，不要输出任何解释、注释或 Markdown。

{schema}

规则：
1. 只输出 SELECT 或 WITH 开头的单条语句，以分号结尾。
2. 禁止 INSERT/UPDATE/DELETE/DROP 等任何写操作。
3. 用户提到业务术语时，严格按上面的指标口径计算。
4. 涉及百分比时，分子分母的数据类型要处理好，避免整数除法。
5. 不确定用户说的"地区"是哪张表时，按上面字段说明选。'''.format(schema=schema_text())

# 错误分类：决定重试策略
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
    """失败兜底：告诉用户哪里出错、建议怎么问。"""
    if error_type == 'security':
        return '系统拒绝了这条查询，因为包含写操作或多条语句。本系统只允许读取数据，请换一个查询类问题。'
    if error_type == 'syntax_or_schema':
        return (f'模型生成的 SQL 多次执行失败（{message}）。建议：'
                '①把问题说得更具体，例如指明"按品类"或"按月份"；'
                '②在「指标口径」页面确认字段名；③点击"查看 SQL"手动核对后重试。')
    return f'查询未能完成：{message}。建议换一种问法，或联系管理员确认数据源配置。'


def _call_llm(messages):
    resp = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=messages,
        temperature=config.LLM_TEMPERATURE,
    )
    return resp.choices[0].message.content.strip()


def _clean_sql(text: str) -> str:
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    return text.rstrip(';') + ';'


def generate_sql(question: str) -> dict:
    """只生成 SQL，不执行。用于 SQL 预览与人工确认。"""
    t0 = time.time()
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': question},
    ]
    sql = _clean_sql(_call_llm(messages))
    return {'question': question, 'sql': sql, 'elapsed': round(time.time()-t0, 2)}


def query(question: str, want_chart: bool = True, want_export: bool = False) -> dict:
    """完整流程：生成 → 执行 → 分类纠错 → 统计/图表/导出。"""
    t0 = time.time()
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': question},
    ]
    sql = ''
    result = {'success': False, 'data': [], 'columns': [], 'row_count': 0, 'message': ''}
    retries = 0
    error_type = None

    for attempt in range(config.MAX_SQL_RETRIES + 1):
        raw = _call_llm(messages)
        sql = _clean_sql(raw)
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

    out = {
        'question': question,
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

    if result['success'] and result['data']:
        data_json = json.dumps(result['data'], ensure_ascii=False)
        stats = get_statistics(data_json)
        out['statistics'] = stats.get('data', {})
        if want_chart:
            chart = generate_chart(data_json, title=question[:20])
            if chart['success']:
                out['chart_path'] = chart['path']
        if want_export:
            exp = export_to_excel(data_json)
            if exp['success']:
                out['export_path'] = exp['path']

    save_history(question, sql, out['success'], out['row_count'], out['elapsed'])
    return out


if __name__ == '__main__':
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else '各品类的销售额是多少？'
    r = query(q)
    print(json.dumps({k: v for k, v in r.items() if k != 'data'}, ensure_ascii=False, indent=2))
