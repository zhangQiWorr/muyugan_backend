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
from auth.password_handler import PasswordHandler

logger = get_logger("superadmin_api")
router = APIRouter(prefix="/api/superadmin", tags=["超级管理员"])
password_handler = PasswordHandler()

# 数据模型
class UserManagement(BaseModel):
    """用户管理数据模型"""
    username: str
    email: str
    phone: Optional[str] = None
    role: str  # 'user', 'teacher', 'superadmin'
    is_active: bool = True
    password: str  # 前端传入的密码

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
            search_conditions = [
                User.username.contains(search),
                User.email.contains(search)
            ]
            if User.phone is not None:
                search_conditions.append(User.phone.contains(search))
            query = query.filter(or_(*search_conditions))
        
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
        
        # 验证密码强度
        password_validation = password_handler.validate_password_strength(user_data.password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"密码强度不足: {', '.join(password_validation['errors'])}"
            )
        
        # 哈希密码
        hashed_password = password_handler.hash_password(user_data.password)
        
        # 创建新用户
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            role=user_data.role,
            is_active=user_data.is_active,
            hashed_password=hashed_password
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
        
        if str(user.id) == str(current_user.id):
            raise HTTPException(status_code=400, detail="不能删除自己的账户")
        
        # 软删除：设置为非活跃状态
        setattr(user, 'is_active', False)
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
    from permission_utils import ROLE_PERMISSIONS, get_role_description
    
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

@router.get("/audit-logs")
@require_permission(Permissions.VIEW_SYSTEM_LOGS)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审计日志
    
    超级管理员可以查看所有用户的操作审计日志
    """
    try:
        from utils.audit_service import AuditService
        
        # 使用审计服务查询日志
        result = AuditService.get_logs(
            db=db,
            page=page,
            size=size,
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            search=search
        )
        
        # 不再记录查看审计日志的操作，避免产生过多审计记录
        # 审计接口的访问已通过中间件排除
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail="获取审计日志失败")

# ==================== 课程管理功能 ====================



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
        course_price = float(course.price) if course.price is not None else 0.0
        if promotion.discount_type == 'percentage':
            discount_price = course_price * (1 - promotion.discount_value / 100)
        else:  # fixed_amount
            discount_price = course_price - promotion.discount_value
        
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

@router.get("/tags/management")
@require_permission(Permissions.MANAGE_COURSE_CATEGORIES)
async def get_tags_management(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程标签管理
    
    超级管理员可以管理所有课程标签
    """
    try:
        # 由于标签模型可能还没有完全实现，先返回模拟数据
        tags = [
            {
                "id": "1",
                "name": "Python",
                "description": "Python编程语言",
                "color": "#3776ab",
                "icon": "code",
                "usage_count": 5,
                "is_active": True,
                "created_at": datetime.now()
            },
            {
                "id": "2",
                "name": "JavaScript",
                "description": "JavaScript编程语言",
                "color": "#f7df1e",
                "icon": "code",
                "usage_count": 3,
                "is_active": True,
                "created_at": datetime.now()
            },
            {
                "id": "3",
                "name": "React",
                "description": "React前端框架",
                "color": "#61dafb",
                "icon": "react",
                "usage_count": 2,
                "is_active": True,
                "created_at": datetime.now()
            }
        ]
        
        return {
            "tags": tags,
            "total_tags": len(tags)
        }
    except Exception as e:
        logger.error(f"Error getting tags management: {str(e)}")
        raise HTTPException(status_code=500, detail="获取标签管理失败")

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

@router.get("/roles")
@require_permission(Permissions.MANAGE_PERMISSIONS)
async def get_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有角色列表
    
    超级管理员可以查看所有可用的角色
    """
    from permission_utils import ROLE_PERMISSIONS, get_role_description
    
    try:
        roles = []
        for role, permissions in ROLE_PERMISSIONS.items():
            roles.append({
                "id": role,
                "name": role,
                "description": get_role_description(role),
                "permissions": list(permissions),
                "permission_count": len(permissions),
                "created_at": datetime.utcnow().isoformat()
            })
        
        return {
            "roles": roles,
            "total": len(roles)
        }
    except Exception as e:
        logger.error(f"Error getting roles: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色列表失败")

@router.get("/permissions")
@require_permission(Permissions.MANAGE_PERMISSIONS)
async def get_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有权限列表
    
    超级管理员可以查看所有可用的权限
    """
    try:
        permissions = []
        
        # 权限分类
        permission_categories = {
            "用户管理": ["view_users", "create_user", "update_user", "delete_user", "manage_user_roles"],
            "课程管理": ["view_courses", "create_course", "update_course", "delete_course", "publish_course", "manage_course_categories"],
            "订单管理": ["view_orders", "create_order", "update_order", "delete_order", "process_refunds"],
            "会员管理": ["view_memberships", "create_membership", "update_membership", "delete_membership", "manage_membership_levels"],
            "系统管理": ["view_system_logs", "manage_permissions", "system_backup", "system_restore", "manage_system_config"],
            "内容管理": ["moderate_content", "manage_reviews", "manage_comments"],
            "财务管理": ["view_financial_reports", "manage_pricing", "manage_promotions"],
            "学习管理": ["view_learning_progress", "manage_learning_paths", "track_user_activity"]
        }
        
        # 权限描述映射
        permission_descriptions = {
            "view_users": "查看用户列表",
            "create_user": "创建新用户",
            "update_user": "更新用户信息",
            "delete_user": "删除用户",
            "manage_user_roles": "管理用户角色",
            "view_courses": "查看课程列表",
            "create_course": "创建新课程",
            "update_course": "更新课程信息",
            "delete_course": "删除课程",
            "publish_course": "发布课程",
            "manage_course_categories": "管理课程分类",
            "view_orders": "查看订单列表",
            "create_order": "创建订单",
            "update_order": "更新订单",
            "delete_order": "删除订单",
            "process_refunds": "处理退款",
            "view_memberships": "查看会员信息",
            "create_membership": "创建会员",
            "update_membership": "更新会员信息",
            "delete_membership": "删除会员",
            "manage_membership_levels": "管理会员等级",
            "view_system_logs": "查看系统日志",
            "manage_permissions": "管理权限",
            "system_backup": "系统备份",
            "system_restore": "系统恢复",
            "manage_system_config": "管理系统配置",
            "moderate_content": "内容审核",
            "manage_reviews": "管理评价",
            "manage_comments": "管理评论",
            "view_financial_reports": "查看财务报表",
            "manage_pricing": "管理定价",
            "manage_promotions": "管理促销活动",
            "view_learning_progress": "查看学习进度",
            "manage_learning_paths": "管理学习路径",
            "track_user_activity": "跟踪用户活动"
        }
        
        for category, perms in permission_categories.items():
            for perm in perms:
                permissions.append({
                    "id": perm,
                    "name": perm,
                    "description": permission_descriptions.get(perm, perm),
                    "category": category
                })
        
        return {
            "permissions": permissions,
            "total": len(permissions),
            "categories": list(permission_categories.keys())
        }
    except Exception as e:
        logger.error(f"Error getting permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="获取权限列表失败")