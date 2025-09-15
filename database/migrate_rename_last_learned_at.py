#!/usr/bin/env python3
"""
数据库迁移脚本：将 last_learned_at 字段重命名为 last_watch_at
"""
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_URL

def migrate_rename_last_learned_at():
    """执行字段重命名迁移"""
    try:
        # 创建数据库连接
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("开始执行数据库迁移：重命名 last_learned_at 字段为 last_watch_at")
        
        # 检查字段是否存在
        check_column_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'course_enrollments' 
            AND column_name = 'last_learned_at'
        """)
        
        result = session.execute(check_column_query).fetchone()
        
        if result:
            print("发现 last_learned_at 字段，开始重命名...")
            
            # 重命名字段
            rename_query = text("""
                ALTER TABLE course_enrollments 
                RENAME COLUMN last_learned_at TO last_watch_at
            """)
            
            session.execute(rename_query)
            session.commit()
            
            print("✅ 字段重命名成功：last_learned_at -> last_watch_at")
            
        else:
            print("❌ 未找到 last_learned_at 字段，可能已经重命名或不存在")
            
            # 检查是否已经存在 last_watch_at 字段
            check_new_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'course_enrollments' 
                AND column_name = 'last_watch_at'
            """)
            
            new_result = session.execute(check_new_column_query).fetchone()
            
            if new_result:
                print("✅ last_watch_at 字段已存在，无需迁移")
            else:
                print("❌ 既没有 last_learned_at 也没有 last_watch_at 字段")
                return False
        
        # 验证迁移结果
        verify_query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'course_enrollments' 
            AND column_name IN ('last_learned_at', 'last_watch_at')
            ORDER BY column_name
        """)
        
        verify_result = session.execute(verify_query).fetchall()
        
        print("\n迁移后的字段信息：")
        for row in verify_result:
            print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")
        
        session.close()
        print("\n🎉 数据库迁移完成！")
        return True
        
    except Exception as e:
        print(f"❌ 数据库迁移失败: {str(e)}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def rollback_migration():
    """回滚迁移（将 last_watch_at 重命名回 last_learned_at）"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("开始回滚迁移：将 last_watch_at 字段重命名回 last_learned_at")
        
        # 检查字段是否存在
        check_column_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'course_enrollments' 
            AND column_name = 'last_watch_at'
        """)
        
        result = session.execute(check_column_query).fetchone()
        
        if result:
            # 重命名字段
            rename_query = text("""
                ALTER TABLE course_enrollments 
                RENAME COLUMN last_watch_at TO last_learned_at
            """)
            
            session.execute(rename_query)
            session.commit()
            
            print("✅ 回滚成功：last_watch_at -> last_learned_at")
        else:
            print("❌ 未找到 last_watch_at 字段，无法回滚")
            return False
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ 回滚失败: {str(e)}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移：重命名 last_learned_at 字段")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = migrate_rename_last_learned_at()
    
    sys.exit(0 if success else 1)
