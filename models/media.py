from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, BigInteger, Enum, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
import enum

class Media(Base):
    __tablename__ = "media"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    description = Column(Text, nullable=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(255), nullable=True)  # 异步上传时可能为空
    media_type = Column(String(50), nullable=False)  # 媒体类型：video、audio或image
    cover_url = Column(String(255), nullable=True)  # 封面图片URL（视频用）
    duration = Column(Integer, nullable=True)  # 时长，单位：秒
    size = Column(BigInteger, nullable=True)  # 文件大小，单位：字节
    mime_type = Column(String(100), nullable=True)  # MIME类型
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(String, ForeignKey("course_lessons.id"), nullable=True)  # 关联的课时ID，可为空
    upload_time = Column(DateTime, server_default=func.now())
    
    # 异步上传相关字段
    upload_status = Column(String(50), default="pending", nullable=False)  # 上传状态
    upload_progress = Column(Float, default=0.0, nullable=False)  # 上传进度 (0.0-100.0)
    task_id = Column(String, nullable=True)  # 异步任务ID
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # OSS存储相关字段
    storage_type = Column(String(50), default="local", nullable=False)  # 存储类型
    oss_key = Column(String(500), nullable=True)  # OSS对象键名
    oss_etag = Column(String(100), nullable=True)  # OSS对象ETag
    oss_storage_class = Column(String(50), nullable=True)  # OSS存储类型
    oss_last_modified = Column(DateTime, nullable=True)  # OSS对象最后修改时间
    oss_version_id = Column(String(100), nullable=True)  # OSS对象版本ID
    
    extra = Column(JSON, default=dict)  # 额外信息存储
    
    # 关联关系
    uploader = relationship("User")
    lesson = relationship("CourseLesson", back_populates="media_files")
    # 视频播放记录关系
    play_records = relationship("MediaPlayRecord", back_populates="media", cascade="all, delete-orphan")
    play_events = relationship("MediaPlayEvent", back_populates="media", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "filename": self.filename,
            "filepath": self.filepath,
            "media_type": self.media_type,
            "cover_url": self.cover_url,
            "duration": self.duration,
            "size": self.size,
            "mime_type": self.mime_type,
            "uploader_id": self.uploader_id,
            "lesson_id": self.lesson_id,
            "upload_time": self.upload_time.isoformat() if self.upload_time is not None else None,
            "upload_status": self.upload_status,
            "upload_progress": self.upload_progress,
            "task_id": self.task_id,
            "error_message": self.error_message,
            "storage_type": self.storage_type,
            "oss_key": self.oss_key,
            "oss_etag": self.oss_etag,
            "oss_storage_class": self.oss_storage_class,
            "oss_last_modified": self.oss_last_modified.isoformat() if self.oss_last_modified is not None else None,
            "oss_version_id": self.oss_version_id,
            "extra": self.extra
        }
