"""
知识付费App数据库迁移脚本
创建所有必要的表结构
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Base, engine
from models import (
    # 现有模型
    User, Conversation, Message, Agent, AgentConfig,
    # 新增模型
    Course, CourseLesson, CourseCategory, CourseEnrollment, LearningProgress,
    CourseReview, CourseFavorite, Order, OrderItem, PaymentRecord,
    Coupon, UserCoupon, RefundRecord, UserBalance, BalanceTransaction,
    MembershipLevel, UserMembership, MembershipOrder, MembershipBenefit, UserBenefitUsage
)


def create_knowledge_app_tables():
    """创建知识付费App相关的表"""
    print("🚀 开始创建知识付费App相关表...")
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 所有表创建成功!")
        
        # 创建索引
        create_indexes()
        
        # 插入初始数据
        insert_initial_data()
        
        print("🎉 知识付费App数据库迁移完成!")
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        raise


def create_indexes():
    """创建必要的索引"""
    print("📊 创建数据库索引...")
    
    with engine.connect() as conn:
        # 课程相关索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_courses_status ON courses(status);
            CREATE INDEX IF NOT EXISTS idx_courses_category ON courses(category_id);
            CREATE INDEX IF NOT EXISTS idx_courses_creator ON courses(creator_id);
            CREATE INDEX IF NOT EXISTS idx_courses_featured ON courses(is_featured);
            CREATE INDEX IF NOT EXISTS idx_courses_hot ON courses(is_hot);
        """))
        
        # 订单相关索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
        """))
        
        # 学习进度索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_learning_user_course ON learning_progress(user_id, course_id);
            CREATE INDEX IF NOT EXISTS idx_learning_enrollment ON learning_progress(enrollment_id);
        """))
        
        # 会员相关索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_membership_user ON user_memberships(user_id);
            CREATE INDEX IF NOT EXISTS idx_membership_status ON user_memberships(status);
        """))
        
        conn.commit()
        print("✅ 索引创建成功!")


def insert_initial_data():
    """插入初始数据"""
    print("📝 插入初始数据...")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 创建默认课程分类
        create_default_categories(db)
        
        # 创建默认会员等级
        create_default_membership_levels(db)
        
        # 创建默认优惠券
        create_default_coupons(db)
        
        db.commit()
        print("✅ 初始数据插入成功!")
        
    except Exception as e:
        print(f"❌ 插入初始数据失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_default_categories(db):
    """创建默认课程分类"""
    categories = [
        {
            "name": "编程开发",
            "description": "编程语言、框架、工具等开发相关课程",
            "icon": "code",
            "sort_order": 1
        },
        {
            "name": "设计创意",
            "description": "UI/UX设计、平面设计、创意设计等",
            "icon": "palette",
            "sort_order": 2
        },
        {
            "name": "商业管理",
            "description": "企业管理、市场营销、财务管理等",
            "icon": "business",
            "sort_order": 3
        },
        {
            "name": "语言学习",
            "description": "英语、日语、韩语等语言学习课程",
            "icon": "language",
            "sort_order": 4
        },
        {
            "name": "生活技能",
            "description": "烹饪、摄影、健身等生活技能课程",
            "icon": "home",
            "sort_order": 5
        }
    ]
    
    for cat_data in categories:
        existing = db.query(CourseCategory).filter(CourseCategory.name == cat_data["name"]).first()
        if not existing:
            category = CourseCategory(**cat_data)
            db.add(category)
            print(f"  ✅ 创建分类: {cat_data['name']}")


def create_default_membership_levels(db):
    """创建默认会员等级"""
    levels = [
        {
            "name": "基础会员",
            "description": "享受基础会员权益",
            "monthly_price": 19.9,
            "quarterly_price": 49.9,
            "yearly_price": 169.9,
            "lifetime_price": 999.0,
            "max_courses": 50,
            "max_storage": 1024,
            "benefits": {},
            "sort_order": 1
        },
        {
            "name": "高级会员",
            "description": "享受更多高级权益",
            "monthly_price": 39.9,
            "quarterly_price": 99.9,
            "yearly_price": 299.9,
            "lifetime_price": 1999.0,
            "max_courses": 200,
            "max_storage": 5120,
            "benefits": {},
            "sort_order": 2
        },
        {
            "name": "VIP会员",
            "description": "享受全部VIP权益",
            "monthly_price": 79.9,
            "quarterly_price": 199.9,
            "yearly_price": 599.9,
            "lifetime_price": 3999.0,
            "max_courses": -1,  # 无限制
            "max_storage": 10240,
            "benefits": {},
            "sort_order": 3
        }
    ]
    
    for level_data in levels:
        existing = db.query(MembershipLevel).filter(MembershipLevel.name == level_data["name"]).first()
        if not existing:
            level = MembershipLevel(**level_data)
            db.add(level)
            print(f"  ✅ 创建会员等级: {level_data['name']}")


def create_default_coupons(db):
    """创建默认优惠券"""
    coupons = [
        {
            "code": "WELCOME2024",
            "name": "新用户专享券",
            "description": "新用户注册专享优惠券",
            "coupon_type": "amount",
            "discount_value": 10.0,
            "min_amount": 50.0,
            "max_discount": 10.0,
            "usage_limit": 1000,
            "per_user_limit": 1,
            "valid_from": "2024-01-01 00:00:00",
            "valid_until": "2024-12-31 23:59:59"
        },
        {
            "code": "FIRSTCOURSE",
            "name": "首课优惠券",
            "description": "购买第一门课程享受优惠",
            "coupon_type": "discount",
            "discount_value": 0.8,
            "min_amount": 0.0,
            "max_discount": 50.0,
            "usage_limit": 5000,
            "per_user_limit": 1,
            "valid_from": "2024-01-01 00:00:00",
            "valid_until": "2024-12-31 23:59:59"
        }
    ]
    
    for coupon_data in coupons:
        existing = db.query(Coupon).filter(Coupon.code == coupon_data["code"]).first()
        if not existing:
            # 转换日期字符串为datetime对象
            from datetime import datetime
            coupon_data["valid_from"] = datetime.strptime(coupon_data["valid_from"], "%Y-%m-%d %H:%M:%S")
            coupon_data["valid_until"] = datetime.strptime(coupon_data["valid_until"], "%Y-%m-%d %H:%M:%S")
            
            coupon = Coupon(**coupon_data)
            db.add(coupon)
            print(f"  ✅ 创建优惠券: {coupon_data['name']}")


def check_existing_tables():
    """检查现有表"""
    print("🔍 检查现有表结构...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    required_tables = [
        "courses", "course_lessons", "course_categories", "course_enrollments",
        "learning_progress", "course_reviews", "course_favorites",
        "orders", "order_items", "payment_records", "coupons", "user_coupons",
        "refund_records", "user_balances", "balance_transactions",
        "membership_levels", "user_memberships", "membership_orders",
        "membership_benefits", "user_benefit_usage"
    ]
    
    missing_tables = [table for table in required_tables if table not in existing_tables]
    
    if missing_tables:
        print(f"❌ 缺少表: {', '.join(missing_tables)}")
        return False
    else:
        print("✅ 所有必需的表都已存在")
        return True


if __name__ == "__main__":
    print("=" * 60)
    print("知识付费App数据库迁移工具")
    print("=" * 60)
    
    try:
        # 检查现有表
        if check_existing_tables():
            print("所有表都已存在，无需迁移")
        else:
            # 创建表
            create_knowledge_app_tables()
        
        print("=" * 60)
        print("迁移完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        sys.exit(1)
