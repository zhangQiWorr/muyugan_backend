#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：合并UserMediaAccess到MediaPlayRecord
将user_media_access表的数据迁移到media_play_record表，然后删除user_media_access表
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.database import DATABASE_URL
from services.logger import get_logger

logger = get_logger("migrate_merge_user_media_access")

def migrate_user_media_access_data():
    """
    迁移user_media_access表的数据到media_play_record表
    """
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        logger.info("🚀 开始迁移user_media_access数据...")
        
        # 检查user_media_access表是否存在
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'user_media_access'
            )
        """))
        
        table_exists = result.scalar()
        
        if not table_exists:
            logger.info("✅ user_media_access表不存在，无需迁移")
            return
        
        # 迁移数据：将user_media_access的数据合并到media_play_records
        migration_sql = text("""
            INSERT INTO media_play_records (
                id, user_id, media_id, play_count, 
                first_played_at, last_played_at, 
                total_watch_time, effective_watch_time, 
                max_progress, completion_rate, 
                is_completed, created_at, updated_at
            )
            SELECT 
                gen_random_uuid()::text as id,
                uma.user_id,
                uma.media_id,
                COALESCE(uma.access_count, 1) as play_count,
                uma.first_accessed_at as first_played_at,
                uma.last_accessed_at as last_played_at,
                0 as total_watch_time,
                0 as effective_watch_time,
                0 as max_progress,
                0 as completion_rate,
                false as is_completed,
                uma.created_at,
                uma.updated_at
            FROM user_media_access uma
            WHERE NOT EXISTS (
                SELECT 1 FROM media_play_records vpr 
                WHERE vpr.user_id = uma.user_id 
                AND vpr.media_id = uma.media_id
            )
        """)
        
        db.execute(migration_sql)
        
        logger.info("📊 成功执行数据迁移到media_play_records表")
        
        # 删除user_media_access表
        db.execute(text("DROP TABLE IF EXISTS user_media_access CASCADE"))
        logger.info("🗑️ 成功删除user_media_access表")
        
        db.commit()
        logger.info("✅ 数据迁移完成！")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_user_media_access_data()