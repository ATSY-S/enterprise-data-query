# 企业数据智能查询系统

基于大语言模型的数据库自然语言查询与可视化系统（毕业设计）

## 快速开始

```bash
# 1. 建虚拟环境（Python 3.10+）
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置模型
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 生成数据库（4 张表，约 2942 行模拟数据）
python backend/init_db.py

# 4. 启动后端（新开一个终端）
cd backend
python -m uvicorn api:app --host 127.0.0.1 --port 8600

# 5. 启动前端（新开一个终端）
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:8601

## 功能

- 中文提问 → 大模型生成 SQL → 只读执行 → 表格 / 图表 / 导出
- SQL 执行失败时自动把错误信息回灌模型修正（最多 3 次）
- 指标口径词典（semantic.py），让"核销率""客单价"按统一定义计算
- SQL 只读守卫，拦截写操作与注入
- 查询历史留痕，可追溯
- 30 道评测脚本与 A/B 消融实验

## 目录

```
backend/   后端：配置、建表、语义层、工具、Agent、API
data/      SQLite 业务库与历史库
eval/      评测题与评测脚本
frontend/  Vue 3 前端
docs/      改动说明
output/    运行产物（交付前可清空）
```

## 注意

- `.env` 含 API Key，不要提交或随代码交付；只交 `.env.example`
- 所有数据均为本地模拟生成，不含真实业务数据
- 仅支持 SELECT / WITH；多层嵌套子查询不在支持范围
