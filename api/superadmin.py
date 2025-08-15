"""
超级管理员API
实现全局管理和课程管理功能
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta

from models import get_db
from models.user import User
from models.course import Course, CourseCategory, CourseStatus
from utils.auth_utils import get_current_user
from permission_utils import require_permission, Permissions
from pydantic import BaseModel
from utils.logger import get_logger

logger = get_logger("superadmin_api")
router = APIRouter(prefix="/api/superadmin", tags=["超级管理员"])

# 数据模型
class UserManagement(BaseModel):
    """用户管理模型"""
    username: str
    email: str
    phone: Optional[str] = None
    role: str  # 'user', 'teacher', 'superadmin'
    is_active: bool = True

class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class RolePermissionConfig(BaseModel):
    """角色权限配置模型"""
    role: str
    permissions: List[str]
    description: Optional[str] = None

class CourseManagement(BaseModel):
    """课程管理模型"""
    title: str
    description: str
    category_id: str
    price: float
    discount_price: Optional[float] = None
    status: str  # 'draft', 'published', 'archived'
    tags: Optional[List[str]] = None

class PromotionStrategy(BaseModel):
    """促销策略模型"""
    course_id: str
    discount_type: str  # 'percentage', 'fixed_amount'
    discount_value: float
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None

class OperationLog(BaseModel):
    """操作日志模型"""
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

# ==================== 全局管理功能 ====================

@router.get("/users")
@require_permission(Permissions.VIEW_USERS)
async def get_all_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有用户列表
    
    超级管理员可以查看、搜索和筛选所有用户账户
    """
    try:
        # 构建查询条件
        query = db.query(User)
        
        if search:
            query = query.filter(
                or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.phone.contains(search) if User.phone else False
                )
            )
        
        if role:
            query = query.filter(User.role == role)
            
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # 分页
        total = query.count()
        users = query.offset((page - 1) * size).limit(size).all()
        
        # 记录操作日志
        logger.info(f"Superadmin {current_user.username} viewed users list")
        
        return {
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "last_login": getattr(user, 'last_login', None)
                } for user in users
            ],
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户列表失败")

@router.post("/users")
@require_permission(Permissions.CREATE_USER)
async def create_user(
    user_data: UserManagement,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新用户
    
    超级管理员可以创建任何角色的用户账户
    """
    try:
        # 检查用户名和邮箱是否已存在
        existing_user = db.query(User).filter(
            or_(User.username == user_data.username, User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
        
        # 创建新用户
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            role=user_data.role,
            is_active=user_data.is_active,
            password_hash="temp_password_hash"  # 实际应该生成临时密码
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Superadmin {current_user.username} created user {new_user.username}")
        
        return {
            "message": "用户创建成功",
            "user_id": new_user.id,
            "username": new_user.username
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="创建用户失败")

@router.put("/users/{user_id}")
@require_permission(Permissions.UPDATE_USER)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息
    
    超级管理员可以修改任何用户的信息和角色
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新用户信息
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Superadmin {current_user.username} updated user {user.username}")
        
        return {
            "message": "用户信息更新成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail="更新用户失败")

@router.delete("/users/{user_id}")
@require_permission(Permissions.DELETE_USER)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户
    
    超级管理员可以删除用户账户（软删除，设置为非活跃状态）
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="不能删除自己的账户")
        
        # 软删除：设置为非活跃状态
        user.is_active = False
        db.commit()
        
        logger.info(f"Superadmin {current_user.username} deleted user {user.username}")
        
        return {"message": "用户删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail="删除用户失败")

@router.get("/roles/permissions")
@require_permission(Permissions.MANAGE_PERMISSIONS)
async def get_role_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取角色权限配置
    
    超级管理员可以查看当前的角色权限配置
    """
    from utils.permission_utils import ROLE_PERMISSIONS, get_role_description
    
    try:
        role_configs = []
        for role, permissions in ROLE_PERMISSIONS.items():
            role_configs.append({
                "role": role,
                "permissions": list(permissions),
                "description": get_role_description(role),
                "permission_count": len(permissions)
            })
        
        return {
            "role_permissions": role_configs,
            "total_roles": len(role_configs)
        }
    except Exception as e:
        logger.error(f"Error getting role permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色权限失败")

@router.get("/operation-logs")
@require_permission(Permissions.VIEW_SYSTEM_LOGS)
async def get_operation_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取操作日志
    
    超级管理员可以审核所有用户的操作日志
    """
    try:
        # TODO: 实现操作日志查询逻辑
        # 这里需要有一个操作日志表来存储所有用户操作
        
        # 模拟数据
        mock_logs = [
            {
                "id": 1,
                "user_id": 2,
                "username": "teacher_zhang",
                "action": "create_course",
                "resource_type": "course",
                "resource_id": "course_123",
                "details": {"course_name": "幼儿数学启蒙", "price": 99.0},
                "ip_address": "192.168.1.100",
                "created_at": "2024-01-16T10:30:00"
            },
            {
                "id": 2,
                "user_id": 3,
                "username": "parent_li",
                "action": "purchase_course",
                "resource_type": "order",
                "resource_id": "order_456",
                "details": {"course_name": "创意手工制作", "amount": 79.0},
                "ip_address": "192.168.1.101",
                "created_at": "2024-01-16T14:20:00"
            }
        ]
        
        return {
            "logs": mock_logs,
            "pagination": {
                "page": page,
                "size": size,
                "total": len(mock_logs),
                "pages": 1
            }
        }
    except Exception as e:
        logger.error(f"Error getting operation logs: {str(e)}")
        raise HTTPException(status_code=500, detail="获取操作日志失败")

# ==================== 课程管理功能 ====================

@router.get("/courses/management")
@require_permission(Permissions.VIEW_COURSES)
async def get_courses_for_management(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程管理列表
    
    超级管理员可以查看和管理所有课程
    """
    try:
        query = db.query(Course)
        
        if status:
            query = query.filter(Course.status == status)
        if category_id:
            query = query.filter(Course.category_id == category_id)
        if search:
            query = query.filter(Course.title.contains(search))
        
        total = query.count()
        courses = query.offset((page - 1) * size).limit(size).all()
        
        return {
            "courses": [
                {
                    "id": course.id,
                    "title": course.title,
                    "description": course.description,
                    "price": course.price,
                    "discount_price": getattr(course, 'discount_price', None),
                    "status": course.status,
                    "category_name": course.category.name if course.category else None,
                    "teacher_name": course.teacher.username if course.teacher else None,
                    "created_at": course.created_at,
                    "updated_at": course.updated_at,
                    "enrollment_count": getattr(course, 'enrollment_count', 0)
                } for course in courses
            ],
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    except Exception as e:
        logger.error(f"Error getting courses for management: {str(e)}")
        raise HTTPException(status_code=500, detail="获取课程列表失败")

@router.put("/courses/{course_id}/status")
@require_permission(Permissions.UPDATE_COURSE)
async def update_course_status(
    course_id: str,
    status: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新课程状态
    
    超级管理员可以上架、下架或归档课程
    """
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        valid_statuses = ['draft', 'published', 'archived', 'suspended']
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail="无效的课程状态")
        
        old_status = course.status
        course.status = status
        course.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Superadmin {current_user.username} changed course {course_id} status from {old_status} to {status}")
        
        return {
            "message": "课程状态更新成功",
            "course_id": course_id,
            "old_status": old_status,
            "new_status": status,
            "reason": reason
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating course status: {str(e)}")
        raise HTTPException(status_code=500, detail="更新课程状态失败")

@router.post("/courses/{course_id}/promotion")
@require_permission(Permissions.MANAGE_PROMOTIONS)
async def create_promotion(
    course_id: str,
    promotion: PromotionStrategy,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建促销策略
    
    超级管理员可以为课程设置限时折扣等促销策略
    """
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        # 计算折扣价格
        if promotion.discount_type == 'percentage':
            discount_price = course.price * (1 - promotion.discount_value / 100)
        else:  # fixed_amount
            discount_price = course.price - promotion.discount_value
        
        if discount_price < 0:
            raise HTTPException(status_code=400, detail="折扣价格不能为负数")
        
        # TODO: 保存促销策略到数据库
        # 这里需要一个促销策略表
        
        logger.info(f"Superadmin {current_user.username} created promotion for course {course_id}")
        
        return {
            "message": "促销策略创建成功",
            "course_id": course_id,
            "original_price": course.price,
            "discount_price": discount_price,
            "discount_type": promotion.discount_type,
            "discount_value": promotion.discount_value,
            "start_date": promotion.start_date,
            "end_date": promotion.end_date
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating promotion: {str(e)}")
        raise HTTPException(status_code=500, detail="创建促销策略失败")

@router.get("/categories/management")
@require_permission(Permissions.MANAGE_COURSE_CATEGORIES)
async def get_categories_management(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程分类管理
    
    超级管理员可以管理所有课程分类
    """
    try:
        categories = db.query(CourseCategory).all()
        
        return {
            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                    "course_count": len(category.courses) if category.courses else 0,
                    "created_at": category.created_at,
                    "is_active": getattr(category, 'is_active', True)
                } for category in categories
            ],
            "total_categories": len(categories)
        }
    except Exception as e:
        logger.error(f"Error getting categories management: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分类管理失败")

@router.get("/dashboard/stats")
@require_permission(Permissions.VIEW_SYSTEM_LOGS)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取管理员仪表板统计数据
    
    超级管理员可以查看系统整体统计信息
    """
    try:
        # 用户统计
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        teachers = db.query(User).filter(User.role == 'teacher').count()
        parents = db.query(User).filter(User.role == 'user').count()
        
        # 课程统计
        total_courses = db.query(Course).count()
        published_courses = db.query(Course).filter(Course.status == 'published').count()
        draft_courses = db.query(Course).filter(Course.status == 'draft').count()
        
        # 分类统计
        total_categories = db.query(CourseCategory).count()
        
        return {
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users,
                "teachers": teachers,
                "parents": parents,
                "inactive_users": total_users - active_users
            },
            "course_stats": {
                "total_courses": total_courses,
                "published_courses": published_courses,
                "draft_courses": draft_courses,
                "archived_courses": total_courses - published_courses - draft_courses
            },
            "category_stats": {
                "total_categories": total_categories
            },
            "system_stats": {
                "last_updated": datetime.utcnow(),
                "system_health": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计数据失败")