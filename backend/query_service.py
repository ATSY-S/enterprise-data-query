"""查询编排层：把 SQL 服务与后处理（统计/图表/导出/留痕）串起来。"""
import json
from tools import (get_statistics, generate_chart, export_to_excel, save_history)
from sql_service import generate as sql_generate, generate_and_execute


def query(question: str, want_chart: bool = True, want_export: bool = False) -> dict:
    r = generate_and_execute(question)
    out = {'question': question, **r}

    if r['success'] and r['data']:
        data_json = json.dumps(r['data'], ensure_ascii=False)
        out['statistics'] = get_statistics(data_json).get('data', {})
        if want_chart:
            chart = generate_chart(data_json, title=question[:20])
            if chart['success']:
                out['chart_path'] = chart['path']
        if want_export:
            exp = export_to_excel(data_json)
            if exp['success']:
                out['export_path'] = exp['path']

    save_history(question, r['sql'], r['success'], r['row_count'], r['elapsed'])
    return out


def preview(question: str) -> dict:
    return sql_generate(question)
