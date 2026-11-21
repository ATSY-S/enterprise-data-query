"""兼容层：保留旧的 agent.query / generate_sql 接口，实际实现已拆分到：
- llm_client.py   模型通信
- sql_service.py  生成、纠错、错误分类
- query_service.py 查询编排与后处理
"""
from sql_service import classify_error, failure_advice
from query_service import query, preview as generate_sql

__all__ = ['query', 'generate_sql', 'classify_error', 'failure_advice']
