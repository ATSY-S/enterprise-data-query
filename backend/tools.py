"""工具函数：只读 SQL 执行、统计、图表、导出，以及查询历史。
每个函数都以字符串进出，方便作为 LangChain 工具注册给大模型。
"""
import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import DATABASE_PATH, HISTORY_DB, CHARTS_DIR, REPORTS_DIR

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

FORBIDDEN = re.compile(r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|PRAGMA|ATTACH|DETACH)\b', re.I)


def _guard(sql: str):
    """只读守卫：拦截非 SELECT 语句和多语句注入。"""
    s = sql.strip().rstrip(';')
    if ';' in s:
        raise ValueError('不允许多条 SQL 语句')
    if not re.match(r'^(SELECT|WITH)\b', s, re.I):
        raise ValueError('只允许 SELECT 查询')
    if FORBIDDEN.search(s):
        raise ValueError('检测到写操作关键字，已拒绝')
    return s


def execute_sql(sql_query: str) -> dict:
    try:
        sql = _guard(sql_query)
        conn = sqlite3.connect(DATABASE_PATH)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return {
            'success': True,
            'data': df.to_dict(orient='records'),
            'columns': list(df.columns),
            'row_count': len(df),
            'message': f'查询成功，共 {len(df)} 行',
        }
    except Exception as e:
        return {'success': False, 'data': [], 'columns': [], 'row_count': 0, 'message': str(e)}


def get_statistics(data_json: str) -> dict:
    try:
        df = pd.DataFrame(json.loads(data_json))
        nums = df.select_dtypes(include='number')
        stats = {}
        for col in nums.columns:
            s = nums[col]
            stats[col] = {
                '总和': round(float(s.sum()), 2),
                '平均值': round(float(s.mean()), 2),
                '最大值': round(float(s.max()), 2),
                '最小值': round(float(s.min()), 2),
                '计数': int(s.count()),
            }
        return {'success': True, 'data': stats, 'message': '统计完成'}
    except Exception as e:
        return {'success': False, 'data': {}, 'message': str(e)}


def generate_chart(data_json: str, chart_type: str = 'bar', title: str = '数据分析图表') -> dict:
    try:
        df = pd.DataFrame(json.loads(data_json))
        if df.empty:
            return {'success': False, 'message': '没有可绘图的数据'}
        label_col = df.columns[0]
        value_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not value_cols:
            return {'success': False, 'message': '没有数值列可绘图'}
        value_col = value_cols[0]
        fig, ax = plt.subplots(figsize=(9, 5))
        if chart_type == 'pie':
            ax.pie(df[value_col], labels=df[label_col].astype(str), autopct='%1.1f%%', startangle=90)
        elif chart_type == 'line':
            ax.plot(df[label_col].astype(str), df[value_col], marker='o')
            ax.tick_params(axis='x', rotation=30)
        else:
            ax.bar(df[label_col].astype(str), df[value_col])
            ax.tick_params(axis='x', rotation=30)
        ax.set_title(title)
        fig.tight_layout()
        name = f'chart_{datetime.now():%Y%m%d_%H%M%S_%f}.png'
        path = CHARTS_DIR / name
        fig.savefig(path, dpi=120)
        plt.close(fig)
        return {'success': True, 'path': str(path), 'message': '图表已生成'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def export_to_excel(data_json: str, filename: str = None) -> dict:
    try:
        df = pd.DataFrame(json.loads(data_json))
        name = filename or f'result_{datetime.now():%Y%m%d_%H%M%S}.xlsx'
        path = REPORTS_DIR / name
        df.to_excel(path, index=False)
        return {'success': True, 'path': str(path), 'message': 'Excel 已导出'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def export_to_csv(data_json: str, filename: str = None) -> dict:
    try:
        df = pd.DataFrame(json.loads(data_json))
        name = filename or f'result_{datetime.now():%Y%m%d_%H%M%S}.csv'
        path = REPORTS_DIR / name
        df.to_csv(path, index=False, encoding='utf-8-sig')
        return {'success': True, 'path': str(path), 'message': 'CSV 已导出'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def save_history(question: str, sql: str, success: bool, rows: int, elapsed: float):
    """企业成品该有的东西：查询留痕，便于审计与复盘。"""
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, question TEXT, sql TEXT, success INTEGER, rows INTEGER, elapsed REAL)''')
    conn.execute('INSERT INTO history(ts,question,sql,success,rows,elapsed) VALUES(?,?,?,?,?,?)',
                 (datetime.now().isoformat(timespec='seconds'), question, sql,
                  int(success), rows, elapsed))
    conn.commit()
    conn.close()


def list_history(limit: int = 20) -> dict:
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, question TEXT, sql TEXT, success INTEGER, rows INTEGER, elapsed REAL)''')
    rows = conn.execute('SELECT ts,question,sql,success,rows,elapsed FROM history ORDER BY id DESC LIMIT ?',
                        (limit,)).fetchall()
    conn.close()
    return {'success': True, 'data': [
        {'ts': r[0], 'question': r[1], 'sql': r[2], 'success': bool(r[3]), 'rows': r[4], 'elapsed': r[5]}
        for r in rows]}


if __name__ == '__main__':
    print(execute_sql('SELECT category, SUM(sales_amount) AS total FROM orders GROUP BY category ORDER BY total DESC'))
    print(list_history(3))
