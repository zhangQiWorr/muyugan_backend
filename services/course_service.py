"""
课程服务
处理课程相关的业务逻辑
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.course import Course, CourseLesson
from services.logger import get_logger

logger = get_logger("course_service")


class CourseService:
    """课程服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def update_course_duration(self, course_id: str) -> Optional[Course]:
        """
        更新课程总时长（基于所有课时的时长）
        
        Args:
            course_id: 课程ID
            
        Returns:
            Course: 更新后的课程对象，如果课程不存在则返回None
        """
        try:
            # 获取课程
            course = self.db.query(Course).filter(Course.id == course_id).first()
            if not course:
                logger.warning(f"课程不存在: {course_id}")
                return None
            
            # 计算所有活跃课时的总时长
            total_duration = self.db.query(
                func.sum(CourseLesson.duration)
            ).filter(
                CourseLesson.course_id == course_id,
                CourseLesson.is_active == True
            ).scalar() or 0
            
            # 计算课时数量
            lesson_count = self.db.query(CourseLesson).filter(
                CourseLesson.course_id == course_id,
                CourseLesson.is_active == True
            ).count()
            
            # 更新课程信息
            course.duration = int(total_duration)
            course.lesson_count = lesson_count
            
            self.db.commit()
            
            logger.info(f"更新课程 {course_id} 时长: {total_duration}秒, 课时数: {lesson_count}")
            return course
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新课程时长失败: {str(e)}")
            raise
    
    def create_lesson(self, course_id: str, title: str, description: str = None,
                     duration: int = 0, sort_order: int = 0, 
                     is_free: bool = False, is_active: bool = True) -> CourseLesson:
        """
        创建课时并自动更新课程时长
        
        Args:
            course_id: 课程ID
            title: 课时标题
            description: 课时描述
            duration: 课时时长（秒）
            sort_order: 排序
            is_free: 是否免费
            is_active: 是否活跃
            
        Returns:
            CourseLesson: 创建的课时对象
        """
        try:
            # 创建课时
            lesson = CourseLesson(
                course_id=course_id,
                title=title,
                description=description,
                duration=duration,
                sort_order=sort_order,
                is_free=is_free,
                is_active=is_active
            )
            
            self.db.add(lesson)
            self.db.flush()  # 获取ID
            
            # 更新课程时长
            self.update_course_duration(course_id)
            
            logger.info(f"创建课时: {title} (时长: {duration}秒)")
            return lesson
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建课时失败: {str(e)}")
            raise
    
    def update_lesson(self, lesson_id: str, title: str = None, description: str = None,
                     duration: int = None, sort_order: int = None,
                     is_free: bool = None, is_active: bool = None) -> Optional[CourseLesson]:
        """
        更新课时并自动更新课程时长
        
        Args:
            lesson_id: 课时ID
            title: 课时标题
            description: 课时描述
            duration: 课时时长（秒）
            sort_order: 排序
            is_free: 是否免费
            is_active: 是否活跃
            
        Returns:
            CourseLesson: 更新后的课时对象，如果课时不存在则返回None
        """
        try:
            # 获取课时
            lesson = self.db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
            if not lesson:
                logger.warning(f"课时不存在: {lesson_id}")
                return None
            
            # 记录原始时长，用于判断是否需要更新课程时长
            original_duration = lesson.duration
            original_is_active = lesson.is_active
            
            # 更新课时信息
            if title is not None:
                lesson.title = title
            if description is not None:
                lesson.description = description
            if duration is not None:
                lesson.duration = duration
            if sort_order is not None:
                lesson.sort_order = sort_order
            if is_free is not None:
                lesson.is_free = is_free
            if is_active is not None:
                lesson.is_active = is_active
            
            # 如果时长或活跃状态发生变化，更新课程时长
            if (duration is not None and duration != original_duration) or \
               (is_active is not None and is_active != original_is_active):
                self.update_course_duration(lesson.course_id)
            
            self.db.commit()
            
            logger.info(f"更新课时: {lesson.title} (时长: {lesson.duration}秒)")
            return lesson
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新课时失败: {str(e)}")
            raise
    
    def delete_lesson(self, lesson_id: str) -> bool:
        """
        删除课时并自动更新课程时长
        
        Args:
            lesson_id: 课时ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取课时
            lesson = self.db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
            if not lesson:
                logger.warning(f"课时不存在: {lesson_id}")
                return False
            
            course_id = lesson.course_id
            
            # 删除课时
            self.db.delete(lesson)
            
            # 更新课程时长
            self.update_course_duration(course_id)
            
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除课时失败: {str(e)}")
            raise
    
    def get_course_duration_info(self, course_id: str) -> dict:
        """
        获取课程时长详细信息
        
        Args:
            course_id: 课程ID
            
        Returns:
            dict: 课程时长信息
        """
        try:
            # 获取课程
            course = self.db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return {
                    'course_id': course_id,
                    'total_duration': 0,
                    'lesson_count': 0,
                    'lessons': []
                }
            
            # 获取所有课时信息
            lessons = self.db.query(CourseLesson).filter(
                CourseLesson.course_id == course_id,
                CourseLesson.is_active == True
            ).order_by(CourseLesson.sort_order).all()
            
            # 计算总时长
            total_duration = sum(lesson.duration for lesson in lessons)
            
            return {
                'course_id': course_id,
                'course_title': course.title,
                'total_duration': total_duration,
                'lesson_count': len(lessons),
                'lessons': [
                    {
                        'lesson_id': lesson.id,
                        'title': lesson.title,
                        'duration': lesson.duration,
                        'is_free': lesson.is_free,
                        'sort_order': lesson.sort_order
                    }
                    for lesson in lessons
                ]
            }
            
        except Exception as e:
            logger.error(f"获取课程时长信息失败: {str(e)}")
            return {
                'course_id': course_id,
                'total_duration': 0,
                'lesson_count': 0,
                'lessons': []
            }
