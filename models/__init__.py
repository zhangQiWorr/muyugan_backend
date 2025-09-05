from .user import User
from .conversation import Conversation, Message
from .agent import Agent, AgentConfig
from .database import Base, engine, SessionLocal, get_db, create_tables
from .audit_log import AuditLog
from .media import Media
# UserMediaAccess已合并到MediaPlayRecord中
from .media_play_record import MediaPlayRecord
from .media_play_event import MediaPlayEvent, EventType

# 新增模型导入
from .course import (
    Course, CourseLesson, CourseCategory, CourseEnrollment, 
    LearningProgress, CourseReview, CourseFavorite,
    CourseStatus, ContentType
)
from .payment import (
    Order, OrderItem, PaymentRecord, Coupon, UserCoupon,
    RefundRecord, UserBalance, BalanceTransaction,
    OrderStatus, PaymentMethod, PaymentStatus, CouponType, CouponStatus
)
from .membership import (
    MembershipLevel, UserMembership, MembershipOrder,
    MembershipBenefit, UserBenefitUsage,
    MembershipType, MembershipStatus
)

__all__ = [
    "User",
    "Conversation", 
    "Message",
    "Agent",
    "AgentConfig", 
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "create_tables",
    "AuditLog",
    "Media",
    # "UserMediaAccess", # 已合并到MediaPlayRecord中
    "MediaPlayRecord",
    "MediaPlayEvent",
    "EventType",
    # 新增模型
    "Course", "CourseLesson", "CourseCategory", "CourseEnrollment",
    "LearningProgress", "CourseReview", "CourseFavorite",
    "CourseStatus", "ContentType",
    "Order", "OrderItem", "PaymentRecord", "Coupon", "UserCoupon",
    "RefundRecord", "UserBalance", "BalanceTransaction",
    "OrderStatus", "PaymentMethod", "PaymentStatus", "CouponType", "CouponStatus",
    "MembershipLevel", "UserMembership", "MembershipOrder",
    "MembershipBenefit", "UserBenefitUsage",
    "MembershipType", "MembershipStatus"
]