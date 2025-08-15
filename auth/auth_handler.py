"""
主要认证处理器
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from email_validator import validate_email, EmailNotValidError
import re

from .jwt_handler import JWTHandler
from .password_handler import PasswordHandler
from .oauth_handler import OAuthHandler
from models.user import User


class AuthHandler:
    """主要认证处理器"""
    
    def __init__(self):
        self.jwt_handler = JWTHandler()
        self.password_handler = PasswordHandler()
        self.oauth_handler = OAuthHandler()
    
    async def register_user(
        self, 
        db: Session, 
        username: Optional[str] = None,
        password: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """用户注册"""
        
        # 如果未提供用户名，则自动生成一个随机用户名
        if not username:
            username = self._generate_random_username(db)
        
        # 检查用户名是否已存在
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被使用"
            )
        
        # 验证邮箱（如果提供）
        if email:
            try:
                valid_email = validate_email(email)
                email = valid_email.email
            except EmailNotValidError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的邮箱格式"
                )
            
            # 检查邮箱是否已存在
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )
        
        # 验证手机号（如果提供）
        if phone:
            if not self._validate_phone(phone):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的手机号格式"
                )
            
            # 检查手机号是否已存在
            existing_user = db.query(User).filter(User.phone == phone).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="手机号已被注册"
                )
        
        # 移除第三方登录验证（字段不存在）
        
        # 验证密码强度（如果提供密码）
        if password:
            password_validation = self.password_handler.validate_password_strength(password)
            if not password_validation["is_valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"密码强度不足: {', '.join(password_validation['errors'])}"
                )
            hashed_password = self.password_handler.hash_password(password)
        else:
            hashed_password = None
        
        # 创建用户
        user_data = {
            "username": username,
            "full_name": full_name,
            "hashed_password": hashed_password
        }
        
        if email:
            user_data["email"] = email
        
        if phone:
            user_data["phone"] = phone
        
        user = User(**user_data)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 生成访问令牌
        access_token = self.jwt_handler.create_access_token(
            data={"sub": user.id, "username": user.username}
        )
        refresh_token = self.jwt_handler.create_refresh_token(
            data={"sub": user.id}
        )
        
        return {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def authenticate_user(
        self, 
        db: Session, 
        login: str, 
        password: str
    ) -> Optional[User]:
        """用户认证（用户名/邮箱/手机号 + 密码）"""
        if not password:
            return None
        
        # 查找用户（支持用户名、邮箱、手机号登录）
        user = None
        if "@" in login:
            # 邮箱登录
            user = db.query(User).filter(User.email == login).first()
        elif re.match(r'^1[3-9]\d{9}$', login):
            # 手机号登录
            user = db.query(User).filter(User.phone == login).first()
        else:
            # 用户名登录
            user = db.query(User).filter(User.username == login).first()
        
        if not user:
            return None
        
        if not user.hashed_password:
            return None
        
        if not self.password_handler.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    async def authenticate_phone(
        self,
        db: Session,
        phone: str,
        code: str
    ) -> Optional[User]:
        """手机验证码认证（简化版本）"""
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return None
        
        # 简化验证：在实际应用中应该实现短信验证码功能
        # 目前直接返回用户，生产环境需要集成短信服务
        return user
    
    async def send_phone_code(
        self,
        db: Session,
        phone: str
    ) -> Dict[str, Any]:
        """发送手机验证码（简化版本）"""
        if not self._validate_phone(phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的手机号格式"
            )
        
        # TODO: 集成短信服务发送验证码
        # 这里应该调用短信服务API发送验证码到用户手机
        
        return {
            "message": "验证码已发送（演示模式）",
            "expires_in": 600  # 10分钟
        }
    
    async def verify_phone(
        self,
        db: Session,
        phone: str,
        code: str
    ) -> Dict[str, Any]:
        """验证手机号（简化版本）"""
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 简化验证：在实际应用中应该实现短信验证码功能
        # 目前直接验证成功，生产环境需要集成短信服务
        
        return {"message": "手机号验证成功（演示模式）"}
    
    async def bind_third_party(
        self,
        db: Session,
        user_id: str,
        platform: str,
        platform_id: str
    ) -> Dict[str, Any]:
        """绑定第三方账号（暂不支持）"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 第三方登录功能暂未实现
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="第三方账号绑定功能暂未实现"
        )
    
    async def unbind_third_party(
        self,
        db: Session,
        user_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """解绑第三方账号（暂不支持）"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 第三方登录功能暂未实现
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="第三方账号解绑功能暂未实现"
        )
    
    async def update_user_profile(
        self,
        db: Session,
        user_id: str,
        user_update: dict
    ) -> Dict[str, Any]:
        """更新用户资料"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 更新用户信息
        update_data = user_update if isinstance(user_update, dict) else user_update.__dict__
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return {
            "message": "用户资料更新成功",
            "user": user.to_dict()
        }
    
    def _validate_phone(self, phone: str) -> bool:
        """验证手机号格式"""
        return bool(re.match(r'^1[3-9]\d{9}$', phone))
    
    def _generate_random_username(self, db: Session) -> str:
        """生成随机用户名"""
        import random
        import string
        import time
        
        # 生成基于时间戳的前缀
        prefix = "user_"
        timestamp = int(time.time())
        
        # 尝试最多10次生成唯一用户名
        for _ in range(10):
            # 生成6位随机字符（数字和小写字母）
            random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            
            # 组合成用户名
            username = f"{prefix}{timestamp}_{random_chars}"
            
            # 检查是否已存在
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                return username
                
        # 如果10次尝试都失败，使用更长的随机字符串
        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        return f"{prefix}{timestamp}_{random_chars}"
    
    def _generate_phone_code(self) -> str:
        """生成6位数字验证码"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    async def login_user(
        self, 
        db: Session, 
        login: str, 
        password: str
    ) -> Dict[str, Any]:
        """用户登录（支持用户名/邮箱/手机号）"""
        
        # 查找用户（支持用户名、邮箱、手机号登录）
        user = None
        if "@" in login:
            # 邮箱登录
            user = db.query(User).filter(User.email == login).first()
        elif re.match(r'^1[3-9]\d{9}$', login):
            # 手机号登录
            user = db.query(User).filter(User.phone == login).first()
        else:
            # 用户名登录
            user = db.query(User).filter(User.username == login).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 验证密码
        if not user.hashed_password or not self.password_handler.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 检查用户状态
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被禁用"
            )
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.commit()
        
        # 生成访问令牌
        access_token = self.jwt_handler.create_access_token(
            data={"sub": user.id, "username": user.username}
        )
        refresh_token = self.jwt_handler.create_refresh_token(
            data={"sub": user.id}
        )
        
        return {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def get_current_user(self, db: Session, token: str) -> User:
        """获取当前用户"""
        payload = self.jwt_handler.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌格式"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被禁用"
            )
        
        return user
    
    async def refresh_token(self, db: Session, refresh_token: str) -> Dict[str, Any]:
        """刷新访问令牌"""
        payload = self.jwt_handler.verify_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )
        
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌类型错误"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )
        
        # 生成新的访问令牌
        new_access_token = self.jwt_handler.create_access_token(
            data={"sub": user.id, "username": user.username}
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    
    async def request_password_reset(self, db: Session, email: str) -> str:
        """请求密码重置（简化版本）"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # 即使用户不存在也返回成功，避免邮箱枚举攻击
            return "如果邮箱存在，您将收到密码重置邮件"
        
        # TODO: 实现邮件发送功能
        # 生产环境需要集成邮件服务发送重置链接
        
        return "密码重置邮件已发送（演示模式）"
    
    async def reset_password(
        self, 
        db: Session, 
        token: str, 
        new_password: str
    ) -> Dict[str, Any]:
        """重置密码（暂不支持）"""
        # 密码重置功能需要邮件服务支持，暂未实现
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="密码重置功能暂未实现"
        )
    
    async def verify_email(self, db: Session, token: str) -> Dict[str, Any]:
        """验证邮箱（暂不支持）"""
        # 邮箱验证功能需要邮件服务支持，暂未实现
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="邮箱验证功能暂未实现"
        )