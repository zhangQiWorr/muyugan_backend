"""
智能体工厂 - 动态创建和配置智能体
"""
import os
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch

from models.agent import Agent
from services.logger import get_logger
from utils.summarization import create_summarization_hook

# 获取factory logger
factory_logger = get_logger("factory")


class AgentFactory:
    """智能体工厂"""
    
    def __init__(self):
        self.available_tools = self._load_available_tools()
        
    def _load_available_tools(self) -> Dict[str, Any]:
        """加载可用工具"""
        tools = {}
        
        @tool
        def get_weather(city: str) -> str:
            """获取指定城市的天气预报"""
            return f"{city}的天气是晴天，温度适宜！"
        
        @tool
        def search_information(query: str) -> str:
            """搜索相关信息"""
            return f"关于 '{query}' 的搜索结果：这是一个示例搜索结果。"
        
        @tool
        def calculate(expression: str) -> str:
            """计算数学表达式"""
            try:
                result = eval(expression)
                return f"计算结果: {expression} = {result}"
            except Exception as e:
                return f"计算错误: {str(e)}"
        
        @tool
        def translate_text(text: str, target_language: str = "en") -> str:
            """翻译文本"""
            return f"将 '{text}' 翻译为 {target_language}: [翻译结果]"
        

        @tool
        def code_analyzer(code: str, language: str = "python") -> str:
            """分析代码"""
            return f"代码分析结果 ({language}): {code[:100]}... [分析完成]"
        
        tools.update({
            "weather": get_weather,
            "calculate": calculate,
            "translate": translate_text,
            "code_analyzer": code_analyzer,
            "web_search": TavilySearch()
        })
        
        return tools
    
    def create_llm(self, agent_config: Agent) -> ChatOpenAI:
        """创建语言模型实例"""
        
        # 获取API密钥
        api_key = None
        if agent_config.api_key_name:
            api_key = os.getenv(agent_config.api_key_name)
        
        # 根据模型名称设置默认配置
        if "deepseek" in agent_config.model_name.lower():
            api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            base_url = agent_config.base_url or "https://api.deepseek.com"
        elif "gpt" in agent_config.model_name.lower():
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            base_url = agent_config.base_url or "https://api.openai.com/v1"
        else:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            base_url = agent_config.base_url
        
        llm_config = {
            "model": agent_config.model_name,
            "temperature": agent_config.temperature,
            "max_tokens": agent_config.max_tokens,
            "top_p": agent_config.top_p,
            "frequency_penalty": agent_config.frequency_penalty,
            "presence_penalty": agent_config.presence_penalty,
            "api_key": api_key
        }
        
        if base_url:
            llm_config["base_url"] = base_url

        print(f"llm config: {llm_config} ")
        
        return ChatOpenAI(
            model= agent_config.model_name,
            base_url= llm_config["base_url"],
            api_key=llm_config["api_key"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            top_p=agent_config.top_p,
            streaming=False,
            model_kwargs={},
            extra_body={"enable_thinking": False}
        )
    
    def get_agent_tools(self, agent_config: Agent) -> List[Any]:
        """获取智能体工具"""
        tools = []
        
        for tool_name in agent_config.tools_enabled:
            if tool_name in self.available_tools:
                tools.append(self.available_tools[tool_name])
        
        return tools

    def create_agent(self, agent_config: Agent, checkpointer=None) -> Any:
        """创建智能体实例"""

        # 使用传入的checkpointer或默认的checkpointer

        factory_logger.info(f"📋 创建智能体实例 - 名称: {agent_config.name}, 模型: {agent_config.model_name}")

        try:
            # 创建语言模型
            llm = self.create_llm(agent_config)

            # 获取工具
            tools = self.get_agent_tools(agent_config)

            # 创建系统消息
            system_message = SystemMessage(content=agent_config.system_prompt)
            
            # 创建摘要钩子
            pre_model_hook = create_summarization_hook(llm)

            # 创建反应式智能体，集成摘要功能
            agent = create_react_agent(
                llm,
                tools,
                prompt=system_message,
                checkpointer=checkpointer,
                pre_model_hook=pre_model_hook
            )

            factory_logger.info(f"✅ 智能体实例创建成功，已集成对话摘要功能")
            return agent
            
        except Exception as e:
            factory_logger.error(f"❌ 创建智能体实例失败: {str(e)}")
            import traceback
            factory_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            raise
    
    def validate_agent_config(self, agent_config: Agent) -> Dict[str, Any]:
        """验证智能体配置"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 检查必需字段
        if not agent_config.model_name:
            validation_result["is_valid"] = False
            validation_result["errors"].append("模型名称不能为空")
        
        if not agent_config.system_prompt:
            validation_result["is_valid"] = False
            validation_result["errors"].append("系统提示词不能为空")
        
        # 检查参数范围
        if not (0.0 <= agent_config.temperature <= 2.0):
            validation_result["warnings"].append("温度参数建议在0.0-2.0之间")
        
        if agent_config.max_tokens <= 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("最大token数必须大于0")
        
        # 检查工具可用性
        invalid_tools = []
        for tool_name in agent_config.tools_enabled:
            if tool_name not in self.available_tools:
                invalid_tools.append(tool_name)
        
        if invalid_tools:
            validation_result["warnings"].append(f"以下工具不可用: {', '.join(invalid_tools)}")
        
        return validation_result
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        return [
            {
                "name": "deepseek-chat",
                "display_name": "DeepSeek Chat",
                "provider": "DeepSeek",
                "description": "DeepSeek的对话模型",
                "context_length": 32768,
                "capabilities": ["chat", "reasoning", "coding"]
            },
            {
                "name": "gpt-4-turbo",
                "display_name": "GPT-4 Turbo",
                "provider": "OpenAI",
                "description": "OpenAI的最新GPT-4模型",
                "context_length": 128000,
                "capabilities": ["chat", "reasoning", "coding", "vision"]
            },
            {
                "name": "gpt-3.5-turbo",
                "display_name": "GPT-3.5 Turbo",
                "provider": "OpenAI",
                "description": "OpenAI的GPT-3.5模型",
                "context_length": 16385,
                "capabilities": ["chat", "reasoning"]
            }
        ]
    
    def get_available_tools_info(self) -> List[Dict[str, Any]]:
        """获取可用工具信息"""
        return [
            {
                "name": "weather",
                "display_name": "天气查询",
                "description": "获取指定城市的天气信息",
                "category": "utility"
            },
            {
                "name": "search",
                "display_name": "信息搜索",
                "description": "搜索相关信息",
                "category": "utility"
            },
            {
                "name": "calculate",
                "display_name": "数学计算",
                "description": "进行数学表达式计算",
                "category": "productivity"
            },
            {
                "name": "translate",
                "display_name": "文本翻译",
                "description": "翻译文本到指定语言",
                "category": "language"
            },
            {
                "name": "code_analyzer",
                "display_name": "代码分析",
                "description": "分析和解释代码",
                "category": "development"
            },
            {
                "name": "web_search",
                "display_name": "网页搜索",
                "description": "联网搜索",
                "category": "development"
            }
        ] 