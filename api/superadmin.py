"""
超级管理员API
实现全局管理和课程管理功能
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from pydantic import BaseModel, Field

from models import get_db
from models.user import User
from models.course import Course, CourseCategory, CourseEnrollment
from models.schemas import SuccessResponse
from utils.auth_utils import get_current_user
from utils.permission_utils import require_permission, Permissions
from services.logger import get_logger
from auth.password_handler import PasswordHandler

logger = get_logger("superadmin_api")
router = APIRouter(prefix="/superadmin", tags=["超级管理员"])
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

# ==================== 课程报名管理模型 ====================

class FreeEnrollmentRequest(BaseModel):
    """免费报名请求"""
    user_id: str = Field(..., description="用户ID")
    course_ids: List[str] = Field(..., description="课程ID列表")

class BatchEnrollmentResponse(BaseModel):
    """批量报名响应"""
    user_id: str
    user_name: str
    total_courses: int
    success_count: int
    failed_count: int
    enrolled_count: int = Field(0, description="新报名数量")
    deactivated_count: int = Field(0, description="取消报名数量")
    reactivated_count: int = Field(0, description="重新激活数量")
    already_enrolled_count: int = Field(0, description="已报名数量")
    enrollments: List[dict] = Field(..., description="报名结果详情")
    errors: List[dict] = Field(default_factory=list, description="错误信息")

class FreeEnrollmentResponse(BaseModel):
    """免费报名响应"""
    id: str
    user_id: str
    course_id: str
    course_title: str
    enrolled_at: datetime
    is_active: bool

class DeleteEnrollmentRequest(BaseModel):
    """删除报名请求"""
    user_id: str = Field(..., description="用户ID")
    course_ids: List[str] = Field(..., description="要删除的课程ID列表")

class DeleteEnrollmentResponse(BaseModel):
    """删除报名响应"""
    user_id: str
    user_name: str
    total_courses: int
    success_count: int
    failed_count: int
    deleted_count: int = Field(0, description="删除报名数量")
    not_found_count: int = Field(0, description="未找到报名数量")
    already_inactive_count: int = Field(0, description="已停用报名数量")
    enrollments: List[dict] = Field(..., description="删除结果详情")
    errors: List[dict] = Field(default_factory=list, description="错误信息")

# ==================== 全局管理功能 ====================

@router.get("/users")
@require_permission(Permissions.VIEW_USERS)
async def get_all_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("last_login", description="排序字段: last_login, created_at, username"),
    sort_order: str = Query("desc", description="排序顺序: asc, desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有用户列表
    
    超级管理员可以查看、搜索和筛选所有用户账户
    
    Args:
        page: 页码，从1开始
        size: 每页数量，1-100之间
        search: 搜索关键词，支持用户名、邮箱、手机号
        role: 角色筛选 (user, teacher, superadmin)
        is_active: 状态筛选 (True/False)
        sort_by: 排序字段 (last_login, created_at, username)，默认为last_login
        sort_order: 排序顺序 (asc, desc)，默认为desc
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
        
        # 排序
        valid_sort_fields = {
            "last_login": User.last_login,
            "created_at": User.created_at,
            "username": User.username
        }
        
        if sort_by in valid_sort_fields:
            sort_field = valid_sort_fields[sort_by]
            if sort_order.lower() == "asc":
                if sort_by == "last_login":
                    # 对于last_login字段，NULL值排在最后
                    query = query.order_by(sort_field.asc().nulls_last())
                else:
                    query = query.order_by(sort_field.asc())
            else:  # 默认desc
                if sort_by == "last_login":
                    # 对于last_login字段，NULL值排在最后
                    query = query.order_by(sort_field.desc().nulls_last())
                else:
                    query = query.order_by(sort_field.desc())
        else:
            # 默认按最后登录时间降序排序，NULL值排在最后
            query = query.order_by(User.last_login.desc().nulls_last())
        
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
        from services.audit_service import AuditService
        
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
    from utils.permission_utils import ROLE_PERMISSIONS, get_role_description
    
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

# ==================== 课程报名管理功能 ====================

@router.post("/enrollments/batch", response_model=BatchEnrollmentResponse)
@require_permission(Permissions.MANAGE_USER_ROLES)
async def batch_create_enrollments(
    enrollment_data: FreeEnrollmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量创建用户课程报名（超级管理员和管理员）"""
    try:
        # 检查目标用户是否存在
        target_user = db.query(User).filter(User.id == enrollment_data.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标用户不存在"
            )
        
        # 检查课程是否存在
        courses = db.query(Course).filter(Course.id.in_(enrollment_data.course_ids)).all()
        course_dict = {course.id: course for course in courses}
        
        # 检查不存在的课程
        missing_courses = [cid for cid in enrollment_data.course_ids if cid not in course_dict]
        if missing_courses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"以下课程不存在: {', '.join(missing_courses)}"
            )
        
        # 批量处理报名
        enrollments = []
        errors = []
        success_count = 0
        failed_count = 0
        enrolled_count = 0
        reactivated_count = 0
        already_enrolled_count = 0
        
        # 处理报名
        for course_id in enrollment_data.course_ids:
            try:
                course = course_dict[course_id]
                
                # 检查是否已经报名过该课程
                existing_enrollment = db.query(CourseEnrollment).filter(
                    CourseEnrollment.user_id == enrollment_data.user_id,
                    CourseEnrollment.course_id == course_id
                ).first()
                
                if existing_enrollment:
                    if existing_enrollment.is_active:
                        # 已经报名过且激活，跳过
                        enrollments.append({
                            "course_id": course_id,
                            "course_title": course.title,
                            "status": "already_enrolled",
                            "message": "用户已经报名过该课程"
                        })
                        success_count += 1
                        already_enrolled_count += 1
                    else:
                        # 如果之前报名过但被禁用了，重新激活
                        existing_enrollment.is_active = True
                        existing_enrollment.enrolled_at = datetime.utcnow()
                        db.commit()
                        db.refresh(existing_enrollment)
                        
                        enrollments.append({
                            "course_id": course_id,
                            "course_title": course.title,
                            "enrollment_id": existing_enrollment.id,
                            "status": "reactivated",
                            "message": "重新激活了之前的报名",
                            "enrolled_at": existing_enrollment.enrolled_at.isoformat()
                        })
                        success_count += 1
                        reactivated_count += 1
                        
                        logger.info(f"重新激活用户 {target_user.username} 的课程报名: {course.title}")
                else:
                    # 创建新的报名记录
                    enrollment = CourseEnrollment(
                        user_id=enrollment_data.user_id,
                        course_id=course_id,
                        is_active=True
                    )
                    
                    db.add(enrollment)
                    db.commit()
                    db.refresh(enrollment)
                    
                    # 更新课程的报名数量
                    course.enroll_count = (course.enroll_count or 0) + 1
                    db.commit()
                    
                    enrollments.append({
                        "course_id": course_id,
                        "course_title": course.title,
                        "enrollment_id": enrollment.id,
                        "status": "created",
                        "message": "成功创建报名",
                        "enrolled_at": enrollment.enrolled_at.isoformat()
                    })
                    success_count += 1
                    enrolled_count += 1
                    
                    logger.info(f"管理员 {current_user.username} 为用户 {target_user.username} 创建免费报名: {course.title}")
                    
            except Exception as e:
                error_msg = f"处理课程 {course_id} 时发生错误: {str(e)}"
                errors.append({
                    "course_id": course_id,
                    "course_title": course_dict.get(course_id, {}).get('title', '未知课程'),
                    "error": error_msg
                })
                failed_count += 1
                logger.error(error_msg)
        
        logger.info(f"批量创建报名完成: 用户 {target_user.username}, 成功 {success_count}, 失败 {failed_count}, 新报名 {enrolled_count}, 重新激活 {reactivated_count}, 已报名 {already_enrolled_count}")
        
        return BatchEnrollmentResponse(
            user_id=enrollment_data.user_id,
            user_name=target_user.username,
            total_courses=len(enrollment_data.course_ids),
            success_count=success_count,
            failed_count=failed_count,
            enrolled_count=enrolled_count,
            deactivated_count=0,  # 不再有取消报名的功能
            reactivated_count=reactivated_count,
            already_enrolled_count=already_enrolled_count,
            enrollments=enrollments,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"批量创建报名失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量创建报名失败"
        )

@router.delete("/enrollments/batch", response_model=DeleteEnrollmentResponse)
@require_permission(Permissions.MANAGE_USER_ROLES)
async def batch_delete_enrollments(
    delete_data: DeleteEnrollmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量删除用户课程报名（超级管理员和管理员）"""
    try:
        # 检查目标用户是否存在
        target_user = db.query(User).filter(User.id == delete_data.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标用户不存在"
            )
        
        # 检查课程是否存在
        courses = db.query(Course).filter(Course.id.in_(delete_data.course_ids)).all()
        course_dict = {course.id: course for course in courses}
        
        # 检查不存在的课程
        missing_courses = [cid for cid in delete_data.course_ids if cid not in course_dict]
        if missing_courses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"以下课程不存在: {', '.join(missing_courses)}"
            )
        
        # 批量处理删除报名
        enrollments = []
        errors = []
        success_count = 0
        failed_count = 0
        deleted_count = 0
        not_found_count = 0
        already_inactive_count = 0
        
        # 处理删除报名
        for course_id in delete_data.course_ids:
            try:
                course = course_dict[course_id]
                
                # 查找用户的报名记录
                enrollment = db.query(CourseEnrollment).filter(
                    CourseEnrollment.user_id == delete_data.user_id,
                    CourseEnrollment.course_id == course_id
                ).first()
                
                if not enrollment:
                    # 没有找到报名记录
                    enrollments.append({
                        "course_id": course_id,
                        "course_title": course.title,
                        "status": "not_found",
                        "message": "用户未报名该课程"
                    })
                    success_count += 1
                    not_found_count += 1
                elif not enrollment.is_active:
                    # 报名记录已停用
                    enrollments.append({
                        "course_id": course_id,
                        "course_title": course.title,
                        "enrollment_id": enrollment.id,
                        "status": "already_inactive",
                        "message": "报名记录已停用"
                    })
                    success_count += 1
                    already_inactive_count += 1
                else:
                    # 停用报名记录
                    enrollment.is_active = False
                    db.commit()
                    
                    # 更新课程的报名数量
                    course.enroll_count = max((course.enroll_count or 0) - 1, 0)
                    db.commit()
                    
                    enrollments.append({
                        "course_id": course_id,
                        "course_title": course.title,
                        "enrollment_id": enrollment.id,
                        "status": "deleted",
                        "message": "成功删除报名"
                    })
                    success_count += 1
                    deleted_count += 1
                    
                    logger.info(f"管理员 {current_user.username} 删除用户 {target_user.username} 的课程报名: {course.title}")
                    
            except Exception as e:
                error_msg = f"删除课程 {course_id} 报名时发生错误: {str(e)}"
                errors.append({
                    "course_id": course_id,
                    "course_title": course_dict.get(course_id, {}).get('title', '未知课程'),
                    "error": error_msg
                })
                failed_count += 1
                logger.error(error_msg)
        
        logger.info(f"批量删除报名完成: 用户 {target_user.username}, 成功 {success_count}, 失败 {failed_count}, 删除 {deleted_count}, 未找到 {not_found_count}, 已停用 {already_inactive_count}")
        
        return DeleteEnrollmentResponse(
            user_id=delete_data.user_id,
            user_name=target_user.username,
            total_courses=len(delete_data.course_ids),
            success_count=success_count,
            failed_count=failed_count,
            deleted_count=deleted_count,
            not_found_count=not_found_count,
            already_inactive_count=already_inactive_count,
            enrollments=enrollments,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"批量删除报名失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量删除报名失败"
        )

@router.get("/enrollments", response_model=List[FreeEnrollmentResponse])
@require_permission(Permissions.VIEW_USERS)
async def get_enrollments(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    course_id: Optional[str] = Query(None, description="课程ID筛选"),
    is_active: Optional[bool] = Query(None, description="是否激活状态筛选"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程报名列表（超级管理员和管理员）"""
    try:
        # 构建查询
        query = db.query(CourseEnrollment)
        
        # 应用筛选条件
        if user_id:
            query = query.filter(CourseEnrollment.user_id == user_id)
        if course_id:
            query = query.filter(CourseEnrollment.course_id == course_id)
        if is_active is not None:
            query = query.filter(CourseEnrollment.is_active == is_active)
        
        # 分页
        total = query.count()
        enrollments = query.offset((page - 1) * size).limit(size).all()
        
        # 加载关联数据
        result = []
        for enrollment in enrollments:
            course = db.query(Course).filter(Course.id == enrollment.course_id).first()
            result.append(FreeEnrollmentResponse(
                id=enrollment.id,
                user_id=enrollment.user_id,
                course_id=enrollment.course_id,
                course_title=course.title if course else "未知课程",
                enrolled_at=enrollment.enrolled_at,
                is_active=enrollment.is_active
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"获取报名列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取报名列表失败"
        )

@router.put("/enrollments/{enrollment_id}/deactivate", response_model=SuccessResponse)
@require_permission(Permissions.MANAGE_USER_ROLES)
async def deactivate_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """停用课程报名（超级管理员和管理员）"""
    try:
        # 查找报名记录
        enrollment = db.query(CourseEnrollment).filter(
            CourseEnrollment.id == enrollment_id
        ).first()
        
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="报名记录不存在"
            )
        
        # 停用报名
        enrollment.is_active = False
        db.commit()
        
        logger.info(f"管理员 {current_user.username} 停用了报名记录: {enrollment_id}")
        
        return SuccessResponse(message="报名已停用")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"停用报名失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="停用报名失败"
        )