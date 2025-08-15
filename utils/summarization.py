"""
长对话摘要模块
使用langmem的SummarizationNode处理超出上下文窗口的对话
"""
import os
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger("summarization")

# 条件导入，避免LangGraph兼容性问题
LANGMEM_AVAILABLE = False
LANGCHAIN_AVAILABLE = False
LANGGRAPH_AVAILABLE = False

try:
    from langchain_core.messages.utils import count_tokens_approximately, trim_messages
    LANGCHAIN_AVAILABLE = True
    logger.info("✅ langchain模块加载成功")
except ImportError:
    logger.warning("⚠️ langchain模块未安装")

try:
    from langgraph.prebuilt.chat_agent_executor import AgentState
    LANGGRAPH_AVAILABLE = True
    logger.info("✅ langgraph模块加载成功")
except ImportError:
    logger.warning("⚠️ langgraph模块未安装")

try:
    from langmem.short_term import SummarizationNode
    LANGMEM_AVAILABLE = True
    logger.info("✅ langmem模块加载成功")
except ImportError:
    logger.warning("⚠️ langmem模块未安装，将使用简单摘要功能")

max_tokens = int(os.getenv("MAX_TOKENS", 1024000))
max_summary_tokens = int(os.getenv("MAX_SUMMARY_TOKENS", 4096))
long_messages_strategy = os.getenv("LONG_MESSAGES_STRATEGY", "summarize")


def create_summarization_hook(model):
    """模型调用前的摘要钩子，管理长对话历史"""
    
    if not LANGCHAIN_AVAILABLE:
        logger.warning("⚠️ langchain不可用，无法创建摘要钩子")
        return None

    if long_messages_strategy == "summarize":
        if not LANGMEM_AVAILABLE:
            logger.warning("⚠️ langmem不可用，无法使用摘要功能")
            return None
            
        summarization_node = SummarizationNode(
            token_counter=count_tokens_approximately,
            model=model,
            max_tokens=max_tokens,  # 设置最大 token 数量，当消息历史超过这个数量时将触发摘要操作
            max_summary_tokens=max_summary_tokens,  # 设置摘要后保留的最大 token 数量。
            output_messages_key="llm_input_messages",  # 指定输出消息的键名，该键将包含经过摘要处理后的消息。
        )
        return summarization_node
    elif long_messages_strategy == "trim":
        def pre_model_hook(state):
            trimmed_messages = trim_messages(
                state["messages"],  # 表示当前状态中的消息历史列表。
                strategy="last",  # 裁剪策略为保留最后几条消息（从后往前保留），直到满足 max_tokens 的限制。
                token_counter=count_tokens_approximately,  # 使用指定的函数估算 token 数量。
                max_tokens=max_tokens,  # 设置最大 token 数量，超过这个限制的消息将被裁剪。
                start_on="human",  # 指定裁剪后的消息序列必须从一个用户（"human"）消息开始。
                end_on=("human", "tool"),  # 指定裁剪后的消息序列可以以用户（"human"）或工具调用（"tool"）消息结束。
            )
            return {"llm_input_messages": trimmed_messages}

        return pre_model_hook


# 便捷函数
def get_summarization_config() -> Dict[str, Any]:
    """获取摘要配置"""
    return {
        "max_tokens": int(os.getenv("MAX_TOKENS", 4000)),
        "max_summary_tokens": int(os.getenv("MAX_SUMMARY_TOKENS", 1000)),
        "enabled": LANGMEM_AVAILABLE and LANGCHAIN_AVAILABLE,
        "langchain_available": LANGCHAIN_AVAILABLE,
        "langgraph_available": LANGGRAPH_AVAILABLE,
        "langmem_available": LANGMEM_AVAILABLE
    } 