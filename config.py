"""
项目配置文件
"""
import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field

class DatabaseSettings(BaseSettings):
    """数据库配置"""
    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/muyugan_db",
        env="DATABASE_URL",
        description="数据库连接URL"
    )
    pool_size: int = Field(default=20, env="DB_POOL_SIZE", description="连接池大小")
    max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW", description="最大溢出连接数")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT", description="连接池超时时间")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE", description="连接回收时间")
    echo: bool = Field(default=False, env="DB_ECHO", description="是否显示SQL语句")

class RedisSettings(BaseSettings):
    """Redis配置"""
    url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis连接URL"
    )
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD", description="Redis密码")
    db: int = Field(default=0, env="REDIS_DB", description="Redis数据库编号")
    max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS", description="最大连接数")

class JWTSettings(BaseSettings):
    """JWT配置"""
    secret_key: str = Field(
        default="your-secret-key-here-please-change-in-production",
        env="JWT_SECRET_KEY",
        description="JWT密钥"
    )
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM", description="JWT算法")
    access_token_expire_minutes: int = Field(
        default=30,
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        description="访问令牌过期时间（分钟）"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        env="JWT_REFRESH_TOKEN_EXPIRE_DAYS",
        description="刷新令牌过期时间（天）"
    )

class LoggingSettings(BaseSettings):
    """日志配置"""
    console_level: str = Field(default="INFO", env="CONSOLE_LOG_LEVEL", description="控制台日志级别")
    file_level: str = Field(default="DEBUG", env="FILE_LOG_LEVEL", description="文件日志级别")
    log_dir: str = Field(default="logs", env="LOG_DIR", description="日志目录")
    max_file_size: int = Field(default=100, env="LOG_MAX_FILE_SIZE", description="日志文件最大大小（MB）")
    backup_count: int = Field(default=10, env="LOG_BACKUP_COUNT", description="日志备份数量")

class AISettings(BaseSettings):
    """AI配置"""
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY", description="OpenAI API密钥")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL", description="OpenAI基础URL")
    tavily_api_key: Optional[str] = Field(default=None, env="TAVILY_API_KEY", description="Tavily API密钥")
    max_tokens: int = Field(default=30000, env="MAX_TOKENS", description="最大令牌数")
    max_summary_tokens: int = Field(default=4096, env="MAX_SUMMARY_TOKENS", description="最大摘要令牌数")
    temperature: float = Field(default=0.7, env="AI_TEMPERATURE", description="AI温度参数")

class FileUploadSettings(BaseSettings):
    """文件上传配置"""
    upload_dir: str = Field(default="static/uploads", env="UPLOAD_DIR", description="上传目录")
    max_file_size: int = Field(default=100, env="MAX_FILE_SIZE", description="最大文件大小（MB）")
    allowed_extensions: list = Field(
        default=["jpg", "jpeg", "png", "gif", "mp4", "avi", "mov", "pdf", "doc", "docx"],
        env="ALLOWED_EXTENSIONS",
        description="允许的文件扩展名"
    )
    image_extensions: list = Field(
        default=["jpg", "jpeg", "png", "gif", "webp"],
        env="IMAGE_EXTENSIONS",
        description="图片文件扩展名"
    )
    video_extensions: list = Field(
        default=["mp4", "avi", "mov", "mkv", "wmv"],
        env="VIDEO_EXTENSIONS",
        description="视频文件扩展名"
    )

class SecuritySettings(BaseSettings):
    """安全配置"""
    cors_origins: list = Field(
        default=["*"],
        env="CORS_ORIGINS",
        description="CORS允许的源"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        env="CORS_ALLOW_CREDENTIALS",
        description="CORS是否允许凭据"
    )
    rate_limit_per_minute: int = Field(
        default=100,
        env="RATE_LIMIT_PER_MINUTE",
        description="每分钟请求限制"
    )
    bcrypt_rounds: int = Field(
        default=12,
        env="BCRYPT_ROUNDS",
        description="bcrypt加密轮数"
    )

class AppSettings(BaseSettings):
    """应用配置"""
    app_name: str = Field(default="Muyugan Backend", env="APP_NAME", description="应用名称")
    app_version: str = Field(default="1.0.0", env="APP_VERSION", description="应用版本")
    debug: bool = Field(default=False, env="DEBUG", description="调试模式")
    host: str = Field(default="0.0.0.0", env="HOST", description="主机地址")
    port: int = Field(default=8000, env="PORT", description="端口号")
    workers: int = Field(default=1, env="WORKERS", description="工作进程数")
    
    # 子配置
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    jwt: JWTSettings = JWTSettings()
    logging: LoggingSettings = LoggingSettings()
    ai: AISettings = AISettings()
    file_upload: FileUploadSettings = FileUploadSettings()
    security: SecuritySettings = SecuritySettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# 全局配置实例
settings = AppSettings()

def get_settings() -> AppSettings:
    """获取配置实例"""
    return settings

def get_database_url() -> str:
    """获取数据库URL"""
    return settings.database.url

def get_redis_url() -> str:
    """获取Redis URL"""
    return settings.redis.url

def get_jwt_secret_key() -> str:
    """获取JWT密钥"""
    return settings.jwt.secret_key

def is_debug_mode() -> bool:
    """是否为调试模式"""
    return settings.debug

def get_cors_origins() -> list:
    """获取CORS源"""
    return settings.security.cors_origins

def get_upload_dir() -> str:
    """获取上传目录"""
    return settings.file_upload.upload_dir

def get_max_file_size() -> int:
    """获取最大文件大小（MB）"""
    return settings.file_upload.max_file_size

def get_allowed_extensions() -> list:
    """获取允许的文件扩展名"""
    return settings.file_upload.allowed_extensions

def get_image_extensions() -> list:
    """获取图片文件扩展名"""
    return settings.file_upload.image_extensions

def get_video_extensions() -> list:
    """获取视频文件扩展名"""
    return settings.file_upload.video_extensions
