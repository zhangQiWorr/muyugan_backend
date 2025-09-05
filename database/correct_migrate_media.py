#!/usr/bin/env python3
"""
正确的Media表迁移脚本
根据models/media.py中的定义重建表结构
"""

import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, Text, JSON, ForeignKey, BigInteger, Enum, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import enum

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 枚举定义（与models/media.py保持一致）
class MediaType(enum.Enum):
    VIDEO = "video"
    AUDIO = "audio"

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

# 数据库连接
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

def backup_existing_data(session):
    """备份现有数据"""
    try:
        result = session.execute(text("SELECT * FROM media"))
        data = [dict(row._mapping) for row in result]
        
        # 转换datetime对象为字符串
        for record in data:
            for key, value in record.items():
                if isinstance(value, datetime):
                    record[key] = value.isoformat()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"media_backup_{timestamp}.json"
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"已备份 {len(data)} 条记录到 {backup_file}")
        return len(data)
    except Exception as e:
        print(f"备份数据时出错: {e}")
        return 0

def create_correct_media_table(engine):
    """创建正确的media表结构"""
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
    
    # 创建表
    Base.metadata.create_all(engine)
    return Media

def verify_table_structure(engine):
    """验证表结构"""
    with engine.connect() as conn:
        # 获取表结构信息
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'media' 
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        
        print("\n新表结构:")
        print("-" * 80)
        print(f"{'列名':<20} {'数据类型':<25} {'可空':<10} {'默认值':<25}")
        print("-" * 80)
        
        for col in columns:
            nullable = "是" if col[2] == "YES" else "否"
            default = col[3] if col[3] else ""
            print(f"{col[0]:<20} {col[1]:<25} {nullable:<10} {default:<25}")
        
        print(f"\n总共 {len(columns)} 个字段")
        
        # 检查必要字段
        required_fields = [
            'id', 'description', 'filename', 'filepath', 'media_type', 
            'cover_url', 'duration', 'size', 'mime_type', 'uploader_id', 
            'lesson_id', 'upload_time', 'upload_status', 'upload_progress', 
            'task_id', 'error_message', 'storage_type', 'oss_key', 'oss_etag', 
            'oss_storage_class', 'oss_last_modified', 'oss_version_id', 'extra'
        ]
        
        existing_fields = [col[0] for col in columns]
        missing_fields = [field for field in required_fields if field not in existing_fields]
        
        if missing_fields:
            print(f"\n❌ 缺少字段: {', '.join(missing_fields)}")
            return False
        else:
            print("\n✓ 所有必要字段都已存在")
            return True

def main():
    print("Media表结构修正迁移脚本")
    print("=" * 50)
    
    # 确认操作
    confirm = input("\n这将删除现有的media表并重新创建。所有数据将被备份。\n继续? (y/N): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = None
    
    try:
        session = Session()
        print(f"\n连接到数据库: {DATABASE_URL}")
        
        # 1. 备份现有数据
        print("\n1. 备份现有数据...")
        record_count = backup_existing_data(session)
        
        # 2. 删除现有表
        print("\n2. 删除现有表...")
        session.execute(text("DROP TABLE IF EXISTS media CASCADE"))
        session.commit()
        print("已删除media表")
        
        # 3. 创建新表
        print("\n3. 创建新表...")
        Media = create_correct_media_table(engine)
        print("已创建新的media表")
        
        # 4. 验证表结构
        print("\n4. 验证表结构...")
        if verify_table_structure(engine):
            print("\n✓ Media表结构修正完成!")
        else:
            print("\n❌ 表结构验证失败")
            
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    main()