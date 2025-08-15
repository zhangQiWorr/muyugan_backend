"""审计日志服务"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta
import time
import json
from fastapi import Request

from models.audit_log import AuditLog
from models.user import User


class AuditService:
    """审计日志服务类"""
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        action: str = "unknown",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> AuditLog:
        """记录操作日志"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                method=method,
                endpoint=endpoint,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                status=status,
                error_message=error_message,
                duration_ms=duration_ms
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            return audit_log
        except Exception as e:
            db.rollback()
            print(f"Failed to log audit action: {str(e)}")
            return None
    
    @staticmethod
    def log_from_request(
        db: Session,
        request: Request,
        user: Optional[User] = None,
        action: str = "api_call",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        start_time: Optional[float] = None
    ) -> AuditLog:
        """从请求对象记录日志"""
        # 计算耗时
        duration_ms = None
        if start_time:
            duration_ms = int((time.time() - start_time) * 1000)
        
        # 获取IP地址
        ip_address = request.client.host if request.client else None
        if not ip_address:
            # 尝试从代理头获取真实IP
            ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            if not ip_address:
                ip_address = request.headers.get("X-Real-IP")
        
        return AuditService.log_action(
            db=db,
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            method=request.method,
            endpoint=str(request.url.path),
            ip_address=ip_address,
            user_agent=request.headers.get("User-Agent"),
            details=details,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )
    
    @staticmethod
    def get_logs(
        db: Session,
        page: int = 1,
        size: int = 50,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询审计日志"""
        try:
            query = db.query(AuditLog)
            
            # 应用筛选条件
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            
            if username:
                query = query.filter(AuditLog.username.ilike(f"%{username}%"))
            
            if action:
                query = query.filter(AuditLog.action == action)
            
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            
            if status:
                query = query.filter(AuditLog.status == status)
            
            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)
            
            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)
            
            if search:
                search_conditions = [
                    AuditLog.username.ilike(f"%{search}%"),
                    AuditLog.action.ilike(f"%{search}%"),
                    AuditLog.resource_type.ilike(f"%{search}%"),
                    AuditLog.resource_name.ilike(f"%{search}%"),
                    AuditLog.endpoint.ilike(f"%{search}%")
                ]
                query = query.filter(or_(*search_conditions))
            
            # 按时间倒序排列
            query = query.order_by(desc(AuditLog.created_at))
            
            # 分页
            total = query.count()
            logs = query.offset((page - 1) * size).limit(size).all()
            
            return {
                "logs": [log.to_dict() for log in logs],
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
        except Exception as e:
            print(f"Failed to get audit logs: {str(e)}")
            return {
                "logs": [],
                "total": 0,
                "page": page,
                "size": size,
                "pages": 0
            }
    
    @staticmethod
    def get_user_activity_summary(
        db: Session,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户活动摘要"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            query = db.query(AuditLog).filter(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= start_date
                )
            )
            
            total_actions = query.count()
            successful_actions = query.filter(AuditLog.status == "success").count()
            failed_actions = query.filter(AuditLog.status == "failed").count()
            
            # 按操作类型统计
            action_stats = {}
            actions = query.all()
            for log in actions:
                action_stats[log.action] = action_stats.get(log.action, 0) + 1
            
            return {
                "user_id": user_id,
                "period_days": days,
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "failed_actions": failed_actions,
                "success_rate": (successful_actions / total_actions * 100) if total_actions > 0 else 0,
                "action_breakdown": action_stats
            }
        except Exception as e:
            print(f"Failed to get user activity summary: {str(e)}")
            return {
                "user_id": user_id,
                "period_days": days,
                "total_actions": 0,
                "successful_actions": 0,
                "failed_actions": 0,
                "success_rate": 0,
                "action_breakdown": {}
            }
    
    @staticmethod
    def cleanup_old_logs(db: Session, days_to_keep: int = 90) -> int:
        """清理旧的审计日志"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            deleted_count = db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).delete()
            
            db.commit()
            
            return deleted_count
        except Exception as e:
            db.rollback()
            print(f"Failed to cleanup old logs: {str(e)}")
            return 0


# 便捷函数
def log_user_action(
    db: Session,
    user: User,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status: str = "success"
) -> AuditLog:
    """记录用户操作的便捷函数"""
    return AuditService.log_action(
        db=db,
        user_id=user.id,
        username=user.username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        details=details,
        status=status
    )


def log_system_action(
    db: Session,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    status: str = "success"
) -> AuditLog:
    """记录系统操作的便捷函数"""
    return AuditService.log_action(
        db=db,
        action=action,
        details=details,
        status=status
    )