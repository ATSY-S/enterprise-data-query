"""建表 + 生成模拟数据。运行：python init_db.py
数据全部本地生成，可复现，不依赖任何真实业务数据。
"""
import sqlite3
import random
from datetime import date, timedelta
from config import DATABASE_PATH

random.seed(20261121)

DDL = """
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS coupons;
DROP TABLE IF EXISTS activities;
DROP TABLE IF EXISTS stores;

CREATE TABLE stores (
    id INTEGER PRIMARY KEY,
    store_name TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL
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
    store_id INTEGER NOT NULL,
    receive_date TEXT NOT NULL,
    verify_date TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY(activity_id) REFERENCES activities(id),
    FOREIGN KEY(store_id) REFERENCES stores(id)
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    order_date TEXT NOT NULL,
    store_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    product_name TEXT NOT NULL,
    region TEXT NOT NULL,
    sales_amount REAL NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY(store_id) REFERENCES stores(id)
);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_category ON orders(category);
CREATE INDEX idx_coupons_activity ON coupons(activity_id);
"""

REGIONS = {
    '华东': ['上海', '杭州', '南京', '苏州'],
    '华南': ['广州', '深圳', '东莞', '佛山'],
    '华北': ['北京', '天津', '石家庄', '太原'],
    '西南': ['成都', '重庆', '昆明', '贵阳'],
}
CATEGORIES = {
    '电子产品': ['平板电脑', '蓝牙耳机', '智能手表', '充电宝'],
    '食品': ['饼干', '咖啡', '坚果礼盒', '果汁'],
    '家居': ['床上用品', '收纳箱', '台灯', '毛巾套装'],
    '服装': ['T恤', '卫衣', '牛仔裤', '外套'],
}
CHANNELS = ['微信', '抖音', '小红书', '线下门店']


def main():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript(DDL)

    stores = []
    sid = 1
    for region, cities in REGIONS.items():
        for city in cities:
            stores.append((sid, f'{city}旗舰店', region, city))
            sid += 1
    conn.executemany('INSERT INTO stores VALUES (?,?,?,?)', stores)

    activities = []
    for i in range(12):
        start = date(2025, 1, 1) + timedelta(days=30 * i)
        end = start + timedelta(days=14)
        activities.append((
            i + 1, f'2025年{start.month}月大促',
            CHANNELS[i % len(CHANNELS)],
            start.isoformat(), end.isoformat(),
            round(random.uniform(8000, 30000), 2),
        ))
    conn.executemany('INSERT INTO activities VALUES (?,?,?,?,?,?)', activities)

    coupons = []
    cid = 1
    for act in activities:
        for _ in range(random.randint(25, 55)):
            store = random.choice(stores)
            received = date.fromisoformat(act[3]) + timedelta(days=random.randint(0, 10))
            verified = received + timedelta(days=random.randint(0, 5)) if random.random() < 0.62 else None
            status = '已核销' if verified else ('已领取' if random.random() < 0.8 else '已过期')
            coupons.append((cid, act[0], store[0], received.isoformat(),
                            verified.isoformat() if verified else None, status))
            cid += 1
    conn.executemany('INSERT INTO coupons VALUES (?,?,?,?,?,?)', coupons)

    orders = []
    oid = 1
    start_date = date(2025, 1, 1)
    for i in range(2400):
        d = start_date + timedelta(days=random.randint(0, 364))
        store = random.choice(stores)
        category = random.choice(list(CATEGORIES))
        product = random.choice(CATEGORIES[category])
        orders.append((
            oid, d.isoformat(), store[0], category, product, store[2],
            round(random.uniform(80, 6000), 2), random.randint(1, 60),
        ))
        oid += 1
    conn.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)', orders)

    conn.commit()
    for t in ('stores', 'activities', 'coupons', 'orders'):
        print(f'{t}: {conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]} 行')
    conn.close()
    print(f'数据库已生成：{DATABASE_PATH}')


if __name__ == '__main__':
    main()
