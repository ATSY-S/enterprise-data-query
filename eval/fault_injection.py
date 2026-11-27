"""故障注入实验：验证纠错机制在 SQL 真的报错时能否自动恢复。

为什么需要这个实验：
前面的纠错消融用正常题，模型生成的 SQL 都能执行（重试触发 0 次），
所以测不出纠错的价值。故障注入直接喂入错误 SQL，测的是容错机制本身，
这是工程上验证可靠性的标准做法。

做法：
1. 构造 5 类典型错误 SQL（字段不存在、表名错误、聚合歧义、语法错误、类型不匹配）
2. 每组用同一条错误 SQL，分别跑「有纠错」和「无纠错」
3. 记录：无纠错组是否失败、有纠错组是否恢复、用了几次重试

边界说明：本实验验证的是「容错机制本身是否可靠」，故障由人为注入，
不代表真实使用中的错误发生率，也不能用来论证日常查询准确率的提升。
这与常规题评测（ablation_retry.py）是两个不同维度，需分开陈述。

运行：python eval/fault_injection.py
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

import config
from llm_client import chat, clean_sql
from tools import execute_sql
from sql_service import classify_error

PROMPT = '''你是一个企业数据查询助手。用户用中文提问，你只输出一条 SQLite SELECT 语句，不要输出解释、注释或 Markdown。

{schema}

规则：
1. 只输出 SELECT 或 WITH 开头的单条语句，以分号结尾。
2. 禁止 INSERT/UPDATE/DELETE/DROP 等任何写操作。
3. 用户提到业务术语时，严格按上面的指标口径计算。
4. 涉及百分比时，分子分母的数据类型要处理好，避免整数除法。
5. 不确定字段属于哪张表时，严格按上面的关联关系选择。'''

from semantic import schema_text
SYSTEM = PROMPT.format(schema=schema_text())

# (描述, 用户问题, 故意写错的 SQL)
FAULTS = [
    ('字段名错误', '统计已完成订单的总销售额',
     "SELECT SUM(sales_amount) FROM orders WHERE status='已完成';"),
    ('表名错误', '查询各品类的销售额',
     "SELECT category, SUM(sales_amount) FROM sales GROUP BY category;"),
    ('列歧义', '查询订单和客户关联后的订单号',
     'SELECT id, customer_name FROM orders JOIN customers ON orders.customer_id=customers.id;'),
    ('语法错误', '统计订单数量',
     'SELECT COUNT(* FROM orders;'),
    ('不存在的聚合列', '查询各门店平均订单金额',
     'SELECT store_id, AVG(amount) FROM orders GROUP BY store_id;'),
]


def run_fault(question: str, wrong_sql: str, enable_retry: bool) -> dict:
    """把错误 SQL 作为模型的上一条输出，让它在报错后修正。"""
    messages = [
        {'role': 'system', 'content': SYSTEM},
        {'role': 'user', 'content': question},
        {'role': 'assistant', 'content': wrong_sql},
    ]
    t0 = time.time()
    max_rounds = config.MAX_SQL_RETRIES if enable_retry else 1
    retries = 0
    result = {'success': False, 'message': ''}
    sql = wrong_sql

    for _ in range(max_rounds):
        # 第一次直接执行注入的错误 SQL，之后回灌错误让模型修正
        if retries > 0:
            sql = clean_sql(chat(messages))
        result = execute_sql(sql)
        if result['success']:
            break
        error_type = classify_error(result['message'])
        if error_type == 'security':
            break
        retries += 1  # 只有确实要回灌重试时才计数
        messages.append({'role': 'assistant', 'content': sql})
        messages.append({
            'role': 'user',
            'content': f'上一条 SQL 执行失败：{result["message"]}。请根据表结构修正，只输出修正后的 SQL。',
        })

    return {
        'success': result['success'],
        'retries': retries,
        'elapsed': round(time.time() - t0, 2),
        'final_sql': sql,
        'message': result['message'][:100],
        'rows': result.get('row_count', 0),
    }


def run() -> None:
    results = {'with_retry': [], 'without_retry': []}
    print(f'故障注入：{len(FAULTS)} 类错误 SQL，测纠错机制能否自动恢复\n')

    for i, (name, question, wrong_sql) in enumerate(FAULTS, 1):
        for mode, enable in [('without_retry', False), ('with_retry', True)]:
            r = run_fault(question, wrong_sql, enable)
            r.update({'id': i, 'fault': name, 'question': question, 'injected_sql': wrong_sql})
            results[mode].append(r)
            print(f'[{i:02d}] {name:<12} {mode:<14} '
                  f'{"恢复成功" if r["success"] else "仍失败":<8} '
                  f'重试={r["retries"]} {r["elapsed"]}s')
        print()

    summary = {}
    for mode, rs in results.items():
        n = len(rs)
        summary[mode] = {
            'total': n,
            'recovered': sum(r['success'] for r in rs),
            'recovery_rate': round(sum(r['success'] for r in rs) / n * 100, 1),
            'avg_retries': round(sum(r['retries'] for r in rs) / n, 2),
            'avg_elapsed': round(sum(r['elapsed'] for r in rs) / n, 2),
        }

    print('=== 汇总 ===')
    for k, v in summary.items():
        print(k, v)

    out = ROOT / 'output' / 'eval'
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    (out / f'fault_injection_{ts}.json').write_text(
        json.dumps({'time': datetime.now().isoformat(timespec='seconds'),
                    'summary': summary, 'details': results}, ensure_ascii=False, indent=2),
        encoding='utf-8')
    print(f'\n结果已写入 output/eval/fault_injection_{ts}.json')


if __name__ == '__main__':
    run()
