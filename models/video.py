from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import uuid

class Video(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(255), nullable=False)
    cover_url = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)  # 秒
    size = Column(BigInteger, nullable=True)  # 视频大小，单位B
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False)
    upload_time = Column(DateTime, server_default=func.now())
    extra = Column(JSON, default=dict)

    uploader = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "filename": self.filename,
            "filepath": self.filepath,
            "cover_url": self.cover_url,
            "duration": self.duration,
            "uploader_id": self.uploader_id,
            "upload_time": self.upload_time.isoformat() if self.upload_time else None,
            "extra": self.extra
        }

# Pydantic响应模型
from pydantic import BaseModel
from typing import Optional

class VideoInfo(BaseModel):
    id: str
    title: str
    description: Optional[str]
    filename: str
    cover_url: Optional[str]
    duration: Optional[int]
    uploader_id: str
    upload_time: Optional[str]

    class Config:
        from_attributes = True
