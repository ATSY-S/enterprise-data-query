"""指标口径与业务术语定义（语义层的简化实现）。
大模型看到这张表，才知道「核销率」「客单价」「毛利」在公司里怎么算。
对照 JimuChatBI / SuperSonic 的 semantic layer 思路，但保持轻量。
"""
import json

METRICS = {
    "销售额": {
        "field": "orders.actual_amount",
        "agg": "SUM",
        "desc": "订单实付金额之和（已扣折扣），单位元。注意不要用 total_amount",
    },
    "订单量": {
        "field": "orders.id",
        "agg": "COUNT",
        "desc": "订单笔数，通常只统计 status='已完成' 的订单",
    },
    "销量": {
        "field": "order_items.quantity",
        "agg": "SUM",
        "desc": "售出商品件数，需通过 order_items 表统计",
    },
    "客单价": {
        "field": "orders.actual_amount",
        "agg": "AVG",
        "desc": "平均每笔订单实付金额",
    },
    "核销率": {
        "formula": "SUM(CASE WHEN coupons.status='已核销' THEN 1 ELSE 0 END)*1.0/COUNT(coupons.id)",
        "desc": "已核销券数 / 已发放券数。按渠道分析时需 JOIN activities 表",
    },
    "预算": {
        "field": "activities.budget",
        "agg": "SUM",
        "desc": "活动预算总和，单位元",
    },
    "毛利": {
        "formula": "SUM(order_items.subtotal - products.cost_price*order_items.quantity)",
        "desc": "销售额减成本，需 JOIN products 表",
    },
    "折扣金额": {
        "field": "orders.discount_amount",
        "agg": "SUM",
        "desc": "订单优惠总额",
    },
}

DIMENSIONS = {
    "地区": "orders 无地区字段，用 stores.region（JOIN orders.store_id=stores.id）",
    "城市": "stores.city",
    "品类": "products.category，查询结果需 JOIN order_items → products",
    "商品": "products.product_name",
    "渠道": "activities.channel（分析核销率时用）",
    "会员等级": "customers.member_level，取值普通/银卡/金卡/白金",
    "客户类型": "customers.customer_type，取值个人客户/企业客户",
    "门店": "stores.store_name",
    "支付方式": "orders.payment_method",
    "订单状态": "orders.status，取值已完成/已取消/已退款",
}

TERMS = {
    "近期/最近": "最近 30 天",
    "旺季": "11 月和 12 月",
    "淡季": "1 月和 2 月",
    "VIP客户": "customers.member_level IN ('金卡','白金')",
    "同比": "与去年同一时期对比",
    "环比": "与上一个相邻月份对比",
    "top": "按指标降序排列后取前 N 条",
}


# 表结构定义（单一数据源）
TABLE_SCHEMAS = {
    'stores': 'stores(id, store_name, region, city, store_level)',
    'employees': 'employees(id, name, store_id, role)',
    'customers': 'customers(id, customer_name, customer_type, member_level, city, register_date)',
    'products': 'products(id, product_name, category, unit_price, cost_price)',
    'activities': 'activities(id, activity_name, channel, start_date, end_date, budget)',
    'coupons': 'coupons(id, activity_id, customer_id, store_id, receive_date, verify_date, status, discount_amount)',
    'orders': 'orders(id, order_no, order_date, customer_id, store_id, employee_id, total_amount, discount_amount, actual_amount, status, payment_method)',
    'order_items': 'order_items(id, order_id, product_id, quantity, unit_price, subtotal)',
}

JOINS = [
    '- orders.customer_id = customers.id',
    '- orders.store_id = stores.id',
    '- orders.employee_id = employees.id',
    '- order_items.order_id = orders.id',
    '- order_items.product_id = products.id',
    '- coupons.activity_id = activities.id',
    '- coupons.customer_id = customers.id',
    '- coupons.store_id = stores.id',
]

# 业务关键词 → 相关表（用于表结构裁剪）
TABLE_KEYWORDS = {
    'orders': ['订单', '销售额', '实付', '金额', '支付', '订单量', '客单价', '月', '日期', '趋势', '渠道销售'],
    'order_items': ['销量', '明细', '商品销售', '品类', '毛利', '成本', '件数'],
    'customers': ['客户', '会员', 'vip', '注册', '客户类型', '白金', '金卡'],
    'products': ['商品', '品类', '单价', '成本', '毛利', '产品'],
    'activities': ['活动', '预算', '渠道核销', '营销', '活动名称'],
    'coupons': ['券', '核销', '领券', '优惠'],
    'stores': ['门店', '地区', '城市', '区域'],
    'employees': ['员工', '店员', '医生', '职员'],
}

# 这些表几乎任何业务查询都可能用到，始终保留
CORE_TABLES = {'orders'}


def _select_tables(question: str) -> list[str]:
    """按问题关键词选表；命中不到时退回全部表，保证不漏。"""
    if not question:
        return list(TABLE_SCHEMAS)
    q = question.lower()
    selected = set(CORE_TABLES)
    for table, keywords in TABLE_KEYWORDS.items():
        if any(k in q for k in keywords):
            selected.add(table)
    # 核销率/品类等需要 JOIN，补上关联表
    if 'coupons' in selected or '活动' in q:
        selected.add('activities')
    if 'order_items' in selected or '毛利' in q:
        selected.add('products')
    if '地区' in q or '城市' in q or '门店' in q:
        selected.add('stores')
    return [t for t in TABLE_SCHEMAS if t in selected]


def _build_schema(tables: list[str]) -> str:
    lines = [
        f"数据库为 SQLite，当前问题相关表 {len(tables)} 张。只允许 SELECT，禁止任何 DML/DDL。",
        "",
        "表结构：",
    ]
    lines.extend(TABLE_SCHEMAS[t] for t in tables)
    lines.extend(["", "已验证的关联关系（只能使用这些 JOIN）："])
    table_set = set(tables)
    for join in JOINS:
        if any(join.find(f'{t}.') >= 0 for t in table_set):
            lines.append(join)
    lines.extend(["", "业务指标口径（用户提到这些词时严格按此计算）："])
    for name, meta in METRICS.items():
        expr = meta.get('formula') or f"{meta['agg']}({meta['field']})"
        lines.append(f"- {name}：{expr}。{meta['desc']}")
    lines.append("")
    lines.append("业务维度与术语：")
    for name, desc in DIMENSIONS.items():
        lines.append(f"- {name}：{desc}")
    for name, desc in TERMS.items():
        lines.append(f"- {name}：{desc}")
    return '\n'.join(lines)


def schema_text(question: str | None = None) -> str:
    """生成给大模型看的库结构说明。

    question 为空时返回完整 8 张表（兼容旧调用与评测脚本）；
    传入问题时按关键词裁剪，减少提示词长度。
    """
    tables = _select_tables(question) if question else list(TABLE_SCHEMAS)
    return _build_schema(tables)


def selected_tables(question: str) -> list[str]:
    """暴露给评测：查看裁剪结果。"""
    return _select_tables(question)


if __name__ == '__main__':
    print(schema_text())
