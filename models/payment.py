"""
支付相关模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
import enum


class OrderStatus(str, enum.Enum):
    """订单状态"""
    PENDING = "pending"       # 待支付
    PAID = "paid"             # 已支付
    CANCELLED = "cancelled"   # 已取消
    REFUNDED = "refunded"     # 已退款
    PARTIAL_REFUNDED = "partial_refunded"  # 部分退款


class PaymentMethod(str, enum.Enum):
    """支付方式"""
    ALIPAY = "alipay"         # 支付宝
    WECHAT = "wechat"         # 微信支付
    BALANCE = "balance"       # 余额支付
    COUPON = "coupon"         # 优惠券支付


class PaymentStatus(str, enum.Enum):
    """支付状态"""
    PENDING = "pending"       # 待支付
    SUCCESS = "success"       # 支付成功
    FAILED = "failed"         # 支付失败
    CANCELLED = "cancelled"   # 已取消


class CouponType(str, enum.Enum):
    """优惠券类型"""
    DISCOUNT = "discount"     # 折扣券
    AMOUNT = "amount"         # 金额券
    FREE = "free"             # 免费券


class CouponStatus(str, enum.Enum):
    """优惠券状态"""
    ACTIVE = "active"         # 可用
    USED = "used"             # 已使用
    EXPIRED = "expired"       # 已过期
    DISABLED = "disabled"     # 已禁用


class Order(Base):
    """订单模型"""
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_no = Column(String(50), unique=True, nullable=False, index=True)  # 订单号
    
    # 用户信息
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 订单金额
    total_amount = Column(Float, nullable=False)  # 总金额
    discount_amount = Column(Float, default=0.0)  # 优惠金额
    final_amount = Column(Float, nullable=False)  # 最终金额
    
    # 订单状态
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    # 支付信息
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    paid_at = Column(DateTime, nullable=True)
    
    # 优惠券
    coupon_id = Column(String, ForeignKey("coupons.id"), nullable=True)
    coupon_discount = Column(Float, default=0.0)  # 优惠券优惠金额
    
    # 备注
    remark = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime, nullable=True)  # 订单过期时间
    
    # 关系
    user = relationship("User")
    coupon = relationship("Coupon")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("PaymentRecord", back_populates="order", cascade="all, delete-orphan")
    refunds = relationship("RefundRecord", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """订单项"""
    __tablename__ = "order_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    
    # 商品信息
    course_title = Column(String(200), nullable=False)  # 课程标题
    course_cover = Column(String(500), nullable=True)   # 课程封面
    price = Column(Float, nullable=False)               # 单价
    quantity = Column(Integer, default=1)               # 数量
    
    # 关系
    order = relationship("Order", back_populates="items")
    course = relationship("Course", back_populates="orders")


class PaymentRecord(Base):
    """支付记录"""
    __tablename__ = "payment_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    
    # 支付信息
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # 第三方支付信息
    transaction_id = Column(String(100), nullable=True)  # 第三方交易号
    payment_url = Column(String(500), nullable=True)    # 支付链接
    callback_data = Column(JSON, nullable=True)         # 回调数据
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    paid_at = Column(DateTime, nullable=True)
    
    # 关系
    order = relationship("Order", back_populates="payments")


class Coupon(Base):
    """优惠券"""
    __tablename__ = "coupons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)  # 优惠券码
    
    # 优惠券信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    coupon_type = Column(Enum(CouponType), nullable=False)
    
    # 优惠规则
    discount_value = Column(Float, nullable=False)  # 优惠值（折扣率或金额）
    min_amount = Column(Float, default=0.0)        # 最低消费金额
    max_discount = Column(Float, nullable=True)    # 最大优惠金额
    
    # 使用限制
    usage_limit = Column(Integer, nullable=True)   # 使用次数限制
    used_count = Column(Integer, default=0)        # 已使用次数
    per_user_limit = Column(Integer, default=1)    # 每用户使用限制
    
    # 状态和时间
    status = Column(Enum(CouponStatus), default=CouponStatus.ACTIVE)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    user_coupons = relationship("UserCoupon", back_populates="coupon", cascade="all, delete-orphan")


class UserCoupon(Base):
    """用户优惠券"""
    __tablename__ = "user_coupons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    coupon_id = Column(String, ForeignKey("coupons.id"), nullable=False)
    
    # 使用状态
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    used_order_id = Column(String, ForeignKey("orders.id"), nullable=True)
    
    # 获取方式
    source = Column(String(50), default="system")  # system: 系统发放, signup: 注册赠送
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    user = relationship("User")
    coupon = relationship("Coupon", back_populates="user_coupons")
    used_order = relationship("Order")
    
    # 唯一约束：一个用户只能拥有一张相同的优惠券
    __table_args__ = (UniqueConstraint('user_id', 'coupon_id', name='uq_user_coupon'),)


class RefundRecord(Base):
    """退款记录"""
    __tablename__ = "refund_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    
    # 退款信息
    refund_amount = Column(Float, nullable=False)  # 退款金额
    refund_reason = Column(Text, nullable=True)    # 退款原因
    refund_status = Column(String(20), default="pending")  # 退款状态
    
    # 处理信息
    processed_by = Column(String, ForeignKey("users.id"), nullable=True)  # 处理人
    processed_at = Column(DateTime, nullable=True)
    remark = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    order = relationship("Order", back_populates="refunds")
    processor = relationship("User")


class UserBalance(Base):
    """用户余额"""
    __tablename__ = "user_balances"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # 余额信息
    balance = Column(Float, default=0.0)           # 当前余额
    frozen_balance = Column(Float, default=0.0)    # 冻结余额
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User")
    transactions = relationship("BalanceTransaction", back_populates="user_balance", cascade="all, delete-orphan")


class BalanceTransaction(Base):
    """余额交易记录"""
    __tablename__ = "balance_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_balance_id = Column(String, ForeignKey("user_balances.id"), nullable=False)
    
    # 交易信息
    transaction_type = Column(String(50), nullable=False)  # 交易类型
    amount = Column(Float, nullable=False)                 # 交易金额
    balance_before = Column(Float, nullable=False)         # 交易前余额
    balance_after = Column(Float, nullable=False)          # 交易后余额
    
    # 关联信息
    related_order_id = Column(String, ForeignKey("orders.id"), nullable=True)
    description = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    user_balance = relationship("UserBalance", back_populates="transactions")
    related_order = relationship("Order")
