"""轻量认证：PBKDF2 密码哈希 + 随机 Token 会话 + 两种角色。

说明：这是功能级权限演示（本科毕设够用），不是企业级 RBAC。
- admin：可查询、看全部历史、导入数据
- user ：可查询、只看自己的历史
密码哈希用标准库 hashlib.pbkdf2_hmac，不额外装依赖。
"""
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime

from config import HISTORY_DB

ITERATIONS = 200_000


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), ITERATIONS).hex()


def _conn():
    c = sqlite3.connect(HISTORY_DB)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        salt TEXT NOT NULL, password_hash TEXT NOT NULL,
        role TEXT NOT NULL, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY, username TEXT NOT NULL, created_at TEXT)''')
    c.commit()
    return c


def init_users():
    """首次运行写入两个演示账号（密码在论文/文档中说明）。"""
    c = _conn()
    for username, password, role in [('admin', 'admin123', 'admin'), ('user', 'user123', 'user')]:
        if not c.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
            salt = secrets.token_hex(16)
            c.execute('INSERT INTO users(username,salt,password_hash,role,created_at) VALUES(?,?,?,?,?)',
                      (username, salt, _hash(password, salt), role, datetime.now().isoformat(timespec='seconds')))
    c.commit()
    c.close()


def login(username: str, password: str) -> dict:
    c = _conn()
    row = c.execute('SELECT salt,password_hash,role FROM users WHERE username=?', (username,)).fetchone()
    if not row:
        c.close()
        return {'success': False, 'message': '用户名或密码错误'}
    salt, expected, role = row
    if not hmac.compare_digest(_hash(password, salt), expected):
        c.close()
        return {'success': False, 'message': '用户名或密码错误'}
    token = secrets.token_urlsafe(32)
    c.execute('INSERT INTO sessions(token,username,created_at) VALUES(?,?,?)',
              (token, username, datetime.now().isoformat(timespec='seconds')))
    c.commit()
    c.close()
    return {'success': True, 'token': token, 'username': username, 'role': role}


def verify(token: str) -> dict | None:
    if not token:
        return None
    c = _conn()
    row = c.execute('''SELECT u.username, u.role FROM sessions s
                       JOIN users u ON s.username=u.username WHERE s.token=?''', (token,)).fetchone()
    c.close()
    if not row:
        return None
    return {'username': row[0], 'role': row[1]}


def logout(token: str):
    c = _conn()
    c.execute('DELETE FROM sessions WHERE token=?', (token,))
    c.commit()
    c.close()


def list_users() -> list:
    c = _conn()
    rows = c.execute('SELECT username,role,created_at FROM users ORDER BY id').fetchall()
    c.close()
    return [{'username': r[0], 'role': r[1], 'created_at': r[2]} for r in rows]


if __name__ == '__main__':
    init_users()
    r = login('admin', 'admin123')
    print(r)
    print(verify(r['token']))
