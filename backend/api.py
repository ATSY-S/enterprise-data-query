"""FastAPI 服务：给前端提供查询、历史、文件下载接口。"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

import agent
from tools import list_history

app = FastAPI(title='企业数据智能查询系统 API', version='1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


class QueryRequest(BaseModel):
    question: str
    want_chart: bool = True
    want_export: bool = False


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.post('/api/query')
def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(400, '问题不能为空')
    return agent.query(req.question, req.want_chart, req.want_export)


@app.get('/api/history')
def history(limit: int = 20):
    return list_history(limit)


@app.get('/api/file')
def download(path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, '文件不存在')
    return FileResponse(p, filename=p.name)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8600)
