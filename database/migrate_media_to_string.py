#!/usr/bin/env python3
"""
数据库迁移脚本：将media表的media_type从枚举类型改为字符串类型

执行步骤：
1. 备份现有media表数据
2. 删除现有media表
3. 删除mediatype枚举类型
4. 重新创建media表（使用字符串类型的media_type）
5. 恢复数据
"""

import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Base
from models.media import Media
from config import get_database_url

def backup_media_data(engine):
    """备份media表数据"""
    print("正在备份media表数据...")
    
    with engine.connect() as conn:
        # 查询所有media数据
        result = conn.execute(text("""
            SELECT id, description, filename, filepath, media_type, cover_url, 
                   duration, size, mime_type, uploader_id, lesson_id, upload_time,
                   upload_status, upload_progress, task_id, error_message,
                   storage_type, oss_key, oss_etag, oss_storage_class, 
                   oss_last_modified, oss_version_id, extra
            FROM media
        """))
        
        media_data = []
        for row in result:
            media_record = {
                'id': row[0],
                'description': row[1],
                'filename': row[2],
                'filepath': row[3],
                'media_type': row[4],
                'cover_url': row[5],
                'duration': row[6],
                'size': row[7],
                'mime_type': row[8],
                'uploader_id': row[9],
                'lesson_id': row[10],
                'upload_time': row[11].isoformat() if row[11] else None,
                'upload_status': row[12],
                'upload_progress': row[13],
                'task_id': row[14],
                'error_message': row[15],
                'storage_type': row[16],
                'oss_key': row[17],
                'oss_etag': row[18],
                'oss_storage_class': row[19],
                'oss_last_modified': row[20].isoformat() if row[20] else None,
                'oss_version_id': row[21],
                'extra': row[22]
            }
            media_data.append(media_record)
    
    # 保存备份文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"media_backup_{timestamp}.json"
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(media_data, f, ensure_ascii=False, indent=2)
    
    print(f"备份完成，共备份 {len(media_data)} 条记录到文件: {backup_file}")
    return media_data, backup_file

def drop_media_table_and_enum(engine):
    """删除media表和相关枚举类型"""
    print("正在删除media表和枚举类型...")
    
    with engine.connect() as conn:
        # 删除media表
        conn.execute(text("DROP TABLE IF EXISTS media CASCADE"))
        print("已删除media表")
        
        # 删除枚举类型（如果存在）
        try:
            conn.execute(text("DROP TYPE IF EXISTS mediatype CASCADE"))
            print("已删除mediatype枚举类型")
        except Exception as e:
            print(f"删除mediatype枚举类型时出错（可能不存在）: {e}")
        
        try:
            conn.execute(text("DROP TYPE IF EXISTS uploadstatus CASCADE"))
            print("已删除uploadstatus枚举类型")
        except Exception as e:
            print(f"删除uploadstatus枚举类型时出错（可能不存在）: {e}")
        
        try:
            conn.execute(text("DROP TYPE IF EXISTS storagetype CASCADE"))
            print("已删除storagetype枚举类型")
        except Exception as e:
            print(f"删除storagetype枚举类型时出错（可能不存在）: {e}")
        
        try:
            conn.execute(text("DROP TYPE IF EXISTS ossstorageclasstype CASCADE"))
            print("已删除ossstorageclasstype枚举类型")
        except Exception as e:
            print(f"删除ossstorageclasstype枚举类型时出错（可能不存在）: {e}")
        
        conn.commit()

def create_new_media_table(engine):
    """创建新的media表（使用字符串类型）"""
    print("正在创建新的media表...")
    
    # 使用SQLAlchemy创建表
    Base.metadata.create_all(engine, tables=[Media.__table__])
    print("新的media表创建完成")

def restore_media_data(engine, media_data):
    """恢复media数据"""
    print("正在恢复media数据...")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        for record in media_data:
            # 创建新的Media对象
            media = Media(
                id=record['id'],
                description=record['description'],
                filename=record['filename'],
                filepath=record['filepath'],
                media_type=record['media_type'],  # 现在是字符串类型
                cover_url=record['cover_url'],
                duration=record['duration'],
                size=record['size'],
                mime_type=record['mime_type'],
                uploader_id=record['uploader_id'],
                lesson_id=record['lesson_id'],
                upload_time=datetime.fromisoformat(record['upload_time']) if record['upload_time'] else None,
                upload_status=record['upload_status'],  # 现在是字符串类型
                upload_progress=record['upload_progress'],
                task_id=record['task_id'],
                error_message=record['error_message'],
                storage_type=record['storage_type'],  # 现在是字符串类型
                oss_key=record['oss_key'],
                oss_etag=record['oss_etag'],
                oss_storage_class=record['oss_storage_class'],  # 现在是字符串类型
                oss_last_modified=datetime.fromisoformat(record['oss_last_modified']) if record['oss_last_modified'] else None,
                oss_version_id=record['oss_version_id'],
                extra=record['extra'] or {}
            )
            session.add(media)
        
        session.commit()
        print(f"数据恢复完成，共恢复 {len(media_data)} 条记录")
        
    except Exception as e:
        session.rollback()
        print(f"数据恢复失败: {e}")
        raise
    finally:
        session.close()

def main():
    """主函数"""
    print("开始执行media表迁移...")
    database_url = get_database_url()
    print(f"数据库连接: {database_url}")
    
    # 创建数据库引擎
    engine = create_engine(database_url)
    
    try:
        # 1. 备份数据
        media_data, backup_file = backup_media_data(engine)
        
        # 2. 删除现有表和枚举
        drop_media_table_and_enum(engine)
        
        # 3. 创建新表
        create_new_media_table(engine)
        
        # 4. 恢复数据
        restore_media_data(engine, media_data)
        
        print("\n迁移完成！")
        print(f"备份文件: {backup_file}")
        print("media表已成功迁移为使用字符串类型的media_type")
        
    except Exception as e:
        print(f"\n迁移失败: {e}")
        print("请检查错误信息并重试")
        sys.exit(1)

if __name__ == "__main__":
    main()