"""权限管理工具模块
提供基于角色的访问控制(RBAC)功能
"""

from enum import Enum
from functools import wraps
from typing import Set, Dict, List
from fastapi import HTTPException
from models.user import User
from services.logger import get_logger

logger = get_logger("permission_utils")

class Permissions(Enum):
    """权限枚举"""
    # 用户管理权限
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    MANAGE_USER_ROLES = "manage_user_roles"
    
    # 课程管理权限
    VIEW_COURSES = "view_courses"
    CREATE_COURSE = "create_course"
    UPDATE_COURSE = "update_course"
    DELETE_COURSE = "delete_course"
    PUBLISH_COURSE = "publish_course"
    MANAGE_COURSES = "manage_courses"
    MANAGE_COURSE_CATEGORIES = "manage_course_categories"
    
    # 订单管理权限
    VIEW_ORDERS = "view_orders"
    CREATE_ORDER = "create_order"
    UPDATE_ORDER = "update_order"
    DELETE_ORDER = "delete_order"
    PROCESS_REFUNDS = "process_refunds"
    
    # 会员管理权限
    VIEW_MEMBERSHIPS = "view_memberships"
    CREATE_MEMBERSHIP = "create_membership"
    UPDATE_MEMBERSHIP = "update_membership"
    DELETE_MEMBERSHIP = "delete_membership"
    MANAGE_MEMBERSHIP_LEVELS = "manage_membership_levels"
    
    # 系统管理权限
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_PERMISSIONS = "manage_permissions"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    
    # 内容管理权限
    MODERATE_CONTENT = "moderate_content"
    MANAGE_REVIEWS = "manage_reviews"
    MANAGE_COMMENTS = "manage_comments"
    
    # 财务管理权限
    VIEW_FINANCIAL_REPORTS = "view_financial_reports"
    MANAGE_PRICING = "manage_pricing"
    MANAGE_PROMOTIONS = "manage_promotions"
    
    # 学习管理权限
    VIEW_LEARNING_PROGRESS = "view_learning_progress"
    MANAGE_LEARNING_PATHS = "manage_learning_paths"
    TRACK_USER_ACTIVITY = "track_user_activity"

# 角色权限映射
ROLE_PERMISSIONS: Dict[str, Set[Permissions]] = {
    "普通用户（家长）": {
        Permissions.VIEW_COURSES,
        Permissions.CREATE_ORDER,
        Permissions.VIEW_ORDERS,
        Permissions.VIEW_LEARNING_PROGRESS,
    },
    "班主任（教师）": {
        # 继承普通用户权限
        Permissions.VIEW_COURSES,
        Permissions.CREATE_ORDER,
        Permissions.VIEW_ORDERS,
        Permissions.VIEW_LEARNING_PROGRESS,
        # 教师特有权限
        Permissions.CREATE_COURSE,
        Permissions.UPDATE_COURSE,
        Permissions.VIEW_USERS,
        Permissions.MANAGE_REVIEWS,
        Permissions.MANAGE_COMMENTS,
        Permissions.TRACK_USER_ACTIVITY,
        Permissions.MANAGE_LEARNING_PATHS,
    },
    "superadmin": {
        # 拥有所有权限
        *list(Permissions)
    }
}

# 角色描述信息
ROLE_DESCRIPTIONS = {
    "普通用户（家长）": {
        "description": "家长用户，可以为孩子购买课程、提交作业、查看学习进度，与老师进行沟通交流",
        "key_features": [
            "浏览和购买课程",
            "提交孩子的作业",
            "查看学习进度和成绩",
            "与班主任沟通交流",
            "接收学习通知和提醒",
            "管理个人账户信息"
        ]
    },
    "班主任（教师）": {
        "description": "教师用户，负责课程教学、作业批改、学生管理，可以创建课程内容和管理班级",
        "key_features": [
            "创建和管理课程内容",
            "批改学生作业和评分",
            "管理班级学生信息",
            "发布课程通知和公告",
            "跟踪学生学习进度",
            "与家长沟通交流",
            "生成学习报告和统计"
        ]
    },
    "superadmin": {
        "description": "超级管理员，拥有平台最高权限，负责整个系统的管理和维护",
        "key_features": [
            "管理所有用户账户",
            "配置系统权限和角色",
            "审核和管理课程内容",
            "处理订单和退款",
            "查看系统运营数据",
            "管理会员等级和权益",
            "系统备份和恢复",
            "内容审核和监管"
        ]
    }
}

def get_role_permissions(role: str) -> Set[Permissions]:
    """获取角色权限"""
    return ROLE_PERMISSIONS.get(role, set())

def get_role_description(role: str) -> Dict:
    """获取角色描述信息"""
    return ROLE_DESCRIPTIONS.get(role, {"description": "未知角色", "key_features": []})

def has_permission(user_role: str, permission: Permissions) -> bool:
    """检查用户是否有指定权限"""
    role_permissions = get_role_permissions(user_role)
    return permission in role_permissions

def require_permission(permission: Permissions):
    """权限装饰器，要求用户具有指定权限"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="需要用户认证"
                )
            
            if not has_permission(current_user.role, permission):
                logger.warning(f"用户 {current_user.username} (角色: {current_user.role}) 尝试访问需要权限 {permission.value} 的资源")
                raise HTTPException(
                    status_code=403,
                    detail=f"权限不足，需要权限: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_user_permissions(user_role: str) -> List[str]:
    """获取用户权限列表"""
    permissions = get_role_permissions(user_role)
    return [p.value for p in permissions]

def count_role_permissions(role: str) -> int:
    """统计角色权限数量"""
    return len(get_role_permissions(role))

def get_all_roles() -> List[str]:
    """获取所有角色列表"""
    return list(ROLE_PERMISSIONS.keys())

def get_all_permissions() -> List[str]:
    """获取所有权限列表"""
    return [p.value for p in Permissions]