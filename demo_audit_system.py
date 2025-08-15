#!/usr/bin/env python3
"""
审计日志系统演示
展示完整的审计日志功能，包括：
1. 系统操作记录
2. 用户操作记录
3. API请求记录
4. 日志查询和分析
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import SessionLocal
from models.audit_log import AuditLog
from utils.audit_service import AuditService, log_system_action, log_user_action
from models.user import User
from datetime import datetime, timedelta
import json

def demo_audit_system():
    """演示审计日志系统功能"""
    db = SessionLocal()
    
    try:
        print("🎯 审计日志系统功能演示")
        print("=" * 50)
        
        # 1. 系统操作日志
        print("\n📋 1. 系统操作日志演示")
        system_actions = [
            ("system_startup", {"version": "2.0.0", "mode": "production"}),
            ("database_migration", {"tables_created": 5, "duration_ms": 1200}),
            ("cache_clear", {"cache_type": "redis", "keys_cleared": 150}),
            ("backup_created", {"backup_size_mb": 256, "location": "/backups/daily"})
        ]
        
        for action, details in system_actions:
            log_system_action(db=db, action=action, details=details)
            print(f"   ✅ 记录系统操作: {action}")
        
        # 2. 模拟用户操作日志
        print("\n👤 2. 用户操作日志演示")
        # 创建模拟用户
        mock_user = User(
            id="demo_user_123",
            username="demo_user",
            email="demo@example.com",
            phone="13800138000"
        )
        
        user_actions = [
            ("user_login", "user", "user_123", "用户登录", {"ip": "192.168.1.100", "device": "iPhone"}),
            ("course_purchase", "course", "course_456", "Python基础课程", {"price": 199.0, "payment_method": "wechat"}),
            ("video_watch", "video", "video_789", "第1章：Python简介", {"duration_seconds": 1800, "progress": 0.8}),
            ("homework_submit", "homework", "hw_101", "作业1", {"score": 85, "submission_time": datetime.now().isoformat()})
        ]
        
        for action, resource_type, resource_id, resource_name, details in user_actions:
            log_user_action(
                db=db,
                user=mock_user,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                details=details
            )
            print(f"   ✅ 记录用户操作: {action} - {resource_name}")
        
        # 3. API请求日志（模拟中间件记录）
        print("\n🌐 3. API请求日志演示")
        api_logs = [
            ("GET", "/api/courses", 200, 45, {"page": 1, "size": 10}),
            ("POST", "/api/orders", 201, 120, {"course_id": "course_456", "amount": 199.0}),
            ("PUT", "/api/users/profile", 200, 80, {"updated_fields": ["avatar", "bio"]}),
            ("DELETE", "/api/courses/draft_123", 204, 25, {"reason": "user_cancelled"})
        ]
        
        for method, endpoint, status_code, duration, details in api_logs:
            status = "success" if status_code < 400 else "error"
            AuditService.log_action(
                db=db,
                user_id="demo_user_123",
                username="demo_user",
                action="api_call",
                method=method,
                endpoint=endpoint,
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
                details=details,
                status=status,
                duration_ms=duration
            )
            print(f"   ✅ 记录API请求: {method} {endpoint} ({status_code})")
        
        # 4. 日志查询和分析
        print("\n📊 4. 日志查询和分析")
        
        # 查询所有日志
        all_logs = AuditService.get_logs(db=db, page=1, size=20)
        print(f"   📈 总日志数量: {all_logs['total']} 条")
        
        # 按操作类型查询
        system_logs = AuditService.get_logs(db=db, action="system_startup")
        print(f"   🔧 系统启动日志: {system_logs['total']} 条")
        
        # 按用户查询
        user_logs = AuditService.get_logs(db=db, user_id="demo_user_123")
        print(f"   👤 用户操作日志: {user_logs['total']} 条")
        
        # 按资源类型查询
        course_logs = AuditService.get_logs(db=db, resource_type="course")
        print(f"   📚 课程相关日志: {course_logs['total']} 条")
        
        # 按状态查询
        success_logs = AuditService.get_logs(db=db, status="success")
        print(f"   ✅ 成功操作日志: {success_logs['total']} 条")
        
        # 时间范围查询
        recent_logs = AuditService.get_logs(
            db=db,
            start_date=datetime.now() - timedelta(hours=1)
        )
        print(f"   ⏰ 最近1小时日志: {recent_logs['total']} 条")
        
        # 5. 用户活动摘要
        print("\n📋 5. 用户活动摘要")
        activity_summary = AuditService.get_user_activity_summary(
            db=db,
            user_id="demo_user_123",
            days=7
        )
        print(f"   📊 最近7天活动统计:")
        print(f"      - 总操作次数: {activity_summary['total_actions']}")
        print(f"      - 成功操作: {activity_summary['successful_actions']}")
        print(f"      - 失败操作: {activity_summary['failed_actions']}")
        print(f"      - 成功率: {activity_summary['success_rate']:.1f}%")
        if activity_summary['action_breakdown']:
            top_actions = sorted(activity_summary['action_breakdown'].items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"      - 最常用操作: {', '.join([f'{action}({count}次)' for action, count in top_actions])}")
        else:
            print(f"      - 最常用操作: 暂无数据")
        
        # 6. 展示最新的几条日志详情
        print("\n📝 6. 最新日志详情")
        latest_logs = AuditService.get_logs(db=db, page=1, size=3)
        for i, log in enumerate(latest_logs['logs'][:3], 1):
            print(f"   {i}. [{log['created_at']}] {log['action']}")
            print(f"      用户: {log['username'] or '系统'}")
            print(f"      状态: {log['status']}")
            if log['resource_type']:
                print(f"      资源: {log['resource_type']} - {log['resource_name'] or log['resource_id']}")
            if log['details']:
                print(f"      详情: {json.dumps(log['details'], ensure_ascii=False, indent=8)}")
            print()
        
        print("🎉 审计日志系统演示完成！")
        print("\n💡 功能特点:")
        print("   ✅ 完整的操作记录（系统、用户、API）")
        print("   ✅ 灵活的查询和筛选")
        print("   ✅ 用户活动分析")
        print("   ✅ 实时日志记录")
        print("   ✅ 结构化数据存储")
        
    except Exception as e:
        print(f"❌ 演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    demo_audit_system()