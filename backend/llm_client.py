"""LLM 客户端层：只负责和 DeepSeek 通信，不碰业务。"""
import logging
from openai import OpenAI
import config
from semantic import schema_text

logger = logging.getLogger('llm_client')
client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_API_BASE)

SYSTEM_PROMPT = '''你是一个企业数据查询助手。用户用中文提问，你只输出一条 SQLite SELECT 语句，不要输出任何解释、注释或 Markdown。

{schema}

规则：
1. 只输出 SELECT 或 WITH 开头的单条语句，以分号结尾。
2. 禁止 INSERT/UPDATE/DELETE/DROP 等任何写操作。
3. 用户提到业务术语时，严格按上面的指标口径计算。
4. 涉及百分比时，分子分母的数据类型要处理好，避免整数除法。
5. 不确定字段属于哪张表时，严格按上面的关联关系选择。'''.format(schema=schema_text())


def chat(messages: list) -> str:
    resp = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=messages,
        temperature=config.LLM_TEMPERATURE,
    )
    return resp.choices[0].message.content.strip()


def build_messages(question: str) -> list:
    return [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': question},
    ]


def clean_sql(text: str) -> str:
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    return text.rstrip(';') + ';'
