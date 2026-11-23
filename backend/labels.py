"""字段名中文映射：一处定义，图表与表格共用。

模型生成的 SQL 常用英文别名（verify_rate、activity_name、v、cnt 等），
直接显示在图表/表格里对业务人员不友好。这里统一映射成中文。
"""
import re

FIELD_LABELS = {
    # 业务字段
    'id': '编号', 'order_id': '订单编号', 'customer_id': '客户编号',
    'product_id': '商品编号', 'store_id': '门店编号', 'activity_id': '活动编号',
    'employee_id': '员工编号', 'order_no': '订单号',
    'order_date': '订单日期', 'receive_date': '领券日期', 'verify_date': '核销日期',
    'register_date': '注册日期', 'start_date': '开始日期', 'end_date': '结束日期',
    'store_name': '门店名称', 'store_level': '门店等级',
    'customer_name': '客户名称', 'customer_type': '客户类型', 'member_level': '会员等级',
    'product_name': '商品名称', 'category': '品类', 'unit_price': '单价',
    'cost_price': '成本价', 'subtotal': '小计', 'quantity': '销量',
    'activity_name': '活动名称', 'channel': '渠道', 'budget': '预算',
    'status': '状态', 'discount_amount': '优惠金额', 'total_amount': '标价金额',
    'actual_amount': '实付金额', 'payment_method': '支付方式',
    'role': '角色', 'name': '姓名', 'region': '地区', 'city': '城市',
    'gender': '性别', 'month': '月份', 'year': '年份', 'date': '日期',
    # 常见聚合别名
    'verify_rate': '核销率', 'sales_amount': '销售额', 'sales': '销售额',
    'total_sales': '销售总额', 'total_amount_sum': '销售总额',
    'avg_amount': '平均金额', 'avg_order': '平均订单金额', 'customer_price': '客单价',
    'gross_profit': '毛利', 'profit': '利润', 'cost': '成本',
    'order_count': '订单数', 'cnt': '数量', 'count': '数量', 'n': '数量',
    'total': '合计', 'value': '数值', 'v': '数值', 'num': '数量',
    'rate': '比率', 'ratio': '占比', 'avg': '平均值', 'sum': '合计',
    'max': '最大值', 'min': '最小值', 'revenue': '营收',
    'growth': '增长率', 'yoy': '同比增长', 'mom': '环比增长',
    'active_customers': '活跃客户数', 'customer_count': '客户数',
}

# 按优先级匹配的后缀（针对 SUM(x) AS x_sum 这类别名）
_SUFFIXES = [('_sum', '合计'), ('_count', '数量'), ('_avg', '平均'),
             ('_rate', '率'), ('_max', '最大'), ('_min', '最小')]


def label_of(col: str) -> str:
    """把字段名转成中文显示名；未知字段原样返回，不强行翻译。"""
    if not isinstance(col, str):
        return str(col)
    key = col.strip().lower()
    if key in FIELD_LABELS:
        return FIELD_LABELS[key]
    m = re.match(r'^(?:sum|avg|count|max|min)\s*\(\s*(\w+)\s*\)$', key)
    if m:
        inner = FIELD_LABELS.get(m.group(1), m.group(1))
        prefix = key.split('(')[0]
        return inner + {'sum': '合计', 'avg': '平均', 'count': '数量',
                        'max': '最大', 'min': '最小'}.get(prefix, '')
    for suffix, name in _SUFFIXES:
        if key.endswith(suffix):
            base = FIELD_LABELS.get(key[:-len(suffix)], key[:-len(suffix)])
            return base + name
    return col


def column_labels(columns: list) -> dict:
    """给前端表格表头用的映射：{原字段名: 中文名}。"""
    return {c: label_of(c) for c in columns}


if __name__ == '__main__':
    for c in ['verify_rate', 'activity_name', ' SUM(actual_amount) ', 'sales_sum', 'unknown_col']:
        print(c, '->', label_of(c))
