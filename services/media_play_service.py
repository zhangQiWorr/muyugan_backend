from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.media_play_record import MediaPlayRecord
from models.media_play_event import MediaPlayEvent, EventType
from models.media import Media
from services.logger import get_logger
import uuid

logger = get_logger("media_play_service")


class MediaPlayService:
    """
    视频播放服务类
    处理播放记录更新、有效观看时长计算和完成率判断
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_play_record(self, user_id: str, media_id: str) -> MediaPlayRecord:
        """
        获取或创建播放记录
        """
        play_record = self.db.query(MediaPlayRecord).filter(
            MediaPlayRecord.user_id == user_id,
            MediaPlayRecord.media_id == media_id
        ).first()
        
        if not play_record:
            play_record = MediaPlayRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                media_id=media_id,
                first_played_at=datetime.now()
            )
            self.db.add(play_record)
            self.db.flush()  # 确保获得ID
        
        return play_record
    
    def create_play_event(self, record_id: str, user_id: str, media_id: str,
                         event_type: EventType, current_time: float, 
                         previous_time: Optional[float] = None,
                         playback_rate: float = 1.0, volume: float = 1.0,
                         is_fullscreen: bool = False,
                         device_info: Optional[str] = None,
                         extra_data: Optional[str] = None) -> MediaPlayEvent:
        """
        创建播放事件记录
        """
        play_event = MediaPlayEvent(
            id=str(uuid.uuid4()),
            record_id=record_id,
            user_id=user_id,
            media_id=media_id,
            event_type=event_type,
            current_time=current_time,
            previous_time=previous_time,
            playback_rate=playback_rate,
            volume=volume,
            is_fullscreen=is_fullscreen,

        )
        self.db.add(play_event)
        return play_event
    
    def update_play_record_basic_info(self, play_record: MediaPlayRecord, 
                                     current_time: float, playback_rate: float = 1.0,
                                     volume: float = 1.0, is_fullscreen: bool = False):
        """
        更新播放记录的基本信息
        """
        # 使用setattr来避免SQLAlchemy列类型问题
        setattr(play_record, 'current_time', current_time)
        current_max = getattr(play_record, 'max_played_time', 0)
        setattr(play_record, 'max_played_time', max(current_max, current_time))
        setattr(play_record, 'playback_rate', playback_rate)
        setattr(play_record, 'volume', volume)
        setattr(play_record, 'is_fullscreen', is_fullscreen)
        setattr(play_record, 'last_played_at', datetime.now())
    
    def update_play_status(self, play_record: MediaPlayRecord, event_type: str):
        """
        根据事件类型更新播放状态
        """
        if event_type == "play":
            setattr(play_record, 'is_playing', True)
            setattr(play_record, 'is_paused', False)
            # 增加播放次数
            current_count = getattr(play_record, 'play_count', 0)
            setattr(play_record, 'play_count', current_count + 1)
        elif event_type == "pause":
            setattr(play_record, 'is_playing', False)
            setattr(play_record, 'is_paused', True)
        elif event_type == "seek":
            # 增加拖动次数
            current_count = getattr(play_record, 'seek_count', 0)
            setattr(play_record, 'seek_count', current_count + 1)
        elif event_type == "ended":
            setattr(play_record, 'is_playing', False)
            setattr(play_record, 'is_ended', True)
    
    def calculate_and_update_progress(self, play_record: MediaPlayRecord, 
                                    current_time: float, video_duration: float):
        """
        计算并更新播放进度
        """
        if video_duration > 0:
            progress = min(current_time / video_duration, 1.0)
            
            setattr(play_record, 'progress', progress)
    
    def update_effective_play_time(self, play_record: MediaPlayRecord, 
                                 event_type: str, current_time: float, 
                                 previous_time: Optional[float] = None,
                                 playback_rate: float = 1.0):
        """
        更新有效观看时长
        
        逻辑说明：
        1. 只有在连续播放的情况下才计入有效时长
        2. 支持的事件类型：pause（暂停）、ended（结束）、heartbeat（心跳）
        3. 必须提供previous_time来计算时间差
        4. 时间差必须在合理范围内（0.1-120秒）
        5. 考虑播放速度对有效时长的影响
        """
        # 获取当前有效时长和总播放时长
        current_effective = getattr(play_record, 'effective_duration', 0) or 0.0
        current_total = getattr(play_record, 'total_play_time', 0) or 0.0
        
        # 处理播放开始事件
        if event_type == "play":
            # 播放开始事件，记录当前时间但不计入有效时长
            logger.debug(f"播放开始事件: {current_time:.2f}s")
            return
        
        # 计算有效观看时长的事件类型
        if event_type in ["pause", "ended", "heartbeat"]:
            # 尝试获取上一个播放时间点
            if previous_time is not None:
                time_diff = current_time - previous_time
            else:
                # 如果没有previous_time，尝试从最近的事件中获取
                last_event = self.db.query(MediaPlayEvent).filter(
                    MediaPlayEvent.record_id == getattr(play_record, 'id'),
                    MediaPlayEvent.event_type.in_([EventType.PLAY, EventType.HEARTBEAT])
                ).order_by(MediaPlayEvent.timestamp.desc()).first()
                
                if last_event and last_event.current_time is not None:
                    time_diff = current_time - last_event.current_time
                else:
                    logger.warning(f"无法计算有效观看时长：缺少previous_time和最近播放事件")
                    return
            
            # 验证时间差的合理性（0.1-120秒之间，扩大范围以适应不同的心跳间隔）
            if 0.1 <= time_diff <= 120:
                # 计算有效观看时长（考虑播放速度）
                # 如果播放速度大于1，实际观看时长应该除以播放速度
                effective_time = time_diff / max(playback_rate, 0.25)  # 防止除零和异常值
                
                # 更新统计数据
                new_effective = current_effective + effective_time
                new_total = current_total + time_diff
                
                setattr(play_record, 'effective_duration', new_effective)
                setattr(play_record, 'total_play_time', new_total)
                
                logger.debug(f"更新有效观看时长: +{effective_time:.2f}s (时间差:{time_diff:.2f}s, 播放速度:{playback_rate}x, 总计: {new_effective:.2f}s)")
            else:
                logger.warning(f"时间差异常，跳过更新: {time_diff:.2f}s (事件类型: {event_type})")
        
        # 对于seek事件，不计入有效时长
        elif event_type == "seek":
            logger.debug(f"拖动事件，不计入有效时长: {current_time:.2f}s")
    
    def check_and_mark_completion(self, play_record: MediaPlayRecord, 
                                video_duration: float, event_type: str,
                                progress: Optional[float] = None,
                                min_completion_rate: float = 0.9,
                                min_effective_rate: float = 0.8) -> bool:
        """
        检查并标记观看完成状态
        
        Returns:
            bool: 是否标记为完成
        """
        # 只在播放结束或进度达到90%时检查
        if event_type != "ended" and (not progress or progress < 0.9):
            return False
        
        if video_duration <= 0:
            return False
        
        # 获取当前数据
        max_played_time = getattr(play_record, 'max_played_time', 0)
        effective_duration = getattr(play_record, 'effective_duration', 0)
        seek_count = getattr(play_record, 'seek_count', 0)
        
        # 计算完成率和有效观看率
        completion_rate = min(max_played_time / video_duration, 1.0)
        effective_rate = effective_duration / video_duration
        
        # 判断是否有效完成
        # 根据拖动次数调整有效观看率要求
        # 如果拖动次数较多，说明用户可能在寻找特定内容，适当降低有效观看率要求
        adjusted_effective_rate = min_effective_rate
        if seek_count > 10:  # 拖动次数过多
            adjusted_effective_rate = min_effective_rate * 0.7  # 降低30%要求
        elif seek_count > 5:  # 拖动次数较多
            adjusted_effective_rate = min_effective_rate * 0.85  # 降低15%要求
        
        is_effectively_completed = (
            completion_rate >= min_completion_rate and
            effective_rate >= adjusted_effective_rate
        )
        
        if is_effectively_completed:
            setattr(play_record, 'completed', True)
            setattr(play_record, 'completed_at', datetime.now())
            
            logger.info(f"标记观看完成 - 完成率: {completion_rate:.2%}, 有效率: {effective_rate:.2%} (要求: {adjusted_effective_rate:.2%}), 拖动次数: {seek_count}")
            return True
        
        return False
    
    def get_video_duration(self, media_id: str) -> float:
        """
        获取视频时长
        """
        media = self.db.query(Media).filter(Media.id == media_id).first()
        if not media:
            return 0.0
        
        # 尝试从不同字段获取时长
        duration = getattr(media, 'duration', None)
        if duration and duration > 0:
            return float(duration)
        
        # 如果没有时长信息，返回默认值
        logger.warning(f"视频 {media_id} 没有时长信息，使用默认值")
        return 3600.0  # 默认1小时
    
    def process_play_event(
        self,
        user_id: str,
        media_id: str,
        event_type: str,
        current_time: float,
        previous_time: Optional[float] = None,
        progress: Optional[float] = None,
        playback_rate: float = 1.0,
        volume: float = 1.0,
        is_fullscreen: bool = False,
        device_info: Optional[dict] = None,
        extra_data: Optional[dict] = None
    ) -> dict:
        """
        处理播放事件的完整逻辑
        """
        try:
            # 获取或创建播放记录
            play_record = self.get_or_create_play_record(user_id, media_id)
            
            # 创建事件类型枚举
            event_type_enum = getattr(EventType, event_type.upper(), None)
            if not event_type_enum:
                raise ValueError(f"不支持的事件类型: {event_type}")
            
            # 创建播放事件
            play_event = self.create_play_event(
                record_id=getattr(play_record, 'id'),
                user_id=user_id,
                media_id=media_id,
                event_type=event_type_enum,
                current_time=current_time,
                previous_time=previous_time,
                playback_rate=playback_rate,
                volume=volume,
                is_fullscreen=is_fullscreen,
                device_info=str(device_info) if device_info else None,
                extra_data=str(extra_data) if extra_data else None
            )
            
            # 更新播放记录基本信息
            self.update_play_record_basic_info(
                play_record, current_time, playback_rate, volume, is_fullscreen
            )
            
            # 更新播放状态
            self.update_play_status(play_record, event_type)
            
            # 获取视频时长并更新进度
            video_duration = self.get_video_duration(media_id)
            self.calculate_and_update_progress(play_record, current_time, video_duration)
            
            # 更新有效播放时长
            self.update_effective_play_time(
                play_record, event_type, current_time, previous_time, playback_rate
            )
            
            # 检查并标记完成状态
            self.check_and_mark_completion(
                play_record, video_duration, event_type, progress
            )
            
            # 提交数据库事务
            self.db.commit()
            
            # 计算完成率
            completion_rate = play_record.calculate_completion_rate(video_duration)
            
            # 返回结果
            return {
                "record_id": getattr(play_record, 'id'),
                "event_id": getattr(play_event, 'id'),
                "current_time": current_time,
                "progress": getattr(play_record, 'progress'),
                "completion_rate": completion_rate,
                "effective_play_time": getattr(play_record, 'effective_duration'),
                "is_completed": getattr(play_record, 'completed')
            }
            
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"处理播放事件失败: {str(e)}")