#!/usr/bin/env python3
"""
数据库迁移脚本：为MediaType枚举添加IMAGE类型

执行步骤：
1. 添加新的枚举值 'image' 到 mediatype 枚举类型
2. 验证更新是否成功

使用方法：
python database/migrate_add_image_mediatype.py
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接使用数据库连接信息
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/muyugan_db')
PSQL_PATH = "/Applications/Postgres.app/Contents/Versions/17/bin/psql"

# 简单的日志记录
class SimpleLogger:
    def info(self, msg):
        print(f"[INFO] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")

logger = SimpleLogger()

def add_image_to_mediatype_enum():
    """为MediaType枚举添加IMAGE类型"""
    conn = None
    cursor = None
    try:
        # 连接数据库
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        logger.info("开始为MediaType枚举添加IMAGE类型...")
        
        # 检查当前枚举值
        cursor.execute("""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'mediatype')
            ORDER BY enumsortorder;
        """)
        current_values = [row[0] for row in cursor.fetchall()]
        logger.info(f"当前MediaType枚举值: {current_values}")
        
        # 检查是否已经存在image类型
        if 'image' in current_values:
            logger.info("IMAGE类型已存在，无需添加")
            return True
            
        # 添加新的枚举值
        logger.info("添加IMAGE枚举值...")
        cursor.execute("ALTER TYPE mediatype ADD VALUE 'image';")
        
        # 验证添加结果
        cursor.execute("""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'mediatype')
            ORDER BY enumsortorder;
        """)
        updated_values = [row[0] for row in cursor.fetchall()]
        logger.info(f"更新后MediaType枚举值: {updated_values}")
        
        if 'image' in updated_values:
            logger.info("✅ IMAGE类型添加成功")
            return True
        else:
            logger.error("❌ IMAGE类型添加失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        return False
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始MediaType枚举迁移")
    logger.info("=" * 50)
    
    success = add_image_to_mediatype_enum()
    
    if success:
        logger.info("🎉 迁移完成！MediaType枚举已成功添加IMAGE类型")
        return 0
    else:
        logger.error("💥 迁移失败！请检查错误信息")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)