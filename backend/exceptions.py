"""自定义异常体系：服务层抛异常，路由层统一转成 API 响应。

大厂实践：不用 dict 的 success 标志满地跑，用异常表达失败路径，
调用方只写 happy path，错误处理集中在中间件里。
"""
from typing import Any, Optional


class AppError(Exception):
    """所有业务异常的基类。"""

    code: int = 400
    message: str = '请求处理失败'

    def __init__(self, message: Optional[str] = None, detail: Any = None):
        self.message = message or self.message
        self.detail = detail
        super().__init__(self.message)


class ValidationError(AppError):
    """参数或输入校验失败。"""
    code = 400
    message = '参数不合法'


class AuthenticationError(AppError):
    """未登录或 Token 无效。"""
    code = 401
    message = '请先登录'


class PermissionDeniedError(AppError):
    """已登录但权限不足。"""
    code = 403
    message = '没有权限执行此操作'


class NotFoundError(AppError):
    """资源不存在。"""
    code = 404
    message = '资源不存在'


class DatabaseError(AppError):
    """数据库读写失败。"""
    code = 500
    message = '数据库操作失败'


class LLMError(AppError):
    """模型调用失败。"""
    code = 502
    message = '模型服务暂时不可用'
