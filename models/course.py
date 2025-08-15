"""
课程相关模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
import enum


class CourseStatus(str, enum.Enum):
    """课程状态"""
    DRAFT = "draft"           # 草稿
    PUBLISHED = "published"   # 已发布
    OFFLINE = "offline"       # 已下架
    ARCHIVED = "archived"     # 已归档


class ContentType(str, enum.Enum):
    """内容类型"""
    VIDEO = "video"           # 视频
    AUDIO = "audio"           # 音频
    TEXT = "text"             # 图文
    PDF = "pdf"               # PDF文档
    QUIZ = "quiz"             # 测验


class CourseCategory(Base):
    """课程分类"""
    __tablename__ = "course_categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    parent_id = Column(String, ForeignKey("course_categories.id"), nullable=True)
    
    # 关系 - 修复自引用关系配置
    parent = relationship("CourseCategory", remote_side=[id], back_populates="children")
    children = relationship("CourseCategory", back_populates="parent", overlaps="parent")
    courses = relationship("Course", back_populates="category")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Course(Base):
    """课程模型"""
    __tablename__ = "courses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    subtitle = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    cover_image = Column(String(500), nullable=True)
    
    # 分类和标签
    category_id = Column(String, ForeignKey("course_categories.id"), nullable=True)
    tags = Column(JSON, default=list)  # 标签列表
    
    # 价格和会员设置
    price = Column(Float, default=0.0)  # 价格，0表示免费
    original_price = Column(Float, nullable=True)  # 原价
    is_free = Column(Boolean, default=True)  # 是否免费
    is_member_only = Column(Boolean, default=False)  # 是否仅会员可见
    
    # 课程信息
    duration = Column(Integer, default=0)  # 总时长（分钟）
    lesson_count = Column(Integer, default=0)  # 课时数量
    difficulty_level = Column(String(20), default="beginner")  # 难度级别
    language = Column(String(20), default="zh-CN")  # 语言
    
    # 状态和权限
    status = Column(Enum(CourseStatus), default=CourseStatus.DRAFT)
    is_featured = Column(Boolean, default=False)  # 是否推荐
    is_hot = Column(Boolean, default=False)  # 是否热门
    
    # 统计信息
    view_count = Column(Integer, default=0)  # 浏览次数
    enroll_count = Column(Integer, default=0)  # 报名次数
    rating = Column(Float, default=0.0)  # 评分
    rating_count = Column(Integer, default=0)  # 评分次数
    
    # 创建者
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime, nullable=True)
    
    # 关系
    category = relationship("CourseCategory", back_populates="courses")
    creator = relationship("User")
    lessons = relationship("CourseLesson", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    reviews = relationship("CourseReview", back_populates="course", cascade="all, delete-orphan")
    orders = relationship("OrderItem", back_populates="course")


class CourseLesson(Base):
    """课程课时"""
    __tablename__ = "course_lessons"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(Enum(ContentType), nullable=False)
    
    # 内容相关
    content_url = Column(String(500), nullable=True)  # 内容链接
    content_text = Column(Text, nullable=True)  # 文本内容
    duration = Column(Integer, default=0)  # 时长（分钟）
    
    # 排序和状态
    sort_order = Column(Integer, default=0)
    is_free = Column(Boolean, default=False)  # 是否免费试看
    is_active = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    course = relationship("Course", back_populates="lessons")
    progress_records = relationship("LearningProgress", back_populates="lesson", cascade="all, delete-orphan")


class CourseEnrollment(Base):
    """课程报名记录"""
    __tablename__ = "course_enrollments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    
    # 报名状态
    is_active = Column(Boolean, default=True)
    enrolled_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # 学习进度
    progress_percentage = Column(Float, default=0.0)  # 进度百分比
    last_learned_at = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship("User")
    course = relationship("Course", back_populates="enrollments")
    progress_records = relationship("LearningProgress", back_populates="enrollment", cascade="all, delete-orphan")
    
    # 唯一约束：一个用户只能报名一次同一门课程
    __table_args__ = (UniqueConstraint('user_id', 'course_id', name='uq_user_course_enrollment'),)


class LearningProgress(Base):
    """学习进度记录"""
    __tablename__ = "learning_progress"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    lesson_id = Column(String, ForeignKey("course_lessons.id"), nullable=False)
    enrollment_id = Column(String, ForeignKey("course_enrollments.id"), nullable=False)
    
    # 学习状态
    is_completed = Column(Boolean, default=False)
    watch_duration = Column(Integer, default=0)  # 观看时长（秒）
    total_duration = Column(Integer, default=0)  # 总时长（秒）
    
    # 时间戳
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    last_watched_at = Column(DateTime, server_default=func.now())
    
    # 关系
    user = relationship("User")
    course = relationship("Course")
    lesson = relationship("CourseLesson", back_populates="progress_records")
    enrollment = relationship("CourseEnrollment", back_populates="progress_records")


class CourseReview(Base):
    """课程评价"""
    __tablename__ = "course_reviews"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    
    # 评价内容
    rating = Column(Integer, nullable=False)  # 评分 1-5
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    
    # 状态
    is_verified = Column(Boolean, default=False)  # 是否已购买验证
    is_public = Column(Boolean, default=True)  # 是否公开显示
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User")
    course = relationship("Course", back_populates="reviews")


class CourseFavorite(Base):
    """课程收藏"""
    __tablename__ = "course_favorites"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    user = relationship("User")
    course = relationship("Course")
    
    # 唯一约束：一个用户只能收藏一次同一门课程
    __table_args__ = (UniqueConstraint('user_id', 'course_id', name='uq_user_course_favorite'),)
