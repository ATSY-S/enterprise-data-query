"""LLM 客户端层：只负责和 DeepSeek 通信，不碰业务。

职责边界：
- 模型调用、消息构造、输出清洗
- 提示词中注入的库结构由 semantic.schema_text() 提供
"""
import logging
from functools import lru_cache
from typing import Any

from openai import OpenAI

import config
from semantic import schema_text

logger = logging.getLogger('llm_client')
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)

BASE_PROMPT = '''你是一个企业数据查询助手。用户用中文提问，你只输出一条 SQLite SELECT 语句，不要输出任何解释、注释或 Markdown。

{schema}

规则：
1. 只输出 SELECT 或 WITH 开头的单条语句，以分号结尾。
2. 禁止 INSERT/UPDATE/DELETE/DROP 等任何写操作。
3. 用户提到业务术语时，严格按上面的指标口径计算。
4. 涉及百分比时，分子分母的数据类型要处理好，避免整数除法。
5. 不确定字段属于哪张表时，严格按上面的关联关系选择。'''


@lru_cache(maxsize=1)
def full_system_prompt() -> str:
    """完整提示词（评测基线用，只算一次）。"""
    return BASE_PROMPT.format(schema=schema_text())


def build_messages(question: str, prune_schema: bool = True) -> list[dict[str, str]]:
    """构造消息。prune_schema=True 时按问题裁剪表结构。"""
    schema = schema_text(question) if prune_schema else schema_text()
    return [
        {'role': 'system', 'content': BASE_PROMPT.format(schema=schema)},
        {'role': 'user', 'content': question},
    ]


def chat(messages: list[dict[str, str]]) -> str:
    """调用模型，返回清洗后的文本。"""
    resp: Any = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=messages,
        temperature=config.LLM_TEMPERATURE,
    )
    content = resp.choices[0].message.content
    if not content:
        raise ValueError('模型返回内容为空')
    return content.strip()


def clean_sql(text: str) -> str:
    """去掉 Markdown 代码块围栏，统一以分号结尾。"""
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    return text.rstrip(';') + ';'
