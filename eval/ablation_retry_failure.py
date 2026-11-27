"""纠错机制定向测试：构造容易触发 SQL 执行错误的场景。

前面的 ablation_retry.py 用的是标准随机题，语义层足够强时模型很少写错 SQL，
两组重试都是 0，看不出纠错的价值。这里用「歧义问题 + 生僻口径」逼出执行错误，
专门验证错误回灌重试是否真的能救回失败请求。

运行：python eval/ablation_retry_failure.py
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))

import cache_service
import sql_service

cache_service.invalidate()

# 这些问法故意不给足信息，模型更容易猜错字段/表名，从而触发执行错误
TRICKY_QUESTIONS = [
    '上个月每个 douyin 渠道的核销率',
    '按 product_type 统计销量',
    '列出 gender 为女的客户订单',
    '各门店的 staff_count 排名',
    '2025年 discount_rate 最高的活动',
    ' vivid 客户的消费总额',
    '按 week 统计订单量',
    '查询 orders 表里 profit 字段的平均值',
    '每个 store_type 的营业额',
    '客户等级为 diamond 的人数',
]


def run() -> None:
    results = {'with_retry': [], 'without_retry': []}
    print(f'纠错定向测试：{len(TRICKY_QUESTIONS)} 道歧义题，专测执行报错后的自动修正')

    for i, q in enumerate(TRICKY_QUESTIONS, 1):
        for mode, enable in [('with_retry', True), ('without_retry', False)]:
            t0 = time.time()
            r = sql_service.generate_and_execute(q, enable_retry=enable, use_cache=False)
            item = {
                'id': i, 'question': q, 'exec_success': r['success'],
                'retries': r['retries'], 'elapsed': round(time.time() - t0, 2),
                'sql': r['sql'], 'message': r['message'][:120],
                'error_type': r['error_type'],
            }
            results[mode].append(item)
            print(f'[{i:02d}/{len(TRICKY_QUESTIONS)}] {mode:<14} '
                  f'{"OK" if r["success"] else "FAIL":<5} retry={r["retries"]} {item["elapsed"]}s')

    summary = {}
    for mode, rs in results.items():
        n = len(rs)
        summary[mode] = {
            'total': n,
            'exec_rate': round(sum(x['exec_success'] for x in rs) / n * 100, 1),
            'total_retries': sum(x['retries'] for x in rs),
            'avg_elapsed': round(sum(x['elapsed'] for x in rs) / n, 2),
        }

    print('\n=== 汇总 ===')
    for k, v in summary.items():
        print(k, v)

    out = ROOT / 'output' / 'eval'
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    (out / f'ablation_retry_failure_{ts}.json').write_text(
        json.dumps({'time': datetime.now().isoformat(timespec='seconds'),
                    'summary': summary, 'details': results}, ensure_ascii=False, indent=2),
        encoding='utf-8')
    print(f'\n结果已写入 output/eval/ablation_retry_failure_{ts}.json')


if __name__ == '__main__':
    run()
