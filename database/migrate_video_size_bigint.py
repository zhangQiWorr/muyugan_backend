"""
将 videos 表的 size 字段从 INTEGER 修改为 BIGINT（PostgreSQL 版本）
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
ALTER TABLE videos ALTER COLUMN size TYPE BIGINT USING size::bigint;
"""

def main():
    print("🚀 开始修改 videos.size 字段为 BIGINT ...")
    with engine.connect() as conn:
        try:
            conn.execute(text(ALTER_SQL))
            print("✅ 修改成功！")
        except Exception as e:
            print(f"❌ 修改失败: {e}")
            raise

if __name__ == "__main__":
    main()
