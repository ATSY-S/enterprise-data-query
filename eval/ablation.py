"""A/B 对照实验：有语义层 vs 无语义层，各跑 30 道题。
论文第 5 章用这个结果回答「指标口径词典到底有没有用」。
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

import config
from semantic import schema_text
from tools import execute_sql
from agent import _clean_sql

QUESTIONS = json.load(open(ROOT / 'eval' / 'questions.json', encoding='utf-8'))
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)

BARE_SCHEMA = '''数据库表：
orders(id, order_date, store_id, category, product_name, region, sales_amount, quantity)
activities(id, activity_name, channel, start_date, end_date, budget)
coupons(id, activity_id, store_id, receive_date, verify_date, status)
stores(id, store_name, region, city)
只输出一条 SELECT 语句。'''

PROMPT = '''你是一个企业数据查询助手。只输出一条 SQLite SELECT 语句，不要解释。

{schema}
'''


def one(question, schema, use_semantic):
    system = PROMPT.format(schema=schema)
    t0 = time.time()
    messages = [{'role':'system','content':system}, {'role':'user','content':question}]
    sql, result, retries = '', None, 0
    for attempt in range(config.MAX_SQL_RETRIES + 1):
        resp = client.chat.completions.create(model=config.DEEPSEEK_MODEL, messages=messages, temperature=0)
        sql = _clean_sql(resp.choices[0].message.content)
        result = execute_sql(sql)
        if result['success']:
            break
        retries = attempt + 1
        if attempt == config.MAX_SQL_RETRIES:
            break
        messages.append({'role':'assistant','content':sql})
        messages.append({'role':'user','content':f'SQL 执行失败：{result["message"]}。请修正后只输出 SQL。'})
    return {
        'success': result['success'] and result['row_count'] > 0,
        'retries': retries,
        'elapsed': round(time.time()-t0, 2),
        'rows': result['row_count'],
        'sql': sql,
    }


def run(limit=None):
    qs = QUESTIONS[:limit] if limit else QUESTIONS
    results = {'with_semantic': [], 'without_semantic': []}
    for i, q in enumerate(qs, 1):
        for mode, schema in [('with_semantic', schema_text()), ('without_semantic', BARE_SCHEMA)]:
            r = one(q['question'], schema, mode=='with_semantic')
            r['id'] = q['id']
            r['category'] = q['category']
            results[mode].append(r)
            print(f"[{i:02d}/{len(qs)}] {q['id']:<4} {mode:<16} "
                  f"{'OK' if r['success'] else 'FAIL':<5} retry={r['retries']} {r['elapsed']}s")

    summary = {}
    for mode, rs in results.items():
        n = len(rs)
        summary[mode] = {
            'total': n,
            'passed': sum(r['success'] for r in rs),
            'success_rate': round(sum(r['success'] for r in rs)/n*100, 1),
            'avg_retries': round(sum(r['retries'] for r in rs)/n, 2),
            'avg_elapsed': round(sum(r['elapsed'] for r in rs)/n, 2),
        }
    report = {'time': datetime.now().isoformat(timespec='seconds'),
              'summary': summary, 'details': results}
    out = ROOT / 'output' / 'eval'
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    (out / f'ablation_{ts}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\n=== 汇总 ===')
    for k, v in summary.items():
        print(k, v)


if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
