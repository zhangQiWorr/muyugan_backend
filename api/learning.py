"""
学习相关API接口
处理用户学习记录、进度跟踪等功能
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import datetime

from models import get_db
from models.user import User
from utils.auth_utils import get_current_user
from services.learning_service import LearningService
from services.logger import get_logger

logger = get_logger("learning_api")
router = APIRouter(prefix="/api/learning", tags=["学习管理"])

# 在文件顶部添加常量导入
from services.learning_service import LESSON_COMPLETION_THRESHOLD

# 数据模型
class MediaProgressRequest(BaseModel):
    """媒体观看进度请求"""
    media_id: str
    watch_duration: int  # 已观看时长（秒）
    total_duration: int  # 总时长（秒）

class LessonProgressRequest(BaseModel):
    """课时学习进度请求"""
    lesson_id: str
    watch_duration: int  # 已观看时长（秒）
    total_duration: int  # 总时长（秒）

class LessonProgressResponse(BaseModel):
    """课时学习进度响应"""
    lesson_id: str
    is_completed: bool
    watch_duration: int
    total_duration: int
    progress_percentage: float
    last_watched_at: datetime
    # 扩展字段，用于课程课时进度接口
    title: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    completed_media: Optional[int] = None
    total_media: Optional[int] = None

class RecentCourseResponse(BaseModel):
    """最近学习课程响应"""
    course_id: str
    title: str
    subtitle: Optional[str]
    cover_image: Optional[str]
    duration: int
    lesson_count: int
    difficulty_level: str
    is_featured: bool
    is_hot: bool
    last_watch_at: str
    course_progress: dict
    last_lesson: dict

class LearningStatsResponse(BaseModel):
    """学习统计响应"""
    total_learning_time: int  # 总学习时长（秒）
    completed_lessons: int    # 已完成课时数
    completed_courses: int    # 已完成课程数
    learning_courses: int     # 正在学习的课程数
    recent_learning_time: int # 最近7天学习时长（秒）
    learning_streak_days: int # 学习连续天数
    today_duration: int       # 今日学习时长（秒）
    enrollment_count: int     # 用户订阅课程数量

class CourseLessonsProgressResponse(BaseModel):
    """课程课时进度响应"""
    course_id: str
    course_title: str
    total_lessons: int
    completed_lessons: int
    total_duration: int  # 课程总时长（秒）
    total_watch_duration: int  # 总观看时长（秒）
    course_progress_percentage: float  # 课程整体进度
    lessons: List[LessonProgressResponse]

@router.post("/lesson/start")
async def start_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """开始学习课时
    
    记录用户开始学习某个课时
    注意：此接口主要用于内部调用，媒体文件播放时会自动调用此接口
    """
    try:
        learning_service = LearningService(db)
        progress = learning_service.record_lesson_start(current_user.id, lesson_id)
        
        logger.info(f"用户 {current_user.username} 开始学习课时 {lesson_id}")
        
        return {
            "message": "开始学习成功",
            "lesson_id": lesson_id,
            "started_at": progress.started_at.isoformat()
        }
    except Exception as e:
        logger.error(f"开始学习失败: {str(e)}")
        raise HTTPException(status_code=500, detail="开始学习失败")

@router.post("/media/progress")
async def update_media_progress(
    progress_data: MediaProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新媒体观看进度
    
    记录用户观看媒体文件的进度，并自动更新相关课时的学习进度
    注意：此接口主要用于内部调用，媒体文件播放事件上报时会自动调用此接口
    """
    try:
        learning_service = LearningService(db)
        
        # 记录媒体观看进度
        play_record = learning_service.record_media_progress(
            current_user.id,
            progress_data.media_id,
            progress_data.watch_duration,
            progress_data.total_duration
        )
        
        # 获取媒体文件信息，找到关联的课时
        from models.media import Media
        media = db.query(Media).filter(Media.id == progress_data.media_id).first()
        
        if media and media.lesson_id:
            # 更新课时学习进度
            lesson_progress = learning_service.update_lesson_progress(
                current_user.id,
                media.lesson_id
            )
            
            # 计算课时进度详情
            lesson_progress_detail = learning_service.calculate_lesson_progress(
                current_user.id,
                media.lesson_id
            )
            
            return {
                "message": "媒体观看进度更新成功",
                "media_id": progress_data.media_id,
                "media_progress": {
                    "progress_percentage": round(play_record.progress * 100, 1),
                    "watch_duration": play_record.effective_duration,
                    "total_duration": progress_data.total_duration,
                    "is_completed": play_record.completed
                },
                "lesson_progress": {
                    "lesson_id": media.lesson_id,
                    "progress_percentage": lesson_progress_detail['progress_percentage'],
                    "completed_media": lesson_progress_detail['completed_media'],
                    "total_media": lesson_progress_detail['total_media'],
                    "is_completed": lesson_progress.is_completed
                }
            }
        else:
            return {
                "message": "媒体观看进度更新成功",
                "media_id": progress_data.media_id,
                "media_progress": {
                    "progress_percentage": round(play_record.progress * 100, 1),
                    "watch_duration": play_record.effective_duration,
                    "total_duration": progress_data.total_duration,
                    "is_completed": play_record.completed
                }
            }
    except Exception as e:
        logger.error(f"更新媒体观看进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新媒体观看进度失败")

@router.post("/lesson/progress", response_model=LessonProgressResponse)
async def update_lesson_progress(
    progress_data: LessonProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新课时学习进度
    
    记录用户的学习进度，包括观看时长等
    注意：此接口主要用于内部调用，媒体文件播放事件上报时会自动调用此接口
    """
    try:
        learning_service = LearningService(db)
        
        # 更新课时进度（基于媒体文件观看进度）
        progress = learning_service.update_lesson_progress(
            current_user.id,
            progress_data.lesson_id
        )
        
        # 计算课时进度详情
        lesson_progress_detail = learning_service.calculate_lesson_progress(
            current_user.id,
            progress_data.lesson_id
        )
        
        return LessonProgressResponse(
            lesson_id=progress.lesson_id,
            is_completed=progress.is_completed,
            watch_duration=progress.watch_duration,
            total_duration=progress.total_duration,
            progress_percentage=lesson_progress_detail['progress_percentage'],
            last_watched_at=progress.last_watched_at
        )
    except Exception as e:
        logger.error(f"更新学习进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新学习进度失败")

@router.get("/courses/recent", response_model=List[RecentCourseResponse])
async def get_recent_courses(
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    user_id: Optional[str] = Query(None, description="用户ID（管理员可指定其他用户）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户最近学习的课程列表
    
    返回用户最近学习的课程，按最后学习时间排序
    
    Args:
        limit: 返回数量限制
        user_id: 用户ID，管理员可指定其他用户，普通用户只能查看自己的数据
        current_user: 当前用户
    """
    try:
        # 确定要查询的用户ID
        target_user_id = user_id if user_id else current_user.id
        
        # 权限检查：如果不是管理员且查询的不是自己的数据，则拒绝访问
        if target_user_id != current_user.id:
            from utils.auth_utils import check_admin_permission
            check_admin_permission(current_user)
        
        learning_service = LearningService(db)
        recent_courses = learning_service.get_user_recent_courses(target_user_id, limit)
        
        return [RecentCourseResponse(**course) for course in recent_courses]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最近学习课程失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取最近学习课程失败")

@router.get("/statistics", response_model=LearningStatsResponse)
async def get_learning_statistics(
    user_id: Optional[str] = Query(None, description="用户ID（管理员可指定其他用户）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户学习统计信息
    
    返回用户的学习统计数据，包括总学习时长、完成课时数等
    
    Args:
        user_id: 用户ID，管理员可指定其他用户，普通用户只能查看自己的数据
        current_user: 当前用户
    """
    try:
        # 确定要查询的用户ID
        target_user_id = user_id if user_id else current_user.id
        
        # 权限检查：如果不是管理员且查询的不是自己的数据，则拒绝访问
        if target_user_id != current_user.id:
            from utils.auth_utils import check_admin_permission
            check_admin_permission(current_user)
        
        learning_service = LearningService(db)
        stats = learning_service.get_user_learning_statistics(target_user_id)
        
        return LearningStatsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学习统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取学习统计失败")

@router.get("/courses/continue")
async def get_continue_learning_courses(
    limit: int = Query(5, ge=1, le=20, description="返回数量限制"),
    user_id: Optional[str] = Query(None, description="用户ID（管理员可指定其他用户）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取继续学习的课程列表
    
    返回用户未完成但已开始学习的课程
    
    Args:
        limit: 返回数量限制
        user_id: 用户ID，管理员可指定其他用户，普通用户只能查看自己的数据
        current_user: 当前用户
    """
    try:
        # 确定要查询的用户ID
        target_user_id = user_id if user_id else current_user.id
        
        # 权限检查：如果不是管理员且查询的不是自己的数据，则拒绝访问
        if target_user_id != current_user.id:
            from utils.auth_utils import check_admin_permission
            check_admin_permission(current_user)
        
        learning_service = LearningService(db)
        recent_courses = learning_service.get_user_recent_courses(target_user_id, limit * 2)
        
        # 过滤出未完成的课程（进度 < 100%）
        continue_courses = []
        for course in recent_courses:
            if course['course_progress']['progress_percentage'] < 100.0:
                continue_courses.append(course)
                if len(continue_courses) >= limit:
                    break
        
        return {
            "courses": continue_courses,
            "total": len(continue_courses)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取继续学习课程失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取继续学习课程失败")

@router.get("/courses/completed")
async def get_completed_courses(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页数量"),
    user_id: Optional[str] = Query(None, description="用户ID（管理员可指定其他用户）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取已完成的课程列表
    
    返回用户已完成学习的课程
    
    Args:
        page: 页码
        size: 每页数量
        user_id: 用户ID，管理员可指定其他用户，普通用户只能查看自己的数据
        current_user: 当前用户
    """
    try:
        # 确定要查询的用户ID
        target_user_id = user_id if user_id else current_user.id
        
        # 权限检查：如果不是管理员且查询的不是自己的数据，则拒绝访问
        if target_user_id != current_user.id:
            from utils.auth_utils import check_admin_permission
            check_admin_permission(current_user)
        
        learning_service = LearningService(db)
        recent_courses = learning_service.get_user_recent_courses(target_user_id, 100)  # 获取更多数据用于过滤
        
        # 过滤出已完成的课程（进度 = 100%）
        completed_courses = [
            course for course in recent_courses 
            if course['course_progress']['progress_percentage'] >= 100.0
        ]
        
        # 分页
        total = len(completed_courses)
        start = (page - 1) * size
        end = start + size
        paginated_courses = completed_courses[start:end]
        
        return {
            "courses": paginated_courses,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取已完成课程失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取已完成课程失败")

@router.get("/courses/{course_id}/lessons/statistics", response_model=CourseLessonsProgressResponse)
async def get_course_lessons_progress(
    course_id: str,
    user_id: Optional[str] = Query(None, description="用户ID（管理员可指定其他用户）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户某个课程下所有课时的学习进度情况
    
    返回指定课程下所有课时的详细学习进度信息
    
    Args:
        course_id: 课程ID
        user_id: 用户ID，管理员可指定其他用户，普通用户只能查看自己的数据
        current_user: 当前用户
    """
    try:
        # 确定要查询的用户ID
        target_user_id = user_id if user_id else current_user.id
        
        # 权限检查：如果不是管理员且查询的不是自己的数据，则拒绝访问
        if target_user_id != current_user.id:
            from utils.auth_utils import check_admin_permission
            check_admin_permission(current_user)
        
        learning_service = LearningService(db)
        
        # 获取课程信息
        from models.course import Course
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        # 获取课程下所有课时
        from models.course import CourseLesson
        lessons = db.query(CourseLesson).filter(
            CourseLesson.course_id == course_id,
            CourseLesson.is_active == True
        ).order_by(CourseLesson.sort_order.asc()).all()
        
        if not lessons:
            return CourseLessonsProgressResponse(
                course_id=course_id,
                course_title=course.title,
                total_lessons=0,
                completed_lessons=0,
                total_duration=0,
                total_watch_duration=0,
                course_progress_percentage=0.0,
                lessons=[]
            )
        
        # 计算每个课时的进度
        lesson_progress_details = []
        total_watch_duration = 0
        completed_lessons = 0
        
        for lesson in lessons:
            # 计算课时进度
            lesson_progress = learning_service.calculate_lesson_progress(target_user_id, lesson.id)

            print("lesson_progress:", lesson_progress)


            
            # 检查课时是否完成
            is_completed = (lesson_progress['progress_percentage'] >= LESSON_COMPLETION_THRESHOLD or
                          lesson_progress['completed_media'] == lesson_progress['total_media'])
            
            if is_completed:
                completed_lessons += 1
            
            total_watch_duration += lesson_progress['total_watch_duration']
            
            # 获取最后观看时间
            last_watched_at = None
            try:
                from models.course import LearningProgress
                learning_progress = db.query(LearningProgress).filter(
                    and_(
                        LearningProgress.user_id == target_user_id,
                        LearningProgress.lesson_id == lesson.id
                    )
                ).first()
                if learning_progress:
                    last_watched_at = learning_progress.last_watched_at
            except Exception as e:
                logger.warning(f"获取最后观看时间失败: {e}")
            
            lesson_detail = LessonProgressResponse(
                lesson_id=lesson.id,
                is_completed=is_completed,
                watch_duration=int(lesson_progress['total_watch_duration']),
                total_duration=lesson.duration,
                progress_percentage=lesson_progress['progress_percentage'],
                last_watched_at=last_watched_at or datetime.now(),
                title=lesson.title,
                description=lesson.description,
                order_index=lesson.sort_order,
                completed_media=lesson_progress['completed_media'],
                total_media=lesson_progress['total_media']
            )
            lesson_progress_details.append(lesson_detail)
        
        # 计算课程总时长
        total_duration = sum(lesson.duration for lesson in lessons)
        
        # 计算课程整体进度
        course_progress_percentage = (total_watch_duration / total_duration) * 100 if total_duration > 0 else 0.0
        
        return CourseLessonsProgressResponse(
            course_id=course_id,
            course_title=course.title,
            total_lessons=len(lessons),
            completed_lessons=completed_lessons,
            total_duration=total_duration,
            total_watch_duration=int(total_watch_duration),
            course_progress_percentage=min(round(course_progress_percentage, 1), 100),
            lessons=lesson_progress_details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取课程课时进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取课程课时进度失败")