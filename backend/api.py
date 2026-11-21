"""FastAPI 服务：查询、SQL 预览、历史、文件下载。"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path

import agent
from tools import list_history

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('api')

app = FastAPI(title='企业数据智能查询系统 API', version='1.1')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=300)
    want_chart: bool = True
    want_export: bool = False


class SQLRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=300)


class ExecuteRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=300)
    sql: str = Field(..., min_length=1, max_length=4000)
    want_chart: bool = True


def ok(data):
    return {'code': 0, 'message': 'ok', 'data': data}


@app.get('/api/health')
def health():
    return ok({'status': 'ok'})


@app.post('/api/preview')
def preview(req: SQLRequest):
    """只生成 SQL，不执行。用户可以先看清楚要跑什么。"""
    logger.info('preview: %s', req.question)
    return ok(agent.generate_sql(req.question))


@app.post('/api/execute')
def execute(req: ExecuteRequest):
    """执行用户在界面上确认过的 SQL。"""
    from tools import execute_sql, get_statistics, generate_chart
    import json
    result = execute_sql(req.sql)
    payload = {
        'question': req.question,
        'sql': req.sql,
        'success': result['success'],
        'columns': result['columns'],
        'data': result['data'],
        'row_count': result['row_count'],
        'message': result['message'],
        'retries': 0,
        'error_type': None,
        'advice': '' if result['success'] else 'SQL 执行失败，请检查后重新预览。',
    }
    if result['success'] and result['data']:
        payload['statistics'] = get_statistics(json.dumps(result['data'], ensure_ascii=False)).get('data', {})
        if req.want_chart:
            chart = generate_chart(json.dumps(result['data'], ensure_ascii=False), title=req.question[:20])
            if chart['success']:
                payload['chart_path'] = chart['path']
    return ok(payload)


@app.post('/api/query')
def query(req: QueryRequest):
    logger.info('query: %s', req.question)
    return ok(agent.query(req.question, req.want_chart, req.want_export))


@app.get('/api/history')
def history(limit: int = 20):
    return ok(list_history(limit).get('data', []))


@app.get('/api/file')
def download(path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, '文件不存在')
    return FileResponse(p, filename=p.name)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8600)
