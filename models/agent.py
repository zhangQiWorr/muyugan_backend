"""
智能体模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid


class Agent(Base):
    """智能体模型"""
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # 智能体配置
    model_name = Column(String(100), nullable=False)  # 如: gpt-4, deepseek-chat
    base_url = Column(String(500), nullable=True)  # API基础URL
    api_key_name = Column(String(100), nullable=True)  # 环境变量名
    
    # 系统提示词
    system_prompt = Column(Text, nullable=False)
    
    # 模型参数
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    top_p = Column(Float, default=1.0)
    frequency_penalty = Column(Float, default=0.0)
    presence_penalty = Column(Float, default=0.0)
    
    # 功能配置
    tools_enabled = Column(JSON, default=list)  # 启用的工具列表
    capabilities = Column(JSON, default=list)  # 能力列表
    
    # 分类和标签
    category = Column(String(50), default="general")  # 分类：general, coding, writing, etc.
    tags = Column(JSON, default=list)  # 标签
    
    # 建议对话内容
    suggested_topics = Column(JSON, default=list)  # 建议的对话主题列表
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)  # 是否公开可用
    is_system = Column(Boolean, default=False)  # 是否为系统内置
    
    # 使用统计
    usage_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 用户关联
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    # 关系
    conversations = relationship("Conversation", back_populates="agent")
    configs = relationship("AgentConfig", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, model={self.model_name})>"
    
    def to_dict(self, include_configs=False):
        """转换为字典格式"""
        result = {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "avatar_url": self.avatar_url,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "tools_enabled": self.tools_enabled,
            "capabilities": self.capabilities,
            "category": self.category,
            "tags": self.tags,
            "suggested_topics": self.suggested_topics,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "is_system": self.is_system,
            "usage_count": self.usage_count,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_configs:
            result["configs"] = [config.to_dict() for config in self.configs]
            
        return result


class AgentConfig(Base):
    """智能体配置模型（用于存储不同场景下的配置）"""
    __tablename__ = "agent_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 配置内容
    config_data = Column(JSON, nullable=False)  # 完整的配置数据
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    agent = relationship("Agent", back_populates="configs")
    
    def __repr__(self):
        return f"<AgentConfig(id={self.id}, name={self.name}, agent_id={self.agent_id})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "config_data": self.config_data,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 