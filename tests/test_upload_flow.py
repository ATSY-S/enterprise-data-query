"""沙箱实测：文件上传审批全链路（正常流程 + 边界情况）。

运行前需启动后端：uvicorn api:app --port 8600
运行：python tests/test_upload_flow.py
注意：本脚本会临时写入测试数据，结束后自动清理。
"""
import io
import sqlite3
import sys
from pathlib import Path

import requests

BASE = 'http://127.0.0.1:8600'
ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'enterprise.db'
HISTORY = ROOT / 'data' / 'query_history.db'

CSV = '''id,customer_name,customer_type,member_level,city,register_date
9201,沙箱测试客户甲,个人客户,银卡,苏州,2026-04-01
9202,沙箱测试客户乙,企业客户,金卡,无锡,2026-04-02
9203,沙箱测试客户丙,个人客户,普通,常州,2026-04-03
'''


def login(username, password):
    r = requests.post(f'{BASE}/api/login', json={'username': username, 'password': password}, timeout=10)
    return r.json()['data']['token']


def headers(token):
    return {'Authorization': 'Bearer ' + token}


def count_customers():
    c = sqlite3.connect(DB)
    n = c.execute("SELECT COUNT(*) FROM customers WHERE customer_name LIKE '沙箱测试客户%'").fetchone()[0]
    c.close()
    return n


def main():
    print('=== 文件审批闭环沙箱实测 ===\n')
    try:
        requests.get(f'{BASE}/api/health', timeout=5)
    except Exception as e:
        print('后端未启动：', e); sys.exit(1)

    admin = login('admin', 'admin123')
    user = login('user', 'user123')
    print('[1] 两种角色登录成功')
    before = count_customers()

    # 用户上传文件申请
    files = {'file': ('sandbox_test.csv', io.BytesIO(CSV.encode('utf-8')), 'text/csv')}
    data = {'table': 'customers', 'reason': '沙箱自动化测试'}
    r = requests.post(f'{BASE}/api/requests', files=files, data=data, headers=headers(user), timeout=15)
    d = r.json()['data']
    assert d['success'], d
    rid = d['id']
    print(f'[2] 普通用户上传文件成功：申请 #{rid}，{d["rows"]} 行')

    # 管理员预览
    r = requests.get(f'{BASE}/api/requests/{rid}/preview', headers=headers(admin), timeout=15)
    d = r.json()['data']
    assert d['success'] and d['rows'] == 3, d
    assert len(d['preview']) == 3
    print(f'[3] 管理员预览成功：{d["rows"]} 行 / {len(d["columns"])} 列，首行={d["preview"][0]["customer_name"]}')

    # 越权检查：普通用户不能预览
    r = requests.get(f'{BASE}/api/requests/{rid}/preview', headers=headers(user), timeout=15)
    assert r.status_code == 403, f'越权预览未被拦截：{r.status_code}'
    print('[4] 越权检查通过：普通用户预览返回 403')

    # 批准
    r = requests.post(f'{BASE}/api/requests/{rid}/review', json={'approve': True, 'note': '沙箱测试批准'},
                      headers=headers(admin), timeout=15)
    d = r.json()['data']
    assert d['success'], d
    print('[5] 管理员批准成功')

    # 重复审批应被拒
    r = requests.post(f'{BASE}/api/requests/{rid}/review', json={'approve': False},
                      headers=headers(admin), timeout=15)
    d = r.json()['data']
    assert not d['success'], '重复审批未被拒绝'
    print('[6] 重复审批被正确拒绝')

    # 执行导入
    r = requests.post(f'{BASE}/api/requests/{rid}/import', headers=headers(admin), timeout=15)
    d = r.json()['data']
    assert d['success'] and d['inserted'] == 3, d
    print(f'[7] 执行导入成功：{d["inserted"]} 行写入 {d["table"]}')

    # 数据库验证
    after = count_customers()
    assert after == before + 3, f'数据库行数异常：{before} -> {after}'
    print(f'[8] 数据库验证通过：测试客户 {before} -> {after}')

    # 重复导入应被拒
    r = requests.post(f'{BASE}/api/requests/{rid}/import', headers=headers(admin), timeout=15)
    d = r.json()['data']
    assert not d['success'], '重复导入未被拒绝'
    print('[9] 重复导入被正确拒绝')

    # 用户看到最终状态
    r = requests.get(f'{BASE}/api/requests', headers=headers(user), timeout=15)
    rows = r.json()['data']
    mine = [x for x in rows if x['id'] == rid][0]
    assert mine['status'] == 'imported' and mine['imported_rows'] == 3, mine
    print(f'[10] 申请人看到最终状态：{mine["status"]}，导入 {mine["imported_rows"]} 行')

    # 清理
    c = sqlite3.connect(DB)
    c.execute("DELETE FROM customers WHERE customer_name LIKE '沙箱测试客户%'")
    c.commit(); c.close()
    c = sqlite3.connect(HISTORY)
    c.execute('DELETE FROM import_requests WHERE id=?', (rid,)); c.commit(); c.close()
    up = ROOT / 'data' / 'import_uploads'
    if up.exists():
        for f in up.glob(f'req_{rid}_*'):
            f.unlink()
    print(f'[11] 测试数据已清理：客户恢复 {count_customers()} 行')
    print('\n=== 全部 11 项通过 ===')


if __name__ == '__main__':
    main()
