"""
课程管理相关API
包含课程的CRUD操作、分类管理、课时管理等
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional
import uuid
from datetime import datetime

from models import get_db
from models.user import User
from models.course import Course, CourseCategory, CourseLesson, CourseStatus, ContentType
from models.schemas import (
    CourseCreate, CourseUpdate, CourseResponse, CourseListResponse,
    CourseCategoryCreate, CourseCategoryUpdate, CourseCategoryResponse,
    CourseLessonCreate, CourseLessonUpdate, CourseLessonResponse,
    PaginationParams, SuccessResponse
)
from utils.logger import get_logger
from utils.auth_utils import get_current_user, get_current_user_optional, check_admin_permission

logger = get_logger("courses_api")
router = APIRouter(prefix="/courses", tags=["课程管理"])


# 课程分类管理
@router.post("/categories", response_model=CourseCategoryResponse)
async def create_category(
    category_data: CourseCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课程分类（管理员）"""
    check_admin_permission(current_user)
    
    # 检查分类名称是否已存在
    existing = db.query(CourseCategory).filter(
        CourseCategory.name == category_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分类名称已存在"
        )
    
    category = CourseCategory(**category_data.dict())
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


@router.get("/categories", response_model=List[CourseCategoryResponse])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取课程分类列表"""
    categories = db.query(CourseCategory).filter(
        CourseCategory.is_active == True
    ).order_by(CourseCategory.sort_order, CourseCategory.name).all()
    
    return categories


@router.get("/categories/{category_id}", response_model=CourseCategoryResponse)
async def get_category(category_id: str, db: Session = Depends(get_db)):
    """获取课程分类详情"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return category


@router.put("/categories/{category_id}", response_model=CourseCategoryResponse)
async def update_category(
    category_id: str,
    category_data: CourseCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新课程分类（管理员）"""
    check_admin_permission(current_user)
    
    category = db.query(CourseCategory).filter(
        CourseCategory.id == category_id
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    # 更新分类信息
    update_data = category_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/categories/{category_id}", response_model=SuccessResponse)
async def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除课程分类（管理员）"""
    check_admin_permission(current_user)
    
    category = db.query(CourseCategory).filter(
        CourseCategory.id == category_id
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    # 检查是否有子分类
    children = db.query(CourseCategory).filter(
        CourseCategory.parent_id == category_id
    ).count()
    if children > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该分类下有子分类，无法删除"
        )
    
    # 检查是否有课程使用该分类
    courses = db.query(Course).filter(
        Course.category_id == category_id
    ).count()
    if courses > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该分类下有课程，无法删除"
        )
    
    db.delete(category)
    db.commit()
    
    return SuccessResponse(message="分类删除成功")


# 课程管理
@router.post("/", response_model=CourseResponse)
async def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课程（管理员）"""
    check_admin_permission(current_user)
    
    # 检查分类是否存在
    if course_data.category_id:
        category = db.query(CourseCategory).filter(
            CourseCategory.id == course_data.category_id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="分类不存在"
            )
    
    course = Course(
        **course_data.dict(),
        creator_id=current_user.id,
        status=CourseStatus.DRAFT
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    
    return course


@router.get("/", response_model=CourseListResponse)
async def get_courses(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取课程列表"""
    query = db.query(Course)
    
    # 权限过滤：普通用户只能看到已发布的课程
    if not current_user or current_user.role not in ['admin', 'superadmin']:
        query = query.filter(Course.status == CourseStatus.PUBLISHED)
    
    # 搜索过滤
    if search:
        query = query.filter(
            or_(
                Course.title.contains(search),
                Course.subtitle.contains(search),
                Course.description.contains(search)
            )
        )
    
    # 分类过滤
    if category_id:
        query = query.filter(Course.category_id == category_id)
    
    # 状态过滤
    if status:
        query = query.filter(Course.status == status)
    
    # 计算总数
    total = query.count()
    
    # 分页
    courses = query.offset((page - 1) * size).limit(size).all()
    
    # 加载关联数据
    for course in courses:
        if course.category_id:
            course.category = db.query(CourseCategory).filter(
                CourseCategory.id == course.category_id
            ).first()
    
    return CourseListResponse(
        courses=courses,
        total=total,
        page=page,
        size=size
    )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取课程详情"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    # 权限检查：普通用户只能查看已发布的课程
    if not current_user or current_user.role not in ['admin', 'superadmin']:
        if course.status != CourseStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )
    
    # 加载关联数据
    if course.category_id:
        course.category = db.query(CourseCategory).filter(
            CourseCategory.id == course.category_id
        ).first()
    
    # 加载课时列表
    course.lessons = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id,
        CourseLesson.is_active == True
    ).order_by(CourseLesson.sort_order).all()
    
    return course


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_data: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新课程（管理员）"""
    check_admin_permission(current_user)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    # 更新课程信息
    update_data = course_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)
    
    db.commit()
    db.refresh(course)
    
    return course


@router.delete("/{course_id}", response_model=SuccessResponse)
async def delete_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除课程（管理员）"""
    check_admin_permission(current_user)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    db.delete(course)
    db.commit()
    
    return SuccessResponse(message="课程删除成功")


# 课时管理
@router.post("/{course_id}/lessons", response_model=CourseLessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    course_id: str,
    lesson_data: CourseLessonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课时（管理员）"""
    check_admin_permission(current_user)
    
    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    lesson = CourseLesson(**lesson_data.dict(), course_id=course_id)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    
    # 更新课程课时数量
    course.lesson_count = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id,
        CourseLesson.is_active == True
    ).count()
    db.commit()
    
    return lesson


@router.get("/{course_id}/lessons", response_model=List[CourseLessonResponse])
async def get_lessons(
    course_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取课程课时列表"""
    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    
    # 权限检查：普通用户只能查看已发布课程的课时
    if not current_user or current_user.role not in ['admin', 'superadmin']:
        if course.status != CourseStatus.PUBLISHED:
            raise HTTPException(status_code=404, detail="课程不存在")
    
    lessons = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id,
        CourseLesson.is_active == True
    ).order_by(CourseLesson.sort_order).all()
    
    return lessons


@router.put("/lessons/{lesson_id}", response_model=CourseLessonResponse)
async def update_lesson(
    lesson_id: str,
    lesson_data: CourseLessonUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新课时（管理员）"""
    check_admin_permission(current_user)
    
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课时不存在"
        )
    
    # 更新课时信息
    update_data = lesson_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)
    
    db.commit()
    db.refresh(lesson)
    
    return lesson


@router.delete("/lessons/{lesson_id}", response_model=SuccessResponse)
async def delete_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除课时（管理员）"""
    check_admin_permission(current_user)
    
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课时不存在"
        )
    
    course_id = lesson.course_id
    db.delete(lesson)
    db.commit()
    
    # 更新课程课时数量
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        course.lesson_count = db.query(CourseLesson).filter(
            CourseLesson.course_id == course_id,
            CourseLesson.is_active == True
        ).count()
        db.commit()
    
    return SuccessResponse(message="课时删除成功")


# 课程状态管理
@router.post("/{course_id}/publish", response_model=SuccessResponse)
async def publish_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布课程（管理员）"""
    check_admin_permission(current_user)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    course.status = CourseStatus.PUBLISHED
    course.published_at = datetime.utcnow()
    db.commit()
    
    return SuccessResponse(message="课程发布成功")


@router.post("/{course_id}/unpublish", response_model=SuccessResponse)
async def unpublish_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下架课程（管理员）"""
    check_admin_permission(current_user)
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课程不存在"
        )
    
    course.status = CourseStatus.OFFLINE
    db.commit()
    
    return SuccessResponse(message="课程下架成功")
