"""Agent 核心：DeepSeek 生成 SQL → 只读执行 → 出错自动回灌修正。
不用复杂 Agent 框架，直接调 API + 一个循环。原理简单，答辩好讲。
"""
import json
import time
from openai import OpenAI

import config
from semantic import schema_text
from tools import (execute_sql, get_statistics, generate_chart,
                   export_to_excel, export_to_csv, save_history)

client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)

SYSTEM_PROMPT = '''你是一个企业数据查询助手。用户用中文提问，你只输出一条 SQLite SELECT 语句，不要输出任何解释、注释或 Markdown。

{schema}

规则：
1. 只输出 SELECT 或 WITH 开头的单条语句，以分号结尾。
2. 禁止 INSERT/UPDATE/DELETE/DROP 等任何写操作。
3. 用户提到业务术语时，严格按上面的指标口径计算。
4. 涉及百分比时，分子分母的数据类型要处理好，避免整数除法。
5. 不确定用户说的"地区"是哪张表时，按上面字段说明选。'''.format(schema=schema_text())


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


def query(question: str, want_chart: bool = True, want_export: bool = False) -> dict:
    """一次完整查询：生成 → 执行 → 失败自动修正 → 统计/图表/导出。"""
    t0 = time.time()
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': question},
    ]
    sql = ''
    result = {'success': False, 'data': [], 'columns': [], 'row_count': 0, 'message': ''}
    retries = 0

    for attempt in range(config.MAX_SQL_RETRIES + 1):
        raw = _call_llm(messages)
        sql = _clean_sql(raw)
        result = execute_sql(sql)
        if result['success']:
            break
        retries = attempt + 1
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
        'elapsed': round(time.time() - t0, 2),
        'message': result['message'],
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
    r = query(q, want_chart=True)
    print(json.dumps({k: v for k, v in r.items() if k != 'data'}, ensure_ascii=False, indent=2))
    print('前3行:', r['data'][:3])
