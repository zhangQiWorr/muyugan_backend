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
router = APIRouter(prefix="/learning", tags=["学习管理"])

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

class EnrolledCourseResponse(BaseModel):
    """已报名课程响应"""
    course_id: str
    title: str
    subtitle: Optional[str]
    description: Optional[str]
    cover_image: Optional[str]
    duration: int  # 课程总时长（秒）
    lesson_count: int  # 课时总数
    difficulty_level: str
    is_featured: bool
    is_hot: bool
    price: float
    original_price: Optional[float]
    enrolled_at: datetime
    last_watch_at: Optional[datetime]
    course_progress: dict  # 课程进度信息
    category: Optional[dict]  # 课程分类信息

class EnrolledCoursesResponse(BaseModel):
    """已报名课程列表响应"""
    courses: List[EnrolledCourseResponse]
    total: int
    page: int
    size: int
    pages: int

class DailyLearningData(BaseModel):
    """每日学习数据"""
    date: str  # 日期 (YYYY-MM-DD)
    duration: int  # 学习时长（秒）
    formatted_duration: str  # 格式化后的时长
    day_of_week: Optional[str] = None  # 星期几（周统计用）
    day_of_month: Optional[int] = None  # 月中的第几天（月统计用）

class MonthlyLearningData(BaseModel):
    """每月学习数据"""
    month: int  # 月份 (1-12)
    month_name: str  # 月份名称
    duration: int  # 学习时长（秒）
    formatted_duration: str  # 格式化后的时长

class LearningTimeStatsResponse(BaseModel):
    """学习时间统计响应"""
    period: str  # 统计周期 ('week', 'month', 'year')
    period_name: str  # 周期名称
    total_duration: int  # 总学习时长（秒）
    formatted_total_duration: str  # 格式化后的总时长
    start_date: Optional[str] = None  # 开始日期
    end_date: Optional[str] = None  # 结束日期
    year: Optional[int] = None  # 年份（年统计用）
    daily_data: Optional[List[DailyLearningData]] = None  # 每日数据（周、月统计用）
    monthly_data: Optional[List[MonthlyLearningData]] = None  # 每月数据（年统计用）

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
        course_progress_percentage = (completed_lessons / len(lessons)) * 100 if len(lessons) > 0 else 0.0
        
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

@router.get("/courses/enrolled", response_model=EnrolledCoursesResponse)
async def get_enrolled_courses(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页数量"),
    user_id: Optional[str] = Query(None, description="用户ID（管理员可指定其他用户）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户已报名的课程列表及其学习进度
    
    返回用户已报名的所有课程，包含每个课程的详细信息和学习进度
    
    Args:
        page: 页码，默认为1
        size: 每页数量，默认为10，最大50
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
        
        # 导入必要的模型
        from models.course import Course, CourseEnrollment, CourseLesson, CourseCategory
        from sqlalchemy import desc, func as sql_func
        
        # 查询用户已报名的课程
        enrolled_courses_query = db.query(
            CourseEnrollment,
            Course,
            CourseCategory
        ).join(
            Course, CourseEnrollment.course_id == Course.id
        ).outerjoin(
            CourseCategory, Course.category_id == CourseCategory.id
        ).filter(
            CourseEnrollment.user_id == target_user_id,
            CourseEnrollment.is_active == True,
            Course.status == "published"  # 只返回已发布的课程
        ).order_by(desc(CourseEnrollment.enrolled_at))
        
        # 获取总数
        total = enrolled_courses_query.count()
        
        # 分页
        enrolled_courses = enrolled_courses_query.offset((page - 1) * size).limit(size).all()
        
        learning_service = LearningService(db)
        enrolled_courses_list = []
        
        for enrollment, course, category in enrolled_courses:
            # 获取课程课时信息
            lessons = db.query(CourseLesson).filter(
                CourseLesson.course_id == course.id,
                CourseLesson.is_active == True
            ).order_by(CourseLesson.sort_order.asc()).all()
            
            # 计算课程总时长
            total_duration = sum(lesson.duration for lesson in lessons) if lessons else 0
            
            # 计算课程学习进度
            course_progress = learning_service.calculate_course_progress(target_user_id, course.id)
            
            # 获取最后观看时间
            last_watch_at = None
            try:
                from models.course import LearningProgress
                last_progress = db.query(LearningProgress).filter(
                    and_(
                        LearningProgress.user_id == target_user_id,
                        LearningProgress.course_id == course.id
                    )
                ).order_by(desc(LearningProgress.last_watched_at)).first()
                if last_progress:
                    last_watch_at = last_progress.last_watched_at
            except Exception as e:
                logger.warning(f"获取最后观看时间失败: {e}")
            
            # 构建课程分类信息
            category_info = None
            if category:
                category_info = {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                    "icon": category.icon
                }
            
            # 构建课程进度信息
            progress_info = {
                "progress_percentage": course_progress.get('progress_percentage', 0.0),
                "total_watch_duration": course_progress.get('total_watch_duration', 0),
                "total_duration": total_duration,
                "completed_lessons": course_progress.get('completed_lessons', 0),
                "total_lessons": len(lessons),
                "is_completed": course_progress.get('progress_percentage', 0.0) >= 100.0
            }
            
            enrolled_course = EnrolledCourseResponse(
                course_id=course.id,
                title=course.title,
                subtitle=course.subtitle,
                description=course.description,
                cover_image=course.cover_image,
                duration=total_duration,
                lesson_count=len(lessons),
                difficulty_level=course.difficulty_level,
                is_featured=course.is_featured,
                is_hot=course.is_hot,
                price=course.price,
                original_price=course.original_price,
                enrolled_at=enrollment.enrolled_at,
                last_watch_at=last_watch_at,
                course_progress=progress_info,
                category=category_info
            )
            
            enrolled_courses_list.append(enrolled_course)
        
        return EnrolledCoursesResponse(
            courses=enrolled_courses_list,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取已报名课程失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取已报名课程失败")

@router.get("/time-statistics", response_model=LearningTimeStatsResponse)
async def get_learning_time_statistics(
    period: str = Query(..., description="统计周期：week(周)、month(月)、year(年)"),
    user_id: Optional[str] = Query(None, description="用户ID（管理员可指定其他用户）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户学习时间统计
    
    根据指定周期返回用户的学习时间统计信息：
    - week: 返回当前周每日学习时间
    - month: 返回当前月份每天学习时间  
    - year: 返回当前年每月学习时间
    
    Args:
        period: 统计周期，支持 'week'、'month'、'year'
        user_id: 用户ID，管理员可指定其他用户，普通用户只能查看自己的数据
        current_user: 当前用户
    """
    try:
        # 验证统计周期参数
        if period not in ['week', 'month', 'year']:
            raise HTTPException(status_code=400, detail="统计周期参数错误，支持: week, month, year")
        
        # 确定要查询的用户ID
        target_user_id = user_id if user_id else current_user.id
        
        # 权限检查：如果不是管理员且查询的不是自己的数据，则拒绝访问
        if target_user_id != current_user.id:
            from utils.auth_utils import check_admin_permission
            check_admin_permission(current_user)
        
        learning_service = LearningService(db)
        stats = learning_service.get_learning_time_statistics(target_user_id, period)
        
        # 根据统计周期构建响应数据
        if period == 'week':
            daily_data = [
                DailyLearningData(
                    date=day['date'],
                    duration=day['duration'],
                    formatted_duration=day['formatted_duration'],
                    day_of_week=day['day_of_week']
                ) for day in stats['daily_data']
            ]
            
            return LearningTimeStatsResponse(
                period=stats['period'],
                period_name=stats['period_name'],
                total_duration=stats['total_duration'],
                formatted_total_duration=stats['formatted_total_duration'],
                start_date=stats['start_date'],
                end_date=stats['end_date'],
                daily_data=daily_data
            )
            
        elif period == 'month':
            daily_data = [
                DailyLearningData(
                    date=day['date'],
                    duration=day['duration'],
                    formatted_duration=day['formatted_duration'],
                    day_of_month=day['day_of_month']
                ) for day in stats['daily_data']
            ]
            
            return LearningTimeStatsResponse(
                period=stats['period'],
                period_name=stats['period_name'],
                total_duration=stats['total_duration'],
                formatted_total_duration=stats['formatted_total_duration'],
                start_date=stats['start_date'],
                end_date=stats['end_date'],
                daily_data=daily_data
            )
            
        elif period == 'year':
            monthly_data = [
                MonthlyLearningData(
                    month=month['month'],
                    month_name=month['month_name'],
                    duration=month['duration'],
                    formatted_duration=month['formatted_duration']
                ) for month in stats['monthly_data']
            ]
            
            return LearningTimeStatsResponse(
                period=stats['period'],
                period_name=stats['period_name'],
                total_duration=stats['total_duration'],
                formatted_total_duration=stats['formatted_total_duration'],
                year=stats['year'],
                monthly_data=monthly_data
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取学习时间统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取学习时间统计失败")