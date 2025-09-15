#!/usr/bin/env python3
"""
测试学习统计功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.learning_service import LearningService
from models.database import get_db
from sqlalchemy.orm import Session

def test_learning_statistics():
    """测试学习统计功能"""
    try:
        print("测试学习统计功能...")
        
        # 获取数据库会话
        db = next(get_db())
        
        # 创建学习服务
        learning_service = LearningService(db)
        
        # 测试用户ID
        test_user_id = "test-user-12345"
        
        print(f"测试用户ID: {test_user_id}")
        
        # 获取学习统计
        stats = learning_service.get_user_learning_statistics(test_user_id)
        
        print("✅ 学习统计获取成功:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    success = test_learning_statistics()
    sys.exit(0 if success else 1)
