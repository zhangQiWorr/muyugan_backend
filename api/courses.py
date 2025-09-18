"""合并后的课程管理API
包含课程的CRUD操作、分类管理、标签管理、促销管理等
合并了course_admin.py和courses.py的功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc, asc, func
from typing import List, Optional, Dict, Any
import re
from datetime import datetime
from pydantic import BaseModel, Field

from models import get_db
from models.user import User
from models.course import Course, CourseCategory, CourseLesson, CourseStatus
from models.promotion import CoursePromotion, PromotionType, PromotionStatus, CourseTag, CourseTagRelation
from models.schemas import (
    CourseCreate, CourseUpdate, CourseDelete, CourseResponse, CourseListResponse,
    CourseCategoryCreate, CourseCategoryUpdate, CourseCategoryResponse,
    CourseLessonCreate, CourseLessonUpdate, CourseLessonResponse,
    SuccessResponse
)
from services.logger import get_logger
from utils.auth_utils import get_current_user, get_current_user_optional, check_admin_permission

logger = get_logger("courses_merged_api")
router = APIRouter(prefix="/courses", tags=["课程管理"])

# ==================== 请求模型定义 ====================

class CoursePublishRequest(BaseModel):
    """课程发布请求"""
    reason: Optional[str] = None
    scheduled_time: Optional[datetime] = None

class CourseUnpublishRequest(BaseModel):
    """课程下架请求"""
    reason: str = Field(..., description="下架原因")
    notify_users: bool = Field(default=True, description="是否通知用户")

class PromotionCreateRequest(BaseModel):
    """促销策略创建请求"""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    promotion_type: PromotionType
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    discount_amount: Optional[float] = Field(None, ge=0)
    min_price: float = Field(default=0.0, ge=0)
    max_discount: Optional[float] = Field(None, ge=0)
    start_time: datetime
    end_time: datetime
    usage_limit: Optional[int] = Field(None, ge=1)
    per_user_limit: int = Field(default=1, ge=1)
    show_countdown: bool = Field(default=True)
    show_original_price: bool = Field(default=True)
    promotion_badge: Optional[str] = Field(None, max_length=50)

class TagCreateRequest(BaseModel):
    """标签创建请求"""
    name: str = Field(..., max_length=50)
    description: Optional[str] = None
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)

class CategoryCreateRequest(BaseModel):
    """分类创建请求"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[str] = None
    sort_order: int = Field(default=0)

class CourseUpdateRequest(BaseModel):
    """课程更新请求"""
    title: Optional[str] = Field(None, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    cover_image: Optional[str] = Field(None, max_length=500)
    category_id: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    original_price: Optional[float] = Field(None, ge=0)
    is_free: Optional[bool] = None
    is_member_only: Optional[bool] = None
    difficulty_level: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, max_length=20)
    is_featured: Optional[bool] = None
    is_hot: Optional[bool] = None
    tag_ids: Optional[List[str]] = None

# ==================== 课程分类管理 ====================

@router.get("/categories", response_model=List[CourseCategoryResponse])
async def get_categories(
    include_inactive: bool = Query(False, description="是否包含未激活的分类"),
    sort_by: str = Query("sort_order", description="排序字段: sort_order, name, created_at, course_count"),
    sort_order: str = Query("asc", description="排序方向: asc, desc"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取课程分类列表（兼容两种权限模式）"""
    try:
        query = db.query(CourseCategory).options(selectinload(CourseCategory.children))
        
        # 如果用户未登录或非管理员，只显示激活的分类
        if not current_user or current_user.role not in ['admin', 'superadmin']:
            query = query.filter(CourseCategory.is_active == True)
        elif not include_inactive:
            query = query.filter(CourseCategory.is_active == True)
        
        # 根据排序参数进行排序
        valid_sort_fields = {
            "sort_order": CourseCategory.sort_order,
            "name": CourseCategory.name,
            "created_at": CourseCategory.created_at
        }
        
        sort_field = valid_sort_fields.get(sort_by, CourseCategory.sort_order)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(asc(sort_field))
        
        # 如果按sort_order排序，添加name作为次要排序
        if sort_by == "sort_order":
            query = query.order_by(sort_field, CourseCategory.name)
        
        categories = query.all()

        # 批量统计课程数量，避免每个分类COUNT导致的N+1
        category_ids = [c.id for c in categories]
        count_map = {}
        if category_ids:
            base_query = db.query(Course.category_id, func.count(Course.id)).\
                filter(Course.category_id.in_(category_ids))
            # 非管理员仅统计已发布课程
            if not current_user or current_user.role not in ['admin', 'superadmin']:
                base_query = base_query.filter(Course.status == CourseStatus.PUBLISHED)
            rows = base_query.group_by(Course.category_id).all()
            count_map = {cid: cnt for cid, cnt in rows}

        category_results = []
        for cat in categories:
            course_count = count_map.get(cat.id, 0)
            category_results.append({
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "icon": cat.icon,
                "sort_order": cat.sort_order,
                "is_active": cat.is_active,
                "parent_id": cat.parent_id,
                "course_count": course_count,
                "created_at": cat.created_at,
                "updated_at": cat.updated_at
            })
        
        # 如果按course_count排序，需要重新排序结果
        if sort_by == "course_count":
            reverse_order = sort_order.lower() == "desc"
            category_results.sort(key=lambda x: x["course_count"], reverse=reverse_order)
        
        # 设置短期缓存，减少分类列表查询压力
        from fastapi import Response
        resp = Response(content=None)
        resp.headers["Cache-Control"] = "public, max-age=300"
        # 直接返回数据对象，FastAPI会处理为JSON；头部由全局中间件附加
        return category_results
        
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分类列表失败")

@router.get("/categories/{category_id}", response_model=CourseCategoryResponse)
async def get_category(category_id: str, db: Session = Depends(get_db)):
    """获取课程分类详情"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return category

@router.post("/categories", response_model=CourseCategoryResponse)
async def create_category(
    category_data: CourseCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课程分类（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 检查分类名称是否已存在
        existing = db.query(CourseCategory).filter(
            CourseCategory.name == category_data.name
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="分类名称已存在"
            )
        
        # 检查父分类是否存在
        if hasattr(category_data, 'parent_id') and category_data.parent_id:
            parent = db.query(CourseCategory).filter(
                CourseCategory.id == category_data.parent_id
            ).first()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="父分类不存在"
                )
        
        category = CourseCategory(**category_data.dict())
        db.add(category)
        db.commit()
        db.refresh(category)
        
        logger.info(f"Category {category.id} created by admin {current_user.username}")
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating category: {str(e)}")
        raise HTTPException(status_code=500, detail="创建分类失败")

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

# ==================== 课程标签管理 ====================

@router.get("/tags")
async def get_tags(
    include_inactive: bool = Query(False, description="是否包含未激活的标签"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取课程标签列表"""
    try:
        query = db.query(CourseTag)
        
        if not include_inactive:
            query = query.filter(CourseTag.is_active == True)
        
        tags = query.order_by(desc(CourseTag.usage_count), CourseTag.name).all()
        
        # 设置短期缓存
        from fastapi import Response
        resp = Response(content=None)
        resp.headers["Cache-Control"] = "public, max-age=300"
        return {
            "tags": [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "description": tag.description,
                    "color": tag.color,
                    "icon": tag.icon,
                    "usage_count": tag.usage_count,
                    "is_active": tag.is_active,
                    "sort_order": getattr(tag, 'sort_order', 0),
                    "created_at": tag.created_at
                } for tag in tags
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting tags: {str(e)}")
        raise HTTPException(status_code=500, detail="获取标签列表失败")

@router.post("/tags")
async def create_tag(
    request: TagCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课程标签（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 检查标签名称是否已存在
        existing = db.query(CourseTag).filter(CourseTag.name == request.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="标签名称已存在")
        
        tag = CourseTag(
            name=request.name,
            description=request.description,
            color=request.color,
            icon=request.icon,
            created_by=current_user.id
        )
        
        db.add(tag)
        db.commit()
        db.refresh(tag)
        
        logger.info(f"Tag {tag.id} created by admin {current_user.username}")
        
        return {
            "message": "标签创建成功",
            "tag": {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description,
                "color": tag.color,
                "icon": tag.icon,
                "usage_count": tag.usage_count,
                "is_active": tag.is_active,
                "created_at": tag.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating tag: {str(e)}")
        raise HTTPException(status_code=500, detail="创建标签失败")

@router.put("/tags/{tag_id}")
async def update_tag(
    tag_id: str,
    request: TagCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新课程标签（管理员）"""
    check_admin_permission(current_user)
    
    try:
        tag = db.query(CourseTag).filter(CourseTag.id == tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="标签不存在")
        
        # 检查标签名称是否已存在（排除当前标签）
        existing = db.query(CourseTag).filter(
            and_(CourseTag.name == request.name, CourseTag.id != tag_id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="标签名称已存在")
        
        # 更新标签信息
        for attr, value in {
            'name': request.name,
            'description': request.description,
            'color': request.color,
            'icon': request.icon,
            'updated_at': datetime.utcnow()
        }.items():
            setattr(tag, attr, value)
        
        db.commit()
        db.refresh(tag)
        
        logger.info(f"Tag {tag.id} updated by admin {current_user.username}")
        
        return {
            "message": "标签更新成功",
            "tag": {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description,
                "color": tag.color,
                "icon": tag.icon,
                "usage_count": tag.usage_count,
                "is_active": tag.is_active,
                "created_at": tag.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="更新标签失败")

@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除课程标签（管理员）"""
    check_admin_permission(current_user)
    
    try:
        tag = db.query(CourseTag).filter(CourseTag.id == tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="标签不存在")
        
        # 检查是否有课程正在使用该标签
        courses_using_tag = db.query(CourseTagRelation).filter(
            CourseTagRelation.tag_id == tag_id
        ).count()
        
        if courses_using_tag > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"无法删除标签，还有 {courses_using_tag} 个课程正在使用该标签"
            )
        
        db.delete(tag)
        db.commit()
        
        logger.info(f"Tag {tag_id} deleted by admin {current_user.username}")
        
        return SuccessResponse(message="标签删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting tag {tag_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="删除标签失败")

# ==================== 课程管理 ====================

@router.post("/", response_model=SuccessResponse)
async def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课程（管理员）"""
    check_admin_permission(current_user)
    
    try:
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
        
        logger.info(f"Course created successfully: {course.id} by user {current_user.username}")
        
        return SuccessResponse(
            message="课程创建成功",
            data={
                "id": course.id,
                "title": course.title,
                "status": course.status,
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建课程失败"
        )

@router.get("/", response_model=CourseListResponse)
async def get_courses(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    featured: Optional[bool] = Query(None, description="是否只获取精选课程"),
    hot: Optional[bool] = Query(None, description="是否只获取热门课程"),
    sort_by: str = Query("created_at", description="排序字段: created_at, updated_at, title, price, view_count, is_featured, is_hot"),
    sort_order: str = Query("desc", description="排序方向: asc, desc"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取课程列表"""
    query = db.query(Course).options(selectinload(Course.category))
    
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
    
    # 精选课程过滤
    if featured is not None:
        query = query.filter(Course.is_featured == featured)
    
    # 热门课程过滤
    if hot is not None:
        query = query.filter(Course.is_hot == hot)
    
    # 排序逻辑
    valid_sort_fields = {
        "created_at": Course.created_at,
        "updated_at": Course.updated_at,
        "title": Course.title,
        "price": Course.price,
        "view_count": Course.view_count,
        "is_featured": Course.is_featured,
        "is_hot": Course.is_hot
    }
    
    sort_field = valid_sort_fields.get(sort_by, Course.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(asc(sort_field))
    
    # 计算总数
    total = query.count()
    
    # 分页
    courses = query.offset((page - 1) * size).limit(size).all()
    
    # 关联数据通过selectinload预加载，避免N+1

    # 设置短期缓存，分页列表通常可缓存
    from fastapi import Response
    resp = Response(content=None)
    resp.headers["Cache-Control"] = "public, max-age=120"
    return CourseListResponse(
        courses=[CourseResponse.from_orm(course) for course in courses],
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
        if getattr(course, 'status', None) != CourseStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )
    
    # 加载关联数据
    if getattr(course, 'category_id', None):
        course.category = db.query(CourseCategory).filter(
            CourseCategory.id == course.category_id
        ).first()
    
    # 加载课时列表
    course.lessons = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id,
        CourseLesson.is_active == True
    ).order_by(CourseLesson.sort_order).all()
    
    return course


@router.put("/{course_id}",  response_model=CourseResponse)
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
    
    setattr(course, 'updated_at', datetime.utcnow())
    db.commit()
    db.refresh(course)
    
    return course

@router.delete("/{course_id}", response_model=SuccessResponse)
async def delete_course(
    course_id: str,
    delete_data: CourseDelete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除课程（管理员）
    
    Args:
        course_id: 课程ID
        delete_data: 删除参数，包含isDeleteLesson字段
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        SuccessResponse: 删除成功响应
        
    Note:
        - 如果isDeleteLesson为True，会同时删除该课程下的所有课时
        - 如果isDeleteLesson为False且有课时，则不允许删除课程
    """
    check_admin_permission(current_user)
    
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )
        
        # 检查课程是否有关联的课时
        lesson_count = db.query(CourseLesson).filter(
            CourseLesson.course_id == course_id,
            CourseLesson.is_active == True
        ).count()
        
        # 如果isDeleteLesson为True，删除该课程下的所有课时
        if delete_data.isDeleteLesson and lesson_count > 0:
            # 删除课程下的所有课时
            lessons = db.query(CourseLesson).filter(
                CourseLesson.course_id == course_id,
                CourseLesson.is_active == True
            ).all()
            
            for lesson in lessons:
                # 使用CourseService删除课时（会自动更新课程时长）
                from services.course_service import CourseService
                course_service = CourseService(db)
                course_service.delete_lesson(lesson.id)
            
            logger.info(f"Deleted {lesson_count} lessons for course {course_id}")
        elif lesson_count > 0:
            # 如果isDeleteLesson为False且有课时，则不允许删除
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"课程下还有 {lesson_count} 个课时，请先删除所有课时后再删除课程，或设置 isDeleteLesson 为 true"
            )
        
        # 删除课程标签关联
        db.query(CourseTagRelation).filter(
            CourseTagRelation.course_id == course_id
        ).delete()
        
        # 删除课程促销策略
        db.query(CoursePromotion).filter(
            CoursePromotion.course_id == course_id
        ).delete()
        
        # 删除课程
        db.delete(course)
        db.commit()
        
        logger.info(f"Course {course_id} deleted by admin {current_user.username}")
        
        return SuccessResponse(message="课程删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="删除课程失败")

# ==================== 课程状态管理 ====================

@router.post("/{course_id}/publish", response_model=SuccessResponse)
async def publish_course(
    course_id: str,
    request: Optional[CoursePublishRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发布课程（管理员）"""
    check_admin_permission(current_user)
    
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )
        
        # 验证课程是否可以发布
        if getattr(course, 'status', None) == CourseStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="课程已经发布"
            )
        
        setattr(course, 'status', CourseStatus.PUBLISHED)
        setattr(course, 'published_at', datetime.utcnow())
        db.commit()
        
        logger.info(f"Course {course_id} published by admin {current_user.username}")
        
        return SuccessResponse(message="课程发布成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error publishing course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="发布课程失败")

@router.post("/{course_id}/unpublish", response_model=SuccessResponse)
async def unpublish_course(
    course_id: str,
    request: Optional[CourseUnpublishRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下架课程（管理员）"""
    check_admin_permission(current_user)
    
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )
        
        setattr(course, 'status', CourseStatus.OFFLINE)
        db.commit()
        
        logger.info(f"Course {course_id} unpublished by admin {current_user.username}")
        
        return SuccessResponse(message="课程下架成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error unpublishing course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="下架课程失败")

# ==================== 课时管理 ====================

@router.post("/{course_id}/lessons", response_model=CourseLessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    course_id: str,
    lesson_data: CourseLessonCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课时（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 检查课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )

        # 提取media_ids并从lesson_data中移除
        media_ids = lesson_data.media_ids
        lesson_dict = lesson_data.dict(exclude={'media_ids'})
        
        # 验证媒体文件
        if media_ids:
            from models.media import Media
            for media_id in media_ids:
                # 检查媒体文件是否存在
                media = db.query(Media).filter(Media.id == media_id).first()
                if not media:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"媒体文件不存在: {media_id}"
                    )
                
                # 检查媒体文件是否已经被其他课时关联
                if media.lesson_id is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"媒体文件 {media_id} 已经被其他课时关联，无法重复使用"
                    )
        
        # 使用CourseService创建课时
        from services.course_service import CourseService
        course_service = CourseService(db)
        
        lesson = course_service.create_lesson(
            course_id=course_id,
            title=lesson_dict['title'],
            description=lesson_dict.get('description'),
            duration=lesson_dict.get('duration', 0),
            sort_order=lesson_dict.get('sort_order', 0),
            is_free=lesson_dict.get('is_free', False),
            is_active=lesson_dict.get('is_active', True)
        )
        
        # 如果提供了媒体文件ID，将课时ID关联到这些媒体文件
        if media_ids:
            from models.media import Media
            for media_id in media_ids:
                media = db.query(Media).filter(Media.id == media_id).first()
                if media:
                    media.lesson_id = lesson.id
            db.commit()
        
        return lesson
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建课时失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建课时失败")

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
        if getattr(course, 'status', None) != CourseStatus.PUBLISHED:
            raise HTTPException(status_code=404, detail="课程不存在")
    
    lessons = db.query(CourseLesson).filter(
        CourseLesson.course_id == course_id,
        CourseLesson.is_active == True
    ).order_by(CourseLesson.sort_order).all()
    
    return lessons

@router.get("/lessons/{lesson_id}/media")
async def get_lesson_media(
    lesson_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取课时的媒体文件列表"""
    lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课时不存在"
        )
    
    # 权限检查：普通用户只能查看已发布课程的课时
    if not current_user or current_user.role not in ['admin', 'superadmin']:
        if lesson.course.status != CourseStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )
    
    # 获取课时的媒体文件
    from models.media import Media
    media_files = db.query(Media).filter(Media.lesson_id == lesson_id).all()
    
    return {
        "lesson_id": lesson_id,
        "lesson_title": lesson.title,
        "media_files": [
            {
                "id": media.id,
                "filename": media.filename,
                "filepath": media.filepath or "",  # 确保filepath不为None
                "media_type": media.media_type,
                "duration": media.duration,
                "size": media.size,
                "cover_url": media.cover_url,
                "upload_time": media.upload_time.isoformat() if media.upload_time else None
            } for media in media_files
        ]
    }

@router.put("/lessons/{lesson_id}", response_model=CourseLessonResponse)
async def update_lesson(
    lesson_id: str,
    lesson_data: CourseLessonUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新课时（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 检查课时是否存在
        lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )

        # 处理媒体文件关联更新
        if hasattr(lesson_data, 'media_ids') and lesson_data.media_ids is not None:
            from models.media import Media
            
            # 获取当前关联的媒体文件
            current_media = db.query(Media).filter(Media.lesson_id == lesson_id).all()
            current_media_ids = {media.id for media in current_media}
            new_media_ids = set(lesson_data.media_ids) if lesson_data.media_ids else set()
            
            # 找出需要取消关联的媒体文件
            media_to_remove = current_media_ids - new_media_ids
            for media_id in media_to_remove:
                media = db.query(Media).filter(Media.id == media_id).first()
                if media:
                    media.lesson_id = None
                    logger.info(f"取消媒体文件 {media_id} 与课时 {lesson_id} 的关联")
            
            # 找出需要新增关联的媒体文件
            media_to_add = new_media_ids - current_media_ids
            for media_id in media_to_add:
                # 检查媒体文件是否存在
                media = db.query(Media).filter(Media.id == media_id).first()
                if not media:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"媒体文件不存在: {media_id}"
                    )
                
                # 检查媒体文件是否已经被其他课时关联
                if media.lesson_id is not None and media.lesson_id != lesson_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"媒体文件 {media_id} 已经被其他课时关联，无法重复使用"
                    )
                
                # 关联媒体文件到当前课时
                media.lesson_id = lesson_id
                logger.info(f"关联媒体文件 {media_id} 到课时 {lesson_id}")

        # 使用CourseService更新课时
        from services.course_service import CourseService
        course_service = CourseService(db)
        
        # 准备更新数据
        update_data = lesson_data.dict(exclude_unset=True)
        update_data.pop('media_ids', None)  # 移除media_ids，因为已经单独处理
        
        lesson = course_service.update_lesson(
            lesson_id=lesson_id,
            title=update_data.get('title'),
            description=update_data.get('description'),
            duration=update_data.get('duration'),
            sort_order=update_data.get('sort_order'),
            is_free=update_data.get('is_free'),
            is_active=update_data.get('is_active')
        )
        
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )
        
        return lesson
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新课时失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新课时失败")

@router.delete("/lessons/{lesson_id}", response_model=SuccessResponse)
async def delete_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除课时（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 检查课时是否存在
        lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )
        
        # 取消媒体文件关联
        media_files = lesson.media_files
        for media in media_files:
            media.lesson_id = None
        
        # 先提交媒体文件关联的取消
        db.commit()
        
        # 使用CourseService删除课时
        from services.course_service import CourseService
        course_service = CourseService(db)
        
        success = course_service.delete_lesson(lesson_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )
        
        return SuccessResponse(message="课时删除成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除课时失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除课时失败")

# 课时媒体播放相关函数
def handle_lesson_media_range_request(request: Request, file_path: str, file_size: int, content_type: str):
    """处理课时媒体文件的Range请求（支持视频和音频）"""
    range_header = request.headers.get('range')
    if not range_header:
        return None
    
    # 解析Range头
    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
    if not range_match:
        return None
    
    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    
    # 确保范围有效
    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))
    
    chunk_size = end - start + 1
    
    def generate():
        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_size = min(8192, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data
    
    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(chunk_size),
        'Content-Type': content_type
    }
    
    return StreamingResponse(
        generate(),
        status_code=206,
        headers=headers
    )

@router.put("/lessons/reorder", response_model=SuccessResponse)
async def reorder_lessons(
    lesson_orders: List[Dict[str, Any]] = Body(..., description="课时排序列表，格式: [{\"id\": \"lesson_id\", \"sort_order\": 1}]"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量更新课时排序（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 验证输入数据
        if not lesson_orders:
            raise HTTPException(status_code=400, detail="排序数据不能为空")
        
        # 批量更新课时排序
        for order_data in lesson_orders:
            lesson_id = order_data.get('id')
            sort_order = order_data.get('sort_order')
            
            if not lesson_id or sort_order is None:
                raise HTTPException(status_code=400, detail="课时ID和排序值不能为空")
            
            lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
            if lesson:
                setattr(lesson, 'sort_order', sort_order)
        
        db.commit()
        logger.info(f"✅ 批量更新课时排序成功，共更新 {len(lesson_orders)} 个课时")
        
        return SuccessResponse(message="课时排序更新成功")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"批量更新课时排序失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新课时排序失败")

# ==================== 促销策略管理 ====================

@router.get("/{course_id}/promotions")
async def get_course_promotions(
    course_id: str,
    status: Optional[PromotionStatus] = Query(None, description="促销状态筛选"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程促销策略列表（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 检查课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        query = db.query(CoursePromotion).filter(CoursePromotion.course_id == course_id)
        
        if status:
            query = query.filter(CoursePromotion.status == status)
        
        promotions = query.order_by(desc(CoursePromotion.created_at)).all()
        
        return {
            "promotions": [
                {
                    "id": promo.id,
                    "title": promo.title,
                    "description": promo.description,
                    "promotion_type": promo.promotion_type,
                    "status": promo.status,
                    "discount_percentage": promo.discount_percentage,
                    "discount_amount": promo.discount_amount,
                    "min_price": promo.min_price,
                    "max_discount": promo.max_discount,
                    "start_time": promo.start_time,
                    "end_time": promo.end_time,
                    "usage_limit": promo.usage_limit,
                    "used_count": promo.used_count,
                    "per_user_limit": promo.per_user_limit,
                    "show_countdown": promo.show_countdown,
                    "show_original_price": promo.show_original_price,
                    "promotion_badge": promo.promotion_badge,
                    "is_active": promo.is_active(),
                    "discounted_price": promo.calculate_discounted_price(getattr(course, 'price', 0)),
                    "created_at": promo.created_at,
                    "updated_at": promo.updated_at
                } for promo in promotions
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting promotions for course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="获取促销策略失败")

@router.post("/{course_id}/promotions")
async def create_promotion(
    course_id: str,
    request: PromotionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建课程促销策略（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 检查课程是否存在
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        # 验证促销参数
        if request.promotion_type == PromotionType.PERCENTAGE:
            if not request.discount_percentage or request.discount_percentage <= 0:
                raise HTTPException(status_code=400, detail="百分比折扣必须大于0")
        elif request.promotion_type == PromotionType.FIXED_AMOUNT:
            if not request.discount_amount or request.discount_amount <= 0:
                raise HTTPException(status_code=400, detail="固定金额折扣必须大于0")
        
        if request.start_time >= request.end_time:
            raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
        
        # 检查是否有重叠的激活促销
        overlapping = db.query(CoursePromotion).filter(
            and_(
                CoursePromotion.course_id == course_id,
                CoursePromotion.status == PromotionStatus.ACTIVE,
                or_(
                    and_(CoursePromotion.start_time <= request.start_time, CoursePromotion.end_time >= request.start_time),
                    and_(CoursePromotion.start_time <= request.end_time, CoursePromotion.end_time >= request.end_time),
                    and_(CoursePromotion.start_time >= request.start_time, CoursePromotion.end_time <= request.end_time)
                )
            )
        ).first()
        
        if overlapping:
            raise HTTPException(status_code=400, detail="该时间段已有激活的促销策略")
        
        promotion = CoursePromotion(
            course_id=course_id,
            title=request.title,
            description=request.description,
            promotion_type=request.promotion_type,
            discount_percentage=request.discount_percentage,
            discount_amount=request.discount_amount,
            min_price=request.min_price,
            max_discount=request.max_discount,
            start_time=request.start_time,
            end_time=request.end_time,
            usage_limit=request.usage_limit,
            per_user_limit=request.per_user_limit,
            show_countdown=request.show_countdown,
            show_original_price=request.show_original_price,
            promotion_badge=request.promotion_badge,
            created_by=current_user.id
        )
        
        db.add(promotion)
        db.commit()
        db.refresh(promotion)
        
        logger.info(f"Promotion {promotion.id} created for course {course_id} by admin {current_user.username}")
        
        return {
            "message": "促销策略创建成功",
            "promotion": {
                "id": promotion.id,
                "title": promotion.title,
                "promotion_type": promotion.promotion_type,
                "status": promotion.status,
                "start_time": promotion.start_time,
                "end_time": promotion.end_time,
                "discounted_price": promotion.calculate_discounted_price(getattr(course, 'price', 0)),
                "created_at": promotion.created_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating promotion for course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="创建促销策略失败")

@router.put("/promotions/{promotion_id}/status")
async def update_promotion_status(
    promotion_id: str,
    status: PromotionStatus = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新促销策略状态（管理员）"""
    check_admin_permission(current_user)
    
    try:
        promotion = db.query(CoursePromotion).filter(CoursePromotion.id == promotion_id).first()
        if not promotion:
            raise HTTPException(status_code=404, detail="促销策略不存在")
        
        old_status = getattr(promotion, 'status', None)
        setattr(promotion, 'status', status)
        setattr(promotion, 'updated_at', datetime.utcnow())
        
        db.commit()
        
        logger.info(f"Promotion {promotion_id} status changed from {old_status} to {status} by admin {current_user.username}")
        
        return {
            "message": "促销策略状态更新成功",
            "promotion_id": promotion_id,
            "old_status": old_status,
            "new_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating promotion status {promotion_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="更新促销策略状态失败")

# ==================== 统计信息 ====================

@router.get("/statistics")
async def get_course_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课程统计信息（管理员）"""
    check_admin_permission(current_user)
    
    try:
        # 课程状态统计
        status_stats = db.query(
            Course.status,
            func.count(Course.id).label('count')
        ).group_by(Course.status).all()
        
        # 分类统计
        category_stats = db.query(
            CourseCategory.name,
            func.count(Course.id).label('count')
        ).join(Course, CourseCategory.id == Course.category_id, isouter=True).group_by(CourseCategory.id, CourseCategory.name).all()
        
        # 促销统计
        promotion_stats = db.query(
            CoursePromotion.status,
            func.count(CoursePromotion.id).label('count')
        ).group_by(CoursePromotion.status).all()
        
        # 总体统计
        total_courses = db.query(Course).count()
        total_categories = db.query(CourseCategory).count()
        total_tags = db.query(CourseTag).count()
        active_promotions = db.query(CoursePromotion).filter(CoursePromotion.status == PromotionStatus.ACTIVE).count()
        
        return {
            "total_statistics": {
                "total_courses": total_courses,
                "total_categories": total_categories,
                "total_tags": total_tags,
                "active_promotions": active_promotions
            },
            "status_statistics": [
                {"status": stat.status, "count": stat.count}
                for stat in status_stats
            ],
            "category_statistics": [
                {"category": stat.name or "未分类", "count": stat.count}
                for stat in category_stats
            ],
            "promotion_statistics": [
                {"status": stat.status, "count": stat.count}
                for stat in promotion_stats
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting course statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")# 在第870行左右，get_lessons函数之后添加新的接口

@router.get("/lessons/{lesson_id}", response_model=CourseLessonResponse)
async def get_lesson_detail(
    lesson_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """获取课时详情"""
    # 查找课时
    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == lesson_id,
        CourseLesson.is_active == True
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="课时不存在"
        )
    
    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == lesson.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关联课程不存在"
        )
    
    # 权限检查：普通用户只能查看已发布课程的课时
    if not current_user or current_user.role not in ['admin', 'superadmin']:
        if getattr(course, 'status', None) != CourseStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )
        
        # 如果课时不是免费的，需要检查用户是否已报名课程
        lesson_is_free = getattr(lesson, 'is_free', True)
        if not lesson_is_free:
            from models.course import CourseEnrollment
            lesson_course_id = getattr(lesson, 'course_id', None)
            if lesson_course_id:
                user_id = getattr(current_user, 'id', None)
                if user_id:
                    enrollment = db.query(CourseEnrollment).filter(
                        CourseEnrollment.user_id == user_id,
                        CourseEnrollment.course_id == lesson_course_id,
                        CourseEnrollment.is_active == True
                    ).first()
                else:
                    enrollment = None
                
                if not enrollment:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="需要报名课程才能查看此课时"
                    )
    
    return lesson
