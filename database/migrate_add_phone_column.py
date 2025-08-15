"""
为 users 表添加 phone 字段（PostgreSQL 版本）
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载数据库URL
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("请在 .env 文件中配置 DATABASE_URL")

engine = create_engine(DATABASE_URL)

ALTER_SQL = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) UNIQUE;
CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone);
"""

def main():
    print("🚀 开始添加 users.phone 字段...")
    with engine.connect() as conn:
        try:
            conn.execute(text(ALTER_SQL))
            conn.commit()
            print("✅ 添加成功！")
        except Exception as e:
            print(f"❌ 添加失败: {e}")
            raise

if __name__ == "__main__":
    main()