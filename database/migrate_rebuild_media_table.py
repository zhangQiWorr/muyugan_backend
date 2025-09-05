#!/usr/bin/env python3
"""
数据库迁移脚本：删除并重新构建media表

使用方法：
python database/migrate_rebuild_media_table.py

注意：此操作将删除media表中的所有数据，请确保已备份重要数据！
"""

import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_database_url
from models.media import Media
from services.logger import get_logger

logger = get_logger("migrate_rebuild_media")

def backup_media_data(session):
    """备份media表数据到JSON文件"""
    try:
        # 检查表是否存在
        inspector = inspect(session.bind)
        if 'media' not in inspector.get_table_names():
            logger.info("media表不存在，跳过备份")
            return None
            
        # 查询所有数据
        result = session.execute(text("SELECT * FROM media"))
        rows = result.fetchall()
        
        if not rows:
            logger.info("media表为空，无需备份")
            return None
            
        # 转换为字典列表
        columns = result.keys()
        backup_data = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                # 处理特殊类型
                if hasattr(value, 'isoformat'):  # datetime对象
                    value = value.isoformat()
                elif hasattr(value, 'value'):  # 枚举对象
                    value = value.value
                row_dict[col] = value
            backup_data.append(row_dict)
        
        # 保存到文件
        import json
        from datetime import datetime
        backup_filename = f"media_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(os.path.dirname(__file__), backup_filename)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 已备份 {len(backup_data)} 条记录到: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"备份失败: {str(e)}")
        return None

def drop_media_table(session):
    """删除media表"""
    try:
        # 检查表是否存在
        inspector = inspect(session.bind)
        if 'media' not in inspector.get_table_names():
            logger.info("media表不存在，无需删除")
            return True
            
        # 删除表
        session.execute(text("DROP TABLE IF EXISTS media CASCADE"))
        session.commit()
        logger.info("✅ 已删除media表")
        return True
        
    except Exception as e:
        logger.error(f"删除media表失败: {str(e)}")
        session.rollback()
        return False

def create_media_table(engine):
    """重新创建media表"""
    try:
        # 使用SQLAlchemy模型创建表
        Media.__table__.create(engine, checkfirst=True)
        logger.info("✅ 已重新创建media表")
        return True
        
    except Exception as e:
        logger.error(f"创建media表失败: {str(e)}")
        return False

def verify_table_structure(session):
    """验证表结构"""
    try:
        inspector = inspect(session.bind)
        
        # 检查表是否存在
        if 'media' not in inspector.get_table_names():
            logger.error("❌ media表不存在")
            return False
            
        # 获取列信息
        columns = inspector.get_columns('media')
        column_names = [col['name'] for col in columns]
        
        # 检查必要的列
        required_columns = [
            'id', 'filename', 'media_type', 'uploader_id', 'upload_time',
            'upload_status', 'storage_type', 'oss_key', 'oss_etag',
            'oss_storage_class', 'oss_last_modified'
        ]
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            logger.error(f"❌ 缺少必要的列: {missing_columns}")
            return False
            
        logger.info(f"✅ 表结构验证通过，共 {len(column_names)} 列")
        logger.info(f"列名: {', '.join(column_names)}")
        return True
        
    except Exception as e:
        logger.error(f"验证表结构失败: {str(e)}")
        return False

def main():
    """主函数"""
    logger.info("开始重建media表...")
    
    try:
        # 创建数据库连接
        engine = create_engine(get_database_url())
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # 1. 备份数据
        logger.info("步骤 1: 备份现有数据...")
        backup_path = backup_media_data(session)
        
        # 2. 删除表
        logger.info("步骤 2: 删除media表...")
        if not drop_media_table(session):
            logger.error("❌ 删除表失败，终止操作")
            return False
            
        # 3. 重新创建表
        logger.info("步骤 3: 重新创建media表...")
        if not create_media_table(engine):
            logger.error("❌ 创建表失败，终止操作")
            return False
            
        # 4. 验证表结构
        logger.info("步骤 4: 验证表结构...")
        if not verify_table_structure(session):
            logger.error("❌ 表结构验证失败")
            return False
            
        logger.info("🎉 media表重建完成！")
        if backup_path:
            logger.info(f"💾 数据备份文件: {backup_path}")
        
        session.close()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"数据库操作失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        return False

if __name__ == "__main__":
    # 确认操作
    print("⚠️  警告：此操作将删除media表中的所有数据！")
    print("📋 操作步骤：")
    print("   1. 备份现有数据到JSON文件")
    print("   2. 删除media表")
    print("   3. 重新创建media表")
    print("   4. 验证表结构")
    print()
    
    confirm = input("确认继续？(输入 'yes' 确认): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)