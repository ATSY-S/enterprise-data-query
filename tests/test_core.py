"""单元测试：安全守卫、错误分类、语义层、数据库完整性。
运行：pytest tests/ -v
"""
import sqlite3
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent / 'backend'
sys.path.insert(0, str(BACKEND))

from config import DATABASE_PATH
from tools import execute_sql, get_statistics, list_history
from sql_service import classify_error, failure_advice
from semantic import schema_text, METRICS, DIMENSIONS


class TestSQLGuard:
    @pytest.mark.parametrize('sql', [
        'DELETE FROM orders',
        'UPDATE orders SET actual_amount=0',
        'DROP TABLE orders',
        'SELECT 1; DROP TABLE orders',
        'PRAGMA table_info(orders)',
        'INSERT INTO orders VALUES (1)',
    ])
    def test_rejects_dangerous_sql(self, sql):
        r = execute_sql(sql)
        assert r['success'] is False
        assert len(r['data']) == 0

    def test_allows_select(self):
        r = execute_sql('SELECT COUNT(*) AS n FROM orders')
        assert r['success'] is True
        assert r['row_count'] == 1
        assert r['data'][0]['n'] > 0

    def test_allows_with_cte(self):
        r = execute_sql('WITH t AS (SELECT COUNT(*) AS n FROM orders) SELECT * FROM t')
        assert r['success'] is True


class TestErrorClassification:
    def test_security_errors(self):
        assert classify_error('只允许 SELECT 查询') == 'security'
        assert classify_error('检测到写操作关键字，已拒绝') == 'security'

    def test_retryable_errors(self):
        assert classify_error('no such column: xyz') == 'syntax_or_schema'
        assert classify_error('near "SELCT": syntax error') == 'syntax_or_schema'

    def test_unknown_error(self):
        assert classify_error('某种未知错误') == 'unknown'

    def test_advice_is_actionable(self):
        advice = failure_advice('测试', 'security', '')
        assert '只允许' in advice or '读取' in advice


class TestSemanticLayer:
    def test_schema_has_all_tables(self):
        s = schema_text()
        for table in ['orders', 'order_items', 'customers', 'products',
                      'stores', 'employees', 'activities', 'coupons']:
            assert table in s

    def test_metrics_defined(self):
        for name in ['销售额', '客单价', '核销率', '毛利']:
            assert name in METRICS

    def test_dimensions_defined(self):
        assert '会员等级' in DIMENSIONS
        assert '渠道' in DIMENSIONS

    def test_schema_mentions_joins(self):
        assert 'order_items.order_id = orders.id' in schema_text()


class TestDatabase:
    @pytest.fixture(scope='class')
    @classmethod
    def conn(cls):
        c = sqlite3.connect(DATABASE_PATH)
        yield c
        c.close()

    @pytest.mark.parametrize('table,minimum', [
        ('orders', 15000), ('order_items', 30000), ('customers', 500),
        ('products', 15), ('stores', 15), ('activities', 30), ('coupons', 3000),
    ])
    def test_table_has_enough_rows(self, conn, table, minimum):
        n = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        assert n >= minimum, f'{table} 只有 {n} 行'

    def test_seasonality_exists(self, conn):
        dec = conn.execute("SELECT COUNT(*) FROM orders WHERE substr(order_date,6,2)='12'").fetchone()[0]
        feb = conn.execute("SELECT COUNT(*) FROM orders WHERE substr(order_date,6,2)='02'").fetchone()[0]
        assert dec > feb * 1.5, '旺季订单量应明显高于淡季'

    def test_referential_integrity(self, conn):
        orphan = conn.execute('''SELECT COUNT(*) FROM orders o
            LEFT JOIN customers c ON o.customer_id=c.id WHERE c.id IS NULL''').fetchone()[0]
        assert orphan == 0

    def test_business_metrics_consistent(self, conn):
        bad = conn.execute('''SELECT COUNT(*) FROM orders
            WHERE ABS(total_amount - discount_amount - actual_amount) > 0.01''').fetchone()[0]
        assert bad == 0


class TestStatistics:
    def test_basic_stats(self):
        import json
        data = json.dumps([{'amount': 10}, {'amount': 20}, {'amount': 30}])
        r = get_statistics(data)
        assert r['success']
        assert r['data']['amount']['总和'] == 60.0
        assert r['data']['amount']['平均值'] == 20.0
