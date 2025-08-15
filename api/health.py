"""
健康检查和统计相关API
包含根路径、健康检查、平台统计等功能
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import get_db
from models.user import User
from models.agent import Agent
from models.conversation import Conversation, Message
from utils.logger import get_logger

logger = get_logger("health_api")
router = APIRouter(tags=["健康检查和统计"])


@router.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI智能聊天对话平台",
        "version": "2.0.0",
        "status": "running"
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }


@router.get("/stats")
async def get_platform_stats(db: Session = Depends(get_db)):
    """获取平台统计信息"""
    total_users = db.query(User).count()
    total_agents = db.query(Agent).filter(Agent.is_active == True).count()
    total_conversations = db.query(Conversation).filter(Conversation.is_deleted == False).count()
    total_messages = db.query(Message).filter(Message.is_deleted == False).count()
    
    return {
        "total_users": total_users,
        "total_agents": total_agents,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "timestamp": datetime.utcnow().isoformat()
    } 