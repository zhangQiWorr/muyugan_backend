"""
数据验证Schema定义
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# 基础Schema
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

    def model_serializer(self, info):
        """自定义序列化器，处理datetime等特殊类型"""
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

# 用户认证相关模型
class UserRegister(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = 'user'  # user, teacher, superadmin

# 用户相关Schema
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)

class PasswordReset(BaseModel):
    token: str
    new_password: str

class UserCreate(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=50)  # 用户名可选，由后端自动生成
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^1[3-9]\d{9}$')
    password: Optional[str] = Field(None, min_length=6)
    # 第三方登录字段已移除，因为数据库中不存在对应列


class UserUpdate(BaseSchema):
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None


class UserLogin(BaseSchema):
    login: str = Field(..., description="用户名、邮箱或手机号")
    password: str = Field(..., min_length=6)


class PhoneLogin(BaseSchema):
    phone: str = Field(..., pattern=r'^1[3-9]\d{9}$')
    code: str = Field(..., min_length=4, max_length=6)


class SendSmsCode(BaseSchema):
    phone: str = Field(..., pattern=r'^1[3-9]\d{9}$')


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# 课程相关Schema
class CourseCategoryBase(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    sort_order: int = 0
    parent_id: Optional[str] = None


class CourseCategoryCreate(CourseCategoryBase):
    pass


class CourseCategoryUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    parent_id: Optional[str] = None


class CourseCategoryResponse(CourseCategoryBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    children: List['CourseCategoryResponse'] = []

class StreamChatRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None

class CourseLessonBase(BaseSchema):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None


    content_text: Optional[str] = None
    duration: int = Field(0, ge=0)
    sort_order: int = 0
    is_free: bool = False

# 对话管理模型
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    agent_id: Optional[str] = None

class CourseLessonCreate(CourseLessonBase):
    media_ids: Optional[List[str]] = Field(None, description="关联的媒体文件ID列表")


class CourseLessonUpdate(BaseSchema):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    content_text: Optional[str] = None
    duration: Optional[int] = Field(None, ge=0)
    sort_order: Optional[int] = None
    is_free: Optional[bool] = None
    media_ids: Optional[List[str]] = Field(None, description="关联的媒体文件ID列表")


class CourseLessonResponse(CourseLessonBase):
    id: str
    course_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    media_files: List['MediaInfoResponse'] = []


class CourseBase(BaseSchema):
    title: str = Field(..., max_length=200)
    subtitle: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    cover_image: Optional[str] = Field(None, max_length=500)
    category_id: Optional[str] = None
    tags: List[str] = []
    price: float = Field(0.0, ge=0)
    original_price: Optional[float] = Field(None, ge=0)
    is_free: bool = True
    is_member_only: bool = False
    difficulty_level: str = Field("beginner", description="beginner, intermediate, advanced")
    language: str = Field("zh-CN", description="语言代码")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseSchema):
    title: Optional[str] = Field(None, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    cover_image: Optional[str] = Field(None, max_length=500)
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    price: Optional[float] = Field(None, ge=0)
    original_price: Optional[float] = Field(None, ge=0)
    is_free: Optional[bool] = None
    is_member_only: Optional[bool] = None
    difficulty_level: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None


class CourseDelete(BaseSchema):
    isDeleteLesson: bool = Field(False, description="是否同时删除该课程下的所有课时")



class CourseResponse(CourseBase):
    id: str
    creator_id: str
    status: str
    is_featured: bool
    is_hot: bool
    view_count: int
    enroll_count: int
    rating: float
    rating_count: int
    duration: int
    lesson_count: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    category: Optional[CourseCategoryResponse] = None
    lessons: List[CourseLessonResponse] = []


class CourseListResponse(BaseSchema):
    courses: List[CourseResponse]
    total: int
    page: int
    size: int


# 订单相关Schema
class OrderItemBase(BaseSchema):
    course_id: str
    quantity: int = Field(1, ge=1)


class OrderCreate(BaseSchema):
    items: List[OrderItemBase]
    coupon_code: Optional[str] = None
    remark: Optional[str] = None


class OrderResponse(BaseSchema):
    id: str
    order_no: str
    user_id: str
    total_amount: float
    discount_amount: float
    final_amount: float
    status: str
    payment_method: Optional[str] = None
    payment_status: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    items: List[Dict[str, Any]] = []


class OrderListResponse(BaseSchema):
    orders: List[OrderResponse]
    total: int
    page: int
    size: int


# 支付相关Schema
class PaymentCreate(BaseSchema):
    order_id: str
    payment_method: str = Field(..., description="alipay, wechat, balance")
    amount: float = Field(..., gt=0)


class PaymentResponse(BaseSchema):
    id: str
    order_id: str
    payment_method: str
    amount: float
    status: str
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None


# 优惠券相关Schema
class CouponBase(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    coupon_type: str = Field(..., description="discount, amount, free")
    discount_value: float = Field(..., gt=0)
    min_amount: float = Field(0.0, ge=0)
    max_discount: Optional[float] = Field(None, gt=0)
    usage_limit: Optional[int] = Field(None, gt=0)
    per_user_limit: int = Field(1, ge=1)
    valid_from: datetime
    valid_until: datetime


class CouponCreate(CouponBase):
    pass


class CouponResponse(CouponBase):
    id: str
    code: str
    status: str
    used_count: int
    created_at: datetime
    updated_at: datetime


class UserCouponResponse(BaseSchema):
    id: str
    coupon: CouponResponse
    is_used: bool
    used_at: Optional[datetime] = None
    created_at: datetime


# 会员相关Schema
class MembershipLevelBase(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    monthly_price: Optional[float] = Field(None, ge=0)
    quarterly_price: Optional[float] = Field(None, ge=0)
    yearly_price: Optional[float] = Field(None, ge=0)
    lifetime_price: Optional[float] = Field(None, ge=0)
    max_courses: int = Field(0, ge=0)
    max_storage: int = Field(0, ge=0)
    benefits: Dict[str, Any] = {}


class MembershipLevelCreate(MembershipLevelBase):
    pass


class MembershipLevelResponse(MembershipLevelBase):
    id: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class MembershipCreate(BaseSchema):
    level_id: str
    membership_type: str = Field(..., description="monthly, quarterly, yearly, lifetime")
    auto_renew: bool = False


class MembershipResponse(BaseSchema):
    id: str
    user_id: str
    level: MembershipLevelResponse
    membership_type: str
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    auto_renew: bool
    price: float
    created_at: datetime


# 学习进度相关Schema
class LearningProgressUpdate(BaseSchema):
    lesson_id: str
    watch_duration: int = Field(0, ge=0)
    is_completed: bool = False


class LearningProgressResponse(BaseSchema):
    id: str
    lesson_id: str
    is_completed: bool
    watch_duration: int
    total_duration: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    last_watched_at: datetime


class CourseEnrollmentResponse(BaseSchema):
    id: str
    course_id: str
    course: CourseResponse
    is_active: bool
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: float
    last_watch_at: Optional[datetime] = None


# 评价相关Schema
class CourseReviewCreate(BaseSchema):
    course_id: str
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None


class CourseReviewResponse(BaseSchema):
    id: str
    user_id: str
    course_id: str
    rating: int
    title: Optional[str] = None
    content: Optional[str] = None
    is_verified: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime
    user: UserResponse


# 收藏相关Schema
class CourseFavoriteCreate(BaseSchema):
    course_id: str


class CourseFavoriteResponse(BaseSchema):
    id: str
    course_id: str
    course: CourseResponse
    created_at: datetime


# 余额相关Schema
class UserBalanceResponse(BaseSchema):
    id: str
    user_id: str
    balance: float
    frozen_balance: float
    created_at: datetime
    updated_at: datetime

class BalanceRecharge(BaseSchema):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., description="alipay, wechat")


# 通用响应Schema
class SuccessResponse(BaseSchema):
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseSchema):
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginationParams(BaseSchema):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    search: Optional[str] = None
    category_id: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field("desc", description="asc, desc")

# 智能体管理模型
class AgentCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    model_name: str
    system_prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    tools_enabled: Optional[List[str]] = []
    category: Optional[str] = "general"
    tags: Optional[List[str]] = []
    suggested_topics: Optional[List[str]] = []
    user_id: Optional[str] = None

# 解决循环引用
CourseCategoryResponse.model_rebuild()


# 图片相关Schema
class ImageUploadRequest(BaseModel):
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: bool = True

class ImageInfoResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    file_path: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_path: Optional[str] = None
    tags: List[str] = []
    is_public: bool
    uploader_id: str
    created_at: datetime
    updated_at: datetime

# 代理相关Schema
class AgentCreateV2(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: str
    config: Dict[str, Any] = {}
    is_active: bool = True

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    agent_type: str
    config: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

# 消息相关Schema
class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"  # text, image, video, audio
    attachments: Optional[List[Dict[str, Any]]] = None

class MessageResponse(BaseModel):
    id: str
    content: str
    message_type: str
    attachments: Optional[List[Dict[str, Any]]] = None
    sender_id: str
    conversation_id: str
    created_at: datetime
    updated_at: datetime

# 密码重置请求
class PasswordResetRequest(BaseModel):
    email: EmailStr

# 用户资料更新
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None

# 聊天相关模型
class ChatRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None

class ConversationUpdate(BaseModel):
    tags: Optional[List[str]] = None


# 健康检查Schema
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    database: str
    services: Dict[str, str]

# 日志管理Schema
class LogLevelRequest(BaseModel):
    level: str = Field(..., description="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")


# 媒体文件相关Schema
class MediaUploadRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class MediaInfoResponse(BaseModel):
    id: str
    description: Optional[str] = None
    filename: str
    filepath: Optional[str] = None  # 修改为可选字段
    media_type: str  # "video" or "audio"
    cover_url: Optional[str] = None
    duration: Optional[int] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    uploader_id: str
    upload_time: Optional[datetime] = None
    lesson_id: Optional[str] = None  # 关联的课时ID
    upload_status: Optional[str] = None
    storage_type: Optional[str] = None
    
    class Config:
        from_attributes = True

class MediaListResponse(BaseModel):
    media: List[MediaInfoResponse]
    total: Optional[int] = None
    page: Optional[int] = None
    size: Optional[int] = None

# OSS同步相关Schema
class OSSObjectInfo(BaseModel):
    """OSS对象信息"""
    key: str
    size: int
    etag: str
    last_modified: datetime
    storage_class: str
    object_type: str = "Normal"

class OSSSyncRequest(BaseModel):
    """OSS同步请求"""
    prefix: Optional[str] = Field(None, description="对象前缀过滤")
    max_keys: Optional[int] = Field(1000, ge=1, le=1000, description="最大返回对象数量")
    force_update: Optional[bool] = Field(False, description="是否强制更新已存在的对象")

class OSSSyncResponse(BaseModel):
    """OSS同步响应"""
    success: bool
    message: str
    synced_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    total_objects: int = 0
    missing_files_count: int = 0
    errors: List[str] = []

class OSSObjectListResponse(BaseModel):
    """OSS对象列表响应"""
    objects: List[OSSObjectInfo]
    total: int
    is_truncated: bool = False
    next_marker: Optional[str] = None

# 播放事件上报相关数据模型
class PlayEventData(BaseModel):
    """播放事件数据模型"""
    user_id: str
    media_id: str  # 修改为 media_id 以匹配前端发送的字段
    event_type: str  # play, pause, seek, heartbeat, ended
    current_time: Optional[float] = None
    previous_time: Optional[float] = None
    duration_time: Optional[float] = None
    progress: Optional[float] = None
    playback_rate: Optional[float] = 1.0
    volume: Optional[float] = 1.0
    is_fullscreen: Optional[bool] = False
    is_ended: Optional[bool] = False
    device_info: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
