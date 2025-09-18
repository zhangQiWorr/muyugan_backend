"""
数据库配置和连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator
import os

# 数据库连接配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"
)

# 连接池配置（与 config.py 对齐，提供环境变量覆盖）
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    echo=False
)

# 创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

def get_db() -> Generator:
    """
    获取数据库会话的依赖注入函数
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """
    创建所有数据库表
    """
    # 确保所有模型都被导入
    from . import user, conversation, agent, audit_log, course, payment, membership
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """
    删除所有数据库表（仅用于开发测试）
    """
    Base.metadata.drop_all(bind=engine)