#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建包含IMAGE类型的media表结构
"""

import os
import sys
import enum
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, BigInteger, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker

# 数据库连接
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/muyugan_db"

# 枚举定义
class MediaType(enum.Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"  # 包含IMAGE类型

class UploadStatus(enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    COMPLETED = "completed"
    FAILED = "failed"
    SYNCED = "synced"

class StorageType(enum.Enum):
    LOCAL = "local"
    OSS = "oss"

class OSSStorageClass(enum.Enum):
    STANDARD = "Standard"
    IA = "IA"
    ARCHIVE = "Archive"
    COLD_ARCHIVE = "ColdArchive"

def create_media_table_with_image():
    """创建包含IMAGE类型的media表"""
    try:
        # 创建数据库引擎
        engine = create_engine(DATABASE_URL)
        Base = declarative_base()
        
        class Media(Base):
            __tablename__ = "media"
            
            id = Column(String, primary_key=True)
            description = Column(Text, nullable=True)
            filename = Column(String(255), nullable=False)
            filepath = Column(String(255), nullable=True)
            media_type = Column(Enum(MediaType), nullable=False)
            cover_url = Column(String(255), nullable=True)
            duration = Column(Integer, nullable=True)
            size = Column(BigInteger, nullable=True)
            mime_type = Column(String(100), nullable=True)
            uploader_id = Column(String, nullable=False)
            lesson_id = Column(String, nullable=True)
            upload_time = Column(DateTime, server_default=func.now())
            
            # 异步上传相关字段
            upload_status = Column(Enum(UploadStatus), default=UploadStatus.PENDING, nullable=False)
            upload_progress = Column(Float, default=0.0, nullable=False)
            task_id = Column(String, nullable=True)
            error_message = Column(Text, nullable=True)
            
            # OSS存储相关字段
            storage_type = Column(Enum(StorageType), default=StorageType.LOCAL, nullable=False)
            oss_key = Column(String(500), nullable=True)
            oss_etag = Column(String(100), nullable=True)
            oss_storage_class = Column(Enum(OSSStorageClass), nullable=True)
            oss_last_modified = Column(DateTime, nullable=True)
            oss_version_id = Column(String(100), nullable=True)
            
            extra = Column(JSON, default=dict)
        
        print("正在删除现有的media表...")
        # 删除现有表
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("DROP TABLE IF EXISTS media CASCADE;"))
                conn.commit()
            print("✅ 现有media表已删除")
        except Exception as e:
            print(f"删除表时出现警告: {e}")
        
        print("正在创建新的media表结构...")
        # 创建新表
        Base.metadata.create_all(engine)
        print("✅ 新的media表结构创建成功")
        
        # 验证表结构
        print("正在验证表结构...")
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'media' 
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            print("\n📋 Media表结构:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
            
            # 检查枚举类型
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'mediatype')
                ORDER BY enumsortorder;
            """))
            enum_values = [row[0] for row in result.fetchall()]
            print(f"\n🏷️  MediaType枚举值: {enum_values}")
            
            if 'image' in enum_values:
                print("✅ IMAGE类型已成功添加到枚举中")
            else:
                print("❌ IMAGE类型未找到")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return False

def main():
    """主函数"""
    print("创建包含IMAGE类型的Media表")
    print("=" * 50)
    
    success = create_media_table_with_image()
    
    if success:
        print("\n🎉 迁移完成！Media表已成功创建，包含IMAGE类型支持")
        return 0
    else:
        print("\n💥 迁移失败！请检查错误信息")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)