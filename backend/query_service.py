"""查询编排层：把 SQL 服务与后处理（统计/图表/导出/留痕）串起来。"""
import json
from tools import get_statistics, export_to_excel, save_history
from chart_service import build_chart
from sql_service import generate as sql_generate, generate_and_execute


def query(question: str, want_chart: bool = True, want_export: bool = False,
          username: str = 'anonymous') -> dict:
    r = generate_and_execute(question)
    out = {'question': question, **r}

    if r['success'] and r['data']:
        data_json = json.dumps(r['data'], ensure_ascii=False, default=str)
        out['statistics'] = get_statistics(data_json).get('data', {})
        if want_chart:
            out['chart'] = build_chart(r['data'], r['columns'], title=question[:40], hint=question)
        if want_export:
            exp = export_to_excel(data_json)
            if exp['success']:
                out['export_path'] = exp['path']

    save_history(question, r['sql'], r['success'], r['row_count'], r['elapsed'], username=username)
    return out


def preview(question: str) -> dict:
    return sql_generate(question)
