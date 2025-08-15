"""
用户模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=True)  # 改为可空，支持手机号登录
    username = Column(String(50), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)  # 手机号
    hashed_password = Column(String(255), nullable=True)  # 改为可空，支持第三方登录
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    role = Column(String(20), default='user')  # user, teacher, superadmin
    
    # 用户偏好设置
    preferences = Column(JSON, default=dict)
    
    # 密码重置
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # 关系
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    # 新增关系
    enrollments = relationship("CourseEnrollment", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("CourseFavorite", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("CourseReview", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    membership = relationship("UserMembership", back_populates="user", cascade="all, delete-orphan", uselist=False)
    balance = relationship("UserBalance", back_populates="user", cascade="all, delete-orphan", uselist=False)
    user_coupons = relationship("UserCoupon", back_populates="user", cascade="all, delete-orphan")
    benefit_usage = relationship("UserBenefitUsage", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, phone={self.phone}, email={self.email})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "role": self.role,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }