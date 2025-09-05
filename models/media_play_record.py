from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.database import Base
from datetime import datetime
import uuid

class MediaPlayRecord(Base):
    """
    用户媒体播放记录模型
    记录用户对特定媒体的播放行为和统计数据
    """
    __tablename__ = "media_play_records"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    media_id = Column(String, ForeignKey("media.id"), nullable=False, index=True)
    
    # 播放进度相关
    current_time = Column(Float, default=0.0)  # 当前播放时间点（秒）
    max_played_time = Column(Float, default=0.0)  # 最大播放到的时间点（秒）
    progress = Column(Float, default=0.0)  # 播放进度百分比 (0.0-1.0)
    
    # 有效观看时长计算
    effective_duration = Column(Float, default=0.0)  # 有效观看时长（秒）
    total_play_time = Column(Float, default=0.0)  # 总播放时间（包含重复播放）
    
    # 播放状态
    is_playing = Column(Boolean, default=False)  # 当前是否正在播放
    is_paused = Column(Boolean, default=False)  # 是否暂停
    is_ended = Column(Boolean, default=False)  # 是否播放结束
    completed = Column(Boolean, default=False)  # 是否完成观看（达到95%以上）
    
    # 播放行为统计
    play_count = Column(Integer, default=0)  # 播放次数
    pause_count = Column(Integer, default=0)  # 暂停次数
    seek_count = Column(Integer, default=0)  # 拖动次数
    
    # 播放设置
    playback_rate = Column(Float, default=1.0)  # 播放速度
    is_fullscreen = Column(Boolean, default=False)  # 是否全屏
    volume = Column(Float, default=1.0)  # 音量 (0.0-1.0)
    
    # 异常行为检测
    abnormal_seek_count = Column(Integer, default=0)  # 异常拖动次数
    is_abnormal_behavior = Column(Boolean, default=False)  # 是否存在异常行为
    
    # 时间戳
    first_played_at = Column(DateTime, default=datetime.now)  # 首次播放时间
    last_played_at = Column(DateTime, default=datetime.now)  # 最后播放时间
    completed_at = Column(DateTime, nullable=True)  # 完成观看时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联关系
    user = relationship("User", back_populates="media_play_records")
    media = relationship("Media", back_populates="play_records")
    events = relationship("MediaPlayEvent", back_populates="play_record", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MediaPlayRecord(user_id={self.user_id}, media_id={self.media_id}, progress={self.progress:.2%})>"
    
    def calculate_completion_rate(self, video_duration: float) -> float:
        """
        计算播放完成率
        注意：此方法应在数据库查询后的实例上调用
        """
        if video_duration <= 0:
            return 0.0
        # 确保获取实际值而不是SQLAlchemy列对象
        max_time = getattr(self, 'max_played_time', 0) or 0
        return min(float(max_time) / video_duration, 1.0)
    
    def is_valid_completion(self, video_duration: float) -> bool:
        """
        判断是否为有效完成观看
        条件：
        1. 播放进度 >= 95%
        2. 有效观看时长 >= 视频总时长的80%
        3. 无异常拖动行为
        注意：此方法应在数据库查询后的实例上调用
        """
        completion_rate = self.calculate_completion_rate(video_duration)
        # 确保获取实际值而不是SQLAlchemy列对象
        effective_dur = getattr(self, 'effective_duration', 0) or 0
        is_abnormal = getattr(self, 'is_abnormal_behavior', False) or False
        return (
            completion_rate >= 0.95 and
            float(effective_dur) >= video_duration * 0.8 and
            not bool(is_abnormal)
        )
    
    def update_effective_duration(self, new_time: float, old_time: float):
        """
        更新有效观看时长
        只有连续播放的时间才计入有效时长
        """
        if new_time > old_time:
            # 正常播放，增加有效时长
            time_diff = new_time - old_time
            # 考虑播放速度
            actual_time = time_diff / self.playback_rate
            self.effective_duration += actual_time
    
    def detect_abnormal_seek(self, from_time: float, to_time: float, threshold: float = 30.0):
        """
        检测异常拖动行为
        如果拖动跨度超过阈值，标记为异常
        """
        seek_distance = abs(to_time - from_time)
        if seek_distance > threshold:
            self.abnormal_seek_count += 1
            # 如果异常拖动次数过多，标记为异常行为
            abnormal_count = getattr(self, 'abnormal_seek_count', 0) or 0
            if int(abnormal_count) >= 5:
                self.is_abnormal_behavior = True
    
    def to_dict(self):
        """
        将模型转换为字典格式
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "media_id": self.media_id,
            "current_time": self.current_time,
            "max_played_time": self.max_played_time,
            "progress": self.progress,
            "effective_duration": self.effective_duration,
            "total_play_time": self.total_play_time,
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "is_ended": self.is_ended,
            "completed": self.completed,
            "play_count": self.play_count,
            "pause_count": self.pause_count,
            "seek_count": self.seek_count,
            "playback_rate": self.playback_rate,
            "is_fullscreen": self.is_fullscreen,
            "volume": self.volume,
            "abnormal_seek_count": self.abnormal_seek_count,
            "is_abnormal_behavior": self.is_abnormal_behavior,
            "first_played_at": self.first_played_at.isoformat() if self.first_played_at is not None else None,
            "last_played_at": self.last_played_at.isoformat() if self.last_played_at is not None else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None
        }