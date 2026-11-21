"""带标准答案判定的评测器。

与旧版 run_eval.py 的区别：
- 旧版：SQL 执行成功且返回行数>0 就算通过（结果错了也算过）
- 新版：把模型结果和预生成的标准答案逐格比对，数字容差 1%，列表按顺序比

用法：
  python eval/generate_cases.py --count 30 --seed 42
  python eval/eval_with_oracle.py eval/cases_random.json
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
from query_service import query


def normalize(v):
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, str):
        return v.strip()
    return v


def close(a, b, tol=0.01):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if b == 0:
            return abs(a) < 1e-6
        return abs(a - b) / abs(b) <= tol
    return normalize(a) == normalize(b)


def compare(actual_rows, expected, tolerance=0.01):
    if isinstance(expected, list):
        if len(actual_rows) != len(expected):
            return False, f'行数 {len(actual_rows)} != {len(expected)}'
        for i, exp_row in enumerate(expected):
            act_row = actual_rows[i]
            if isinstance(exp_row, list) and isinstance(act_row, dict):
                vals = list(act_row.values())
            else:
                vals = act_row
            if len(vals) != len(exp_row):
                return False, f'第{i+1}行列数不符'
            for a, e in zip(vals, exp_row):
                if not close(a, e, tolerance):
                    return False, f'第{i+1}行: {a} != {e}'
        return True, '完全一致'
    if not actual_rows:
        return False, '无结果'
    val = list(actual_rows[0].values())[0]
    if not close(val, expected, tolerance):
        return False, f'{val} != {expected}'
    return True, f'{val} ≈ {expected}'


def run(case_file, limit=None):
    data = json.load(open(case_file, encoding='utf-8'))
    cases = data['cases'][:limit] if limit else data['cases']
    results = []
    print(f'题目数量：{len(cases)}  (seed={data.get("seed")})')
    print(f'判定标准：SQL 可执行 + 结果与标准答案逐格比对（数值容差 1%）\n')

    for i, c in enumerate(cases, 1):
        t0 = time.time()
        r = query(c['question'], want_chart=False)
        exec_ok = r['success']
        match, detail = (False, 'SQL 执行失败') if not exec_ok else compare(r['data'], c['expected'])
        rec = {
            'id': c['id'], 'category': c['category'], 'question': c['question'],
            'expected': c['expected'], 'actual': r['data'][:5],
            'sql': r['sql'], 'exec_ok': exec_ok, 'match': match,
            'detail': detail, 'retries': r['retries'],
            'elapsed': round(time.time() - t0, 2),
        }
        results.append(rec)
        print(f"[{i:02d}/{len(cases)}] {c['id']} {c['category']:<5} "
              f"{'PASS' if match else 'FAIL':<4} {detail[:40]:<40} {rec['elapsed']}s")

    total = len(results)
    exec_passed = sum(x['exec_ok'] for x in results)
    correct = sum(x['match'] for x in results)
    report = {
        'time': datetime.now().isoformat(timespec='seconds'),
        'case_file': str(case_file), 'seed': data.get('seed'),
        'judge': 'SQL 可执行 + 结果与 oracle 逐格比对，数值容差 1%',
        'total': total, 'exec_success': exec_passed,
        'exec_success_rate': round(exec_passed / total * 100, 1),
        'correct': correct, 'accuracy': round(correct / total * 100, 1),
        'avg_retries': round(sum(x['retries'] for x in results) / total, 2),
        'results': results,
    }
    out = ROOT / 'output' / 'eval'
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    (out / f'oracle_eval_{ts}.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSQL 可执行率 {exec_passed}/{total} = {report['exec_success_rate']}%")
    print(f"结果正确率   {correct}/{total} = {report['accuracy']}%")


if __name__ == '__main__':
    f = sys.argv[1] if len(sys.argv) > 1 else 'eval/cases_random.json'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run(ROOT / f, limit)
