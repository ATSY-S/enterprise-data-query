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
from llm_client import clean_sql

QUESTIONS = json.load(open(ROOT / 'eval' / 'questions.json', encoding='utf-8'))
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)

# 对照组：表结构与实验组完全一致，只去掉「指标口径 / 关联关系 / 业务术语」。
# 这样才能保证差异只来自语义层，而不是表结构本身。
BARE_SCHEMA = '''数据库为 SQLite，共 8 张表。只允许 SELECT，禁止任何 DML/DDL。

表结构：
stores(id, store_name, region, city, store_level)
employees(id, name, store_id, role)
customers(id, customer_name, customer_type, member_level, city, register_date)
products(id, product_name, category, unit_price, cost_price)
activities(id, activity_name, channel, start_date, end_date, budget)
coupons(id, activity_id, customer_id, store_id, receive_date, verify_date, status, discount_amount)
orders(id, order_no, order_date, customer_id, store_id, employee_id, total_amount, discount_amount, actual_amount, status, payment_method)
order_items(id, order_id, product_id, quantity, unit_price, subtotal)

只输出一条 SELECT 语句，不要解释。'''

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
        sql = clean_sql(resp.choices[0].message.content)
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


def run_with_oracle(case_file, limit=None):
    """消融 + 正确性判定：两组用相同题目，各自结果与 oracle 比对。"""
    import eval_with_oracle as eo
    data = json.load(open(case_file, encoding='utf-8'))
    cases = data['cases'][:limit] if limit else data['cases']
    results = {'with_semantic': [], 'without_semantic': []}
    print(f'消融+正确性判定：{len(cases)} 题，两组表结构相同，仅差语义层')

    for c in cases:
        for mode, schema in [('with_semantic', schema_text()), ('without_semantic', BARE_SCHEMA)]:
            r = one(c['question'], schema, mode == 'with_semantic')
            if r['success']:
                # one() 没保留 data，这里重新取一次用于比对会造成额外开销；
                # 故用 oracle_sql 直接查标准结果集，只比对执行成功与否之外的行数据
                import sqlite3
                conn = sqlite3.connect(ROOT / 'data' / 'enterprise.db')
                rows = conn.execute(r['sql']).fetchall()
                conn.close()
                match, detail = eo.compare([dict(zip([f'c{i}' for i in range(len(rows[0]))], row)) for row in rows],
                                           c['expected']) if rows else (False, '无结果')
            else:
                match, detail = False, 'SQL执行失败'
            r.update({'id': c['id'], 'match': match, 'detail': detail})
            results[mode].append(r)

    summary = {}
    for mode, rs in results.items():
        n = len(rs)
        summary[mode] = {
            'total': n,
            'exec_rate': round(sum(x['success'] for x in rs) / n * 100, 1),
            'accuracy': round(sum(x['match'] for x in rs) / n * 100, 1),
            'avg_elapsed': round(sum(x['elapsed'] for x in rs) / n, 2),
        }
    print('\n=== 汇总 ===')
    for k, v in summary.items():
        print(k, v)
    out = ROOT / 'output' / 'eval'
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    (out / f'ablation_oracle_{ts}.json').write_text(
        json.dumps({'time': datetime.now().isoformat(timespec='seconds'),
                    'case_file': str(case_file), 'summary': summary, 'details': results},
                   ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].endswith('.json'):
        run_with_oracle(ROOT / sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
