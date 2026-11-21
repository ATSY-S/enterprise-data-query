"""指标口径与业务术语定义（语义层的简化实现）。
大模型看到这张表，才知道「核销率」「客单价」在你们公司怎么算。
"""
import json
from pathlib import Path

METRICS = {
    "销售额": {
        "field": "orders.sales_amount",
        "agg": "SUM",
        "desc": "订单实付金额之和，单位为元",
    },
    "订单量": {
        "field": "orders.id",
        "agg": "COUNT",
        "desc": "订单笔数",
    },
    "销量": {
        "field": "orders.quantity",
        "agg": "SUM",
        "desc": "售出商品件数",
    },
    "客单价": {
        "field": "orders.sales_amount",
        "agg": "AVG",
        "desc": "平均每个订单的实付金额",
    },
    "核销率": {
        "formula": "COUNT( coupons.status='已核销' ) * 1.0 / COUNT( coupons.id )",
        "desc": "已核销优惠券数 / 已领取优惠券总数。分子分母都要按 activity_id 过滤到同一活动",
    },
    "预算": {
        "field": "activities.budget",
        "agg": "SUM",
        "desc": "活动预算金额，单位为元",
    },
}

DIMENSIONS = {
    "地区": "orders.region，取值为华东/华南/华北/西南",
    "品类": "orders.category，取值为电子产品/食品/家居/服装",
    "渠道": "activities.channel，取值为微信/抖音/小红书/线下门店",
    "门店": "stores.store_name，需通过 orders.store_id 或 coupons.store_id 关联",
    "活动": "activities.activity_name，需通过 coupons.activity_id 关联",
}

TERMS = {
    "近期": "最近 30 天",
    "上个月": "按 order_date 或 receive_date 取上一个自然月",
    "同比": "与去年同一时期对比",
    "环比": "与上一个相邻时期对比",
    "top": "按指标降序排列后取前 N 条",
}


def schema_text() -> str:
    """生成给大模型看的数据库结构说明。"""
    lines = [
        "数据库共 4 张表，使用 SQLite。只允许 SELECT，禁止任何 DML/DDL。",
        "",
        "表结构：",
        "orders(id, order_date, store_id, category, product_name, region, sales_amount, quantity)",
        "activities(id, activity_name, channel, start_date, end_date, budget)",
        "coupons(id, activity_id, store_id, receive_date, verify_date, status)",
        "stores(id, store_name, region, city)",
        "",
        "字段说明与已验证的关联关系：",
        "- orders.store_id = stores.id（订单 → 门店）",
        "- coupons.activity_id = activities.id（优惠券 → 活动）",
        "- coupons.store_id = stores.id（优惠券 → 门店）",
        "- orders.region 与 stores.region 含义相同；按「地区」筛选用 orders.region 即可",
        "",
        "业务指标口径（用户提到这些词时严格按此计算）：",
    ]
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


if __name__ == '__main__':
    print(schema_text())
