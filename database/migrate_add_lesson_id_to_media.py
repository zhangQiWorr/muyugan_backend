#!/usr/bin/env python3
"""
数据库迁移脚本：为media表添加lesson_id字段

执行方式：
python database/migrate_add_lesson_id_to_media.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接使用环境变量获取数据库URL，避免pydantic版本问题
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")

# 简单的日志记录
def log_info(message):
    print(f"[INFO] {message}")

def log_error(message):
    print(f"[ERROR] {message}")

def migrate_add_lesson_id_to_media():
    """为media表添加lesson_id字段"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                # 检查lesson_id字段是否已存在
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'media' AND column_name = 'lesson_id'
                """))
                
                if result.fetchone():
                    log_info("lesson_id字段已存在，跳过迁移")
                    trans.rollback()
                    return True
                
                log_info("开始为media表添加lesson_id字段...")
                
                # 添加lesson_id字段
                conn.execute(text("""
                    ALTER TABLE media 
                    ADD COLUMN lesson_id VARCHAR(255)
                """))
                
                # 添加外键约束
                conn.execute(text("""
                    ALTER TABLE media 
                    ADD CONSTRAINT fk_media_lesson_id 
                    FOREIGN KEY (lesson_id) REFERENCES course_lessons(id) 
                    ON DELETE SET NULL
                """))
                
                # 为lesson_id字段添加索引以提高查询性能
                conn.execute(text("""
                    CREATE INDEX idx_media_lesson_id ON media(lesson_id)
                """))
                
                # 提交事务
                trans.commit()
                log_info("media表lesson_id字段添加成功")
                
                return True
                
            except Exception as e:
                # 回滚事务
                trans.rollback()
                log_error(f"迁移过程中发生错误: {str(e)}")
                raise
                
    except SQLAlchemyError as e:
        log_error(f"数据库连接错误: {str(e)}")
        return False
    except Exception as e:
        log_error(f"迁移失败: {str(e)}")
        return False

def main():
    """主函数"""
    log_info("开始执行media表lesson_id字段迁移...")
    
    success = migrate_add_lesson_id_to_media()
    
    if success:
        log_info("迁移完成！")
        print("✅ media表lesson_id字段迁移成功")
    else:
        log_error("迁移失败！")
        print("❌ media表lesson_id字段迁移失败")
        sys.exit(1)

if __name__ == "__main__":
    main()