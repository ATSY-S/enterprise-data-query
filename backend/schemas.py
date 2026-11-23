"""Pydantic 模型：统一 API 的请求/响应契约。"""
from pydantic import BaseModel, Field


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


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class ImportRequest(BaseModel):
    table: str = Field(..., min_length=1, max_length=50)
    filename: str = Field('', max_length=200)
    reason: str = Field('', max_length=300)
    mode: str = 'append'


class ReviewRequest(BaseModel):
    approve: bool
    note: str = ''


class ApiResponse(BaseModel):
    code: int = 0
    message: str = 'ok'
    data: object = None


class QueryResult(BaseModel):
    question: str
    sql: str
    success: bool
    columns: list = []
    data: list = []
    row_count: int = 0
    retries: int = 0
    error_type: str | None = None
    elapsed: float = 0.0
    message: str = ''
    advice: str = ''
    statistics: dict | None = None
    chart_path: str | None = None
    export_path: str | None = None
