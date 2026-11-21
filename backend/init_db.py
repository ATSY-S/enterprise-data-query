"""企业销售数据集生成器 —— 仿真实业务数据。

设计目标：让评测结果可信。数据具备以下真实业务特征：
1. 多表关联：订单关联客户/商品/门店/员工，不是一张宽表
2. 时间跨度：2024-01 至 2025-12，两年
3. 季节性：年底旺季、春节低谷、夏季平缓
4. 客户分层：个人/企业客户，普通/银卡/金卡/白金
5. 业务口径：成本与毛利可算，折扣与实付区分
6. 活动效果：不同渠道的领券核销率有差异

运行：python init_db.py --fresh
"""
import argparse
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATABASE_PATH

random.seed(20251121)

SCHEMA = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS coupons;
DROP TABLE IF EXISTS activities;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS stores;

CREATE TABLE stores (
    id INTEGER PRIMARY KEY,
    store_name TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    store_level TEXT NOT NULL
);
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    store_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    FOREIGN KEY(store_id) REFERENCES stores(id)
);
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_type TEXT NOT NULL,
    member_level TEXT NOT NULL,
    city TEXT NOT NULL,
    register_date TEXT NOT NULL
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL,
    cost_price REAL NOT NULL
);
CREATE TABLE activities (
    id INTEGER PRIMARY KEY,
    activity_name TEXT NOT NULL,
    channel TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    budget REAL NOT NULL
);
CREATE TABLE coupons (
    id INTEGER PRIMARY KEY,
    activity_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    receive_date TEXT NOT NULL,
    verify_date TEXT,
    status TEXT NOT NULL,
    discount_amount REAL NOT NULL,
    FOREIGN KEY(activity_id) REFERENCES activities(id),
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(store_id) REFERENCES stores(id)
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    order_no TEXT NOT NULL UNIQUE,
    order_date TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    discount_amount REAL NOT NULL,
    actual_amount REAL NOT NULL,
    status TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(store_id) REFERENCES stores(id),
    FOREIGN KEY(employee_id) REFERENCES employees(id)
);
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_items_order ON order_items(order_id);
CREATE INDEX idx_coupons_activity ON coupons(activity_id);
"""

REGIONS = {
    '华东': ['上海', '杭州', '南京', '苏州', '宁波'],
    '华南': ['广州', '深圳', '东莞', '佛山', '厦门'],
    '华北': ['北京', '天津', '石家庄', '太原'],
    '西南': ['成都', '重庆', '昆明', '贵阳'],
    '华中': ['武汉', '长沙', '郑州'],
}
CATEGORIES = {
    '电子产品': [('平板电脑', 3200, 2300), ('蓝牙耳机', 599, 340), ('智能手表', 1299, 780), ('充电宝', 199, 95), ('便携音箱', 399, 220)],
    '食品': [('精品咖啡', 89, 45), ('坚果礼盒', 158, 88), ('手工饼干', 68, 32), ('鲜榨果汁', 35, 16), ('有机麦片', 79, 40)],
    '家居': [('床上四件套', 399, 210), ('收纳箱', 129, 68), ('护眼台灯', 269, 145), ('毛巾套装', 89, 42), ('香薰加湿器', 329, 180)],
    '服装': [('纯棉T恤', 129, 55), ('连帽卫衣', 299, 135), ('牛仔裤', 359, 175), ('轻薄外套', 499, 240), ('运动套装', 429, 205)],
}
CHANNELS = ['微信', '抖音', '小红书', '线下门店', '支付宝小程序']
MEMBER_LEVELS = ['普通', '银卡', '金卡', '白金']
STATUS = ['已完成', '已完成', '已完成', '已完成', '已取消', '已退款']


def seasonal_factor(d: date) -> float:
    """年底旺季、春节低谷、暑期平缓。"""
    if d.month == 11 or d.month == 12:
        return random.uniform(1.3, 1.9)
    if d.month == 1 or d.month == 2:
        return random.uniform(0.5, 0.85)
    if d.month in (6, 7, 8):
        return random.uniform(0.85, 1.15)
    return random.uniform(0.95, 1.25)


def main():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript(SCHEMA)

    stores = []
    sid = 1
    for region, cities in REGIONS.items():
        for city in cities:
            stores.append((sid, f'{city}{"旗舰店" if sid % 3 == 0 else "体验店"}',
                           region, city, '旗舰' if sid % 3 == 0 else '标准'))
            sid += 1
    conn.executemany('INSERT INTO stores VALUES (?,?,?,?,?)', stores)

    employees = []
    eid = 1
    roles = ['店长', '销售顾问', '销售顾问', '收银员']
    for store in stores:
        for role in random.sample(roles, k=random.randint(2, 4)):
            employees.append((eid, f'员工{eid:03d}', store[0], role))
            eid += 1
    conn.executemany('INSERT INTO employees VALUES (?,?,?,?)', employees)

    customers = []
    for cid in range(1, 601):
        ctype = '企业客户' if random.random() < 0.18 else '个人客户'
        level = random.choices(MEMBER_LEVELS, weights=[45, 30, 18, 7])[0]
        city = random.choice([c for cities in REGIONS.values() for c in cities])
        reg = date(random.randint(2023, 2024), random.randint(1, 12), random.randint(1, 28))
        customers.append((cid, f'客户{cid:04d}', ctype, level, city, reg.isoformat()))
    conn.executemany('INSERT INTO customers VALUES (?,?,?,?,?,?)', customers)

    products = []
    pid = 1
    for category, items in CATEGORIES.items():
        for name, price, cost in items:
            products.append((pid, name, category, price, cost))
            pid += 1
    conn.executemany('INSERT INTO products VALUES (?,?,?,?,?)', products)

    activities = []
    for i in range(36):
        start = date(2024, 1, 1) + timedelta(days=20 * i)
        end = start + timedelta(days=random.randint(7, 21))
        activities.append((
            i + 1, f'{start.year}年{start.month}月{["春日", "夏日", "金秋", "冬日"][start.month % 4]}大促',
            CHANNELS[i % len(CHANNELS)], start.isoformat(), end.isoformat(),
            round(random.uniform(12000, 60000), 2),
        ))
    conn.executemany('INSERT INTO activities VALUES (?,?,?,?,?,?)', activities)

    coupons = []
    cid = 1
    for act in activities:
        base_rate = random.uniform(0.45, 0.78)
        for _ in range(random.randint(60, 140)):
            customer = random.choice(customers)
            store = random.choice(stores)
            received = date.fromisoformat(act[3]) + timedelta(days=random.randint(0, 12))
            verified = (received + timedelta(days=random.randint(0, 8))
                        if random.random() < base_rate else None)
            status = '已核销' if verified else ('已过期' if random.random() < 0.25 else '已领取')
            coupons.append((cid, act[0], customer[0], store[0], received.isoformat(),
                            verified.isoformat() if verified else None, status,
                            round(random.choice([20, 30, 50, 100]), 2)))
            cid += 1
    conn.executemany('INSERT INTO coupons VALUES (?,?,?,?,?,?,?,?)', coupons)

    orders, items = [], []
    oid = 1
    start = date(2024, 1, 1)
    # 按季节权重抽取订单日期：旺季订单多，淡季订单少，才有真实业务曲线
    date_pool = []
    for day_offset in range(730):
        d = start + timedelta(days=day_offset)
        weight = max(0.3, seasonal_factor(d) * (1.15 if d.weekday() >= 5 else 1.0))
        date_pool.extend([d] * max(1, int(weight * 10)))

    for i in range(20000):
        d = random.choice(date_pool)
        factor = seasonal_factor(d)
        n_items = random.choices([1, 2, 3, 4], weights=[45, 30, 18, 7])[0]
        chosen = random.sample(products, k=n_items)
        subtotal = 0.0
        iid = len(items) + 1
        for p in chosen:
            qty = random.randint(1, 4)
            sub = round(p[3] * qty, 2)
            items.append((iid, oid, p[0], qty, p[3], sub))
            subtotal += sub
            iid += 1
        discount = round(subtotal * random.choice([0, 0, 0.05, 0.1, 0.15]) * min(factor, 1.2), 2)
        actual = round(subtotal - discount, 2)
        status = random.choices(STATUS, weights=[82, 6, 5, 4, 2, 1])[0]
        orders.append((
            oid, f'SO{d:%Y%m%d}{oid:06d}', d.isoformat(),
            random.choice(customers)[0], random.choice(stores)[0], random.choice(employees)[0],
            round(subtotal, 2), discount, actual, status,
            random.choices(['微信支付', '支付宝', '银行卡', '现金'], weights=[40, 35, 20, 5])[0],
        ))
        oid += 1
    conn.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)', orders)
    conn.executemany('INSERT INTO order_items VALUES (?,?,?,?,?,?)', items)

    conn.commit()
    for t in ('stores', 'employees', 'customers', 'products', 'activities',
              'coupons', 'orders', 'order_items'):
        print(f'{t:<14} {conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]:>6} 行')
    conn.close()
    print(f'\n数据库已生成：{DATABASE_PATH}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true', help='重新生成（默认也是覆盖）')
    parser.parse_args()
    main()
