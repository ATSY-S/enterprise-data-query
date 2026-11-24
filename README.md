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

# 3. 生成数据库（8 张表，约 5.9 万行模拟数据）
python backend/init_db.py

# 4. 启动后端（新开一个终端）
cd backend
python -m uvicorn api:app --host 127.0.0.1 --port 8600

# 5. 启动前端（新开一个终端）
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:8601，用演示账号登录：
- 管理员 `admin / admin123`（可导入数据、审批申请、看全部历史）
- 普通用户 `user / user123`（可查询、可提交导入申请、只看自己的历史）

## 功能

- 中文提问 → 大模型生成 SQL → 只读执行 → 表格 / 交互式图表 / 导出
- ECharts 图表：悬停看数值、柱状/折线/饼图切换、点击放大、下载 PNG
- SQL 执行失败时自动把错误信息回灌模型修正（最多 3 次），安全类错误直接拒绝
- SQL 预览 + 人工确认模式（前端开关）
- 指标口径词典（semantic.py），让"核销率""客单价"按统一定义计算
- 数据导入：上传 Excel/CSV，预览后追加到业务表，导入后立即可查（仅管理员）
- 导入审批：普通用户上传文件并提交申请，管理员预览内容、批准/驳回、一键执行导入，全程留痕
- 角色权限：admin / user 两种角色，菜单与数据可见范围按角色区分
- 字段名中文化：图表坐标、图例与表格表头统一显示中文
- 登录页微动态背景：光斑漂移 + Canvas 鼠标粒子交互
- SQL 只读守卫，拦截写操作与注入
- 查询历史与导入记录留痕，可追溯
- 30 道随机评测脚本、标准答案判定与 A/B 消融实验

## 目录

```
backend/   后端：配置、建表、语义层、认证、导入、图表、工具、分层服务、API
data/      SQLite 业务库与历史库
eval/      随机出题、标准答案评测与 A/B 消融
frontend/  Vue 3 前端（ECharts 交互图表、登录、数据导入）
tests/     27 个单元测试
docs/      改动说明与评估文档
output/    运行产物（交付前可清空）
```

## 注意

- `.env` 含 API Key，不要提交或随代码交付；只交 `.env.example`
- 所有数据均为本地模拟生成，不含真实业务数据
- 仅支持 SELECT / WITH；多层嵌套子查询不在支持范围
