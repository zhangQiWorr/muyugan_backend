#!/usr/bin/env python3
"""
测试审计日志功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import SessionLocal
from models.audit_log import AuditLog
from utils.audit_service import AuditService, log_system_action
from datetime import datetime

def test_audit_log():
    """测试审计日志功能"""
    db = SessionLocal()
    
    try:
        print("🔍 测试审计日志功能...")
        
        # 1. 测试创建审计日志
        print("\n1. 创建测试审计日志...")
        log_system_action(
            db=db,
            action="test_audit_system",
            details={
                "test_type": "audit_log_functionality",
                "timestamp": datetime.now().isoformat(),
                "message": "测试审计日志系统功能"
            }
        )
        print("✅ 审计日志创建成功")
        
        # 2. 查询审计日志
        print("\n2. 查询审计日志...")
        result = AuditService.get_logs(
            db=db,
            page=1,
            size=10,
            action="test_audit_system"
        )
        
        print(f"✅ 查询到 {result['total']} 条审计日志")
        
        # 3. 显示日志详情
        if result['logs']:
            print("\n3. 最新审计日志详情:")
            latest_log = result['logs'][0]
            print(f"   ID: {latest_log['id']}")
            print(f"   操作: {latest_log['action']}")
            print(f"   资源类型: {latest_log['resource_type']}")
            print(f"   状态: {latest_log['status']}")
            print(f"   创建时间: {latest_log['created_at']}")
            print(f"   详情: {latest_log['details']}")
        
        # 4. 测试数据库直接查询
        print("\n4. 数据库直接查询测试...")
        total_logs = db.query(AuditLog).count()
        print(f"✅ 数据库中共有 {total_logs} 条审计日志")
        
        # 5. 测试不同类型的日志
        print("\n5. 创建不同类型的测试日志...")
        test_actions = [
            ("user_login", {"username": "test_user", "resource_type": "user"}),
            ("course_create", {"title": "测试课程", "resource_type": "course"}),
            ("order_create", {"amount": 99.0, "resource_type": "order"}),
        ]
        
        for action, details in test_actions:
            log_system_action(
                db=db,
                action=action,
                details=details
            )
            print(f"   ✅ 创建 {action} 日志")
        
        # 6. 最终统计
        print("\n6. 最终统计...")
        final_count = db.query(AuditLog).count()
        print(f"✅ 测试完成，数据库中共有 {final_count} 条审计日志")
        
        print("\n🎉 审计日志功能测试成功！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_audit_log()