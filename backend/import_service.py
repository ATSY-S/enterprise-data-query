"""数据导入服务：Excel/CSV → 预览 → 白名单校验 → 追加入库。

安全默认（照抄 JimuReport 的 autoTableEnabled=false 思路）：
- 只允许 INSERT 到白名单业务表，不接受用户传来的 DDL/DML
- 字段名必须在目标表已存在列中，不允许用户新建任意表结构
- 主键/自增列由数据库管理，导入时剔除
"""
import io
import sqlite3
from datetime import datetime

import pandas as pd

from config import DATABASE_PATH, HISTORY_DB

ALLOWED_TABLES = {'orders', 'order_items', 'customers', 'products', 'stores', 'activities', 'coupons'}
AUTO_COLUMNS = {'id', 'order_no'}


def _conn():
    return sqlite3.connect(DATABASE_PATH)


def table_info() -> list:
    """概览页数据源区块用：列出各表规模。"""
    c = _conn()
    out = []
    for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        n = c.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        cols = [r[1] for r in c.execute(f'PRAGMA table_info("{name}")').fetchall()]
        out.append({'name': name, 'rows': n, 'columns': len(cols)})
    c.close()
    return out


def parse_upload(filename: str, content: bytes) -> dict:
    """解析上传的 CSV / Excel，返回预览数据，不写库。"""
    try:
        if filename.lower().endswith('.csv'):
            for enc in ('utf-8-sig', 'gbk', 'utf-8'):
                try:
                    df = pd.read_csv(io.BytesIO(content), encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return {'success': False, 'message': 'CSV 编码无法识别，请另存为 UTF-8'}
        elif filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            return {'success': False, 'message': '只支持 .csv / .xlsx / .xls 文件'}

        if df.empty:
            return {'success': False, 'message': '文件没有数据行'}
        return {
            'success': True,
            'columns': [str(c) for c in df.columns],
            'rows': len(df),
            'preview': df.head(5).astype(str).to_dict(orient='records'),
            '_df': df,
        }
    except Exception as e:
        return {'success': False, 'message': f'解析失败：{e}'}


def validate_target(table: str, columns: list) -> dict:
    """校验目标表是否合法、字段是否匹配。"""
    if table not in ALLOWED_TABLES:
        return {'success': False, 'message': f'表 {table} 不在允许导入的白名单中'}
    c = _conn()
    exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not exists:
        c.close()
        return {'success': False, 'message': f'目标表 {table} 不存在'}
    db_cols = [r[1] for r in c.execute(f'PRAGMA table_info("{table}")').fetchall()]
    c.close()
    unknown = [c for c in columns if c not in db_cols and c not in AUTO_COLUMNS]
    if unknown:
        return {'success': False, 'message': f'字段 {unknown} 在目标表中不存在'}
    usable = [c for c in columns if c in db_cols]
    if not usable:
        return {'success': False, 'message': '没有可导入的字段'}
    return {'success': True, 'columns': usable, 'all_columns': db_cols}


def import_rows(df: pd.DataFrame, table: str, columns: list) -> dict:
    """把 DataFrame 的数据追加到目标表。只做 INSERT，不碰表结构。"""
    check = validate_target(table, list(df.columns))
    if not check['success']:
        return check
    usable = check['columns']
    c = _conn()
    before = c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    placeholders = ','.join('?' for _ in usable)
    sql = f'INSERT INTO "{table}" ({",".join(chr(34)+x+chr(34) for x in usable)}) VALUES ({placeholders})'
    try:
        for _, row in df.iterrows():
            vals = [None if pd.isna(row[col]) else (row[col].item() if hasattr(row[col], 'item') else row[col])
                    for col in usable]
            c.execute(sql, vals)
        c.commit()
    except Exception as e:
        c.rollback()
        c.close()
        return {'success': False, 'message': f'写入失败：{e}'}
    after = c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    c.close()
    _log_import(table, len(df), after - before)
    # 数据变更后必须清缓存，否则用户查到旧结果
    from cache_service import invalidate
    invalidate()
    return {'success': True, 'inserted': after - before, 'table': table,
            'message': f'已导入 {after - before} 行到 {table}'}


def _log_import(table: str, attempted: int, inserted: int):
    c = sqlite3.connect(HISTORY_DB)
    c.execute('''CREATE TABLE IF NOT EXISTS import_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, table_name TEXT, attempted INTEGER, inserted INTEGER, username TEXT)''')
    c.execute('INSERT INTO import_history(ts,table_name,attempted,inserted,username) VALUES(?,?,?,?,?)',
              (datetime.now().isoformat(timespec='seconds'), table, attempted, inserted, 'system'))
    c.commit()
    c.close()


def import_history(limit: int = 20) -> list:
    c = sqlite3.connect(HISTORY_DB)
    c.execute('''CREATE TABLE IF NOT EXISTS import_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, table_name TEXT, attempted INTEGER, inserted INTEGER, username TEXT)''')
    rows = c.execute('SELECT ts,table_name,attempted,inserted FROM import_history ORDER BY id DESC LIMIT ?',
                     (limit,)).fetchall()
    c.close()
    return [{'ts': r[0], 'table': r[1], 'attempted': r[2], 'inserted': r[3]} for r in rows]


if __name__ == '__main__':
    print(table_info())
