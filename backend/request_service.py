"""导入申请服务：普通用户提交申请 → 管理员审批 → 批准后执行导入。

这是功能级工作流演示（本科毕设够用），不是企业级 OA 审批引擎。
状态：pending（待审批）/ approved（已批准）/ rejected（已驳回）
"""
import sqlite3
from datetime import datetime

from config import DATABASE_PATH, HISTORY_DB
from import_service import ALLOWED_TABLES


def _conn():
    c = sqlite3.connect(HISTORY_DB)
    c.execute('''CREATE TABLE IF NOT EXISTS import_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, applicant TEXT, filename TEXT, table_name TEXT,
        reason TEXT, status TEXT DEFAULT 'pending',
        reviewer TEXT, review_ts TEXT, review_note TEXT)''')
    c.commit()
    return c


def submit(applicant: str, filename: str, table_name: str, reason: str) -> dict:
    if not filename or not table_name:
        return {'success': False, 'message': '文件名和目标表不能为空'}
    if table_name not in ALLOWED_TABLES:
        return {'success': False, 'message': f'表 {table_name} 不在允许导入的白名单中'}
    conn = sqlite3.connect(DATABASE_PATH)
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
    conn.close()
    if not exists:
        return {'success': False, 'message': f'目标表 {table_name} 不存在'}
    c = _conn()
    c.execute('''INSERT INTO import_requests(ts,applicant,filename,table_name,reason,status)
                 VALUES(?,?,?,?,?,'pending')''',
              (datetime.now().isoformat(timespec='seconds'), applicant,
               filename, table_name, reason or ''))
    rid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    c.commit(); c.close()
    return {'success': True, 'id': rid, 'message': f'申请已提交，编号 {rid}，等待管理员审批'}


def list_requests(applicant: str = None, role: str = None, status: str = None) -> list:
    c = _conn()
    sql = 'SELECT id,ts,applicant,filename,table_name,reason,status,reviewer,review_ts,review_note FROM import_requests WHERE 1=1'
    args = []
    if role != 'admin' and applicant:
        sql += ' AND applicant=?'; args.append(applicant)
    if status:
        sql += ' AND status=?'; args.append(status)
    sql += ' ORDER BY id DESC LIMIT 100'
    rows = c.execute(sql, args).fetchall(); c.close()
    return [{'id': r[0], 'ts': r[1], 'applicant': r[2], 'filename': r[3],
             'table': r[4], 'reason': r[5], 'status': r[6],
             'reviewer': r[7], 'review_ts': r[8], 'review_note': r[9]} for r in rows]


def review(request_id: int, reviewer: str, approve: bool, note: str = '') -> dict:
    c = _conn()
    row = c.execute('SELECT status FROM import_requests WHERE id=?', (request_id,)).fetchone()
    if not row:
        c.close(); return {'success': False, 'message': '申请不存在'}
    if row[0] != 'pending':
        c.close(); return {'success': False, 'message': '该申请已处理，不能重复审批'}
    status = 'approved' if approve else 'rejected'
    c.execute('''UPDATE import_requests SET status=?,reviewer=?,review_ts=?,review_note=?
                 WHERE id=?''',
              (status, reviewer, datetime.now().isoformat(timespec='seconds'), note, request_id))
    c.commit(); c.close()
    return {'success': True, 'status': status,
            'message': ('已批准' if approve else '已驳回') + f'申请 #{request_id}'}


def pending_count() -> int:
    c = _conn()
    n = c.execute("SELECT COUNT(*) FROM import_requests WHERE status='pending'").fetchone()[0]
    c.close(); return n


if __name__ == '__main__':
    print(submit('user', 'test.csv', 'customers', '测试'))
    print(list_requests('user', 'user'))
