"""FastAPI 依赖注入：鉴权、用户上下文统一在此处理。

路由层只需声明 Depends(get_current_user) / Depends(require_admin)，
不再每个接口手写 Header 解析和角色判断。
"""
from typing import Annotated

from fastapi import Depends, Header

import auth
from exceptions import AuthenticationError, PermissionDeniedError


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    """解析 Bearer Token；未登录返回 guest 身份（查询类接口允许匿名）。"""
    if not authorization or not authorization.startswith('Bearer '):
        return {'username': 'anonymous', 'role': 'guest'}
    user = auth.verify(authorization[7:].strip())
    return user or {'username': 'anonymous', 'role': 'guest'}


def require_login(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """要求已登录。用于提交申请等需要身份的接口。"""
    if user['role'] == 'guest':
        raise AuthenticationError()
    return user


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """要求管理员角色。"""
    if user['role'] != 'admin':
        raise PermissionDeniedError('仅管理员可执行此操作')
    return user


# 常用依赖别名，减少路由层重复声明
CurrentUser = Annotated[dict, Depends(get_current_user)]
AdminUser = Annotated[dict, Depends(require_admin)]
LoggedInUser = Annotated[dict, Depends(require_login)]
