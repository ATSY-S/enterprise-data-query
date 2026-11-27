"""统计与语义层展示服务：从数据库/语义定义生成概览页所需数据。"""
import sqlite3
from typing import Any

from config import DATABASE_PATH
from semantic import DIMENSIONS, METRICS, TERMS

TRACKED_TABLES = ('orders', 'order_items', 'customers', 'products',
                  'coupons', 'activities', 'stores', 'employees')


def overview() -> dict[str, Any]:
    """业务库实时统计，避免前端写死数字。"""
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        counts = {t: conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                  for t in TRACKED_TABLES}
        date_range = conn.execute(
            'SELECT MIN(order_date), MAX(order_date) FROM orders'
        ).fetchone()
    finally:
        conn.close()
    return {**counts, 'date_start': date_range[0], 'date_end': date_range[1]}


def _metric_expr(meta: dict) -> str:
    """把指标定义转成可读表达式。"""
    if meta.get('formula'):
        return meta['formula']
    if meta.get('field') and meta.get('agg'):
        return f"{meta['agg']}({meta['field']})"
    return meta.get('field', '')


def semantics() -> dict[str, list[dict[str, str]]]:
    """语义层定义，供前端指标口径页展示。"""
    return {
        'metrics': [
            {'name': k, 'expr': _metric_expr(v), 'desc': v.get('desc', '')}
            for k, v in METRICS.items()
        ],
        'dimensions': [{'name': k, 'desc': v} for k, v in DIMENSIONS.items()],
        'terms': [{'name': k, 'desc': v} for k, v in TERMS.items()],
    }
