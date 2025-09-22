import os
import uuid
from typing import Optional
from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_

from models import get_db
from models.media import Media
# UserMediaAccess已合并到MediaPlayRecord中
from models.media_play_record import MediaPlayRecord
from models.course import CourseLesson, Course
from services.media_play_service import MediaPlayService
from models.schemas import (
    MediaInfoResponse, 
    OSSSyncRequest,
    OSSSyncResponse,
    PlayEventData
)
from models.user import User
from utils.auth_utils import get_current_user
from services.logger import get_logger
from services.learning_service import LearningService

logger = get_logger("media_api")

# 导入生成预签名URL的函数
try:
    from ossAPI.getPresignUrl import generate_download_url
    PRESIGN_URL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"预签名URL模块导入失败: {e}")
    PRESIGN_URL_AVAILABLE = False
    generate_download_url = None

# 导入重构后的OSS接口
try:
    from ossAPI.oss_client import get_oss_client, OSSClient
    from ossAPI.listObjectV2 import list_all_objects_v2, list_objects_paginated
    from ossAPI.getObjectV2 import get_object_v2, get_object_info
    import alibabacloud_oss_v2 as oss
    OSS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OSS模块导入失败: {e}，OSS功能将不可用")
    OSS_AVAILABLE = False
    oss = None
    get_oss_client = None
    get_object_v2 = None
    get_object_info = None
    list_all_objects_v2 = None
    list_objects_paginated = None

router = APIRouter(prefix="/media", tags=["媒体文件"])

# 媒体文件存储目录
STATIC_DIR = "static"
VIDEO_DIR = os.path.join(STATIC_DIR, "videos")
AUDIO_DIR = os.path.join(STATIC_DIR, "audios")
IMAGE_DIR = os.path.join(STATIC_DIR, "images")
DOCUMENT_DIR = os.path.join(STATIC_DIR, "documents")


# 支持的MIME类型
VIDEO_TYPES = {
    "video/mp4", "video/avi", "video/mov", "video/wmv", "video/flv", 
    "video/webm", "video/mkv", "video/3gp", "video/m4v"
}

AUDIO_TYPES = {
    "audio/mp3", "audio/wav", "audio/flac", "audio/aac", "audio/ogg", 
    "audio/wma", "audio/m4a", "audio/opus", "audio/mpeg"
}

IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp", 
    "image/svg+xml", "image/tiff", "image/ico"
}

DOCUMENT_TYPES = {
    "application/pdf", "application/msword", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", 
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint", 
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain", "text/csv", "application/rtf"
}

ALL_SUPPORTED_TYPES = VIDEO_TYPES | AUDIO_TYPES | IMAGE_TYPES | DOCUMENT_TYPES

async def handle_range_request_local(file_path: str, range_header: str, mime_type: str, file_size: int):
    """处理本地文件的Range请求"""
    # 解析Range头
    range_match = re.search(r'bytes=(\d*)-(\d*)', range_header)
    if not range_match:
        raise HTTPException(status_code=400, detail="无效的Range请求")
    
    start_str, end_str = range_match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    
    # 验证范围
    if start >= file_size or start > end:
        raise HTTPException(status_code=416, detail="请求范围不满足")
    
    # 如果end超过文件大小，调整为文件末尾
    if end >= file_size:
        end = file_size - 1
    
    # 计算实际范围
    actual_end = min(end, file_size - 1)
    content_length = actual_end - start + 1
    
    def file_iterator():
        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = content_length
            chunk_size = 8192
            
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)
    
    return StreamingResponse(
        file_iterator(),
        media_type=mime_type,
        headers={
            "Content-Range": f"bytes {start}-{actual_end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600"
        },
        status_code=206
    )

async def handle_range_request_oss(oss_key: str, range_header: str, mime_type: str, file_size: int, bucket_name: str):
    """处理OSS文件的Range请求"""
    # 解析Range头
    range_match = re.search(r'bytes=(\d*)-(\d*)', range_header)
    if not range_match:
        raise HTTPException(status_code=400, detail="无效的Range请求")
    
    start_str, end_str = range_match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    
    # 验证范围
    if start >= file_size or start > end:
        raise HTTPException(status_code=416, detail="请求范围不满足")
    
    # 如果end超过文件大小，调整为文件末尾
    if end >= file_size:
        end = file_size - 1
    
    # 计算实际范围
    actual_end = min(end, file_size - 1)
    content_length = actual_end - start + 1
    
    # 构造OSS Range头
    oss_range = f"bytes={start}-{actual_end}"
    
    def oss_iterator():
        try:
            if get_object_v2 is None:
                raise Exception("OSS获取对象功能不可用")
            result = get_object_v2(
                bucket=bucket_name,
                key=oss_key,
                range_header=oss_range
            )
            
            if result and hasattr(result, 'body') and result.body:
                body_stream = result.body
                try:
                    for chunk in body_stream.iter_bytes(block_size=8192):
                        if not chunk:
                            break
                        yield chunk
                finally:
                    if hasattr(body_stream, 'close'):
                        body_stream.close()
        except Exception as e:
            logger.error(f"OSS分片下载失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OSS文件下载失败: {str(e)}")
    
    return StreamingResponse(
        oss_iterator(),
        media_type=mime_type,
        headers={
            "Content-Range": f"bytes {start}-{actual_end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600"
        },
        status_code=206
    )

def get_media_type_from_extension(filename: str) -> Optional[str]:
    """根据文件扩展名判断媒体类型"""
    if not filename or '.' not in filename:
        return None
    
    ext = filename.split('.')[-1].lower()
    
    video_exts = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', '3gp', 'm4v'}
    audio_exts = {'mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a', 'opus'}
    image_exts = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'tiff', 'ico'}
    
    if ext in video_exts:
        return "video"
    elif ext in audio_exts:
        return "audio"
    elif ext in image_exts:
        return "image"
    
    return None

@router.get("", summary="获取媒体文件列表")
async def get_media_list(
    page: int = 1,
    size: int = 20,
    search: Optional[str] = None,
    media_type: Optional[str] = None,
    file_types: Optional[str] = None,
    course_id: Optional[str] = None,
    lesson_id: Optional[str] = None,
    exclude_associated: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取媒体文件列表
    
    Args:
        page: 页码，默认为1
        size: 每页数量，默认为20
        search: 搜索关键词，支持文件名模糊搜索
        media_type: 媒体类型过滤 (video/audio/image/document)
        file_types: 文件类型过滤，多个类型用逗号分隔 (如: "video,audio")
        course_id: 课程ID过滤
        lesson_id: 课时ID过滤
        exclude_associated: 是否排除已关联的媒体文件 (true/false)
    
    Note:
        结果默认按照文件名进行升序排序
    """
    # 使用joinedload预加载关联的课时和课程信息
    query = db.query(Media).options(
        joinedload(Media.lesson).joinedload(CourseLesson.course)
    )
    
    # 搜索功能：支持文件名模糊搜索
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Media.filename.ilike(search_term),
                Media.oss_key.ilike(search_term)
            )
        )
    
    # 媒体类型过滤（单个类型）
    if media_type:
        query = query.filter(Media.media_type == media_type)
    
    # 文件类型过滤（多个类型）
    if file_types:
        type_list = [t.strip().lower() for t in file_types.split(',') if t.strip()]
        valid_types = ['video', 'audio', 'image', 'document']
        filtered_types = [t for t in type_list if t in valid_types]
        if filtered_types:
            query = query.filter(Media.media_type.in_(filtered_types))
    
    if course_id:
        # Filter by course_id through lesson relationship
        # 使用子查询来避免影响joinedload
        from sqlalchemy import select
        subquery = select(CourseLesson.id).where(CourseLesson.course_id == course_id)
        query = query.filter(Media.lesson_id.in_(subquery))
    
    if lesson_id:
        query = query.filter(Media.lesson_id == lesson_id)
    
    # 过滤已关联的媒体文件
    if exclude_associated is not None:
        if exclude_associated:
            # 排除已关联的媒体文件（lesson_id不为空）
            query = query.filter(Media.lesson_id.is_(None))
        else:
            # 只显示已关联的媒体文件（lesson_id不为空）
            query = query.filter(Media.lesson_id.isnot(None))
    
    total = query.count()
    
    media_list = query.order_by(Media.filename).offset((page - 1) * size).limit(size).all()
    
    # 构建包含课时和课程信息的响应数据
    items = []
    for media in media_list:
        media_dict = {
            "id": media.id,
            "description": media.description,
            "filename": media.filename,
            "filepath": media.filepath,
            "media_type": media.media_type,
            "cover_url": media.cover_url,
            "duration": media.duration,
            "size": media.size,
            "mime_type": media.mime_type,
            "uploader_id": media.uploader_id,
            "upload_time": media.upload_time,
            "lesson_id": media.lesson_id,
            "lesson": None,
            "course": None
        }

        # 添加课时信息
        if media.lesson:
            media_dict["lesson"] = {
                "id": media.lesson.id,
                "title": media.lesson.title
            }


            # 添加课程信息
            if media.lesson.course:
                media_dict["course"] = {
                    "id": media.lesson.course.id,
                    "title": media.lesson.course.title
                }
        
        items.append(media_dict)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "search": search,
        "media_type": media_type,
        "file_types": file_types
    }

@router.get("/info/{media_id}", response_model=MediaInfoResponse, summary="获取媒体文件信息")
async def get_media_info(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取媒体文件信息"""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    return MediaInfoResponse.from_orm(media)

@router.delete("/{media_id}", summary="删除媒体文件")
async def delete_media(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除媒体文件"""
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    if media.filepath is not None:
        file_path = os.path.join(STATIC_DIR, media.filepath.lstrip('/static/'))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"✅ 文件已删除: {file_path}")
            except Exception as e:
                logger.error(f"❌ 删除文件失败: {str(e)}")
    
    db.delete(media)
    db.commit()
    
    logger.info(f"✅ 媒体记录已删除: {media_id}")
    return {"message": "媒体文件删除成功"}

@router.post("/sync-oss", summary="同步OSS对象到数据库")
async def sync_oss_objects(
    sync_request: OSSSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """同步OSS对象到数据库"""
    try:
        # 检查OSS功能是否可用
        if not OSS_AVAILABLE:
            raise HTTPException(status_code=500, detail="OSS功能不可用，请检查SDK安装")
        
        # 从环境变量获取OSS配置
        bucket_name = os.getenv('OSS_BUCKET_NAME', 'zhangqi-video11')
        # 使用重构后的OSS客户端
        try:
            if not get_oss_client:
                raise HTTPException(status_code=500, detail="OSS客户端不可用")
            oss_client = get_oss_client()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OSS客户端初始化失败: {str(e)}")
        
        synced_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        total_objects = 0
        
        try:
            # 使用重构后的分页列表接口
            if not list_all_objects_v2:
                raise HTTPException(status_code=500, detail="OSS列表功能不可用")
            objects = list_all_objects_v2(bucket=bucket_name, prefix=sync_request.prefix)
            total_objects += len(objects)

            print(f"📄 当前页对象数量: {len(objects)}")


            for obj in objects:
                try:
                    # 检查文件类型
                    media_type = get_media_type_from_extension(obj['key'])
                    if not media_type:
                        skipped_count += 1
                        continue

                    # 检查是否已存在
                    existing_media = db.query(Media).filter(Media.oss_key == obj['key']).first()
                    if existing_media:
                        # 强制更新模式
                        existing_media.filename = obj['key'].split('/')[-1]  # type: ignore
                        existing_media.size = obj['size']  # type: ignore
                        if obj.get('etag'):
                            existing_media.oss_etag = str(obj.get('etag')).strip('"')  # type: ignore
                        if obj.get('storage_class'):
                            # 直接使用字符串值
                            storage_class_value = obj.get('storage_class')
                            # 验证是否为有效的存储类型
                            valid_storage_classes = ['Standard', 'IA', 'Archive', 'ColdArchive']
                            if storage_class_value in valid_storage_classes:
                                existing_media.oss_storage_class = storage_class_value  # type: ignore
                        if obj.get('last_modified'):
                            existing_media.oss_last_modified = obj.get('last_modified')  # type: ignore
                        # 注意：需要根据实际SQLAlchemy模型配置调整赋值方式
                        existing_media.upload_status = "completed"  # type: ignore
                        existing_media.storage_type = "oss"  # type: ignore
                        existing_media.media_type = media_type  # type: ignore
                        db.add(existing_media)
                        synced_count += 1
                    else:
                        # 创建新记录
                        filename = obj['key'].split('/')[-1]
                        # 生成文件路径（OSS对象的key）
                        filepath = f"oss://{bucket_name}/{obj['key']}"
                        # 处理OSS存储类型
                        oss_storage_class = None
                        if obj.get('storage_class'):
                            storage_class_value = obj.get('storage_class')
                            # 验证是否为有效的存储类型
                            valid_storage_classes = ['Standard', 'IA', 'Archive', 'ColdArchive']
                            if storage_class_value in valid_storage_classes:
                                oss_storage_class = storage_class_value
                        
                        # 获取第一个用户作为默认上传者
                        default_user = db.query(User).first()
                        uploader_id = default_user.id if default_user else str(uuid.uuid4())
                        
                        new_media = Media(
                            filename=filename,
                            filepath=filepath,
                            media_type=media_type,
                            size=obj['size'],
                            uploader_id=uploader_id,
                            upload_status="completed",
                            storage_type="oss",
                            oss_key=obj['key'],
                            oss_etag=str(obj['etag']).strip('"') if obj.get('etag') else None,
                            oss_storage_class=oss_storage_class,
                            oss_last_modified=obj.get('last_modified')
                        )
                        db.add(new_media)
                        synced_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"处理对象 {obj.get('key', 'unknown')} 时出错: {str(e)}")
                    logger.error(f"处理OSS对象失败: {obj.get('key', 'unknown')}, 错误: {str(e)}")
                    continue
            
            # 提交数据库更改
            db.commit()
            
            # 检查数据库中存在但OSS中不存在的文件，设置为异常状态
            logger.info("开始检查数据库中存在但OSS中不存在的文件...")
            
            # 查询所有OSS存储类型且状态为COMPLETED的媒体文件
            oss_media_files = db.query(Media).filter(
                Media.storage_type == "oss",
                Media.upload_status == "completed",
                Media.oss_key.isnot(None)
            ).all()
            
            missing_count = 0
            for media in oss_media_files:
                try:
                    # 检查OSS对象是否存在
                    if not oss_client.object_exists(bucket_name, str(media.oss_key)):
                        # OSS中不存在，设置为异常状态
                        media.upload_status = "failure"  # type: ignore
                        media.error_message = f"OSS对象不存在: {media.oss_key}"  # type: ignore
                        missing_count += 1
                        logger.warning(f"发现缺失的OSS对象: {media.oss_key}")
                except Exception as e:
                    logger.error(f"检查OSS对象存在性失败: {media.oss_key}, 错误: {str(e)}")
                    continue
            
            if missing_count > 0:
                db.commit()
                logger.info(f"✅ 已标记 {missing_count} 个缺失的OSS文件为异常状态")
            else:
                logger.info("✅ 所有数据库中的OSS文件在对象存储中都存在")
            
        except Exception as e:
            db.rollback()
            logger.error(f"OSS同步失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OSS同步失败: {str(e)}")
        
        result = OSSSyncResponse(
            success=True,
            message="OSS对象同步完成",
            total_objects=total_objects,
            synced_count=synced_count,
            skipped_count=skipped_count,
            error_count=error_count,
            errors=errors[:10],  # 只返回前10个错误
            missing_files_count=missing_count if 'missing_count' in locals() else 0
        )
        
        logger.info(f"✅ OSS同步完成: 总计{total_objects}个对象，同步{synced_count}个，跳过{skipped_count}个，错误{error_count}个")
        return result
        
    except Exception as e:
        logger.error(f"❌ OSS同步失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OSS同步失败: {str(e)}")

@router.get("/presign/{media_id}", summary="生成媒体文件的预签名URL")
async def generate_presign_url(
    media_id: str,
    expires_in_hours: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成媒体文件的预签名URL
    
    Args:
        media_id: 媒体文件ID
        expires_in_hours: URL过期时间（小时），默认1小时
        
    Returns:
        包含预签名URL信息的字典
    """
    # 获取媒体文件信息
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    try:
        # 记录用户播放事件
        play_record = db.query(MediaPlayRecord).filter(
            MediaPlayRecord.user_id == current_user.id,
            MediaPlayRecord.media_id == media_id
        ).first()
        
        current_time = datetime.now()
        
        if play_record:
            # 更新播放次数和最后播放时间
            new_play_count = play_record.play_count + 1
            db.query(MediaPlayRecord).filter(
                MediaPlayRecord.user_id == current_user.id,
                MediaPlayRecord.media_id == media_id
            ).update({
                MediaPlayRecord.play_count: new_play_count,
                MediaPlayRecord.last_played_at: current_time
            })
            logger.info(f"📊 更新用户播放记录: 用户{current_user.id} 播放媒体{media_id} 第{new_play_count}次")
            play_count = new_play_count
        else:
            # 创建新的播放记录
            play_record = MediaPlayRecord(
                user_id=current_user.id,
                media_id=media_id,
                play_count=1,
                last_played_at=current_time,
                first_played_at=current_time
            )
            db.add(play_record)
            logger.info(f"📊 创建用户播放记录: 用户{current_user.id} 首次播放媒体{media_id}")
            play_count = 1
        
        db.commit()
        
        # 自动开始学习记录（如果媒体文件关联了课时）
        try:
            if media.lesson_id:
                # 调用start_lesson接口
                from api.learning import start_lesson
                await start_lesson(media.lesson_id, current_user, db)
                logger.info(f"📚 自动开始学习记录: 用户{current_user.id} 开始学习课时{media.lesson_id}")
        except Exception as e:
            logger.warning(f"⚠️ 自动开始学习记录失败: {str(e)}")
        
        # 检查文件存储类型
        if str(media.storage_type) == "oss" and media.oss_key is not None:
            # OSS文件处理
            if not PRESIGN_URL_AVAILABLE or generate_download_url is None:
                raise HTTPException(status_code=500, detail="OSS预签名URL功能不可用")
            
            # 从环境变量获取OSS配置
            bucket_name = os.getenv('OSS_BUCKET_NAME', 'zhangqi-video11')
            region = os.getenv('OSS_REGION', 'cn-guangzhou')
            
            # 生成预签名URL
            result = generate_download_url(
                bucket=bucket_name,
                key=str(media.oss_key),
                expires_in_hours=expires_in_hours,
                region=region
            )
            
            logger.info(f"✅ 成功生成OSS预签名URL: {media.filename}")
            
            return {
                "success": True,
                "message": "预签名URL生成成功",
                "data": {
                    "media_id": media_id,
                    "filename": media.filename,
                    "url": result['url'],
                    "expiration": result['expiration_str'],
                    "expires_in_hours": expires_in_hours,
                    "play_count": play_count
                }
            }
        else:
            # 本地文件处理
            if media.filepath is None:
                raise HTTPException(status_code=400, detail="本地文件路径不存在")
            
            # 构建本地文件服务地址
            local_url = f"http://10.98.24.238:8000{media.filepath}"
            
            logger.info(f"✅ 成功生成本地文件URL: {media.filename}")
            
            return {
                "success": True,
                "message": "本地文件URL生成成功",
                "data": {
                    "media_id": media_id,
                    "filename": media.filename,
                    "url": local_url,
                    "expiration": None,  # 本地文件无过期时间
                    "expires_in_hours": None,
                    "play_count": play_count
                }
            }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 生成预签名URL失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成预签名URL失败: {str(e)}")





@router.get("/preview/{media_id}", summary="预览媒体文件")
async def preview_media(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    预览媒体文件
    
    Args:
        media_id: 媒体文件ID
        
    Returns:
        媒体文件预览信息，包括预览URL和类型
    """
    # 获取媒体文件信息
    media = db.query(Media).filter(Media.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    try:
        # 检查文件是否存在
        if not media.filepath or not os.path.exists(media.filepath):
            raise HTTPException(status_code=404, detail="媒体文件不存在")
        
        # 根据媒体类型生成预览信息
        preview_info = {
            "media_id": media.id,
            "filename": media.filename,
            "media_type": media.media_type,
            "file_size": media.size,
            "duration": media.duration,
            "mime_type": media.mime_type,
            "preview_url": None,
            "preview_type": None
        }
        
        # 构建预览URL
        if media.storage_type == "oss" and media.oss_key:
            # OSS文件
            if PRESIGN_URL_AVAILABLE and generate_download_url:
                bucket_name = os.getenv('OSS_BUCKET_NAME', 'zhangqi-video11')
                region = os.getenv('OSS_REGION', 'cn-guangzhou')
                
                result = generate_download_url(
                    bucket=bucket_name,
                    key=str(media.oss_key),
                    expires_in_hours=1,
                    region=region
                )
                preview_info["preview_url"] = result['url']
            else:
                raise HTTPException(status_code=500, detail="OSS预览功能不可用")
        else:
            # 本地文件
            preview_info["preview_url"] = f"http://10.98.24.251:8000{media.filepath}"
        
        # 根据媒体类型设置预览类型
        if media.media_type == "image":
            preview_info["preview_type"] = "image"
        elif media.media_type == "video":
            preview_info["preview_type"] = "video"
        elif media.media_type == "audio":
            preview_info["preview_type"] = "audio"
        elif media.media_type == "document":
            preview_info["preview_type"] = "document"
        else:
            preview_info["preview_type"] = "unknown"
        
        logger.info(f"✅ 成功生成媒体文件预览: {media.filename} ({media.media_type})")
        
        return {
            "success": True,
            "message": "媒体文件预览信息获取成功",
            "data": preview_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取媒体文件预览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取媒体文件预览失败: {str(e)}")


@router.post("/report", summary="上报视频播放事件")
async def report_play_event(
    event_data: PlayEventData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    处理前端播放事件上报
    支持 play/pause/seek/heartbeat/ended 事件类型
    """
    try:
        # 验证用户权限
        if event_data.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限操作其他用户的播放记录")
        
        # 验证媒体文件是否存在
        media = db.query(Media).filter(Media.id == event_data.media_id).first()
        if not media:
            raise HTTPException(status_code=404, detail="媒体文件不存在")
        
        # 检查并更新媒体文件时长
        if event_data.duration_time and media.duration != event_data.duration_time:
            # 如果上报的时长与数据库中的不一致,更新数据库中的时长
            logger.info(f"更新媒体文件时长: {media.id} - 原时长:{media.duration}s, 新时长:{event_data.duration_time}s")
            media.duration = event_data.duration_time
            db.commit()

        # 创建视频播放服务实例
        video_service = MediaPlayService(db)
        
        # 处理播放事件
        result = video_service.process_play_event(
            user_id=event_data.user_id,
            media_id=event_data.media_id,
            event_type=event_data.event_type,
            current_time=event_data.current_time,
            previous_time=event_data.previous_time,
            progress=event_data.progress,
            playback_rate=event_data.playback_rate or 1.0,
            volume=event_data.volume or 1.0,
            is_fullscreen=event_data.is_fullscreen or False,
            device_info=event_data.device_info,
            extra_data=event_data.extra_data
        )
        
        # 自动更新学习进度（如果媒体文件关联了课时）
        # 只在特定事件下更新，避免不必要的数据库操作
        if event_data.event_type in ["pause", "ended", "heartbeat"]:
            try:
                if media.lesson_id:
                    learning_service = LearningService(db)
                    
                    # 更新课时学习进度（内部会自动更新媒体观看进度）
                    learning_service.update_lesson_progress(
                        current_user.id,
                        media.lesson_id
                    )
                    logger.info(f"📚 自动更新课时学习进度: 用户{current_user.id} 课时{media.lesson_id} 事件:{event_data.event_type}")
                    
            except Exception as e:
                logger.warning(f"⚠️ 自动更新学习进度失败: {str(e)}")
        
        logger.info(f"✅ 播放事件上报成功: {event_data.event_type} - 用户:{event_data.user_id} 媒体:{event_data.media_id}")
        
        return {
            "success": True,
            "message": "播放事件上报成功",
            "data": result
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"❌ 播放事件上报参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 播放事件上报失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"播放事件上报失败: {str(e)}")




