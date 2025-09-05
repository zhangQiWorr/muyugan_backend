#!/usr/bin/env python3
"""
简化的Media表重建脚本
直接使用数据库URL，避免复杂的配置依赖
"""

import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接使用数据库URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"

def backup_media_data(session):
    """备份现有的media数据"""
    try:
        # 检查表是否存在
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'media'
            );
        """))
        
        table_exists = result.scalar()
        
        if not table_exists:
            print("Media表不存在，跳过备份")
            return []
        
        # 备份数据
        result = session.execute(text("SELECT * FROM media"))
        columns = result.keys()
        rows = result.fetchall()
        
        backup_data = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                # 处理datetime对象
                if isinstance(value, datetime):
                    value = value.isoformat()
                row_dict[col] = value
            backup_data.append(row_dict)
        
        # 保存备份到文件
        backup_file = f"media_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"已备份 {len(backup_data)} 条记录到 {backup_file}")
        return backup_data
        
    except Exception as e:
        print(f"备份数据时出错: {e}")
        return []

def drop_media_table(session):
    """删除media表"""
    try:
        session.execute(text("DROP TABLE IF EXISTS media CASCADE"))
        session.commit()
        print("已删除media表")
    except Exception as e:
        print(f"删除表时出错: {e}")
        session.rollback()
        raise

def create_media_table(session):
    """创建新的media表"""
    try:
        # 创建media表的SQL
        create_sql = """
        CREATE TABLE media (
            id SERIAL PRIMARY KEY,
            filename VARCHAR NOT NULL,
            original_filename VARCHAR,
            file_path VARCHAR,
            file_size BIGINT,
            mime_type VARCHAR,
            upload_status VARCHAR DEFAULT 'PENDING',
            storage_type VARCHAR DEFAULT 'LOCAL',
            oss_key VARCHAR,
            oss_etag VARCHAR,
            oss_storage_class VARCHAR,
            oss_last_modified TIMESTAMP,
            error_message TEXT,
            user_id INTEGER,
            lesson_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        session.execute(text(create_sql))
        session.commit()
        print("已创建新的media表")
        
    except Exception as e:
        print(f"创建表时出错: {e}")
        session.rollback()
        raise

def verify_table_structure(session):
    """验证表结构"""
    try:
        result = session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'media'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        print("\n新表结构:")
        print("-" * 80)
        print(f"{'列名':<20} {'数据类型':<20} {'可空':<10} {'默认值':<20}")
        print("-" * 80)
        
        for col in columns:
            nullable = "是" if col[2] == 'YES' else "否"
            default = col[3] if col[3] else ""
            print(f"{col[0]:<20} {col[1]:<20} {nullable:<10} {default:<20}")
        
        print(f"\n总共 {len(columns)} 个字段")
        
        # 检查必要的字段
        required_fields = [
            'id', 'filename', 'upload_status', 'storage_type',
            'oss_key', 'oss_etag', 'oss_storage_class', 'oss_last_modified'
        ]
        
        existing_fields = [col[0] for col in columns]
        missing_fields = [field for field in required_fields if field not in existing_fields]
        
        if missing_fields:
            print(f"\n警告: 缺少字段: {missing_fields}")
        else:
            print("\n✓ 所有必要字段都已存在")
            
    except Exception as e:
        print(f"验证表结构时出错: {e}")

def main():
    """主函数"""
    print("开始Media表重建过程...")
    
    # 确认操作
    confirm = input("\n警告: 此操作将删除现有的media表并重新创建。是否继续? (y/N): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
    
    session = None
    try:
        # 创建数据库连接
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        print(f"\n连接到数据库: {DATABASE_URL}")
        
        # 1. 备份现有数据
        print("\n1. 备份现有数据...")
        backup_data = backup_media_data(session)
        
        # 2. 删除现有表
        print("\n2. 删除现有表...")
        drop_media_table(session)
        
        # 3. 创建新表
        print("\n3. 创建新表...")
        create_media_table(session)
        
        # 4. 验证表结构
        print("\n4. 验证表结构...")
        verify_table_structure(session)
        
        print("\n✓ Media表重建完成!")
        
        if backup_data:
            print(f"\n注意: 原有的 {len(backup_data)} 条记录已备份，如需恢复请手动导入")
        
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        return 1
    
    finally:
        if session:
            session.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())