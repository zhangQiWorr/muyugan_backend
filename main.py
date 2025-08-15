#!/usr/bin/env python3
"""
AI 智能聊天对话平台 + 知识付费App后端主应用
基于 LangGraph 框架构建的完整智能聊天系统
包含用户认证、智能体管理、对话管理、课程管理、订单支付、会员系统等完整功能
"""

import os
import sys
from contextlib import asynccontextmanager

# FastAPI 相关导入
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 自定义模块导入
from models import SessionLocal, create_tables
from auth.auth_handler import AuthHandler
from utils.logger import get_logger
from utils.middleware import APILoggingMiddleware, RequestContextMiddleware

# API路由导入 - 基础功能
from api import (
    auth_router,
    health_router,
    video_router,
    images_router
)

# 知识付费相关API路由导入
from api.courses import router as courses_router
from api.orders import router as orders_router
from api.learning import router as learning_router
from api.membership import router as membership_router
from api.superadmin import router as superadmin_router

# 获取主应用logger
logger = get_logger("main")


def setup_environment():
    """设置默认环境变量"""
    env_vars = {
        "JWT_SECRET_KEY": "your-secret-key-here-please-change-in-production",
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable",
        "MAX_TOKENS": "30000",
        "MAX_SUMMARY_TOKENS": "4096",
        "LONG_MESSAGES_STRATEGY": "summarize",
        "CONSOLE_LOG_LEVEL": "INFO",
        "FILE_LOG_LEVEL": "INFO",
        "TAVILY_API_KEY": "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",

        "VISION_MODEL_NAME": "qwen-vl-max",
        "VISION_MODEL_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "VISION_MODEL_API_KEY_NAME":"DASHSCOPE_API_KEY",
        "DASHSCOPE_API_KEY":"sk-0ff6fec39a9f4b8597cde0b572bbd7af"
    }
    
    # 设置必需的环境变量
    for key, default_value in env_vars.items():
        if not os.getenv(key):
            os.environ[key] = default_value
            logger.debug(f"设置默认环境变量: {key}")


def check_dependencies():
    """检查必要的依赖"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        logger.info("✅ 基础依赖检查通过")
        
        # 尝试导入AI相关依赖
        try:
            import langgraph
            import langchain
            logger.info("✅ AI相关依赖检查通过")
            return True, True  # 返回(基础依赖, AI依赖)
        except ImportError as e:
            logger.warning(f"⚠️ AI相关依赖缺失: {e}")
            logger.info("系统将以简化模式运行，仅支持知识付费功能")
            return True, False  # 返回(基础依赖, AI依赖)
            
    except ImportError as e:
        logger.error(f"❌ 缺少基础依赖: {e}")
        logger.error("请运行: pip install -r requirements.txt")
        return False, False


def print_startup_banner():
    """打印启动横幅"""
    banner = """
╭─────────────────────────────────────────────────╮
│        AI 智能聊天 + 知识付费App后端系统         │
│                                               │
│   🤖 AI智能聊天系统                            │
│   🎓 课程管理系统                             │
│   👤 用户认证系统                             │
│   🛒 订单支付系统                             │
│   👑 会员管理系统                             │
│   📊 学习跟踪系统                             │
│                                               │
│   版本: 2.0.0                                 │
╰─────────────────────────────────────────────────╯
"""
    print(banner)


# 动态注册AI相关路由（如果依赖可用）
def register_ai_routes():
    """动态注册AI相关路由"""
    try:
        from api import (
            agents_router,
            conversations_router,
            chat_router,
            admin_router
        )
        
        app.include_router(agents_router)
        app.include_router(conversations_router)
        app.include_router(chat_router)
        app.include_router(admin_router)
        
        logger.info("✅ AI相关路由已注册")
        return True
    except ImportError as e:
        logger.warning(f"⚠️ AI相关路由注册失败: {e}")
        return False

# 在lifespan中注册AI路由
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 打印启动横幅
    print_startup_banner()
    
    # 检查依赖
    base_deps_ok, ai_deps_ok = check_dependencies()
    if not base_deps_ok:
        logger.error("❌ 基础依赖检查失败，请安装必要的依赖")
        sys.exit(1)
    
    # 设置环境变量
    setup_environment()
    
    # 启动时初始化
    if ai_deps_ok:
        logger.info("🚀 正在启动AI智能聊天 + 知识付费App后端系统...")
    else:
        logger.info("🚀 正在启动知识付费App后端系统（简化模式）...")
    
    # 创建数据库表
    create_tables()
    logger.info("✅ 数据库表已创建")
    
    # 初始化基础管理器
    app.state.auth_handler = AuthHandler()
    
    # 尝试初始化AI相关功能
    if ai_deps_ok:
        try:
            # 尝试导入AI相关模块
            from langgraph.checkpoint.memory import MemorySaver
            from langgraph.checkpoint.postgres import PostgresSaver
            from agents.agent_manager import AgentManager
            
            # 初始化检查点存储
            try:
                with PostgresSaver.from_conn_string(os.getenv("DATABASE_URL")) as checkpointer:
                    checkpointer.setup()
                    logger.info("✅ PostgreSQL检查点存储已初始化")
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL连接失败，使用内存存储: {e}")
                checkpointer = MemorySaver()
            
            # 初始化智能体管理器
            app.state.agent_manager = AgentManager()
            
            # 初始化数据库会话
            db = SessionLocal()
            try:
                await app.state.agent_manager.initialize_default_agents(db)
                logger.info("✅ 默认智能体已初始化")
                
                # 初始化默认智能体到内存中
                await app.state.agent_manager.initialize_default_agent(db)
                logger.info("✅ 默认智能体已加载到内存")
            finally:
                db.close()
                
            logger.info("✅ AI智能聊天功能已启用")
            
        except Exception as e:
            logger.error(f"❌ AI功能初始化失败: {e}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            logger.warning("系统将以简化模式运行，仅支持知识付费功能")
            ai_deps_ok = False
    else:
        logger.info("ℹ️ AI功能未启用，系统以简化模式运行")
    
    # 尝试注册AI路由
    if ai_deps_ok:
        try:
            register_ai_routes()
        except Exception as e:
            logger.warning(f"⚠️ AI路由注册失败: {e}")
    
    if ai_deps_ok:
        logger.info("🎉 AI智能聊天 + 知识付费App后端系统启动完成!")
    else:
        logger.info("🎉 知识付费App后端系统启动完成!")
    
    yield
    
    # 关闭时清理
    logger.info("👋 正在关闭后端系统...")


# 创建FastAPI应用
app = FastAPI(
    title="AI智能聊天 + 知识付费App后端系统",
    description="完整的AI聊天平台和知识付费应用后端，支持智能对话、课程管理、用户管理、订单支付、会员系统等功能",
    version="2.0.0",
    lifespan=lifespan
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件
app.add_middleware(APILoggingMiddleware)
app.add_middleware(RequestContextMiddleware)

# 注册基础路由
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(video_router)
app.include_router(images_router)

# 注册知识付费相关路由
app.include_router(courses_router)
app.include_router(orders_router)
app.include_router(learning_router)
app.include_router(membership_router)
app.include_router(superadmin_router)

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "AI智能聊天 + 知识付费App后端系统",
        "version": "2.0.0",
        "features": {
            "ai_chat": "enabled",  # 根据实际状态动态设置
            "knowledge_app": "enabled"
        }
    }

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用AI智能聊天 + 知识付费App后端系统",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "AI智能聊天",
            "课程管理",
            "用户认证",
            "订单支付",
            "会员系统",
            "学习跟踪"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )