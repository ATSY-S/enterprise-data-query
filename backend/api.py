"""API 路由层：只做参数校验、鉴权声明、调用服务、封装响应。

大厂规范要点：
- 路由不含业务逻辑（统计、语义格式化、SQL 编排都在 service 层）
- 鉴权用 FastAPI Depends，不重复手写 Header 解析
- 业务异常由全局处理器统一转响应（exceptions.py）
- 每个请求带 request_id，日志可追踪
- 类型注解完整
"""
import json
from typing import Any

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import auth
import cache_service
import import_service
import query_service
import request_service
import stats_service
from dependencies import AdminUser, CurrentUser, LoggedInUser
from exceptions import AppError, NotFoundError
from logging_config import get_logger, new_request_id, setup_logging
from labels import column_labels
from schemas import (ApiResponse, ExecuteRequest, ImportRequest, LoginRequest,
                     QueryRequest, ReviewRequest, SQLRequest)
from tools import execute_sql, get_statistics, list_history
from chart_service import build_chart

setup_logging()
logger = get_logger('api')

app = FastAPI(title='企业数据智能查询系统 API', version='3.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in __import__('config').settings.cors_origins.split(',')],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ---------- 中间件与异常处理 ----------
@app.middleware('http')
async def request_context(request, call_next):
    rid = new_request_id()
    response = await call_next(request)
    response.headers['X-Request-ID'] = rid
    return response


@app.exception_handler(AppError)
async def app_error_handler(_request, exc: AppError):
    logger.warning('业务异常: %s | detail=%s', exc.message, exc.detail)
    return JSONResponse(
        status_code=exc.code,
        content={'code': exc.code, 'message': exc.message, 'data': exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={'code': 400, 'message': '参数校验失败', 'data': exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={'code': exc.status_code, 'message': str(exc.detail), 'data': None},
    )


def ok(data: Any) -> ApiResponse:
    return ApiResponse(data=data)


auth.init_users()


# ---------- 健康检查 ----------
@app.get('/api/health')
def health() -> ApiResponse:
    return ok({'status': 'ok'})


# ---------- 认证 ----------
@app.post('/api/login')
def login(req: LoginRequest) -> ApiResponse:
    result = auth.login(req.username, req.password)
    if result['success']:
        logger.info('登录成功: %s', result['username'])
    return ok(result)


@app.post('/api/logout')
def logout(authorization: str | None = Header(None)) -> ApiResponse:
    if authorization and authorization.startswith('Bearer '):
        auth.logout(authorization[7:].strip())
    return ok({'success': True})


@app.get('/api/me')
def me(user: CurrentUser) -> ApiResponse:
    return ok(user)


@app.get('/api/users')
def users(_admin: AdminUser) -> ApiResponse:
    return ok(auth.list_users())


# ---------- 查询 ----------
@app.post('/api/preview')
def preview(req: SQLRequest, _user: CurrentUser) -> ApiResponse:
    """只生成 SQL，不执行（人工确认模式第一步）。"""
    return ok(query_service.preview(req.question))


@app.post('/api/execute')
def execute(req: ExecuteRequest, _user: CurrentUser) -> ApiResponse:
    """执行用户确认过的 SQL。"""
    result = execute_sql(req.sql)
    payload: dict[str, Any] = {
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
def query(req: QueryRequest, user: CurrentUser) -> ApiResponse:
    logger.info('query: %s by %s', req.question, user['username'])
    return ok(query_service.query(req.question, req.want_chart, req.want_export,
                                  username=user['username']))


@app.get('/api/history')
def history(user: CurrentUser, limit: int = 20) -> ApiResponse:
    return ok(list_history(limit, username=user['username'], role=user['role']).get('data', []))


# ---------- 概览与语义层 ----------
@app.get('/api/tables')
def tables(_user: CurrentUser) -> ApiResponse:
    return ok(import_service.table_info())


@app.get('/api/stats')
def stats(_user: CurrentUser) -> ApiResponse:
    return ok(stats_service.overview())


@app.get('/api/semantics')
def semantics(_user: CurrentUser) -> ApiResponse:
    return ok(stats_service.semantics())


@app.get('/api/cache')
def cache_info(_admin: AdminUser) -> ApiResponse:
    """缓存命中统计（管理员可看，便于评测与优化）。"""
    return ok(cache_service.cache_info())


@app.post('/api/cache/clear')
def cache_clear(_admin: AdminUser) -> ApiResponse:
    cache_service.invalidate()
    return ok({'success': True, 'message': '缓存已清空'})


# ---------- 数据接入 ----------
@app.post('/api/import/preview')
async def import_preview(file: UploadFile = File(...)) -> ApiResponse:
    result = import_service.parse_upload(file.filename or '', await file.read())
    result.pop('_df', None)
    return ok(result)


@app.post('/api/import/commit')
async def import_commit(
    _admin: AdminUser,
    file: UploadFile = File(...),
    table: str = Form(...),
) -> ApiResponse:
    parsed = import_service.parse_upload(file.filename or '', await file.read())
    if not parsed['success']:
        return ok(parsed)
    result = import_service.import_rows(parsed['_df'], table, parsed['columns'])
    if result['success']:
        cache_service.invalidate()
    return ok(result)


@app.get('/api/import/history')
def import_log(_admin: AdminUser) -> ApiResponse:
    return ok(import_service.import_history())


# ---------- 导入申请与审批 ----------
@app.post('/api/requests')
async def submit_request(
    user: LoggedInUser,
    file: UploadFile = File(...),
    table: str = Form(...),
    reason: str = Form(''),
) -> ApiResponse:
    result = request_service.submit(user['username'], file.filename or '', table, reason, await file.read())
    return ok(result)


@app.get('/api/requests')
def list_requests(user: CurrentUser, status: str | None = None) -> ApiResponse:
    return ok(request_service.list_requests(applicant=user['username'],
                                            role=user['role'], status=status))


@app.get('/api/requests/pending-count')
def pending_count(user: CurrentUser) -> ApiResponse:
    count = request_service.pending_count() if user['role'] == 'admin' else 0
    return ok({'count': count})


@app.get('/api/requests/{request_id}/preview')
def preview_request_file(request_id: int, _admin: AdminUser) -> ApiResponse:
    return ok(request_service.preview_file(request_id))


@app.post('/api/requests/{request_id}/review')
def review_request(request_id: int, req: ReviewRequest, admin: AdminUser) -> ApiResponse:
    return ok(request_service.review(request_id, admin['username'], req.approve, req.note))


@app.post('/api/requests/{request_id}/import')
def import_request_file(request_id: int, admin: AdminUser) -> ApiResponse:
    result = request_service.import_approved(request_id, admin['username'])
    if result['success']:
        cache_service.invalidate()
    return ok(result)


# ---------- 文件下载 ----------
@app.get('/api/file')
def download(path: str) -> FileResponse:
    from pathlib import Path
    p = Path(path).resolve()
    base = Path(__file__).resolve().parent.parent / 'output'
    if base not in p.parents or not p.exists():
        raise NotFoundError('文件不存在或无权访问')
    return FileResponse(p, filename=p.name)


if __name__ == '__main__':
    import uvicorn
    from config import settings
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
