"""项目配置：类型安全、启动即校验、敏感信息不入库。

用 pydantic-settings 管理，支持 .env 覆盖；保留原模块级常量导出，
使已有代码（import config / from config import X）无需改动。
"""
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / '.env'


class Settings(BaseSettings):
    """应用配置。所有字段都可在 .env 中覆盖。"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    # 环境：dev / test / prod
    app_env: str = Field(default='dev', description='运行环境')

    # 模型
    deepseek_api_key: str = Field(default='', description='DeepSeek API Key')
    deepseek_api_base: str = Field(default='https://api.deepseek.com/v1')
    deepseek_model: str = Field(default='deepseek-chat')
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_sql_retries: int = Field(default=3, ge=0, le=10)

    # 服务
    api_host: str = Field(default='127.0.0.1')
    api_port: int = Field(default=8600, ge=1024, le=65535)
    cors_origins: str = Field(default='*', description='逗号分隔的允许来源')

    # 日志
    log_level: str = Field(default='INFO')

    @field_validator('app_env')
    @classmethod
    def validate_env(cls, v: str) -> str:
        if v not in {'dev', 'test', 'prod'}:
            raise ValueError(f'app_env 必须是 dev/test/prod，收到 {v}')
        return v

    @field_validator('log_level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        if v.upper() not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
            raise ValueError(f'非法日志级别: {v}')
        return v.upper()

    @property
    def is_prod(self) -> bool:
        return self.app_env == 'prod'


settings = Settings()

# ---------- 兼容别名：保持旧代码 import 不变 ----------
DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'output'
CHARTS_DIR = OUTPUT_DIR / 'charts'
REPORTS_DIR = OUTPUT_DIR / 'reports'
for d in (DATA_DIR, OUTPUT_DIR, CHARTS_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = str(DATA_DIR / 'enterprise.db')
HISTORY_DB = str(DATA_DIR / 'query_history.db')

DEEPSEEK_API_KEY = settings.deepseek_api_key
DEEPSEEK_API_BASE = settings.deepseek_api_base
DEEPSEEK_MODEL = settings.deepseek_model
LLM_TEMPERATURE = settings.llm_temperature
MAX_SQL_RETRIES = settings.max_sql_retries
LOG_LEVEL = settings.log_level
