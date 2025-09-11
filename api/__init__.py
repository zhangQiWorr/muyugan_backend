"""
API模块包初始化文件 - 完整版本
包含AI聊天功能和知识付费App功能的所有API路由
"""

from .auth import router as auth_router
from .health import router as health_router
from .images import router as images_router
from .media import router as media_router

# 知识付费相关路由
from .courses import router as courses_router
from .orders import router as orders_router
from .learning import router as learning_router
from .membership import router as membership_router

# 基础路由列表
base_routers = [
    "auth_router",
    "health_router",
    "images_router",
    "media_router",
    "courses_router",
    "orders_router",
    "learning_router",
    "membership_router",
]

# AI相关路由（可选，根据依赖可用性动态导入）
ai_routers = []
try:
    from .agents import router as agents_router
    from .conversations import router as conversations_router
    from .chat import router as chat_router
    from .admin import router as admin_router
    
    ai_routers = [
        "agents_router",
        "conversations_router",
        "chat_router",
        "admin_router",
    ]
    
    __all__ = base_routers + ai_routers
except ImportError as e:
    # 如果AI相关模块不可用，只导出基础功能
    print(f"⚠️ AI相关模块导入失败: {e}")
    print("系统将以简化模式运行，仅支持知识付费功能")
    __all__ = base_routers