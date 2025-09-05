"""促销策略相关模型定义"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
import enum


class PromotionType(str, enum.Enum):
    """促销类型"""
    PERCENTAGE = "percentage"  # 百分比折扣
    FIXED_AMOUNT = "fixed_amount"  # 固定金额折扣
    LIMITED_TIME = "limited_time"  # 限时折扣
    FLASH_SALE = "flash_sale"  # 闪购
    BUNDLE = "bundle"  # 套餐优惠


class PromotionStatus(str, enum.Enum):
    """促销状态"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 激活
    PAUSED = "paused"  # 暂停
    EXPIRED = "expired"  # 已过期
    CANCELLED = "cancelled"  # 已取消


class CoursePromotion(Base):
    """课程促销策略"""
    __tablename__ = "course_promotions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    
    # 促销基本信息
    title = Column(String(200), nullable=False)  # 促销标题
    description = Column(Text, nullable=True)  # 促销描述
    promotion_type = Column(Enum(PromotionType), nullable=False)
    status = Column(Enum(PromotionStatus), default=PromotionStatus.DRAFT)
    
    # 折扣设置
    discount_percentage = Column(Float, nullable=True)  # 折扣百分比 (0-100)
    discount_amount = Column(Float, nullable=True)  # 固定折扣金额
    min_price = Column(Float, default=0.0)  # 最低价格限制
    max_discount = Column(Float, nullable=True)  # 最大折扣金额
    
    # 时间设置
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # 限制条件
    usage_limit = Column(Integer, nullable=True)  # 使用次数限制
    used_count = Column(Integer, default=0)  # 已使用次数
    per_user_limit = Column(Integer, default=1)  # 每用户限制次数
    
    # 显示设置
    show_countdown = Column(Boolean, default=True)  # 显示倒计时
    show_original_price = Column(Boolean, default=True)  # 显示原价
    promotion_badge = Column(String(50), nullable=True)  # 促销标签
    
    # 创建者和时间戳
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    course = relationship("Course")
    creator = relationship("User")
    
    def calculate_discounted_price(self, original_price: float) -> float:
        """计算折扣后价格"""
        if self.promotion_type == PromotionType.PERCENTAGE:
            discount = original_price * (self.discount_percentage / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
            discounted_price = original_price - discount
        elif self.promotion_type == PromotionType.FIXED_AMOUNT:
            discounted_price = original_price - self.discount_amount
        else:
            discounted_price = original_price
        
        # 确保不低于最低价格
        return max(discounted_price, self.min_price)
    
    def is_active(self) -> bool:
        """检查促销是否激活"""
        from datetime import datetime
        now = datetime.utcnow()
        return (
            self.status == PromotionStatus.ACTIVE and
            self.start_time <= now <= self.end_time and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )


class PromotionUsage(Base):
    """促销使用记录"""
    __tablename__ = "promotion_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    promotion_id = Column(String, ForeignKey("course_promotions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=True)
    
    # 使用信息
    original_price = Column(Float, nullable=False)
    discounted_price = Column(Float, nullable=False)
    discount_amount = Column(Float, nullable=False)
    
    # 时间戳
    used_at = Column(DateTime, server_default=func.now())
    
    # 关系
    promotion = relationship("CoursePromotion")
    user = relationship("User")
    order = relationship("Order")


class CourseTag(Base):
    """课程标签"""
    __tablename__ = "course_tags"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#3B82F6")  # 标签颜色 (hex)
    icon = Column(String(50), nullable=True)  # 图标名称
    
    # 统计信息
    usage_count = Column(Integer, default=0)  # 使用次数
    
    # 管理信息
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    creator = relationship("User")


class CourseTagRelation(Base):
    """课程标签关联表"""
    __tablename__ = "course_tag_relations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    tag_id = Column(String, ForeignKey("course_tags.id"), nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    course = relationship("Course")
    tag = relationship("CourseTag")
    
    # 唯一约束
    __table_args__ = (
        {"mysql_charset": "utf8mb4"},
    )