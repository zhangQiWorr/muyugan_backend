"""课时资料上传API
处理课时的文本、音频、视频资料上传功能
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import mimetypes
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from models import get_db
from models.user import User
from utils.auth_utils import get_current_user, check_admin_permission
from services.logger import get_logger
from utils.media_utils import get_media_duration_from_upload, get_media_duration
from models.course import Course, CourseLesson, ContentType


logger = get_logger("lesson_materials")
router = APIRouter(prefix="/lesson-materials", tags=["课时资料"])

# 配置
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
MATERIALS_DIR = os.path.join(STATIC_DIR, 'lesson_materials')

# 文件类型配置
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB

SUPPORTED_VIDEO_TYPES = {
    'video/mp4': '.mp4',
    'video/avi': '.avi',
    'video/mov': '.mov',
    'video/wmv': '.wmv',
    'video/flv': '.flv',
    'video/webm': '.webm'
}

SUPPORTED_AUDIO_TYPES = {
    'audio/mp3': '.mp3',
    'audio/mpeg': '.mp3',
    'audio/wav': '.wav',
    'audio/ogg': '.ogg',
    'audio/aac': '.aac',
    'audio/m4a': '.m4a'
}

SUPPORTED_DOCUMENT_TYPES = {
    'application/pdf': '.pdf',
    'text/plain': '.txt',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
}


def validate_file(file: UploadFile, content_type: ContentType) -> tuple[bool, str]:
    """验证上传文件"""
    if not file.filename:
        return False, "文件名不能为空"
    
    if content_type == ContentType.VIDEO:
        if file.content_type not in SUPPORTED_VIDEO_TYPES:
            return False, f"不支持的视频格式: {file.content_type}"
        if file.size and file.size > MAX_VIDEO_SIZE:
            return False, f"视频文件大小超过限制 ({MAX_VIDEO_SIZE // 1024 // 1024}MB)"
    
    elif content_type == ContentType.AUDIO:
        if file.content_type not in SUPPORTED_AUDIO_TYPES:
            return False, f"不支持的音频格式: {file.content_type}"
        if file.size and file.size > MAX_AUDIO_SIZE:
            return False, f"音频文件大小超过限制 ({MAX_AUDIO_SIZE // 1024 // 1024}MB)"
    
    elif content_type == ContentType.DOCUMENT:
        if file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            return False, f"不支持的文档格式: {file.content_type}"
        if file.size and file.size > MAX_DOCUMENT_SIZE:
            return False, f"文档文件大小超过限制 ({MAX_DOCUMENT_SIZE // 1024 // 1024}MB)"
    
    return True, ""


def get_file_directory(content_type: ContentType, course_id: Optional[str] = None) -> str:
    """根据内容类型和课程ID获取存储目录"""
    if course_id:
        base_dir = os.path.join(MATERIALS_DIR, course_id)
    else:
        base_dir = MATERIALS_DIR

    # 创建目录
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    return base_dir


def get_file_extension(content_type: Optional[str], content_type_enum: ContentType) -> str:
    """根据MIME类型获取文件扩展名"""
    if content_type_enum == ContentType.VIDEO:
        return SUPPORTED_VIDEO_TYPES.get(content_type or '', '.mp4')
    elif content_type_enum == ContentType.AUDIO:
        return SUPPORTED_AUDIO_TYPES.get(content_type or '', '.mp3')
    elif content_type_enum == ContentType.DOCUMENT:
        return SUPPORTED_DOCUMENT_TYPES.get(content_type or '', '.pdf')
    else:
        return os.path.splitext(content_type or '')[1] or '.bin'


@router.post("/{course_id}/upload")
async def upload_lesson_material(
    course_id: str,
    file: UploadFile = File(...),
    content_type: ContentType = Form(...),
    lesson_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    """上传课时资料"""
    check_admin_permission(current_user)
    
    # 验证文件
    is_valid, error_msg = validate_file(file, content_type)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # 如果提供了lesson_id，验证课时是否存在
    if lesson_id:
        lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )
    
    try:
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        logger.info(f"上传文件:{file.filename}")
        print(f"上传文件:{file.filename}")
        file_extension = get_file_extension(file.content_type, content_type)
        filename = f"{timestamp}_{file.filename}"

        print(f"course_id:{course_id}")
        # 确定存储目录（按课程ID分目录）
        storage_dir = get_file_directory(content_type, course_id)
        print(f"存储目录:{storage_dir}")
        filepath = os.path.join(storage_dir, filename)
        
        # 保存文件
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 获取文件大小
        file_size = os.path.getsize(filepath)
        
        # 生成访问URL
        relative_path = os.path.relpath(filepath, STATIC_DIR)
        file_url = f"/static/{relative_path.replace(os.sep, '/')}"
        
        # 如果指定了课时ID，更新课时的资料URL
        if lesson_id:
            lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
            if lesson:
                setattr(lesson, 'content_url', file_url)
                setattr(lesson, 'content_type', content_type)
                
                # 如果是音频或视频文件，自动检测时长
                if content_type in [ContentType.VIDEO, ContentType.AUDIO]:
                    try:
                        with open(filepath, 'rb') as f:
                            file_content = f.read()
                        filename = file.filename or "unknown"
                        duration = get_media_duration_from_upload(file_content, filename, content_type.value)
                        if duration:
                            setattr(lesson, 'duration', int(duration))
                            logger.info(f"✅ 检测到媒体文件时长: {duration}秒")
                    except Exception as e:
                        logger.warning(f"⚠️ 无法检测媒体文件时长: {str(e)}")
                
                db.commit()
                logger.info(f"✅ 课时 {lesson_id} 资料更新成功: {filename}")
        
        logger.info(f"✅ 课时资料上传成功: {filename} ({file_size // 1024}KB)")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "data": {
                "file_id": file_id,
                "filename": filename,
                "original_filename": file.filename,
                "url": file_url,
                "size": file_size,
                "content_type": content_type.value,
                "mime_type": file.content_type,
                "upload_time": datetime.now().isoformat(),
                "lesson_id": lesson_id
            }
        }
    
    except Exception as e:
        # 清理已上传的文件
        if 'filepath' in locals() and 'filepath' in locals() and os.path.exists(locals()['filepath']):
            os.remove(locals()['filepath'])
        
        logger.error(f"❌ 文件上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.delete("/file")
async def delete_lesson_material_file(
    content_url: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """删除课时资料文件
    
    Args:
        content_url: 文件的URL路径，格式如: /static/lesson_materials/course_id/videos/filename
    """
    check_admin_permission(current_user)
    
    try:
        # 验证content_url格式
        if not content_url or not content_url.startswith('/static/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件URL格式，必须以/static/开头"
            )
        
        # 从URL中提取文件路径
        # content_url格式: /static/lesson_materials/course_id/videos/filename
        relative_path = content_url[8:]  # 去掉 '/static/' 前缀
        file_path = os.path.join(STATIC_DIR, relative_path)
        
        # 安全检查：确保文件路径在允许的目录内
        if not file_path.startswith(MATERIALS_DIR):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件路径不在允许的目录范围内"
            )
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ 要删除的文件不存在: {file_path}")
            return {
                "success": True,
                "message": "文件不存在，可能已被删除",
                "content_url": content_url,
                "file_existed": False
            }
        
        # 删除文件
        filename = os.path.basename(file_path)
        os.remove(file_path)
        logger.info(f"🗑️ 删除课时资料文件: {filename}")
        
        # 尝试删除空的父目录（如果为空）
        try:
            parent_dir = os.path.dirname(file_path)
            if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                os.rmdir(parent_dir)
                logger.info(f"🧹 删除空目录: {parent_dir}")
        except OSError:
            # 目录不为空或其他原因，忽略
            pass
        
        return {
            "success": True,
            "message": "课时文件删除成功",
            "content_url": content_url,
            "deleted_file": filename,
            "file_existed": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除课时文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除课时文件失败: {str(e)}"
        )


@router.get("/{lesson_id}")
async def get_lesson_material_info(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取课时底层文件信息"""
    check_admin_permission(current_user)
    
    try:
        # 查询课时信息
        lesson = db.query(CourseLesson).filter(CourseLesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课时不存在"
            )
        
        # 获取课时的文件信息
        content_url = getattr(lesson, 'content_url', None)
        content_type = getattr(lesson, 'content_type', None)
        duration = getattr(lesson, 'duration', None)
        
        # 类型检查，确保content_url不为None
        if content_url is None:
            content_url = ""
        
        if not content_url:
            return {
                "success": True,
                "message": "该课时没有关联的文件",
                "data": {
                    "lesson_id": lesson_id,
                    "has_file": False,
                    "file_info": None
                }
            }
        
        # 从URL中提取文件路径
        if content_url.startswith('/static/'):
            relative_path = content_url[8:]  # 去掉 '/static/' 前缀
            file_path = os.path.join(STATIC_DIR, relative_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件URL格式"
            )
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "success": True,
                "message": "文件不存在",
                "data": {
                    "lesson_id": lesson_id,
                    "has_file": False,
                    "file_info": {
                        "url": content_url,
                        "content_type": content_type.value if content_type else None,
                        "duration": duration,
                        "file_exists": False
                    }
                }
            }
        
        # 获取文件信息
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        file_extension = os.path.splitext(filename)[1]
        mime_type, _ = mimetypes.guess_type(file_path)
        duration = get_media_duration(file_path, content_type.value)


        # 如果未保存时长，且是音视频，尝试即时检测并回写数据库
        if (not duration or duration == 0) and content_type in [ContentType.VIDEO, ContentType.AUDIO]:
            try:
                detected = get_media_duration(file_path, content_type.value)
                if detected:
                    duration = int(detected)
                    # 回写课时时长，便于下次直接读取
                    lesson.duration = duration
                    db.commit()
            except Exception:
                pass
        
        # 获取文件创建和修改时间
        created_time = datetime.fromtimestamp(os.path.getctime(file_path))
        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # 构建文件信息
        file_info = {
            "filename": filename,
            "url": content_url,
            "size": file_size,
            "size_formatted": f"{file_size / 1024 / 1024:.2f} MB" if file_size > 1024 * 1024 else f"{file_size / 1024:.2f} KB",
            "content_type": content_type.value if content_type else None,
            "mime_type": mime_type,
            "file_extension": file_extension,
            "duration": duration,
            "duration_formatted": f"{duration // 60}:{duration % 60:02d}" if duration else None,
            "created_time": created_time.isoformat(),
            "modified_time": modified_time.isoformat(),
            "file_exists": True
        }
        
        logger.info(f"📋 获取课时 {lesson_id} 文件信息: {filename}")
        
        return {
            "success": True,
            "message": "获取文件信息成功",
            "data": {
                "lesson_id": lesson_id,
                "has_file": True,
                "file_info": file_info
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取课时文件信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取课时文件信息失败: {str(e)}"
        )


@router.get("/list")
async def list_lesson_materials(
    content_type: Optional[ContentType] = None,
    course_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """获取课时资料列表"""
    check_admin_permission(current_user)
    
    try:
        materials = []
        
        def scan_directory(base_dir, type_name):
            if not os.path.exists(base_dir):
                return
            
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                
                if os.path.isfile(item_path):
                    # 基础目录中的文件
                    relative_path = os.path.relpath(item_path, STATIC_DIR)
                    file_url = f"/static/{relative_path.replace(os.sep, '/')}"
                    
                    materials.append({
                        "filename": item,
                        "url": file_url,
                        "size": os.path.getsize(item_path),
                        "content_type": type_name,
                        "course_id": None,
                        "upload_time": datetime.fromtimestamp(
                            os.path.getctime(item_path)
                        ).isoformat()
                    })
                    
                elif os.path.isdir(item_path):
                    # 课程子目录
                    course_dir_id = item
                    
                    # 如果指定了course_id，只扫描对应的课程目录
                    if course_id and course_dir_id != course_id:
                        continue
                    
                    for sub_filename in os.listdir(item_path):
                        sub_filepath = os.path.join(item_path, sub_filename)
                        if os.path.isfile(sub_filepath):
                            relative_path = os.path.relpath(sub_filepath, STATIC_DIR)
                            file_url = f"/static/{relative_path.replace(os.sep, '/')}"
                            
                            materials.append({
                                "filename": sub_filename,
                                "url": file_url,
                                "size": os.path.getsize(sub_filepath),
                                "content_type": type_name,
                                "course_id": course_dir_id,
                                "upload_time": datetime.fromtimestamp(
                                    os.path.getctime(sub_filepath)
                                ).isoformat()
                            })
        
        # 扫描不同类型的目录
        if course_id:
            directories = [
                (os.path.join(MATERIALS_DIR, course_id)),
                (os.path.join(MATERIALS_DIR, course_id)),
                (os.path.join(MATERIALS_DIR, course_id))
            ]
        else:
            directories = [
                (os.path.join(MATERIALS_DIR, 'videos')),
                (os.path.join(MATERIALS_DIR, 'audios')),
                (os.path.join(MATERIALS_DIR, 'documents'))
            ]
        
        for directory, type_name in directories:
            scan_directory(directory, type_name)
        
        # 按上传时间倒序排列
        materials.sort(key=lambda x: x["upload_time"], reverse=True)
        
        return {
            "success": True,
            "data": materials,
            "total": len(materials)
        }
    
    except Exception as e:
        logger.error(f"❌ 获取资料列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取资料列表失败: {str(e)}"
        )