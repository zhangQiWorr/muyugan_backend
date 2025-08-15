"""
智能体管理相关API
包含智能体的CRUD操作、模型和工具管理
"""

from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import get_db
from models.user import User
from models.schemas import AgentCreate
from api.auth import get_current_user
from utils.logger import get_logger

logger = get_logger("agents_api")
router = APIRouter(prefix="/agents", tags=["智能体管理"])


def get_agent_manager():
    """获取智能体管理器"""
    from main import app
    return app.state.agent_manager


@router.get("", response_model=dict)
async def get_agents(
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取智能体列表"""
    agent_manager = get_agent_manager()
    return await agent_manager.get_agents_list(
        db=db,
        category=category,
        search_query=search,
        skip=skip,
        limit=limit
    )


@router.get("/{agent_id}", response_model=dict)
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """获取智能体详情"""
    agent_manager = get_agent_manager()
    agent = await agent_manager.get_agent_by_id(db, agent_id)
    return agent.to_dict()


@router.post("", response_model=dict)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建智能体"""
    agent_manager = get_agent_manager()
    agent = await agent_manager.create_agent(
        db=db,
        agent_data=agent_data.dict()
    )
    return agent.to_dict()


@router.put("/{agent_id}", response_model=dict)
async def update_agent(
    agent_id: str,
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新智能体"""
    agent_manager = get_agent_manager()
    agent = await agent_manager.update_agent(
        db=db,
        agent_id=agent_id,
        agent_data=agent_data.dict()
    )
    return agent.to_dict()


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除智能体"""
    agent_manager = get_agent_manager()
    return await agent_manager.delete_agent(db, agent_id)


@router.get("/models/available", response_model=List[dict])
async def get_available_models():
    """获取可用模型列表"""
    agent_manager = get_agent_manager()
    return await agent_manager.get_available_models()


@router.get("/tools/available", response_model=List[dict])
async def get_available_tools():
    """获取可用工具列表"""
    agent_manager = get_agent_manager()
    return await agent_manager.get_available_tools() 