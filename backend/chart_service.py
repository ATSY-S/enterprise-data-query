"""图表数据服务：把查询结果整理成前端可直接渲染的 ECharts 数据结构。

后端不再生成 PNG 图片，只返回结构化数据：
  {type, title, labels, series:[{name, data}], x_name, y_name}
前端拿到后自行渲染，支持悬停、切换类型、放大、导出。
"""
import re
from datetime import date, datetime

import pandas as pd


def _label_key(col: str) -> str:
    """把字段名转成更友好的坐标名。"""
    mapping = {
        'region': '地区', 'city': '城市', 'category': '品类', 'channel': '渠道',
        'store_name': '门店', 'member_level': '会员等级', 'month': '月份',
        'order_date': '日期', 'activity_name': '活动', 'gender': '性别',
    }
    return mapping.get(col, col)


def _fmt(v):
    if isinstance(v, (datetime, date)):
        return v.strftime('%Y-%m-%d')
    if pd.isna(v):
        return None
    if hasattr(v, 'item'):
        v = v.item()
    if isinstance(v, float):
        return round(v, 4)
    return v


def build_chart(rows: list, columns: list, title: str = '查询结果', hint: str = '') -> dict:
    """根据查询结果构造图表数据。数据行数过多时截断，避免前端卡死。"""
    if not rows or not columns:
        return {'available': False, 'reason': '没有可绘图的数据'}

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return {'available': False, 'reason': '没有可绘图的数据'}

    label_col = columns[0]
    numeric_cols = [c for c in columns[1:] if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        numeric_cols = [c for c in columns if c != label_col and pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return {'available': False, 'reason': '结果中没有数值列，无法绘图'}

    if len(df) > 200:
        df = df.head(200)

    labels = [str(_fmt(v)) if _fmt(v) is not None else '' for v in df[label_col]]
    series = [{'name': _label_key(c), 'data': [_fmt(v) for v in df[c]]} for c in numeric_cols[:3]]

    chart_type = 'bar'
    if hint:
        h = hint.lower()
        if '饼' in hint or '占比' in h or 'pie' in h:
            chart_type = 'pie'
        elif '折线' in hint or '趋势' in h or '变化' in h or 'line' in h:
            chart_type = 'line'
        elif '柱状' in hint or '条形' in h or 'bar' in h:
            chart_type = 'bar'

    return {
        'available': True,
        'type': chart_type,
        'title': title[:40],
        'labels': labels,
        'series': series,
        'x_name': _label_key(label_col),
        'y_name': _label_key(numeric_cols[0]),
        'total': len(df),
    }


if __name__ == '__main__':
    demo = [{'地区': '华东', '销售额': 9467172}, {'地区': '华南', '销售额': 9242821}]
    print(build_chart(demo, ['地区', '销售额'], '各地区销售额'))
