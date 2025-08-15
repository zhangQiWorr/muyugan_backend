"""
认证工具模块
提供通用的认证相关函数
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from models import get_db
from models.user import User
from utils.logger import get_logger

logger = get_logger("auth_utils")
security = HTTPBearer()


def get_auth_handler():
    """获取认证处理器"""
    try:
        from main_simple import app
        return app.state.auth_handler
    except ImportError:
        # 如果main_simple不可用，尝试从main导入
        from main import app
        return app.state.auth_handler


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前认证用户（依赖注入函数）"""
    token = credentials.credentials
    auth_handler = get_auth_handler()
    return await auth_handler.get_current_user(db, token)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取当前认证用户（可选，用于公开接口）"""
    try:
        token = credentials.credentials
        auth_handler = get_auth_handler()
        return await auth_handler.get_current_user(db, token)
    except:
        return None


def check_admin_permission(user: User):
    """检查管理员权限"""
    if user.role not in ['teacher', 'superadmin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )


def check_superadmin_permission(user: User):
    """检查超级管理员权限"""
    if user.role != 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
