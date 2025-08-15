"""
用户认证相关API
包含注册、登录、密码重置等功能
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from models import get_db
from models.user import User
from models.schemas import (
    UserCreate, UserLogin, PhoneLogin, SendSmsCode, 
    UserUpdate, SuccessResponse
)
from utils.logger import get_logger
from utils.file_upload import save_avatar_file, delete_avatar_files, get_default_avatar_url

logger = get_logger("auth_api")
router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer()


def get_auth_handler():
    """获取认证处理器"""
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


@router.post("/register", response_model=dict)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    auth_handler = get_auth_handler()
    
    # 验证必填字段
    if not user_data.password and not user_data.phone:
        raise HTTPException(status_code=400, detail="至少需要提供密码或手机号之一")
    
    # 用户名由后端自动生成
    return await auth_handler.register_user(
        db=db,
        username=None,  # 用户名由后端自动生成
        password=user_data.password,
        email=user_data.email,
        phone=user_data.phone,
        full_name=user_data.full_name
    )


@router.post("/login", response_model=dict)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录（用户名/邮箱/手机号 + 密码）"""
    auth_handler = get_auth_handler()
    
    if not user_data.password:
        raise HTTPException(status_code=400, detail="密码不能为空")
    
    return await auth_handler.login_user(
        db=db,
        login=user_data.login,
        password=user_data.password
    )


@router.post("/login/phone", response_model=dict)
async def login_with_phone(user_data: PhoneLogin, db: Session = Depends(get_db)):
    """手机验证码登录"""
    auth_handler = get_auth_handler()
    
    user = await auth_handler.authenticate_phone(
        db=db,
        phone=user_data.phone,
        code=user_data.code
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="验证码无效或已过期"
        )
    
    # 生成访问令牌
    jwt_handler = auth_handler.jwt_handler
    access_token = jwt_handler.create_access_token(
        data={"sub": user.id, "username": user.username}
    )
    refresh_token = jwt_handler.create_refresh_token(
        data={"sub": user.id}
    )
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/sms/send", response_model=dict)
async def send_sms_code(request: SendSmsCode, db: Session = Depends(get_db)):
    """发送手机验证码"""
    auth_handler = get_auth_handler()
    return await auth_handler.send_phone_code(db, request.phone)


@router.post("/sms/verify", response_model=dict)
async def verify_sms_code(request: PhoneLogin, db: Session = Depends(get_db)):
    """验证手机验证码"""
    auth_handler = get_auth_handler()
    return await auth_handler.verify_phone(db, request.phone, request.code)


@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """刷新访问令牌"""
    auth_handler = get_auth_handler()
    return await auth_handler.refresh_token(db, refresh_token)


@router.post("/password-reset-request")
async def request_password_reset(email: str, db: Session = Depends(get_db)):
    """请求密码重置"""
    auth_handler = get_auth_handler()
    token = await auth_handler.request_password_reset(db, email)
    return {"message": "如果邮箱存在，您将收到密码重置邮件", "reset_token": token}


@router.post("/password-reset")
async def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    """重置密码"""
    auth_handler = get_auth_handler()
    return await auth_handler.reset_password(db, token, new_password)


@router.post("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """验证邮箱"""
    auth_handler = get_auth_handler()
    return await auth_handler.verify_email(db, token)


# 第三方登录绑定功能已移除，因为数据库中不存在对应字段


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user.to_dict()


@router.put("/me", response_model=dict)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户资料"""
    auth_handler = get_auth_handler()
    return await auth_handler.update_user_profile(db, current_user.id, user_update)




@router.post("/avatar", response_model=dict)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传用户头像"""
    try:
        # 保存头像文件
        avatar_data = await save_avatar_file(file, current_user.id)
        
        # 删除旧头像
        if current_user.avatar_url and current_user.avatar_url != get_default_avatar_url():
            delete_avatar_files(current_user.avatar_url)
        
        # 更新用户头像（使用medium尺寸作为主头像）
        current_user.avatar_url = avatar_data["medium"]
        db.commit()
        
        return {
            "message": "头像上传成功", 
            "avatar_url": avatar_data["medium"],
            "avatar_urls": avatar_data  # 返回所有尺寸的头像URL
        }
    except Exception as e:
        logger.error(f"头像上传失败: {e}")
        raise HTTPException(status_code=500, detail="头像上传失败")


@router.delete("/avatar", response_model=dict)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户头像"""
    try:
        # 删除头像文件
        if current_user.avatar_url and current_user.avatar_url != get_default_avatar_url():
            delete_avatar_files(current_user.avatar_url)
        
        # 设置默认头像
        current_user.avatar_url = get_default_avatar_url()
        db.commit()
        
        return {"message": "头像已删除，已设置为默认头像"}
    except Exception as e:
        logger.error(f"头像删除失败: {e}")
        raise HTTPException(status_code=500, detail="头像删除失败")


@router.post("/logout", response_model=SuccessResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出"""
    # 这里可以将token加入黑名单
    # 暂时只返回成功消息
    return SuccessResponse(message="登出成功")