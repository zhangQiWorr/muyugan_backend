#!/usr/bin/env python3
"""
简化的数据库迁移脚本：将media表改为使用字符串类型
"""

import os
import sys
from sqlalchemy import create_engine, text

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """主函数"""
    print("开始执行media表迁移...")
    
    # 直接使用数据库URL
    database_url = "postgresql://postgres:postgres@localhost:5432/muyugan_db"
    print(f"数据库连接: {database_url}")
    
    # 创建数据库引擎
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # 删除现有表和枚举类型
            print("正在删除现有表和枚举类型...")
            conn.execute(text("DROP TABLE IF EXISTS media CASCADE"))
            conn.execute(text("DROP TYPE IF EXISTS mediatype CASCADE"))
            conn.execute(text("DROP TYPE IF EXISTS uploadstatus CASCADE"))
            conn.execute(text("DROP TYPE IF EXISTS storagetype CASCADE"))
            conn.execute(text("DROP TYPE IF EXISTS ossstorageclasstype CASCADE"))
            
            # 创建新的media表
            print("正在创建新的media表...")
            create_table_sql = """
            CREATE TABLE media (
                id VARCHAR PRIMARY KEY,
                description TEXT,
                filename VARCHAR(255) NOT NULL,
                filepath VARCHAR(255),
                media_type VARCHAR(50) NOT NULL,
                cover_url VARCHAR(255),
                duration INTEGER,
                size BIGINT,
                mime_type VARCHAR(100),
                uploader_id VARCHAR NOT NULL,
                lesson_id VARCHAR,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upload_status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                upload_progress FLOAT DEFAULT 0.0 NOT NULL,
                task_id VARCHAR,
                error_message TEXT,
                storage_type VARCHAR(50) DEFAULT 'local' NOT NULL,
                oss_key VARCHAR(500),
                oss_etag VARCHAR(100),
                oss_storage_class VARCHAR(50),
                oss_last_modified TIMESTAMP,
                oss_version_id VARCHAR(100),
                extra JSON DEFAULT '{}'
            )
            """
            conn.execute(text(create_table_sql))
            
            # 添加外键约束（如果需要的话）
            try:
                conn.execute(text("ALTER TABLE media ADD CONSTRAINT fk_media_uploader FOREIGN KEY (uploader_id) REFERENCES users(id)"))
                print("已添加uploader_id外键约束")
            except Exception as e:
                print(f"添加uploader_id外键约束失败（可能users表不存在）: {e}")
            
            try:
                conn.execute(text("ALTER TABLE media ADD CONSTRAINT fk_media_lesson FOREIGN KEY (lesson_id) REFERENCES course_lessons(id)"))
                print("已添加lesson_id外键约束")
            except Exception as e:
                print(f"添加lesson_id外键约束失败（可能course_lessons表不存在）: {e}")
            
            conn.commit()
            print("\n迁移完成！")
            print("media表已成功迁移为使用字符串类型")
        
    except Exception as e:
        print(f"\n迁移失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()