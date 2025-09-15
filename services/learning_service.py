"""
学习记录服务
处理用户学习行为的记录和查询
"""
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from datetime import datetime, timedelta
from models.user import User
from models.course import Course, CourseLesson, LearningProgress, CourseEnrollment
from models.media import Media
from models.media_play_record import MediaPlayRecord
from services.logger import get_logger

# 课时完成阈值常量（百分比）
LESSON_COMPLETION_THRESHOLD = 90.0

logger = get_logger("learning_service")

class LearningService:
    """学习记录服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_lesson_start(self, user_id: str, lesson_id: str) -> LearningProgress:
        """
        记录用户开始学习课时
        
        Args:
            user_id: 用户ID
            lesson_id: 课时ID
            
        Returns:
            LearningProgress: 学习进度记录
        """
        try:
            # 获取课时信息
            lesson = self.db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
            if not lesson:
                raise ValueError(f"课时不存在: {lesson_id}")
            
            # 获取课程信息（用于日志记录）
            course = self.db.query(Course).filter(Course.id == lesson.course_id).first()
            if not course:
                raise ValueError(f"课程不存在: {lesson.course_id}")
            
            # 检查是否已有学习进度记录
            progress = self.db.query(LearningProgress).filter(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.lesson_id == lesson_id
                )
            ).first()
            
            if not progress:
                # 创建新的学习进度记录
                progress = LearningProgress(
                    user_id=user_id,
                    course_id=lesson.course_id,
                    lesson_id=lesson_id,
                    started_at=datetime.now(),
                    last_watched_at=datetime.now()
                )
                self.db.add(progress)
            else:
                # 更新最后观看时间
                progress.last_watched_at = datetime.now()
            
            self.db.commit()
            course_type = "免费课程" if course.is_free else "付费课程"
            logger.info(f"用户 {user_id} 开始学习{course_type}课时 {lesson_id}")
            return progress
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"记录学习开始失败: {str(e)}")
            raise
    
    def record_media_progress(self, user_id: str, media_id: str, 
                            watch_duration: int, total_duration: int) -> MediaPlayRecord:
        """
        记录用户观看媒体文件的进度
        
        Args:
            user_id: 用户ID
            media_id: 媒体文件ID
            watch_duration: 已观看时长（秒）
            total_duration: 总时长（秒）
            
        Returns:
            MediaPlayRecord: 媒体播放记录
        """
        try:
            # 获取媒体文件信息
            media = self.db.query(Media).filter(Media.id == media_id).first()
            if not media:
                raise ValueError(f"媒体文件不存在: {media_id}")
            
            # 获取或创建媒体播放记录
            play_record = self.db.query(MediaPlayRecord).filter(
                and_(
                    MediaPlayRecord.user_id == user_id,
                    MediaPlayRecord.media_id == media_id
                )
            ).first()
            
            if not play_record:
                # 创建新的播放记录
                play_record = MediaPlayRecord(
                    user_id=user_id,
                    media_id=media_id,
                    current_time=watch_duration,
                    max_played_time=watch_duration,
                    total_duration=total_duration,
                    effective_duration=watch_duration,
                    total_play_time=watch_duration,
                    is_playing=True,
                    play_count=1,
                    first_played_at=datetime.now(),
                    last_played_at=datetime.now()
                )
                self.db.add(play_record)
            else:
                # 更新播放记录
                play_record.current_time = watch_duration
                if watch_duration > play_record.max_played_time:
                    play_record.max_played_time = watch_duration
                
                # 更新有效观看时长
                if watch_duration > play_record.current_time:
                    play_record.update_effective_duration(watch_duration, play_record.current_time)
                
                play_record.total_play_time += watch_duration - play_record.current_time
                play_record.last_played_at = datetime.now()
            
            # 计算播放进度
            if total_duration > 0:
                play_record.progress = min(watch_duration / total_duration, 1.0)
            
            # 判断是否完成观看（观看进度达到指定阈值）
            if play_record.progress >= 0.9:  # 注意：这里的0.9是媒体播放记录的完成阈值，与课程学习的阈值不同
                play_record.completed = True
                play_record.completed_at = datetime.now()
                logger.info(f"用户 {user_id} 完成观看媒体 {media_id}")
            
            self.db.commit()
            return play_record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"记录媒体观看进度失败: {str(e)}")
            raise

    def calculate_lesson_progress(self, user_id: str, lesson_id: str) -> Dict[str, Any]:
        """
        计算课时学习进度（基于媒体文件观看进度）
        
        Args:
            user_id: 用户ID
            lesson_id: 课时ID
            
        Returns:
            Dict: 课时进度信息
        """
        try:
            # 获取课时的所有媒体文件
            media_files = self.db.query(Media).filter(
                and_(
                    Media.lesson_id == lesson_id,
                    Media.media_type == 'video'  # 只计算视频文件
                )
            ).all()
            
            if not media_files:
                return {
                    'progress_percentage': 0.0,
                    'completed_media': 0,
                    'total_media': 0,
                    'total_watch_duration': 0,
                    'total_duration': 0
                }
            
            # 获取用户的媒体观看记录
            total_watch_duration = 0
            total_duration = 0
            completed_media = 0
            
            for media in media_files:
                # 获取该媒体的播放记录
                play_record = self.db.query(MediaPlayRecord).filter(
                    and_(
                        MediaPlayRecord.user_id == user_id,
                        MediaPlayRecord.media_id == media.id
                    )
                ).first()
                
                if play_record:
                    total_watch_duration += play_record.effective_duration
                    if play_record.completed:
                        completed_media += 1
                
                # 累加媒体总时长
                if media.duration:
                    total_duration += media.duration
            
            # 计算进度百分比
            progress_percentage = 0.0
            if total_duration > 0:
                progress_percentage = (total_watch_duration / total_duration) * 100
            
            return {
                'progress_percentage': min(progress_percentage, 100.0),
                'completed_media': completed_media,
                'total_media': len(media_files),
                'total_watch_duration': total_watch_duration,
                'total_duration': total_duration
            }
            
        except Exception as e:
            logger.error(f"计算课时进度失败: {str(e)}")
            return {
                'progress_percentage': 0.0,
                'completed_media': 0,
                'total_media': 0,
                'total_watch_duration': 0,
                'total_duration': 0
            }
    
    def update_lesson_progress(self, user_id: str, lesson_id: str) -> LearningProgress:
        """
        更新课时学习进度（基于媒体文件观看进度）
        
        Args:
            user_id: 用户ID
            lesson_id: 课时ID
            
        Returns:
            LearningProgress: 学习进度记录
        """
        try:
            # 获取学习进度记录
            progress = self.db.query(LearningProgress).filter(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.lesson_id == lesson_id
                )
            ).first()
            
            if not progress:
                # 如果没有记录，先创建
                progress = self.record_lesson_start(user_id, lesson_id)
            
            # 计算课时进度
            lesson_progress = self.calculate_lesson_progress(user_id, lesson_id)
            
            # 更新学习进度记录
            progress.watch_duration = int(lesson_progress['total_watch_duration'])
            progress.total_duration = int(lesson_progress['total_duration'])
            progress.last_watched_at = datetime.now()
            
            # 判断是否完成学习（进度达到90%或所有媒体都完成）
            is_completed = (
                lesson_progress['progress_percentage'] >= LESSON_COMPLETION_THRESHOLD or 
                lesson_progress['completed_media'] == lesson_progress['total_media']
            )
            
            if is_completed and not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = datetime.now()
                logger.info(f"用户 {user_id} 完成课时 {lesson_id}")
            
            self.db.commit()
            return progress
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新课时进度失败: {str(e)}")
            raise
    
    def get_user_recent_courses(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用户最近学习的课程列表
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 最近学习的课程列表
        """
        try:
            # 查询用户最近的学习记录，按最后观看时间排序
            recent_lessons = self.db.query(
                LearningProgress,
                Course,
                CourseLesson
            ).join(
                Course, LearningProgress.course_id == Course.id
            ).join(
                CourseLesson, LearningProgress.lesson_id == CourseLesson.id
            ).filter(
                LearningProgress.user_id == user_id
            ).order_by(
                desc(LearningProgress.last_watched_at)
            ).limit(limit * 3).all()  # 多取一些，因为要去重
            
            # 按课程去重，保留每个课程最近的学习记录
            course_dict = {}
            for progress, course, lesson in recent_lessons:
                if course.id not in course_dict:
                    course_dict[course.id] = {
                        'course': course,
                        'progress': progress,
                        'lesson': lesson,
                        'last_watch_at': progress.last_watched_at
                    }
            
            # 转换为返回格式
            recent_courses = []
            for course_data in list(course_dict.values())[:limit]:
                course = course_data['course']
                progress = course_data['progress']
                
                # 计算课程学习进度
                course_progress = self._calculate_course_progress(user_id, course.id)
                
                recent_courses.append({
                    'course_id': course.id,
                    'title': course.title,
                    'subtitle': course.subtitle,
                    'cover_image': course.cover_image,
                    'duration': course.duration,
                    'lesson_count': course.lesson_count,
                    'difficulty_level': course.difficulty_level,
                    'is_featured': course.is_featured,
                    'is_hot': course.is_hot,
                    'last_watch_at': course_data['last_watch_at'].isoformat(),
                    'course_progress': course_progress,
                    'last_lesson': {
                        'lesson_id': course_data['lesson'].id,
                        'title': course_data['lesson'].title,
                        'duration': course_data['lesson'].duration
                    }
                })
            
            return recent_courses
            
        except Exception as e:
            logger.error(f"获取用户最近学习课程失败: {str(e)}")
            raise
    
    def get_user_learning_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户学习统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 学习统计信息
        """
        try:
            # 总学习时长（秒）
            total_learning_time = self.db.query(
                func.sum(LearningProgress.watch_duration)
            ).filter(
                LearningProgress.user_id == user_id
            ).scalar() or 0
            
            # 已完成的课时数
            completed_lessons = self.db.query(LearningProgress).filter(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.is_completed == True
                )
            ).count()
            
            # 正在学习的课程数
            learning_courses = self.db.query(
                func.count(func.distinct(LearningProgress.course_id))
            ).filter(
                LearningProgress.user_id == user_id
            ).scalar() or 0
            
            # 已完成的课程数
            completed_courses = self._calculate_completed_courses(user_id)
            
            # 最近7天学习时长（秒）
            week_ago = datetime.now() - timedelta(days=7)
            recent_learning_time = self.db.query(
                func.sum(LearningProgress.watch_duration)
            ).filter(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.last_watched_at >= week_ago
                )
            ).scalar() or 0
            
            # 今日学习时长（秒）
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_duration = self.db.query(
                func.sum(LearningProgress.watch_duration)
            ).filter(
                and_(
                    LearningProgress.user_id == user_id,
                    LearningProgress.last_watched_at >= today_start
                )
            ).scalar() or 0
            
            # 用户订阅课程数量
            enrollment_count = self.db.query(CourseEnrollment).filter(
                and_(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.is_active == True
                )
            ).count()
            
            # 学习连续天数
            learning_days = self._calculate_learning_streak(user_id)
            
            return {
                'total_learning_time': total_learning_time,
                'completed_lessons': completed_lessons,
                'completed_courses': completed_courses,
                'learning_courses': learning_courses,
                'recent_learning_time': recent_learning_time,
                'learning_streak_days': learning_days,
                'today_duration': today_duration,
                'enrollment_count': enrollment_count
            }
            
        except Exception as e:
            logger.error(f"获取用户学习统计失败: {str(e)}")
            raise
    
    def _calculate_course_progress(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """
        计算课程学习进度（基于课时完成情况）
        
        Args:
            user_id: 用户ID
            course_id: 课程ID
            
        Returns:
            Dict: 课程进度信息
        """
        try:
            # 获取课程的所有课时
            lessons = self.db.query(CourseLesson).filter(
                CourseLesson.course_id == course_id
            ).all()
            
            if not lessons:
                return {
                    'progress_percentage': 0.0, 
                    'completed_lessons': 0, 
                    'total_lessons': 0,
                    'total_watch_duration': 0,
                    'total_duration': 0
                }
            
            # 计算每个课时的进度
            completed_lessons = 0
            total_watch_duration = 0
            total_duration = 0
            
            for lesson in lessons:
                # 计算课时进度
                lesson_progress = self.calculate_lesson_progress(user_id, lesson.id)
                
                # 累加观看时长
                total_watch_duration += lesson_progress['total_watch_duration']
                total_duration += lesson_progress['total_duration']
                # 判断课时是否完成（进度达到90%或所有媒体都完成）
                if (lesson_progress['progress_percentage'] >= LESSON_COMPLETION_THRESHOLD or 
                    lesson_progress['completed_media'] == lesson_progress['total_media']):
                    completed_lessons += 1

            # 计算课程进度百分比
            progress_percentage = (completed_lessons / len(lessons)) * 100 if lessons else 0.0
            logger.info(f"✅ 计算课程进度成功: 课程【{course_id}】进度: {progress_percentage:.1f}%")
            
            return {
                'progress_percentage':min(round(progress_percentage, 1), 100) ,
                'completed_lessons': completed_lessons,
                'total_lessons': len(lessons),
                'total_watch_duration': total_watch_duration,
                'total_duration': total_duration
            }
            
        except Exception as e:
            logger.error(f"计算课程进度失败: {str(e)}")
            return {
                'progress_percentage': 0.0, 
                'completed_lessons': 0, 
                'total_lessons': 0,
                'total_watch_duration': 0,
                'total_duration': 0
            }
    
    def _calculate_completed_courses(self, user_id: str) -> int:
        """
        计算用户已完成的课程数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 已完成的课程数量
        """
        try:
            # 获取用户学习过的所有课程
            user_courses = self.db.query(
                func.distinct(LearningProgress.course_id)
            ).filter(
                LearningProgress.user_id == user_id
            ).all()
            
            completed_courses = 0
            
            for (course_id,) in user_courses:
                # 计算课程进度，使用与get_completed_courses相同的逻辑
                course_progress = self._calculate_course_progress(user_id, course_id)
                
                # 如果课程进度达到阈值，则认为课程已完成
                if course_progress['progress_percentage'] >= LESSON_COMPLETION_THRESHOLD:
                    completed_courses += 1
            
            return completed_courses
            
        except Exception as e:
            logger.error(f"计算已完成课程数量失败: {str(e)}")
            return 0

    def _calculate_learning_streak(self, user_id: str) -> int:
        """
        计算学习连续天数
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 连续学习天数
        """
        try:
            # 获取用户最近的学习记录，按日期分组
            learning_dates = self.db.query(
                func.date(LearningProgress.last_watched_at).label('learn_date')
            ).filter(
                LearningProgress.user_id == user_id
            ).distinct().order_by(
                desc(func.date(LearningProgress.last_watched_at))
            ).all()
            
            if not learning_dates:
                return 0
            
            # 计算连续天数
            streak = 0
            current_date = datetime.now().date()
            
            for record in learning_dates:
                learn_date = record.learn_date
                if learn_date == current_date or learn_date == current_date - timedelta(days=streak):
                    streak += 1
                    current_date = learn_date
                else:
                    break
            
            return streak
            
        except Exception as e:
            logger.error(f"计算学习连续天数失败: {str(e)}")
            return 0
