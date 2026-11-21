"""评测脚本：30 道题，统计执行成功率、重试次数、耗时。
论文第 5 章的实验结果就来自这个脚本。
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))
import agent as agent_module
from tools import execute_sql

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = json.load(open(ROOT / 'eval' / 'questions.json', encoding='utf-8'))


def run(limit=None):
    questions = QUESTIONS[:limit] if limit else QUESTIONS
    results = []
    print(f'题目数量：{len(questions)}')
    for i, q in enumerate(questions, 1):
        t0 = time.time()
        r = agent_module.query(q['question'], want_chart=False)
        ok = r['success'] and r['row_count'] > 0
        rec = {
            'id': q['id'], 'category': q['category'], 'question': q['question'],
            'success': ok, 'sql': r['sql'], 'retries': r['retries'],
            'rows': r['row_count'], 'elapsed': round(time.time() - t0, 2),
        }
        results.append(rec)
        print(f"[{i:02d}/{len(questions)}] {q['id']} {q['category']:<6} "
              f"{'OK' if ok else 'FAIL'}  {rec['elapsed']}s  重试{rec['retries']}")
    total = len(results)
    passed = sum(x['success'] for x in results)
    report = {
        'time': datetime.now().isoformat(timespec='seconds'),
        'total': total,
        'passed': passed,
        'success_rate': round(passed / total * 100, 1),
        'avg_elapsed': round(sum(x['elapsed'] for x in results) / total, 2),
        'total_retries': sum(x['retries'] for x in results),
        'results': results,
    }
    out = ROOT / 'output' / 'eval'
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    (out / f'eval_{ts}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n通过 {passed}/{total}，成功率 {report['success_rate']}%，"
          f"平均 {report['avg_elapsed']}s，总重试 {report['total_retries']} 次")


if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv) > 1 else None)
