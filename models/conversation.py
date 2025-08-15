"""
对话和消息模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, asc, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid




class Message(Base):
    """消息模型"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    
    # 消息内容
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)

    # 消息元数据
    message_metadata = Column(JSON, default=dict)  # 包含工具调用、附件等信息
    token_count = Column(Integer, default=0)
    
    # 消息状态
    is_deleted = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    parent_message_id = Column(String, nullable=True)  # 用于消息编辑历史
    
    # 工具相关
    tool_calls = Column(JSON, default=list)  # 工具调用信息
    tool_call_id = Column(String, nullable=True)  # 工具调用ID
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "message_metadata": self.message_metadata,
            "token_count": self.token_count,
            "is_deleted": self.is_deleted,
            "is_edited": self.is_edited,
            "parent_message_id": self.parent_message_id,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Conversation(Base):
    """对话模型"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False, default="新对话")
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)

    # 对话状态
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # 对话元数据
    context = Column(JSON, default=dict)  # 对话上下文信息
    summary = Column(Text, nullable=True)  # 对话摘要
    tags = Column(JSON, default=list)  # 对话标签

    # 统计信息
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime, server_default=func.now())

    # 关系
    user = relationship("User", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by=asc(Message.created_at), cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, user_id={self.user_id})>"

    def to_dict(self, include_messages=False):
        """转换为字典格式"""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "agent_id": self.agent_id,
            "is_active": self.is_active,
            "context": self.context,
            "summary": self.summary,
            "tags": self.tags,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }

        if include_messages:
            result["messages"] = [msg.to_dict() for msg in self.messages]

        return result
