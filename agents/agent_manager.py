"""
智能体管理器
"""
from typing import List, Dict, Any, Optional

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from models.agent import Agent, AgentConfig
from .agent_factory import AgentFactory
from .default_agents import DefaultAgents
from utils.logger import get_logger

# 获取agent logger
agent_logger = get_logger("agent")


class AgentManager:
    """智能体管理器"""
    
    def __init__(self):
        self.agent_factory = AgentFactory()
        self._default_agent = None  # 内存中存储的默认agent
        self._default_agent_id = None  # 默认agent的ID
    
    async def initialize_default_agent(self, db: Session):
        """初始化默认智能体到内存中（硬编码配置，但需要保存到数据库以满足外键约束）"""
        try:
            # 创建一个硬编码的默认智能体配置
            default_agent_data = {
                "id": "default-agent-memory",
                "name": "default_assistant",
                "display_name": "默认助手",
                "description": "这是一个默认的AI助手，可以帮助您解答各种问题，提供信息查询、计算、翻译等服务。",
                "avatar_url": "/static/avatars/default_assistant.png",
                "model_name": "deepseek-v3",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key_name": "DASHSCOPE_API_KEY",
                "system_prompt": """你是一个友好、专业的AI助手，名字叫"默认助手"。你的主要职责是帮助用户解答问题、提供信息和完成各种任务。

你的特点：
- 友好亲切，善于沟通
- 知识渊博，能够提供准确的信息
- 有耐心，会详细解释复杂概念
- 支持多种语言交流
- 能够使用工具来帮助用户

你可以帮助用户：
1. 回答各种知识性问题
2. 查询天气信息
3. 进行数学计算
4. 翻译文本
5. 搜索相关信息

请始终保持礼貌、专业，并尽力为用户提供有用的帮助。""",
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "tools_enabled": ["weather", "search", "calculate", "translate", "web_search"],
                "capabilities": ["问答", "信息查询", "计算", "翻译"],
                "category": "general",
                "tags": ["通用", "助手", "默认"],
                "suggested_topics": [
                    "你现在的智慧达到了人类水平了吗?",
                    "请你给20-28岁未婚女性几点人生建议",
                    "艺术的无限可能,英文怎么翻译"
                ],
                "is_active": True,
                "is_public": True,
                "is_system": True,
                "usage_count": 0,
                "rating": 0.0
            }
            
            # 检查数据库中是否已经存在默认agent
            existing_default_agent = db.query(Agent).filter(Agent.id == default_agent_data["id"]).first()
            
            if existing_default_agent:
                # 如果已存在，更新配置（保持硬编码的最新配置）
                allowed_fields = {
                    "name", "display_name", "description", "avatar_url", "model_name", 
                    "base_url", "api_key_name", "system_prompt", "temperature", "max_tokens", 
                    "top_p", "frequency_penalty", "presence_penalty", "tools_enabled", 
                    "capabilities", "category", "tags", "suggested_topics", "is_active", "is_public", "is_system"
                }
                
                is_updated = False
                for key, value in default_agent_data.items():
                    if key in allowed_fields and hasattr(existing_default_agent, key):
                        current_value = getattr(existing_default_agent, key)
                        if current_value != value:
                            setattr(existing_default_agent, key, value)
                            is_updated = True
                
                if is_updated:
                    db.commit()
                    agent_logger.info(f"✅ 默认智能体配置已更新: {existing_default_agent.display_name}")
                
                # 设置内存引用
                self._default_agent = existing_default_agent
                self._default_agent_id = existing_default_agent.id
                
            else:
                # 如果不存在，创建新的默认agent并保存到数据库
                new_default_agent = Agent(**default_agent_data)
                db.add(new_default_agent)
                db.commit()
                db.refresh(new_default_agent)
                
                # 设置内存引用
                self._default_agent = new_default_agent
                self._default_agent_id = new_default_agent.id
                
                agent_logger.info(f"✅ 默认智能体已创建并保存到数据库: {new_default_agent.display_name}")
            
            agent_logger.info(f"✅ 默认智能体已加载到内存: {self._default_agent.display_name} (ID: {self._default_agent_id})")
                     
        except Exception as e:
            agent_logger.error(f"❌ 初始化默认智能体失败: {str(e)}")
            import traceback
            agent_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            
    def get_default_agent_id(self) -> Optional[str]:
        """获取默认智能体ID"""
        return self._default_agent_id
    
    def get_default_agent(self) -> Optional[Agent]:
        """获取默认智能体对象"""
        return self._default_agent

    async def initialize_default_agents(self, db: Session):
        """初始化默认智能体"""
        default_agents = DefaultAgents.get_default_agents()
        
        for agent_data in default_agents:
            # 检查是否已存在
            existing_agent = db.query(Agent).filter(Agent.name == agent_data["name"]).first()
            if not existing_agent:
                agent = Agent(**agent_data)
                db.add(agent)
            else:
                allowed_fields = {"name", "description", "tools_enabled", "updated_at","tags"}
                isUpdate = False
                for key, value in agent_data.items():
                    if hasattr(existing_agent, key) and key in allowed_fields and value != getattr(existing_agent, key):
                        setattr(existing_agent, key, value)
                        isUpdate = True
                if isUpdate:
                    agent_logger.info(f"更新智能体: {agent_data['name']}")
                    db.add(existing_agent)
        
        db.commit()
        agent_logger.info(f"已初始化 {len(default_agents)} 个默认智能体")
    
    async def get_agents_list(
        self, 
        db: Session,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = True,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取智能体列表"""
        
        query = db.query(Agent).filter(Agent.is_active == True)
        
        # 排除 default-agent-memory
        query = query.filter(Agent.id != "default-agent-memory")
        
        if is_public:
            query = query.filter(Agent.is_public == True)
        
        if user_id:
            query = query.filter(Agent.user_id == user_id)
        
        if category:
            query = query.filter(Agent.category == category)
        
        if tags:
            for tag in tags:
                query = query.filter(Agent.tags.contains([tag]))
        
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Agent.display_name.ilike(search_term),
                    Agent.description.ilike(search_term),
                    Agent.tags.cast(str).ilike(search_term)
                )
            )
        
        # 按使用量和创建时间排序
        query = query.order_by(Agent.usage_count.desc(), Agent.created_at.desc())
        
        total = query.count()
        agents = query.offset(skip).limit(limit).all()
        
        return {
            "agents": [agent.to_dict() for agent in agents],
            "total": total,
            "skip": skip,
            "limit": limit,
            "categories": DefaultAgents.get_agent_categories()
        }
    
    async def get_agent_by_id(self, db: Session, agent_id: str) -> Agent:
        """根据ID获取智能体"""
        agent_logger.info(f"获取智能体: {agent_id}")

        if agent_id:
            if agent_id == self._default_agent_id:
                return self.get_default_agent()

            agent = db.query(Agent).filter(
                and_(Agent.id == agent_id, Agent.is_active == True)
            ).first()

            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="智能体不存在"
                )
        else:
            agent = self.get_default_agent()
        
        return agent
    
    async def create_agent(self, db: Session, agent_data: Dict[str, Any]) -> Agent:
        """创建新智能体"""
        
        # 检查名称是否已存在
        existing_agent = db.query(Agent).filter(Agent.name == agent_data.get("name")).first()
        if existing_agent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="智能体名称已存在"
            )
        
        # 创建智能体
        agent = Agent(**agent_data)
        
        # 验证配置
        validation_result = self.agent_factory.validate_agent_config(agent)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"智能体配置无效: {', '.join(validation_result['errors'])}"
            )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        return agent
    
    async def update_agent(self, db: Session, agent_id: str, agent_data: Dict[str, Any]) -> Agent:
        """更新智能体"""
        agent = await self.get_agent_by_id(db, agent_id)
        
        # 更新字段
        for key, value in agent_data.items():
            if hasattr(agent, key) and key != "id":
                setattr(agent, key, value)
        
        # 验证配置
        validation_result = self.agent_factory.validate_agent_config(agent)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"智能体配置无效: {', '.join(validation_result['errors'])}"
            )
        
        db.commit()
        db.refresh(agent)
        
        return agent
    
    async def delete_agent(self, db: Session, agent_id: str) -> Dict[str, Any]:
        """删除智能体"""
        agent = await self.get_agent_by_id(db, agent_id)
        
        # 检查是否为系统内置智能体
        if agent.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法删除系统内置智能体"
            )
        
        # 软删除
        agent.is_active = False
        db.commit()
        
        return {"message": "智能体已删除"}
    
    async def get_agent_instance(self, db: Session, agent_id: str, model_name: str, base_url: str, api_key_name: str, checkpointer):
        """获取智能体实例（用于聊天）"""
        try:

            # 从数据库获取配置
            agent_config = await self.get_agent_by_id(db, agent_id)
            # 创建智能体实例
            agent_instance = self.agent_factory.create_agent(agent_config, checkpointer)

            # 增加使用计数
            agent_config.usage_count += 1
            db.commit()

            if model_name:
                agent_config.model_name = model_name
            if base_url:
                agent_config.base_url = base_url
            if api_key_name:
                agent_config.api_key_name = api_key_name

            return agent_instance
            
        except Exception as e:
            agent_logger.error(f"❌ 获取智能体实例失败: {str(e)}")
            import traceback
            raise
    
    async def clone_agent(self, db: Session, agent_id: str, new_name: str) -> Agent:
        """克隆智能体"""
        original_agent = await self.get_agent_by_id(db, agent_id)
        
        # 检查新名称是否已存在
        existing_agent = db.query(Agent).filter(Agent.name == new_name).first()
        if existing_agent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="智能体名称已存在"
            )
        
        # 克隆智能体
        agent_data = original_agent.to_dict()
        agent_data["name"] = new_name
        agent_data["display_name"] = f"{original_agent.display_name} (副本)"
        agent_data["is_system"] = False  # 克隆的智能体不是系统内置
        
        # 移除ID字段
        agent_data.pop("id", None)
        agent_data.pop("created_at", None)
        agent_data.pop("updated_at", None)
        agent_data.pop("usage_count", None)
        
        new_agent = Agent(**agent_data)
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        return new_agent
    
    async def get_agent_configs(self, db: Session, agent_id: str) -> List[AgentConfig]:
        """获取智能体的所有配置"""
        agent = await self.get_agent_by_id(db, agent_id)
        
        configs = db.query(AgentConfig).filter(
            and_(AgentConfig.agent_id == agent_id, AgentConfig.is_active == True)
        ).all()
        
        return configs
    
    async def create_agent_config(
        self, 
        db: Session, 
        agent_id: str, 
        config_data: Dict[str, Any]
    ) -> AgentConfig:
        """为智能体创建新配置"""
        agent = await self.get_agent_by_id(db, agent_id)
        
        config = AgentConfig(
            agent_id=agent_id,
            **config_data
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return config
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        return self.agent_factory.get_available_models()
    
    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self.agent_factory.get_available_tools_info()
    
    async def validate_agent_config(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证智能体配置"""
        # 创建临时智能体对象进行验证
        temp_agent = Agent(**agent_data)
        return self.agent_factory.validate_agent_config(temp_agent) 