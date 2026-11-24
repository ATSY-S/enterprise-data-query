"""导入申请服务：普通用户上传文件 → 管理员预览审核 → 批准后直接入库。

这是功能级工作流演示（本科毕设够用），不是企业级 OA 审批引擎。
状态：pending（待审批）/ approved（已批准）/ rejected（已驳回）/ imported（已导入）
"""
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE_PATH, HISTORY_DB, DATA_DIR
from import_service import ALLOWED_TABLES, import_rows, parse_upload

UPLOAD_DIR = DATA_DIR / 'import_uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _conn():
    c = sqlite3.connect(HISTORY_DB)
    c.execute('''CREATE TABLE IF NOT EXISTS import_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, applicant TEXT, filename TEXT, table_name TEXT,
        reason TEXT, status TEXT DEFAULT 'pending',
        file_path TEXT, reviewer TEXT, review_ts TEXT, review_note TEXT,
        imported_rows INTEGER DEFAULT 0)''')
    cols = [r[1] for r in c.execute('PRAGMA table_info(import_requests)').fetchall()]
    for col, ddl in [('file_path', 'TEXT'), ('imported_rows', 'INTEGER DEFAULT 0')]:
        if col not in cols:
            c.execute(f'ALTER TABLE import_requests ADD COLUMN {col} {ddl}')
    c.commit()
    return c


def _safe_name(name: str) -> str:
    """清洗文件名，防路径穿越。"""
    return Path(name or 'upload').name.replace('/', '_').replace('\\', '_')


def submit(applicant: str, filename: str, table_name: str, reason: str,
           content: bytes) -> dict:
    if not content:
        return {'success': False, 'message': '请上传文件'}
    if not table_name:
        return {'success': False, 'message': '请选择目标表'}
    if table_name not in ALLOWED_TABLES:
        return {'success': False, 'message': f'表 {table_name} 不在允许导入的白名单中'}
    conn = sqlite3.connect(DATABASE_PATH)
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
    conn.close()
    if not exists:
        return {'success': False, 'message': f'目标表 {table_name} 不存在'}

    parsed = parse_upload(_safe_name(filename), content)
    if not parsed['success']:
        return parsed

    c = _conn()
    c.execute('''INSERT INTO import_requests(ts,applicant,filename,table_name,reason,status)
                 VALUES(?,?,?,?,?,'pending')''',
              (datetime.now().isoformat(timespec='seconds'), applicant,
               _safe_name(filename), table_name, reason or ''))
    rid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    dest = UPLOAD_DIR / f'req_{rid}_{_safe_name(filename)}'
    dest.write_bytes(content)
    c.execute('UPDATE import_requests SET file_path=? WHERE id=?', (str(dest), rid))
    c.commit(); c.close()
    return {'success': True, 'id': rid, 'rows': parsed['rows'],
            'message': f'申请已提交，编号 {rid}，文件已保存，等待管理员审批'}


def get_request(request_id: int) -> dict | None:
    c = _conn()
    c.row_factory = sqlite3.Row
    r = c.execute('SELECT * FROM import_requests WHERE id=?', (request_id,)).fetchone()
    c.close()
    return dict(r) if r else None


def preview_file(request_id: int) -> dict:
    """管理员审核用：预览申请文件的前 5 行，不写库。"""
    item = get_request(request_id)
    if not item:
        return {'success': False, 'message': '申请不存在'}
    p = Path(item['file_path'] or '')
    if not p.exists():
        return {'success': False, 'message': '申请文件丢失'}
    parsed = parse_upload(p.name, p.read_bytes())
    if not parsed['success']:
        return parsed
    return {'success': True, 'id': request_id, 'filename': item['filename'],
            'table': item['table_name'], 'rows': parsed['rows'],
            'columns': parsed['columns'], 'preview': parsed['preview'],
            'reason': item['reason'], 'applicant': item['applicant']}


def import_approved(request_id: int, reviewer: str) -> dict:
    """批准后的实际导入：读申请文件 → 写入目标表 → 状态变 imported。"""
    item = get_request(request_id)
    if not item:
        return {'success': False, 'message': '申请不存在'}
    if item['status'] != 'approved':
        return {'success': False, 'message': '只有已批准的申请才能导入'}
    p = Path(item['file_path'] or '')
    if not p.exists():
        return {'success': False, 'message': '申请文件丢失'}
    parsed = parse_upload(p.name, p.read_bytes())
    if not parsed['success']:
        return parsed
    result = import_rows(parsed['_df'], item['table_name'], parsed['columns'])
    if result['success']:
        c = _conn()
        c.execute('UPDATE import_requests SET status=?,imported_rows=?,reviewer=? WHERE id=?',
                  ('imported', result['inserted'], reviewer, request_id))
        c.commit(); c.close()
    return result


def list_requests(applicant: str = None, role: str = None, status: str = None) -> list:
    c = _conn()
    sql = '''SELECT id,ts,applicant,filename,table_name,reason,status,file_path,
                    reviewer,review_ts,review_note,imported_rows
             FROM import_requests WHERE 1=1'''
    args = []
    if role != 'admin' and applicant:
        sql += ' AND applicant=?'; args.append(applicant)
    if status:
        sql += ' AND status=?'; args.append(status)
    sql += ' ORDER BY id DESC LIMIT 100'
    rows = c.execute(sql, args).fetchall(); c.close()
    return [{'id': r[0], 'ts': r[1], 'applicant': r[2], 'filename': r[3],
             'table': r[4], 'reason': r[5], 'status': r[6], 'file_path': r[7],
             'reviewer': r[8], 'review_ts': r[9], 'review_note': r[10],
             'imported_rows': r[11]} for r in rows]


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
