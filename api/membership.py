"""
会员管理相关API
包含会员等级管理、会员购买、权益管理等
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from models import get_db
from models.user import User
from models.membership import (
    MembershipLevel, UserMembership, MembershipOrder,
    MembershipBenefit, UserBenefitUsage,
    MembershipType, MembershipStatus
)
from models.schemas import (
    MembershipLevelCreate, MembershipLevelResponse,
    MembershipCreate, MembershipResponse,
    SuccessResponse, PaginationParams
)
from utils.logger import get_logger
from utils.auth_utils import get_current_user, get_current_user_optional, check_admin_permission, check_superadmin_permission

logger = get_logger("membership_api")
router = APIRouter(prefix="/membership", tags=["会员管理"])


def generate_membership_order_no() -> str:
    """生成会员订单号"""
    import time
    return f"MEM{int(time.time())}{uuid.uuid4().hex[:8].upper()}"


# 会员等级管理
@router.post("/levels", response_model=MembershipLevelResponse)
async def create_membership_level(
    level_data: MembershipLevelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建会员等级（管理员）"""
    check_admin_permission(current_user)
    
    # 检查等级名称是否已存在
    existing = db.query(MembershipLevel).filter(
        MembershipLevel.name == level_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="等级名称已存在"
        )
    
    level = MembershipLevel(**level_data.dict())
    db.add(level)
    db.commit()
    db.refresh(level)
    
    return level


@router.get("/levels", response_model=List[MembershipLevelResponse])
async def get_membership_levels(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取会员等级列表"""
    levels = db.query(MembershipLevel).filter(
        MembershipLevel.is_active == True
    ).order_by(MembershipLevel.sort_order, MembershipLevel.name).all()
    
    return levels


@router.get("/levels/{level_id}", response_model=MembershipLevelResponse)
async def get_membership_level(
    level_id: str,
    db: Session = Depends(get_db)
):
    """获取会员等级详情"""
    level = db.query(MembershipLevel).filter(
        MembershipLevel.id == level_id,
        MembershipLevel.is_active == True
    ).first()
    
    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员等级不存在"
        )
    
    return level


@router.put("/levels/{level_id}", response_model=MembershipLevelResponse)
async def update_membership_level(
    level_id: str,
    level_data: MembershipLevelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新会员等级（管理员）"""
    check_admin_permission(current_user)
    
    level = db.query(MembershipLevel).filter(MembershipLevel.id == level_id).first()
    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员等级不存在"
        )
    
    # 更新等级信息
    update_data = level_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(level, field, value)
    
    db.commit()
    db.refresh(level)
    
    return level


@router.delete("/levels/{level_id}", response_model=SuccessResponse)
async def delete_membership_level(
    level_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除会员等级（管理员）"""
    check_admin_permission(current_user)
    
    level = db.query(MembershipLevel).filter(MembershipLevel.id == level_id).first()
    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员等级不存在"
        )
    
    # 检查是否有用户使用该等级
    users = db.query(UserMembership).filter(
        UserMembership.level_id == level_id
    ).count()
    if users > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该等级下有用户，无法删除"
        )
    
    db.delete(level)
    db.commit()
    
    return SuccessResponse(message="会员等级删除成功")


# 会员购买
@router.post("/purchase", response_model=MembershipResponse)
async def purchase_membership(
    membership_data: MembershipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """购买会员"""
    # 检查会员等级是否存在
    level = db.query(MembershipLevel).filter(
        MembershipLevel.id == membership_data.level_id,
        MembershipLevel.is_active == True
    ).first()
    
    if not level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员等级不存在"
        )
    
    # 检查是否已有有效会员
    existing_membership = db.query(UserMembership).filter(
        UserMembership.user_id == current_user.id,
        UserMembership.status == MembershipStatus.ACTIVE
    ).first()
    
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已有有效会员，请先取消当前会员"
        )
    
    # 计算价格和有效期
    if membership_data.membership_type == MembershipType.MONTHLY:
        price = level.monthly_price
        end_date = datetime.utcnow() + timedelta(days=30)
    elif membership_data.membership_type == MembershipType.QUARTERLY:
        price = level.quarterly_price
        end_date = datetime.utcnow() + timedelta(days=90)
    elif membership_data.membership_type == MembershipType.YEARLY:
        price = level.yearly_price
        end_date = datetime.utcnow() + timedelta(days=365)
    elif membership_data.membership_type == MembershipType.LIFETIME:
        price = level.lifetime_price
        end_date = None
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的会员类型"
        )
    
    if not price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该会员类型暂未开放"
        )
    
    # 创建会员记录
    membership = UserMembership(
        user_id=current_user.id,
        level_id=level.id,
        membership_type=membership_data.membership_type,
        status=MembershipStatus.ACTIVE,
        start_date=datetime.utcnow(),
        end_date=end_date,
        auto_renew=membership_data.auto_renew,
        price=price
    )
    db.add(membership)
    
    # 创建会员订单
    order = MembershipOrder(
        user_id=current_user.id,
        membership_id=membership.id,
        order_no=generate_membership_order_no(),
        amount=price,
        payment_method="balance",  # 暂时使用余额支付
        payment_status="success",
        membership_type=membership_data.membership_type,
        duration_months=None if membership_data.membership_type == MembershipType.LIFETIME else {
            MembershipType.MONTHLY: 1,
            MembershipType.QUARTERLY: 3,
            MembershipType.YEARLY: 12
        }[membership_data.membership_type],
        paid_at=datetime.utcnow()
    )
    db.add(order)
    
    db.commit()
    db.refresh(membership)
    
    # 加载等级信息
    membership.level = level
    
    return membership


@router.get("/my", response_model=MembershipResponse)
async def get_my_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的会员信息"""
    membership = db.query(UserMembership).filter(
        UserMembership.user_id == current_user.id,
        UserMembership.status == MembershipStatus.ACTIVE
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您暂无有效会员"
        )
    
    # 加载等级信息
    membership.level = db.query(MembershipLevel).filter(
        MembershipLevel.id == membership.level_id
    ).first()
    
    return membership


@router.post("/cancel", response_model=SuccessResponse)
async def cancel_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消会员"""
    membership = db.query(UserMembership).filter(
        UserMembership.user_id == current_user.id,
        UserMembership.status == MembershipStatus.ACTIVE
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您暂无有效会员"
        )
    
    membership.status = MembershipStatus.CANCELLED
    membership.auto_renew = False
    db.commit()
    
    return SuccessResponse(message="会员取消成功")


@router.post("/renew", response_model=MembershipResponse)
async def renew_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """续费会员"""
    membership = db.query(UserMembership).filter(
        UserMembership.user_id == current_user.id,
        UserMembership.status == MembershipStatus.ACTIVE
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您暂无有效会员"
        )
    
    # 计算新的结束时间
    if membership.membership_type == MembershipType.MONTHLY:
        new_end_date = (membership.end_date or datetime.utcnow()) + timedelta(days=30)
    elif membership.membership_type == MembershipType.QUARTERLY:
        new_end_date = (membership.end_date or datetime.utcnow()) + timedelta(days=90)
    elif membership.membership_type == MembershipType.YEARLY:
        new_end_date = (membership.end_date or datetime.utcnow()) + timedelta(days=365)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="终身会员无需续费"
        )
    
    membership.end_date = new_end_date
    db.commit()
    db.refresh(membership)
    
    # 加载等级信息
    membership.level = db.query(MembershipLevel).filter(
        MembershipLevel.id == membership.level_id
    ).first()
    
    return membership


# 会员权益管理
@router.post("/benefits", response_model=dict)
async def create_membership_benefit(
    name: str,
    description: str,
    benefit_type: str,
    value: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建会员权益（管理员）"""
    check_admin_permission(current_user)
    
    benefit = MembershipBenefit(
        name=name,
        description=description,
        benefit_type=benefit_type,
        value=value
    )
    db.add(benefit)
    db.commit()
    db.refresh(benefit)
    
    return {
        "message": "权益创建成功",
        "benefit": {
            "id": benefit.id,
            "name": benefit.name,
            "description": benefit.description,
            "benefit_type": benefit.benefit_type,
            "value": benefit.value
        }
    }


@router.get("/benefits", response_model=List[dict])
async def get_membership_benefits(
    db: Session = Depends(get_db)
):
    """获取会员权益列表"""
    benefits = db.query(MembershipBenefit).filter(
        MembershipBenefit.is_active == True
    ).order_by(MembershipBenefit.sort_order, MembershipBenefit.name).all()
    
    return [
        {
            "id": benefit.id,
            "name": benefit.name,
            "description": benefit.description,
            "benefit_type": benefit.benefit_type,
            "value": benefit.value,
            "icon": benefit.icon
        }
        for benefit in benefits
    ]


@router.put("/benefits/{benefit_id}", response_model=SuccessResponse)
async def update_membership_benefit(
    benefit_id: str,
    name: str,
    description: str,
    benefit_type: str,
    value: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新会员权益（管理员）"""
    check_admin_permission(current_user)
    
    benefit = db.query(MembershipBenefit).filter(
        MembershipBenefit.id == benefit_id
    ).first()
    
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="权益不存在"
        )
    
    benefit.name = name
    benefit.description = description
    benefit.benefit_type = benefit_type
    benefit.value = value
    
    db.commit()
    
    return SuccessResponse(message="权益配置更新成功")
