"""API 路由层：只做鉴权、参数校验、调用服务、封装响应。不含业务逻辑。"""
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import auth
import import_service
import query_service
import request_service
from chart_service import build_chart
from labels import column_labels
from semantic import METRICS, DIMENSIONS, TERMS
from schemas import (QueryRequest, SQLRequest, ExecuteRequest, ApiResponse,
                     LoginRequest, ImportRequest, ReviewRequest)
from tools import execute_sql, get_statistics, list_history

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('api')

app = FastAPI(title='企业数据智能查询系统 API', version='2.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
auth.init_users()


def ok(data):
    return ApiResponse(data=data)


def current_user(authorization: str | None) -> dict:
    """从 Authorization: Bearer <token> 解析用户；未登录时用匿名身份。"""
    if not authorization or not authorization.startswith('Bearer '):
        return {'username': 'anonymous', 'role': 'guest'}
    user = auth.verify(authorization[7:].strip())
    return user or {'username': 'anonymous', 'role': 'guest'}


def require_admin(authorization: str | None) -> dict:
    user = current_user(authorization)
    if user['role'] != 'admin':
        raise HTTPException(403, '仅管理员可执行此操作')
    return user


@app.get('/api/health')
def health():
    return ok({'status': 'ok'})


# ---------- 认证 ----------
@app.post('/api/login')
def login(req: LoginRequest):
    result = auth.login(req.username, req.password)
    if not result['success']:
        return ok(result)
    logger.info('登录成功: %s', result['username'])
    return ok(result)


@app.post('/api/logout')
def logout(authorization: str | None = Header(None)):
    if authorization and authorization.startswith('Bearer '):
        auth.logout(authorization[7:].strip())
    return ok({'success': True})


@app.get('/api/me')
def me(authorization: str | None = Header(None)):
    return ok(current_user(authorization))


@app.get('/api/users')
def users(authorization: str | None = Header(None)):
    require_admin(authorization)
    return ok(auth.list_users())


# ---------- 查询 ----------
@app.post('/api/preview')
def preview(req: SQLRequest, authorization: str | None = Header(None)):
    """只生成 SQL，不执行（人工确认模式第一步）。"""
    logger.info('preview: %s', req.question)
    return ok(query_service.preview(req.question))


@app.post('/api/execute')
def execute(req: ExecuteRequest, authorization: str | None = Header(None)):
    user = current_user(authorization)
    result = execute_sql(req.sql)
    payload = {
        'question': req.question, 'sql': req.sql,
        'success': result['success'], 'columns': result['columns'],
        'column_labels': column_labels(result['columns']),
        'data': result['data'], 'row_count': result['row_count'],
        'message': result['message'], 'retries': 0, 'error_type': None,
        'advice': '' if result['success'] else 'SQL 执行失败，请检查后重新预览。',
    }
    if result['success'] and result['data']:
        data_json = json.dumps(result['data'], ensure_ascii=False, default=str)
        payload['statistics'] = get_statistics(data_json).get('data', {})
        if req.want_chart:
            payload['chart'] = build_chart(result['data'], result['columns'],
                                           title=req.question[:40], hint=req.question)
    return ok(payload)


@app.post('/api/query')
def query(req: QueryRequest, authorization: str | None = Header(None)):
    user = current_user(authorization)
    logger.info('query: %s by %s', req.question, user['username'])
    return ok(query_service.query(req.question, req.want_chart, req.want_export,
                                  username=user['username']))


@app.get('/api/history')
def history(limit: int = 20, authorization: str | None = Header(None)):
    user = current_user(authorization)
    return ok(list_history(limit, username=user['username'], role=user['role']).get('data', []))


# ---------- 数据接入 ----------
@app.get('/api/tables')
def tables(authorization: str | None = Header(None)):
    return ok(import_service.table_info())


@app.get('/api/semantics')
def semantics(authorization: str | None = Header(None)):
    """语义层定义：指标口径、业务维度、术语（前端指标页读取真实数据）。"""
    def metric_expr(v):
        if v.get('formula'):
            return v['formula']
        if v.get('field') and v.get('agg'):
            return f"{v['agg']}({v['field']})"
        return v.get('field', '')

    metrics = [{'name': k, 'expr': metric_expr(v), 'desc': v.get('desc', '')}
               for k, v in METRICS.items()]
    dims = [{'name': k, 'desc': v} for k, v in DIMENSIONS.items()]
    terms = [{'name': k, 'desc': v} for k, v in TERMS.items()]
    return ok({'metrics': metrics, 'dimensions': dims, 'terms': terms})


@app.post('/api/import/preview')
async def import_preview(file: UploadFile = File(...)):
    content = await file.read()
    result = import_service.parse_upload(file.filename or '', content)
    result.pop('_df', None)
    return ok(result)


@app.post('/api/import/commit')
async def import_commit(file: UploadFile = File(...), table: str = Form(...),
                        authorization: str | None = Header(None)):
    user = require_admin(authorization)
    content = await file.read()
    parsed = import_service.parse_upload(file.filename or '', content)
    if not parsed['success']:
        return ok(parsed)
    result = import_service.import_rows(parsed['_df'], table, parsed['columns'])
    logger.info('数据导入: table=%s by=%s result=%s', table, user['username'], result['success'])
    return ok(result)


@app.get('/api/import/history')
def import_log(authorization: str | None = Header(None)):
    require_admin(authorization)
    return ok(import_service.import_history())


# ---------- 导入申请与审批 ----------
@app.post('/api/requests')
async def submit_request(file: UploadFile = File(...), table: str = Form(...),
                         reason: str = Form(''), authorization: str | None = Header(None)):
    user = current_user(authorization)
    if user['role'] == 'guest':
        raise HTTPException(401, '请先登录')
    content = await file.read()
    result = request_service.submit(user['username'], file.filename or '', table, reason, content)
    logger.info('导入申请: %s by %s -> %s', file.filename, user['username'], result['success'])
    return ok(result)


@app.get('/api/requests')
def list_requests(status: str = None, authorization: str | None = Header(None)):
    user = current_user(authorization)
    return ok(request_service.list_requests(applicant=user['username'],
                                            role=user['role'], status=status))


@app.get('/api/requests/pending-count')
def pending_count(authorization: str | None = Header(None)):
    user = current_user(authorization)
    if user['role'] != 'admin':
        return ok({'count': 0})
    return ok({'count': request_service.pending_count()})


@app.get('/api/requests/{request_id}/preview')
def preview_request_file(request_id: int, authorization: str | None = Header(None)):
    require_admin(authorization)
    return ok(request_service.preview_file(request_id))


@app.post('/api/requests/{request_id}/review')
def review_request(request_id: int, req: ReviewRequest, authorization: str | None = Header(None)):
    user = require_admin(authorization)
    result = request_service.review(request_id, user['username'], req.approve, req.note)
    logger.info('审批申请 #%s by %s -> %s', request_id, user['username'], result['success'])
    return ok(result)


@app.post('/api/requests/{request_id}/import')
def import_request_file(request_id: int, authorization: str | None = Header(None)):
    user = require_admin(authorization)
    result = request_service.import_approved(request_id, user['username'])
    logger.info('执行申请导入 #%s by %s -> %s', request_id, user['username'], result['success'])
    return ok(result)


@app.get('/api/file')
def download(path: str):
    p = Path(path).resolve()
    # 只允许下载 output 目录下的文件，防止路径穿越
    base = Path(__file__).resolve().parent.parent / 'output'
    if base not in p.parents or not p.exists():
        raise HTTPException(404, '文件不存在或无权访问')
    return FileResponse(p, filename=p.name)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8600)
