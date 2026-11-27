"""A/B 对照实验：有自动纠错 vs 无自动纠错，各跑 30 道随机题。

论文第 5 章第二组消融，回答「错误回灌重试到底有没有用」。
两组使用完全相同的题目、语义层、提示词，唯一差异是 enable_retry。
判定用标准答案逐格比对（oracle），不是只看 SQL 能不能跑。

运行：python eval/ablation_retry.py eval/cases_random.json
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
import eval_with_oracle as eo

cache_service.invalidate()  # 评测必须走真实模型调用，避免缓存污染


def run(case_file: Path, limit: int | None = None) -> None:
    data = json.load(open(case_file, encoding='utf-8'))
    cases = data['cases'][:limit] if limit else data['cases']
    results = {'with_retry': [], 'without_retry': []}

    print(f'纠错消融：{len(cases)} 题，两组题目/语义层相同，仅差自动纠错')
    for i, c in enumerate(cases, 1):
        for mode, enable in [('with_retry', True), ('without_retry', False)]:
            t0 = time.time()
            r = sql_service.generate_and_execute(
                c['question'], enable_retry=enable, use_cache=False
            )
            if r['success'] and r['data']:
                try:
                    # execute_sql 返回的 data 已是 dict 列表，直接传给 compare
                    match, detail = eo.compare(r['data'], c['expected'])
                except Exception as e:
                    match, detail = False, f'比对出错: {e}'
            else:
                match, detail = False, 'SQL执行失败'

            item = {
                'id': c['id'], 'question': c['question'], 'category': c.get('category', ''),
                'exec_success': r['success'], 'match': match, 'detail': detail,
                'retries': r['retries'], 'elapsed': round(time.time() - t0, 2),
                'sql': r['sql'], 'error_type': r['error_type'],
            }
            results[mode].append(item)
            print(f'[{i:02d}/{len(cases)}] {c["id"]:<4} {mode:<14} '
                  f'{"PASS" if match else "FAIL":<5} retry={r["retries"]} {item["elapsed"]}s')

    summary = {}
    for mode, rs in results.items():
        n = len(rs)
        summary[mode] = {
            'total': n,
            'exec_rate': round(sum(x['exec_success'] for x in rs) / n * 100, 1),
            'accuracy': round(sum(x['match'] for x in rs) / n * 100, 1),
            'avg_retries': round(sum(x['retries'] for x in rs) / n, 2),
            'avg_elapsed': round(sum(x['elapsed'] for x in rs) / n, 2),
        }

    print('\n=== 汇总 ===')
    for k, v in summary.items():
        print(k, v)

    out = ROOT / 'output' / 'eval'
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    (out / f'ablation_retry_{ts}.json').write_text(
        json.dumps({
            'time': datetime.now().isoformat(timespec='seconds'),
            'case_file': str(case_file),
            'summary': summary,
            'details': results,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n结果已写入 output/eval/ablation_retry_{ts}.json')


if __name__ == '__main__':
    case_file = ROOT / (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith('.json')
                        else 'eval/cases_random.json')
    run(case_file, int(sys.argv[2]) if len(sys.argv) > 2 else None)
