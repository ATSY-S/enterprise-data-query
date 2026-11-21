"""随机评测题生成器。

思路：从数据库真实数据里抽取参数（如某个地区、某个品类、某个月），
用参数化 SQL 预先算出标准答案，再生成中文问题。题目与答案天然配对，
避免人工出固定题被质疑"挑题"。

运行：
  python eval/generate_cases.py --count 30 --seed 42
  python eval/generate_cases.py --count 30 --seed 42 --out eval/cases_random.json
"""
import argparse
import json
import random
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'enterprise.db'

REGIONS = ['华东', '华南', '华北', '西南', '华中']
CATEGORIES = ['电子产品', '食品', '家居', '服装']
LEVELS = ['普通', '银卡', '金卡', '白金']
CHANNELS = ['微信', '抖音', '小红书', '线下门店', '支付宝小程序']
MONTHS = [f'2025-{m:02d}' for m in range(1, 13)]
PAYMENTS = ['微信支付', '支付宝', '银行卡', '现金']


def val(cur, sql, params=()):
    r = cur.execute(sql, params).fetchone()
    return r[0] if r else None


def build_cases(count, seed):
    rng = random.Random(seed)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cases = []
    used = set()

    generators = [
        # (类别, 生成函数)
        ('基础筛选', lambda: case_region_count(cur, rng)),
        ('基础筛选', lambda: case_member_list(cur, rng)),
        ('基础筛选', lambda: case_payment_count(cur, rng)),
        ('聚合统计', lambda: case_month_sales(cur, rng)),
        ('聚合统计', lambda: case_channel_budget(cur, rng)),
        ('聚合统计', lambda: case_coupon_total(cur, rng)),
        ('分组分析', lambda: case_region_sales(cur, rng)),
        ('分组分析', lambda: case_level_orders(cur, rng)),
        ('分组分析', lambda: case_category_sales(cur, rng)),
        ('Top-N', lambda: case_top_store(cur, rng)),
        ('Top-N', lambda: case_top_product(cur, rng)),
        ('Top-N', lambda: case_top_activity(cur, rng)),
        ('业务指标', lambda: case_avg_order(cur, rng)),
        ('业务指标', lambda: case_verify_rate(cur, rng)),
        ('业务指标', lambda: case_profit(cur, rng)),
        ('时间趋势', lambda: case_year_compare(cur, rng)),
        ('多表关联', lambda: case_city_sales(cur, rng)),
    ]

    guard = 0
    while len(cases) < count and guard < count * 30:
        guard += 1
        category, gen = rng.choice(generators)
        try:
            case = gen()
        except (ValueError, ZeroDivisionError, TypeError):
            continue
        if case is None or case['question'] in used:
            continue
        used.add(case['question'])
        case['id'] = f'r{len(cases)+1:03d}'
        case['category'] = category
        case['seed'] = seed
        cases.append(case)

    conn.close()
    return cases


def make(question, sql, expected, params=None, note=''):
    return {'question': question, 'oracle_sql': sql,
            'expected': expected, 'params': params or [], 'note': note}


def case_region_count(cur, rng):
    region = rng.choice(REGIONS)
    sql = "SELECT COUNT(*) FROM orders o JOIN stores s ON o.store_id=s.id WHERE s.region=? AND o.status='已完成'"
    expected = val(cur, sql, (region,))
    return make(f'{region}地区已完成的订单有多少笔？', sql, expected, [region])


def case_member_list(cur, rng):
    level = rng.choice(LEVELS)
    sql = "SELECT COUNT(*) FROM customers WHERE member_level=?"
    expected = val(cur, sql, (level,))
    return make(f'{level}会员有多少个客户？', sql, expected, [level])


def case_payment_count(cur, rng):
    pay = rng.choice(PAYMENTS)
    sql = "SELECT COUNT(*) FROM orders WHERE payment_method=? AND status='已完成'"
    expected = val(cur, sql, (pay,))
    return make(f'使用{pay}方式支付的已完成订单有多少笔？', sql, expected, [pay])


def case_month_sales(cur, rng):
    m = rng.choice(MONTHS)
    sql = "SELECT ROUND(SUM(actual_amount),2) FROM orders WHERE substr(order_date,1,7)=? AND status='已完成'"
    expected = val(cur, sql, (m,))
    return make(f'{m}的销售额是多少？', sql, expected, [m])


def case_channel_budget(cur, rng):
    ch = rng.choice(CHANNELS)
    sql = "SELECT ROUND(SUM(budget),2) FROM activities WHERE channel=?"
    expected = val(cur, sql, (ch,))
    return make(f'{ch}渠道的活动预算总和是多少？', sql, expected, [ch])


def case_coupon_total(cur, rng):
    st = rng.choice(['已核销', '已领取', '已过期'])
    sql = "SELECT COUNT(*) FROM coupons WHERE status=?"
    expected = val(cur, sql, (st,))
    return make(f'{st}状态的优惠券有多少张？', sql, expected, [st])


def case_region_sales(cur, rng):
    sql = """SELECT s.region, ROUND(SUM(o.actual_amount),2) AS v
             FROM orders o JOIN stores s ON o.store_id=s.id
             WHERE o.status='已完成' GROUP BY s.region ORDER BY v DESC"""
    expected = [list(r) for r in cur.execute(sql).fetchall()]
    return make('各地区的销售额从高到低分别是多少？', sql, expected)


def case_level_orders(cur, rng):
    sql = """SELECT c.member_level, COUNT(*) AS n FROM orders o
             JOIN customers c ON o.customer_id=c.id
             WHERE o.status='已完成' GROUP BY c.member_level ORDER BY n DESC"""
    expected = [list(r) for r in cur.execute(sql).fetchall()]
    return make('各会员等级的订单量从高到低排列？', sql, expected)


def case_category_sales(cur, rng):
    sql = """SELECT p.category, ROUND(SUM(oi.subtotal),2) AS v FROM order_items oi
             JOIN products p ON oi.product_id=p.id JOIN orders o ON oi.order_id=o.id
             WHERE o.status='已完成' GROUP BY p.category ORDER BY v DESC"""
    expected = [list(r) for r in cur.execute(sql).fetchall()]
    return make('各品类的销售额从高到低分别是多少？', sql, expected)


def case_top_store(cur, rng):
    n = rng.choice([3, 5])
    sql = """SELECT s.store_name, ROUND(SUM(o.actual_amount),2) AS v FROM orders o
             JOIN stores s ON o.store_id=s.id WHERE o.status='已完成'
             GROUP BY s.id, s.store_name ORDER BY v DESC LIMIT ?"""
    expected = [list(r) for r in cur.execute(sql, (n,)).fetchall()]
    return make(f'销售额最高的{n}个门店是哪些？', sql, expected, [n])


def case_top_product(cur, rng):
    n = rng.choice([3, 5, 10])
    sql = """SELECT p.product_name, SUM(oi.quantity) AS q FROM order_items oi
             JOIN products p ON oi.product_id=p.id GROUP BY p.product_name
             ORDER BY q DESC LIMIT ?"""
    expected = [list(r) for r in cur.execute(sql, (n,)).fetchall()]
    return make(f'销量最高的{n}个商品是哪些？', sql, expected, [n])


def case_top_activity(cur, rng):
    n = rng.choice([3, 5])
    sql = """SELECT a.activity_name,
             ROUND(SUM(CASE WHEN c.status='已核销' THEN 1 ELSE 0 END)*1.0/COUNT(c.id),4) AS rate
             FROM coupons c JOIN activities a ON c.activity_id=a.id
             GROUP BY a.id, a.activity_name ORDER BY rate DESC LIMIT ?"""
    expected = [list(r) for r in cur.execute(sql, (n,)).fetchall()]
    return make(f'核销率最高的{n}个活动是哪些？', sql, expected, [n])


def case_avg_order(cur, rng):
    level = rng.choice(LEVELS)
    sql = """SELECT ROUND(AVG(o.actual_amount),2) FROM orders o
             JOIN customers c ON o.customer_id=c.id
             WHERE c.member_level=?"""
    expected = val(cur, sql, (level,))
    return make(f'{level}会员的平均客单价是多少？', sql, expected, [level])


def case_verify_rate(cur, rng):
    ch = rng.choice(CHANNELS)
    sql = """SELECT ROUND(SUM(CASE WHEN c.status='已核销' THEN 1 ELSE 0 END)*1.0/COUNT(c.id),4)
             FROM coupons c JOIN activities a ON c.activity_id=a.id WHERE a.channel=?"""
    expected = val(cur, sql, (ch,))
    return make(f'{ch}渠道的优惠券核销率是多少？', sql, expected, [ch])


def case_profit(cur, rng):
    cat = rng.choice(CATEGORIES)
    sql = """SELECT ROUND(SUM(oi.subtotal - p.cost_price*oi.quantity),2)
             FROM order_items oi JOIN products p ON oi.product_id=p.id
             JOIN orders o ON oi.order_id=o.id
             WHERE p.category=? AND o.status='已完成'"""
    expected = val(cur, sql, (cat,))
    return make(f'{cat}品类的毛利是多少？', sql, expected, [cat])


def case_year_compare(cur, rng):
    sql = """SELECT substr(order_date,1,4) AS y, COUNT(*) AS n FROM orders
             WHERE status='已完成' GROUP BY y ORDER BY y"""
    expected = [list(r) for r in cur.execute(sql).fetchall()]
    return make('2024年和2025年的已完成订单量分别是多少？', sql, expected)


def case_city_sales(cur, rng):
    sql = """SELECT s.city, ROUND(SUM(o.actual_amount),2) AS v FROM orders o
             JOIN stores s ON o.store_id=s.id WHERE o.status='已完成'
             GROUP BY s.city ORDER BY v DESC LIMIT 5"""
    expected = [list(r) for r in cur.execute(sql).fetchall()]
    return make('销售额前5的城市是哪些？', sql, expected)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--count', type=int, default=30)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--out', type=str, default='eval/cases_random.json')
    a = p.parse_args()
    cases = build_cases(a.count, a.seed)
    out = ROOT / a.out
    out.write_text(json.dumps({
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'seed': a.seed, 'count': len(cases), 'cases': cases,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'生成 {len(cases)} 道题 → {out}（seed={a.seed}）')
    for c in cases[:5]:
        print(f"  {c['id']} [{c['category']}] {c['question']} → {c['expected']}")
