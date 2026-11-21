"""API 路由层：只做参数校验、调用服务、封装响应。不含业务逻辑。"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

import query_service
from schemas import QueryRequest, SQLRequest, ExecuteRequest, ApiResponse
from tools import execute_sql, get_statistics, generate_chart, list_history
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('api')

app = FastAPI(title='企业数据智能查询系统 API', version='1.2')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


def ok(data):
    return ApiResponse(data=data)


@app.get('/api/health')
def health():
    return ok({'status': 'ok'})


@app.post('/api/preview')
def preview(req: SQLRequest):
    """只生成 SQL，不执行（人工确认模式第一步）。"""
    logger.info('preview: %s', req.question)
    return ok(query_service.preview(req.question))


@app.post('/api/execute')
def execute(req: ExecuteRequest):
    """执行用户确认过的 SQL。"""
    logger.info('execute confirmed SQL for: %s', req.question)
    result = execute_sql(req.sql)
    payload = {
        'question': req.question, 'sql': req.sql,
        'success': result['success'], 'columns': result['columns'],
        'data': result['data'], 'row_count': result['row_count'],
        'message': result['message'], 'retries': 0, 'error_type': None,
        'advice': '' if result['success'] else 'SQL 执行失败，请检查后重新预览。',
    }
    if result['success'] and result['data']:
        data_json = json.dumps(result['data'], ensure_ascii=False)
        payload['statistics'] = get_statistics(data_json).get('data', {})
        if req.want_chart:
            chart = generate_chart(data_json, title=req.question[:20])
            if chart['success']:
                payload['chart_path'] = chart['path']
    return ok(payload)


@app.post('/api/query')
def query(req: QueryRequest):
    logger.info('query: %s', req.question)
    return ok(query_service.query(req.question, req.want_chart, req.want_export))


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
