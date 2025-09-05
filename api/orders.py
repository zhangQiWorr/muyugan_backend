"""
订单支付相关API
包含订单创建、支付处理、优惠券管理等
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from models import get_db
from models.user import User
from models.payment import (
    Order, OrderItem, PaymentRecord, Coupon, UserCoupon,
    OrderStatus, PaymentMethod, PaymentStatus, CouponType, CouponStatus
)
from models.course import Course
from models.schemas import (
    OrderCreate, OrderResponse, OrderListResponse,
    PaymentCreate, PaymentResponse,
    CouponCreate, CouponResponse, UserCouponResponse,
    SuccessResponse
)
from services.logger import get_logger
from utils.auth_utils import get_current_user, check_admin_permission

logger = get_logger("orders_api")
router = APIRouter(prefix="/orders", tags=["订单支付"])


def generate_order_no() -> str:
    """生成订单号"""
    import time
    return f"ORD{int(time.time())}{uuid.uuid4().hex[:8].upper()}"


# 订单管理
@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建订单"""
    # 验证课程是否存在
    course_ids = [item.course_id for item in order_data.items]
    courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
    
    if len(courses) != len(course_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="部分课程不存在"
        )
    
    # 计算订单金额
    total_amount = 0.0
    discount_amount = 0.0
    order_items = []
    
    for item in order_data.items:
        course = next(c for c in courses if c.id == item.course_id)
        if course.is_free:
            continue  # 免费课程不计入订单
        
        item_total = course.price * item.quantity
        total_amount += item_total
        
        order_items.append({
            "course_id": course.id,
            "course_title": course.title,
            "course_cover": course.cover_image,
            "price": course.price,
            "quantity": item.quantity
        })
    
    # 处理优惠券
    coupon_discount = 0.0
    coupon = None
    if order_data.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == order_data.coupon_code,
            Coupon.status == CouponStatus.ACTIVE
        ).first()
        
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="优惠券不存在或已失效"
            )
        
        # 检查优惠券使用条件
        if total_amount < coupon.min_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"订单金额不足，最低消费{coupon.min_amount}元"
            )
        
        # 计算优惠金额
        if coupon.coupon_type == CouponType.DISCOUNT:
            coupon_discount = total_amount * (1 - coupon.discount_value / 100)
            if coupon.max_discount:
                coupon_discount = min(coupon_discount, coupon.max_discount)
        elif coupon.coupon_type == CouponType.AMOUNT:
            coupon_discount = coupon.discount_value
        elif coupon.coupon_type == CouponType.FREE:
            coupon_discount = total_amount
        
        discount_amount += coupon_discount
    
    final_amount = total_amount - discount_amount
    
    # 创建订单
    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        total_amount=total_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
        status=OrderStatus.PENDING,
        coupon_id=coupon.id if coupon else None,
        coupon_discount=coupon_discount,
        remark=order_data.remark,
        expires_at=datetime.utcnow() + timedelta(hours=24)  # 24小时过期
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # 创建订单项
    for item_data in order_items:
        order_item = OrderItem(
            order_id=order.id,
            **item_data
        )
        db.add(order_item)
    
    db.commit()
    
    return order


@router.get("/", response_model=OrderListResponse)
async def get_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户订单列表"""
    query = db.query(Order).filter(Order.user_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    # 加载订单项
    for order in orders:
        order.items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    
    return OrderListResponse(
        orders=orders,
        total=total,
        page=page,
        size=size
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取订单详情"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )
    
    # 加载订单项
    order.items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    
    return order


@router.post("/{order_id}/cancel", response_model=SuccessResponse)
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消订单"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能取消待支付的订单"
        )
    
    order.status = OrderStatus.CANCELLED
    db.commit()
    
    return SuccessResponse(message="订单取消成功")


# 支付处理
@router.post("/{order_id}/pay", response_model=PaymentResponse)
async def create_payment(
    order_id: str,
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建支付记录"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="订单状态不正确"
        )
    
    # 检查支付金额
    if payment_data.amount != order.final_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="支付金额不正确"
        )
    
    # 处理余额支付
    if payment_data.payment_method == PaymentMethod.BALANCE:
        # 检查用户余额
        from models.payment import UserBalance
        user_balance = db.query(UserBalance).filter(
            UserBalance.user_id == current_user.id
        ).first()
        
        if not user_balance or user_balance.balance < payment_data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="余额不足"
            )
        
        # 扣除余额
        user_balance.balance -= payment_data.amount
        db.commit()
        
        # 创建支付记录
        payment = PaymentRecord(
            order_id=order_id,
            payment_method=payment_data.payment_method,
            amount=payment_data.amount,
            status=PaymentStatus.SUCCESS,
            paid_at=datetime.utcnow()
        )
        db.add(payment)
        
        # 更新订单状态
        order.status = OrderStatus.PAID
        order.payment_method = payment_data.payment_method
        order.payment_status = PaymentStatus.SUCCESS
        order.paid_at = datetime.utcnow()
        
        db.commit()
        db.refresh(payment)
        
        return payment
    
    # 其他支付方式（模拟）
    payment = PaymentRecord(
        order_id=order_id,
        payment_method=payment_data.payment_method,
        amount=payment_data.amount,
        status=PaymentStatus.PENDING,
        payment_url=f"https://payment.example.com/pay/{order_id}"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return payment


@router.post("/{order_id}/pay/callback", response_model=SuccessResponse)
async def payment_callback(
    order_id: str,
    payment_id: str,
    status: str,
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """支付回调处理"""
    payment = db.query(PaymentRecord).filter(
        PaymentRecord.id == payment_id,
        PaymentRecord.order_id == order_id
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="支付记录不存在"
        )
    
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if status == "success":
        payment.status = PaymentStatus.SUCCESS
        payment.transaction_id = transaction_id
        payment.paid_at = datetime.utcnow()
        
        order.status = OrderStatus.PAID
        order.payment_status = PaymentStatus.SUCCESS
        order.paid_at = datetime.utcnow()
    else:
        payment.status = PaymentStatus.FAILED
    
    db.commit()
    
    return SuccessResponse(message="支付回调处理成功")


# 优惠券管理
@router.post("/coupons", response_model=CouponResponse)
async def create_coupon(
    coupon_data: CouponCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建优惠券（管理员）"""
    check_admin_permission(current_user)
    
    # 生成优惠券码
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # 检查优惠券码是否已存在
    while db.query(Coupon).filter(Coupon.code == code).first():
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    coupon = Coupon(
        code=code,
        **coupon_data.dict()
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    
    return coupon


@router.get("/coupons", response_model=List[CouponResponse])
async def get_coupons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取优惠券列表（管理员）"""
    check_admin_permission(current_user)
    
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    return coupons


@router.post("/coupons/{coupon_code}/claim", response_model=SuccessResponse)
async def claim_coupon(
    coupon_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """领取优惠券"""
    # 检查优惠券是否存在
    coupon = db.query(Coupon).filter(
        Coupon.code == coupon_code,
        Coupon.status == CouponStatus.ACTIVE
    ).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="优惠券不存在或已失效"
        )
    
    # 检查是否已领取
    existing = db.query(UserCoupon).filter(
        UserCoupon.user_id == current_user.id,
        UserCoupon.coupon_id == coupon.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已领取过此优惠券"
        )
    
    # 检查领取限制
    if coupon.per_user_limit > 1:
        user_coupon_count = db.query(UserCoupon).filter(
            UserCoupon.user_id == current_user.id,
            UserCoupon.coupon_id == coupon.id
        ).count()
        
        if user_coupon_count >= coupon.per_user_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已达到领取限制"
            )
    
    # 创建用户优惠券
    user_coupon = UserCoupon(
        user_id=current_user.id,
        coupon_id=coupon.id,
        source="manual"
    )
    db.add(user_coupon)
    db.commit()
    
    return SuccessResponse(message="优惠券领取成功")


@router.get("/my-coupons", response_model=List[UserCouponResponse])
async def get_my_coupons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的优惠券"""
    user_coupons = db.query(UserCoupon).filter(
        UserCoupon.user_id == current_user.id
    ).order_by(UserCoupon.created_at.desc()).all()
    
    return user_coupons
