from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from models.database import Base
from datetime import datetime
from typing import Optional
import enum

class EventType(enum.Enum):
    """
    播放事件类型枚举
    """
    PLAY = "play"          # 开始播放
    PAUSE = "pause"        # 暂停播放
    SEEK = "seek"          # 拖动进度条
    HEARTBEAT = "heartbeat" # 心跳事件（定期上报）
    ENDED = "ended"        # 播放结束
    RESUME = "resume"      # 恢复播放
    STOP = "stop"          # 停止播放
    RATE_CHANGE = "rate_change"  # 播放速度改变
    VOLUME_CHANGE = "volume_change"  # 音量改变
    FULLSCREEN = "fullscreen"  # 全屏切换

class MediaPlayEvent(Base):
    """
    媒体播放事件模型
    记录用户播放媒体时的每个具体事件
    """
    __tablename__ = "media_play_events"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    media_id = Column(String, ForeignKey("media.id"), nullable=False, index=True)
    record_id = Column(String, ForeignKey("media_play_records.id"), nullable=True, index=True)
    
    # 事件基本信息
    event_type = Column(Enum(EventType), nullable=False, index=True)
    event_data = Column(Text, nullable=True)  # JSON格式的事件详细数据
    
    # 播放位置信息
    current_time = Column(Float, nullable=False, default=0.0)  # 事件发生时的播放时间点（秒）
    previous_time = Column(Float, nullable=True)  # 上一个时间点（用于seek事件）
    
    # 播放状态信息
    playback_rate = Column(Float, default=1.0)  # 播放速度
    volume = Column(Float, default=1.0)  # 音量 (0.0-1.0)
    is_fullscreen = Column(Boolean, default=False)  # 是否全屏
    is_muted = Column(Boolean, default=False)  # 是否静音
    
    # 设备和环境信息
    user_agent = Column(String, nullable=True)  # 用户代理
    ip_address = Column(String, nullable=True)  # IP地址
    device_type = Column(String, nullable=True)  # 设备类型（mobile/desktop/tablet）
    screen_resolution = Column(String, nullable=True)  # 屏幕分辨率
    
    # 网络和性能信息
    buffer_health = Column(Float, nullable=True)  # 缓冲健康度
    network_speed = Column(Float, nullable=True)  # 网络速度（Mbps）
    video_quality = Column(String, nullable=True)  # 视频质量（720p/1080p等）
    
    # 时间戳
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联关系
    user = relationship("User")
    media = relationship("Media")
    play_record = relationship("MediaPlayRecord", back_populates="events")
    
    def __repr__(self):
        return f"<MediaPlayEvent(type={self.event_type.value}, user_id={self.user_id}, time={self.current_time})>"
    
    @classmethod
    def create_play_event(cls, user_id: str, media_id: str, record_id: Optional[str] = None, **kwargs):
        """
        创建播放开始事件
        """
        return cls(
            user_id=user_id,
            media_id=media_id,
            record_id=record_id,
            event_type=EventType.PLAY,
            current_time=kwargs.get('current_time', 0.0),
            playback_rate=kwargs.get('playback_rate', 1.0),
            volume=kwargs.get('volume', 1.0),
            is_fullscreen=kwargs.get('is_fullscreen', False),
            **kwargs
        )
    
    @classmethod
    def create_pause_event(cls, user_id: str, media_id: str, current_time: float, record_id: Optional[str] = None, **kwargs):
        """
        创建暂停事件
        """
        return cls(
            user_id=user_id,
            media_id=media_id,
            record_id=record_id,
            event_type=EventType.PAUSE,
            current_time=current_time,
            **kwargs
        )
    
    @classmethod
    def create_seek_event(cls, user_id: str, media_id: str, from_time: float, to_time: float, record_id: Optional[str] = None, **kwargs):
        """
        创建拖动事件
        """
        return cls(
            user_id=user_id,
            media_id=media_id,
            record_id=record_id,
            event_type=EventType.SEEK,
            previous_time=from_time,
            current_time=to_time,
            **kwargs
        )
    
    @classmethod
    def create_heartbeat_event(cls, user_id: str, media_id: str, current_time: float, record_id: Optional[str] = None, **kwargs):
        """
        创建心跳事件
        """
        return cls(
            user_id=user_id,
            media_id=media_id,
            record_id=record_id,
            event_type=EventType.HEARTBEAT,
            current_time=current_time,
            playback_rate=kwargs.get('playback_rate', 1.0),
            volume=kwargs.get('volume', 1.0),
            is_fullscreen=kwargs.get('is_fullscreen', False),
            buffer_health=kwargs.get('buffer_health'),
            network_speed=kwargs.get('network_speed'),
            video_quality=kwargs.get('video_quality'),
            **kwargs
        )
    
    @classmethod
    def create_ended_event(cls, user_id: str, media_id: str, current_time: float, record_id: Optional[str] = None, **kwargs):
        """
        创建播放结束事件
        """
        return cls(
            user_id=user_id,
            media_id=media_id,
            record_id=record_id,
            event_type=EventType.ENDED,
            current_time=current_time,
            **kwargs
        )
    
    def get_seek_distance(self) -> float:
        """
        获取拖动距离（仅适用于seek事件）
        """
        event_type = getattr(self, 'event_type', None)
        previous_time = getattr(self, 'previous_time', None)
        if event_type != EventType.SEEK or previous_time is None:
            return 0.0
        return abs(getattr(self, 'current_time', 0) - getattr(self, 'previous_time', 0))
    
    def is_forward_seek(self) -> bool:
        """
        判断是否为向前拖动（仅适用于seek事件）
        """
        event_type = getattr(self, 'event_type', None)
        previous_time = getattr(self, 'previous_time', None)
        if event_type != EventType.SEEK or previous_time is None:
            return False
        current = getattr(self, 'current_time', 0)
        previous = getattr(self, 'previous_time', 0)
        return current > previous
    
    def is_backward_seek(self) -> bool:
        """
        判断是否为向后拖动（仅适用于seek事件）
        """
        event_type = getattr(self, 'event_type', None)
        previous_time = getattr(self, 'previous_time', None)
        if event_type != EventType.SEEK or previous_time is None:
            return False
        current = getattr(self, 'current_time', 0)
        previous = getattr(self, 'previous_time', 0)
        return current < previous