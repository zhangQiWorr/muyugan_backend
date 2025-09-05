"""
对话管理相关API
包含对话的创建、查询、更新、删除等功能
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models import get_db
from models.user import User
from models.conversation import Conversation
from models.schemas import ConversationCreate, ConversationUpdate
from api.auth import get_current_user
from services.logger import get_logger

logger = get_logger("conversations_api")
router = APIRouter(prefix="/conversations", tags=["对话管理"])


def get_agent_manager():
    """获取智能体管理器"""
    from main import app
    return app.state.agent_manager


@router.get("", response_model=dict)
async def get_conversations(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户对话列表"""
    query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    )
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(Conversation.title.ilike(search_term))
    
    query = query.order_by(Conversation.last_message_at.desc())
    total = query.count()
    conversations = query.offset(skip).limit(limit).all()
    
    return {
        "conversations": [conv.to_dict() for conv in conversations],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=dict)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新对话"""
    # 验证智能体是否存在
    agent_manager = get_agent_manager()
    agent = await agent_manager.get_agent_by_id(db, conversation_data.agent_id)


    conversation = Conversation(
        user_id=current_user.id,
        agent_id=agent.id,
        title=conversation_data.title or f"与{agent.display_name}的对话"
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return conversation.to_dict()


@router.get("/{conversation_id}", response_model=dict)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取对话详情和消息历史"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    return conversation.to_dict(include_messages=True)


@router.put("/{conversation_id}", response_model=dict)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新对话信息"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    if update_data.title:
        conversation.title = update_data.title
    
    if update_data.tags:
        conversation.tags = update_data.tags
    
    db.commit()
    db.refresh(conversation)
    
    return conversation.to_dict()


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除对话"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )
    
    conversation.is_deleted = True
    db.commit()
    
    return {"message": "对话已删除"} 