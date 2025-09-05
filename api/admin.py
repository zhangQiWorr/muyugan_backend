"""
管理员功能相关API
包含日志管理、摘要配置等管理功能
"""

from fastapi import APIRouter, Depends
from models.user import User
from models.schemas import LogLevelRequest
from api.auth import get_current_user
from services.logger import get_logger, EnhancedLogger

logger = get_logger("admin_api")
router = APIRouter(prefix="/admin", tags=["管理员"])


# 日志管理接口
@router.post("/logs/console/level")
async def set_console_log_level_api(request: LogLevelRequest, current_user: User = Depends(get_current_user)):
    """设置控制台日志级别"""
    logger.info(f"用户 {current_user.username} 设置控制台日志级别为: {request.level}")
    # 使用新的日志系统API
    EnhancedLogger.get_logger("muyugan.app").setLevel(request.level.upper())
    return {"message": f"控制台日志级别已设置为: {request.level}"}


@router.post("/logs/file/level")
async def set_file_log_level_api(request: LogLevelRequest, current_user: User = Depends(get_current_user)):
    """设置文件日志级别"""
    logger.info(f"用户 {current_user.username} 设置文件日志级别为: {request.level}")
    # 使用新的日志系统API
    EnhancedLogger.get_logger("muyugan.app").setLevel(request.level.upper())
    return {"message": f"文件日志级别已设置为: {request.level}"}


@router.post("/logs/debug/enable")
async def enable_debug_mode_api(current_user: User = Depends(get_current_user)):
    """启用调试模式"""
    logger.info(f"用户 {current_user.username} 启用调试模式")
    # 使用新的日志系统API
    EnhancedLogger.get_logger("muyugan.app").setLevel("DEBUG")
    return {"message": "调试模式已启用"}


@router.post("/logs/debug/disable")
async def disable_debug_mode_api(current_user: User = Depends(get_current_user)):
    """禁用调试模式"""
    logger.info(f"用户 {current_user.username} 禁用调试模式")
    # 使用新的日志系统API
    EnhancedLogger.get_logger("muyugan.app").setLevel("INFO")
    return {"message": "调试模式已禁用"}


@router.get("/summarization/config")
async def get_summarization_config_api():
    """获取摘要配置信息"""
    try:
        from utils.summarization import get_summarization_config
        config = get_summarization_config()
        return {
            "message": "摘要配置信息",
            "config": config
        }
    except ImportError as e:
        logger.warning(f"摘要功能不可用: {e}")
        return {
            "message": "摘要功能不可用",
            "config": {
                "enabled": False,
                "error": str(e)
            }
        } 