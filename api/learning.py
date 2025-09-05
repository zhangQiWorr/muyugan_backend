"""
学习管理相关API
包含课程报名、学习进度、评价、收藏等
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from models import get_db
from models.user import User
from models.course import Course, CourseLesson, CourseEnrollment, LearningProgress, CourseReview, CourseFavorite
from models.schemas import (
    LearningProgressUpdate, LearningProgressResponse,
    CourseEnrollmentResponse, CourseReviewCreate, CourseReviewResponse,
    CourseFavoriteCreate, CourseFavoriteResponse,
    SuccessResponse
)
from services.logger import get_logger
from utils.auth_utils import get_current_user

logger = get_logger("learning_api")
router = APIRouter(prefix="/learning", tags=["学习管理"])


# 课程报名
@router.post("/enroll/{course_id}", response_model=CourseEnrollmentResponse)
async def enroll_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """报名课程"""
    # 检查课程是否存在
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.status == "published"
    ).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在或未发布"
        )
    
    # 检查是否已报名
    existing_enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.is_active == True
    ).first()
    
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已报名此课程"
        )
    
    # 创建报名记录
    enrollment = CourseEnrollment(
        user_id=current_user.id,
        course_id=course_id
    )
    db.add(enrollment)
    
    # 更新课程报名人数
    course.enroll_count += 1
    
    db.commit()
    db.refresh(enrollment)
    
    # 加载课程信息
    enrollment.course = course
    
    return enrollment


@router.get("/enrollments", response_model=List[CourseEnrollmentResponse])
async def get_my_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的报名课程"""
    enrollments = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.is_active == True
    ).order_by(CourseEnrollment.enrolled_at.desc()).all()
    
    # 加载课程信息
    for enrollment in enrollments:
        enrollment.course = db.query(Course).filter(Course.id == enrollment.course_id).first()
    
    return enrollments


# 学习进度
@router.post("/progress", response_model=LearningProgressResponse)
async def update_learning_progress(
    progress_data: LearningProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新学习进度"""
    # 检查是否已报名课程
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.course_id == progress_data.course_id,
        CourseEnrollment.is_active == True
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先报名课程"
        )
    
    # 检查课时是否存在
    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == progress_data.lesson_id,
        CourseLesson.course_id == progress_data.course_id
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课时不存在"
        )
    
    # 查找或创建学习进度记录
    progress = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id,
        LearningProgress.course_id == progress_data.course_id,
        LearningProgress.lesson_id == progress_data.lesson_id,
        LearningProgress.enrollment_id == enrollment.id
    ).first()
    
    if not progress:
        progress = LearningProgress(
            user_id=current_user.id,
            course_id=progress_data.course_id,
            lesson_id=progress_data.lesson_id,
            enrollment_id=enrollment.id,
            total_duration=lesson.duration * 60  # 转换为秒
        )
        db.add(progress)
    
    # 更新进度信息
    progress.watch_duration = progress_data.watch_duration
    progress.is_completed = progress_data.is_completed
    progress.last_watched_at = datetime.utcnow()
    
    if progress_data.is_completed and not progress.completed_at:
        progress.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(progress)
    
    return progress


@router.get("/progress/{course_id}", response_model=List[LearningProgressResponse])
async def get_course_progress(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程学习进度"""
    # 检查是否已报名课程
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.is_active == True
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先报名课程"
        )
    
    progress_records = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id,
        LearningProgress.course_id == course_id,
        LearningProgress.enrollment_id == enrollment.id
    ).all()
    
    return progress_records


# 课程评价
@router.post("/reviews", response_model=CourseReviewResponse)
async def create_course_review(
    review_data: CourseReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课程评价"""
    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == review_data.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    # 检查是否已评价
    existing_review = db.query(CourseReview).filter(
        CourseReview.user_id == current_user.id,
        CourseReview.course_id == review_data.course_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已评价过此课程"
        )
    
    # 检查是否已报名课程
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.course_id == review_data.course_id,
        CourseEnrollment.is_active == True
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先报名课程"
        )
    
    # 创建评价
    review = CourseReview(
        user_id=current_user.id,
        course_id=review_data.course_id,
        rating=review_data.rating,
        title=review_data.title,
        content=review_data.content,
        is_verified=True  # 已报名用户评价自动验证
    )
    db.add(review)
    
    # 更新课程评分
    course.rating_count += 1
    # 重新计算平均评分
    total_rating = db.query(func.sum(CourseReview.rating)).filter(
        CourseReview.course_id == review_data.course_id,
        CourseReview.is_verified == True
    ).scalar()
    course.rating = total_rating / course.rating_count if course.rating_count > 0 else 0
    
    db.commit()
    db.refresh(review)
    
    # 加载用户信息
    review.user = current_user
    
    return review


@router.get("/reviews/{course_id}", response_model=List[CourseReviewResponse])
async def get_course_reviews(
    course_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取课程评价列表"""
    query = db.query(CourseReview).filter(
        CourseReview.course_id == course_id,
        CourseReview.is_public == True
    )
    
    total = query.count()
    reviews = query.order_by(CourseReview.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    # 加载用户信息
    for review in reviews:
        review.user = db.query(User).filter(User.id == review.user_id).first()
    
    return reviews


# 课程收藏
@router.post("/favorites", response_model=CourseFavoriteResponse)
async def add_course_favorite(
    favorite_data: CourseFavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """收藏课程"""
    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == favorite_data.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    # 检查是否已收藏
    existing_favorite = db.query(CourseFavorite).filter(
        CourseFavorite.user_id == current_user.id,
        CourseFavorite.course_id == favorite_data.course_id
    ).first()
    
    if existing_favorite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已收藏此课程"
        )
    
    # 创建收藏记录
    favorite = CourseFavorite(
        user_id=current_user.id,
        course_id=favorite_data.course_id
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    # 加载课程信息
    favorite.course = course
    
    return favorite


@router.get("/favorites", response_model=List[CourseFavoriteResponse])
async def get_my_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的收藏"""
    favorites = db.query(CourseFavorite).filter(
        CourseFavorite.user_id == current_user.id
    ).order_by(CourseFavorite.created_at.desc()).all()
    
    # 加载课程信息
    for favorite in favorites:
        favorite.course = db.query(Course).filter(Course.id == favorite.course_id).first()
    
    return favorites


@router.delete("/favorites/{course_id}", response_model=SuccessResponse)
async def remove_course_favorite(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消收藏"""
    favorite = db.query(CourseFavorite).filter(
        CourseFavorite.user_id == current_user.id,
        CourseFavorite.course_id == course_id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏记录不存在"
        )
    
    db.delete(favorite)
    db.commit()
    
    return SuccessResponse(message="取消收藏成功")


# 学习统计
@router.get("/statistics")
async def get_learning_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取学习统计"""
    # 报名课程数
    enrollment_count = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.is_active == True
    ).count()
    
    # 完成课程数
    completed_courses = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.is_active == True,
        CourseEnrollment.completed_at.isnot(None)
    ).count()
    
    # 总学习时长（分钟）
    total_duration = db.query(func.sum(LearningProgress.watch_duration)).filter(
        LearningProgress.user_id == current_user.id
    ).scalar() or 0
    total_duration = total_duration // 60  # 转换为分钟
    
    # 今日学习时长（分钟）
    today = datetime.utcnow().date()
    today_duration = db.query(func.sum(LearningProgress.watch_duration)).filter(
        LearningProgress.user_id == current_user.id,
        func.date(LearningProgress.last_watched_at) == today
    ).scalar() or 0
    today_duration = today_duration // 60  # 转换为分钟
    
    # 收藏课程数
    favorite_count = db.query(CourseFavorite).filter(
        CourseFavorite.user_id == current_user.id
    ).count()
    
    return {
        "enrollment_count": enrollment_count,
        "completed_courses": completed_courses,
        "total_duration": total_duration,
        "today_duration": today_duration,
        "favorite_count": favorite_count
    }


# 学习证书
@router.get("/certificate/{course_id}")
async def get_course_certificate(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程完成证书"""
    # 检查是否已报名并完成课程
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.user_id == current_user.id,
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.is_active == True
    ).first()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先报名课程"
        )
    
    if not enrollment.completed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="课程尚未完成"
        )
    
    # 获取课程信息
    course = db.query(Course).filter(Course.id == course_id).first()
    
    # 生成证书信息
    certificate = {
        "certificate_id": f"CERT-{course_id}-{current_user.id}",
        "student_name": current_user.full_name or current_user.username,
        "course_name": course.title,
        "completion_date": enrollment.completed_at.isoformat(),
        "progress_percentage": enrollment.progress_percentage,
        "issued_date": datetime.utcnow().isoformat()
    }
    
    return certificate
