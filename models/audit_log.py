"""审计日志模型定义"""
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.sql import func
from .database import Base
import uuid


class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)  # 用户ID，可为空（系统操作）
    username = Column(String(50), nullable=True)  # 用户名，冗余存储便于查询
    action = Column(String(50), nullable=False)  # 操作类型：login, logout, create, update, delete, view等
    resource_type = Column(String(50), nullable=True)  # 资源类型：user, course, order等
    resource_id = Column(String, nullable=True)  # 资源ID
    resource_name = Column(String(255), nullable=True)  # 资源名称
    method = Column(String(10), nullable=True)  # HTTP方法：GET, POST, PUT, DELETE
    endpoint = Column(String(255), nullable=True)  # API端点
    ip_address = Column(String(45), nullable=True)  # IP地址（支持IPv6）
    user_agent = Column(Text, nullable=True)  # 用户代理
    details = Column(JSON, nullable=True)  # 详细信息，JSON格式
    status = Column(String(20), default='success')  # 操作状态：success, failed, error
    error_message = Column(Text, nullable=True)  # 错误信息
    duration_ms = Column(Integer, nullable=True)  # 操作耗时（毫秒）
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user={self.username}, action={self.action}, resource={self.resource_type})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "method": self.method,
            "endpoint": self.endpoint,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def create_log(cls, **kwargs):
        """创建审计日志的便捷方法"""
        return cls(**kwargs)