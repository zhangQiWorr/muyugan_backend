"""
学习相关API接口
处理用户学习记录、进度跟踪等功能
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from models import get_db
from models.user import User
from utils.auth_utils import get_current_user
from services.learning_service import LearningService
from services.logger import get_logger

logger = get_logger("learning_api")
router = APIRouter(prefix="/api/learning", tags=["学习管理"])

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
    last_learned_at: str
    course_progress: dict
    last_lesson: dict

class LearningStatsResponse(BaseModel):
    """学习统计响应"""
    total_learning_time: int  # 总学习时长（分钟）
    completed_lessons: int    # 已完成课时数
    learning_courses: int     # 正在学习的课程数
    recent_learning_time: int # 最近7天学习时长（分钟）
    learning_streak_days: int # 学习连续天数

@router.post("/lesson/start")
async def start_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """开始学习课时
    
    记录用户开始学习某个课时
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户最近学习的课程列表
    
    返回用户最近学习的课程，按最后学习时间排序
    """
    try:
        learning_service = LearningService(db)
        recent_courses = learning_service.get_user_recent_courses(current_user.id, limit)
        
        return [RecentCourseResponse(**course) for course in recent_courses]
    except Exception as e:
        logger.error(f"获取最近学习课程失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取最近学习课程失败")

@router.get("/statistics", response_model=LearningStatsResponse)
async def get_learning_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户学习统计信息
    
    返回用户的学习统计数据，包括总学习时长、完成课时数等
    """
    try:
        learning_service = LearningService(db)
        stats = learning_service.get_user_learning_statistics(current_user.id)
        
        return LearningStatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取学习统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取学习统计失败")

@router.get("/courses/continue")
async def get_continue_learning_courses(
    limit: int = Query(5, ge=1, le=20, description="返回数量限制"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取继续学习的课程列表
    
    返回用户未完成但已开始学习的课程
    """
    try:
        learning_service = LearningService(db)
        recent_courses = learning_service.get_user_recent_courses(current_user.id, limit * 2)
        
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
    except Exception as e:
        logger.error(f"获取继续学习课程失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取继续学习课程失败")

@router.get("/courses/completed")
async def get_completed_courses(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取已完成的课程列表
    
    返回用户已完成学习的课程
    """
    try:
        learning_service = LearningService(db)
        recent_courses = learning_service.get_user_recent_courses(current_user.id, 100)  # 获取更多数据用于过滤
        
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
    except Exception as e:
        logger.error(f"获取已完成课程失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取已完成课程失败")