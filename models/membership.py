"""
会员相关模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
import enum


class MembershipType(str, enum.Enum):
    """会员类型"""
    MONTHLY = "monthly"       # 月度会员
    QUARTERLY = "quarterly"   # 季度会员
    YEARLY = "yearly"         # 年度会员
    LIFETIME = "lifetime"     # 终身会员


class MembershipStatus(str, enum.Enum):
    """会员状态"""
    ACTIVE = "active"         # 有效
    EXPIRED = "expired"       # 已过期
    CANCELLED = "cancelled"   # 已取消
    SUSPENDED = "suspended"   # 已暂停


class MembershipLevel(Base):
    """会员等级"""
    __tablename__ = "membership_levels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # 价格设置
    monthly_price = Column(Float, nullable=True)    # 月度价格
    quarterly_price = Column(Float, nullable=True)  # 季度价格
    yearly_price = Column(Float, nullable=True)     # 年度价格
    lifetime_price = Column(Float, nullable=True)   # 终身价格
    
    # 权益设置
    benefits = Column(JSON, default=dict)  # 权益配置
    max_courses = Column(Integer, default=0)  # 最大课程数量
    max_storage = Column(Integer, default=0)  # 最大存储空间(MB)
    
    # 状态
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    memberships = relationship("UserMembership", back_populates="level")


class UserMembership(Base):
    """用户会员"""
    __tablename__ = "user_memberships"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    level_id = Column(String, ForeignKey("membership_levels.id"), nullable=False)
    
    # 会员信息
    membership_type = Column(Enum(MembershipType), nullable=False)
    status = Column(Enum(MembershipStatus), default=MembershipStatus.ACTIVE)
    
    # 时间设置
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # 终身会员为null
    auto_renew = Column(Boolean, default=False)  # 是否自动续费
    
    # 价格信息
    price = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=True)
    
    # 关系
    user = relationship("User")
    level = relationship("MembershipLevel", back_populates="memberships")
    orders = relationship("MembershipOrder", back_populates="membership", cascade="all, delete-orphan")
    
    # 唯一约束：一个用户只能有一个有效会员
    __table_args__ = (UniqueConstraint('user_id', name='uq_user_membership'),)


class MembershipOrder(Base):
    """会员订单"""
    __tablename__ = "membership_orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    membership_id = Column(String, ForeignKey("user_memberships.id"), nullable=False)
    
    # 订单信息
    order_no = Column(String(50), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False)
    payment_status = Column(String(20), default="pending")
    
    # 会员信息
    membership_type = Column(Enum(MembershipType), nullable=False)
    duration_months = Column(Integer, nullable=True)  # 时长（月），终身为null
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship("User")
    membership = relationship("UserMembership", back_populates="orders")


class MembershipBenefit(Base):
    """会员权益"""
    __tablename__ = "membership_benefits"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    
    # 权益类型
    benefit_type = Column(String(50), nullable=False)  # 权益类型
    value = Column(JSON, nullable=True)  # 权益值
    
    # 状态
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserBenefitUsage(Base):
    """用户权益使用记录"""
    __tablename__ = "user_benefit_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    benefit_id = Column(String, ForeignKey("membership_benefits.id"), nullable=False)
    
    # 使用信息
    usage_count = Column(Integer, default=0)  # 使用次数
    max_usage = Column(Integer, nullable=True)  # 最大使用次数
    reset_period = Column(String(20), nullable=True)  # 重置周期
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_reset_at = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship("User")
    benefit = relationship("MembershipBenefit")
