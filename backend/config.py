"""项目配置：路径与模型参数。敏感信息从 .env 读取，不写入代码。"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'output'
CHARTS_DIR = OUTPUT_DIR / 'charts'
REPORTS_DIR = OUTPUT_DIR / 'reports'
for d in (DATA_DIR, OUTPUT_DIR, CHARTS_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = str(DATA_DIR / 'enterprise.db')
HISTORY_DB = str(DATA_DIR / 'query_history.db')

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
LLM_TEMPERATURE = 0.0
MAX_SQL_RETRIES = 3
