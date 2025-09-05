"""
视频相关API
提供视频上传、播放、管理等功能
"""

import os
import uuid
import cv2
import ffmpeg
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import re

from models.user import User
from api.auth import get_current_user
from models import get_db
from models.schemas import VideoInfoResponse, VideoListResponse
from models.video import Video
from services.logger import get_logger

logger = get_logger("video_api")

router = APIRouter(prefix="/videos", tags=["视频"])

# 静态文件存储目录
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# 视频文件存储目录
VIDEO_DIR = os.path.join(STATIC_DIR, 'videos')
if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)

# 封面图片存储目录
COVER_DIR = os.path.join(STATIC_DIR, 'covers')
if not os.path.exists(COVER_DIR):
    os.makedirs(COVER_DIR)



def extract_video_cover(video_path: str, video_id: str) -> str:
    """提取视频封面"""
    try:
        logger.info(f"🖼️  开始提取视频封面: {video_path}")
        
        # 使用ffmpeg提取第一帧
        cover_filename = f"{video_id}_cover.jpg"
        cover_path = os.path.join(COVER_DIR, cover_filename)
        
        # 使用ffmpeg提取第一帧作为封面
        try:
            # 先检查文件是否存在
            if not os.path.exists(video_path):
                raise Exception(f"视频文件不存在: {video_path}")
            
            # 使用ffmpeg提取第一帧
            stream = ffmpeg.input(video_path, ss=0)  # 从0秒开始
            stream = ffmpeg.filter(stream, 'scale', 640, -1)  # 缩放到640宽度，保持比例
            stream = ffmpeg.output(stream, cover_path, vframes=1, q=2)  # 只输出1帧，高质量
            
            # 运行ffmpeg命令
            result = ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True, quiet=True)
            
            logger.info(f"✅ ffmpeg命令执行成功")
            
            # 检查文件是否成功创建
            if os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
                cover_url = f"/static/covers/{cover_filename}"
                logger.info(f"✅ 视频封面提取成功: {cover_url}")
                return cover_url
            else:
                raise Exception("封面文件创建失败")
                
        except Exception as e:
            logger.warning(f"⚠️  ffmpeg提取封面失败: {str(e)}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            # 如果ffmpeg失败，尝试使用OpenCV
            return extract_video_cover_opencv(video_path, video_id)
            
    except Exception as e:
        logger.error(f"❌ 视频封面提取失败: {str(e)}")
        return None

def extract_video_cover_opencv(video_path: str, video_id: str) -> str:
    """使用OpenCV提取视频封面（备用方案）"""
    try:
        logger.info(f"🖼️  使用OpenCV提取视频封面: {video_path}")
        
        # 尝试打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"❌ 无法打开视频文件: {video_path}")
            return None
        
        # 读取第一帧
        ret, frame = cap.read()
        if not ret:
            logger.error(f"❌ 无法读取视频帧: {video_path}")
            cap.release()
            return None
        
        # 保存封面
        cover_filename = f"{video_id}_cover.jpg"
        cover_path = os.path.join(COVER_DIR, cover_filename)
        
        # 调整图片大小
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            new_width = 640
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
        
        # 保存图片
        success = cv2.imwrite(cover_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        cap.release()
        
        if success:
            cover_url = f"/static/covers/{cover_filename}"
            logger.info(f"✅ OpenCV封面提取成功: {cover_url}")
            return cover_url
        else:
            logger.error(f"❌ 封面保存失败: {cover_path}")
            return None
            
    except Exception as e:
        logger.error(f"❌ OpenCV封面提取失败: {str(e)}")
        return None

def get_video_duration(video_path: str) -> int:
    """获取视频时长"""
    try:
        logger.info(f"⏱️  开始获取视频时长: {video_path}")
        
        # 使用ffmpeg获取视频时长
        try:
            probe = ffmpeg.probe(video_path)
            # 查找视频流
            video_stream = None
            for stream in probe['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                    break
            
            if video_stream and 'duration' in video_stream:
                duration = float(video_stream['duration'])
                logger.info(f"✅ 视频时长获取成功: {duration}秒")
                return int(duration)
            else:
                logger.warning(f"⚠️  无法从ffmpeg probe获取时长信息")
                return get_video_duration_opencv(video_path)
            
        except Exception as e:
            logger.warning(f"⚠️  ffmpeg获取时长失败: {str(e)}")
            # 如果ffmpeg失败，尝试使用OpenCV
            return get_video_duration_opencv(video_path)
            
    except Exception as e:
        logger.error(f"❌ 视频时长获取失败: {str(e)}")
        return None

def get_video_duration_opencv(video_path: str) -> int:
    """使用OpenCV获取视频时长（备用方案）"""
    try:
        logger.info(f"⏱️  使用OpenCV获取视频时长: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"❌ 无法打开视频文件: {video_path}")
            return None
        
        # 获取总帧数和帧率
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        cap.release()
        
        if total_frames > 0 and fps > 0:
            duration = total_frames / fps
            logger.info(f"✅ OpenCV时长获取成功: {duration}秒")
            return int(duration)
        else:
            logger.error(f"❌ 无法获取视频时长信息")
            return None
            
    except Exception as e:
        logger.error(f"❌ OpenCV时长获取失败: {str(e)}")
        return None

@router.post("/upload", response_model=VideoInfoResponse)
async def upload_video(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传视频"""
    try:
        # 检查文件类型
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="只支持视频文件")
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(VIDEO_DIR, filename)

        # 保存文件
        try:
            with open(filepath, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"❌ 文件保存失败: {str(e)}")
            # 清理已保存的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            raise HTTPException(status_code=500, detail="文件保存失败")

        # 创建视频记录
        video_id = str(uuid.uuid4())
        # 计算视频文件大小
        file_size = os.path.getsize(filepath)
        video = Video(
            id=video_id,
            title=title,
            description=description,
            filename=filename,
            filepath=f"/static/videos/{filename}",  # 保存相对路径
            uploader_id=current_user.id,
            size=file_size
        )
        
        # 提取封面和获取时长
        try:
            # 提取封面
            cover_url = extract_video_cover(filepath, video_id)
            if cover_url:
                video.cover_url = cover_url
            
            # 获取时长
            duration = get_video_duration(filepath)
            if duration:
                video.duration = duration
                
        except Exception as e:
            logger.warning(f"⚠️  视频信息提取失败: {str(e)}")
            # 即使提取失败也继续保存视频记录
        
        # 保存到数据库
        db.add(video)
        db.commit()
        db.refresh(video)
        
        logger.info(f"✅ 视频上传成功: {video.title} (ID: {video.id})")
        
        return VideoInfoResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            filename=video.filename,
            filepath=video.filepath,
            cover_url=video.cover_url,
            duration=video.duration,
            size=video.size,
            uploader_id=video.uploader_id,
            upload_time=video.upload_time.isoformat() if video.upload_time else None
        )
        
    except HTTPException as e:
        # 上传失败时删除本地视频文件
        cleanup_uploaded_files(locals())
        raise e
    except Exception as e:
        # 上传失败时删除本地视频文件
        cleanup_uploaded_files(locals())
        logger.error(f"❌ 视频上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"视频上传失败: {str(e)}")

def cleanup_uploaded_files(local_vars: dict):
    """清理上传过程中创建的文件"""
    try:
        # 清理原始文件
        if 'filepath' in local_vars and os.path.exists(local_vars['filepath']):
            try:
                os.remove(local_vars['filepath'])
                logger.info(f"🗑️ 已删除本地视频文件: {local_vars['filepath']}")
            except Exception as del_e:
                logger.warning(f"⚠️ 删除本地视频文件失败: {del_e}")
        
        # 清理转换后的文件（如果存在）
        if 'mp4_filepath' in local_vars and os.path.exists(local_vars['mp4_filepath']):
            try:
                os.remove(local_vars['mp4_filepath'])
                logger.info(f"🗑️ 已删除转换后的视频文件: {local_vars['mp4_filepath']}")
            except Exception as del_e:
                logger.warning(f"⚠️ 删除转换后的视频文件失败: {del_e}")
                
    except Exception as e:
        logger.warning(f"⚠️ 清理文件时出错: {str(e)}")

@router.get("/list", response_model=VideoListResponse)
async def list_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取视频列表"""
    try:

        videos = db.query(Video).all()
        # # 根据用户角色获取视频列表
        # if current_user.role in ['admin', 'superadmin']:
        #     # 管理员可以看到所有视频
        #     videos = db.query(Video).all()
        # else:
        #     # 普通用户只能看到自己上传的视频
        #     videos = db.query(Video).filter(Video.uploader_id == current_user.id).all()
        
        video_list = []
        for v in videos:
            video_list.append(VideoInfoResponse(
                id=v.id,
                title=v.title,
                description=v.description,
                filename=v.filename,
                filepath=v.filepath,
                cover_url=v.cover_url,
                duration=v.duration,
                size=v.size,
                uploader_id=v.uploader_id,
                upload_time=v.upload_time.isoformat() if v.upload_time else None
            ))
        
        logger.info(f"📋 用户 {current_user.email} 获取视频列表: {len(video_list)} 个视频")
        
        return VideoListResponse(videos=video_list)
        
    except Exception as e:
        logger.error(f"❌ 获取视频列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取视频列表失败")

@router.get("/info/{video_id}", response_model=VideoInfoResponse)
async def get_video_info(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取视频信息"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 检查用户权限
        if (video.uploader_id != current_user.id and 
            current_user.role not in ['admin', 'superadmin']):
            raise HTTPException(status_code=403, detail="无权限访问该视频")
        
        logger.info(f"📹 用户 {current_user.email} 获取视频信息: {video.title}")
        
        return VideoInfoResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            filename=video.filename,
            filepath=video.filepath,
            cover_url=video.cover_url,
            size=video.size,
            duration=video.duration,
            uploader_id=video.uploader_id,
            upload_time=video.upload_time.isoformat() if video.upload_time else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取视频信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取视频信息失败")

@router.get("/play/{video_id}")
async def play_video(
    video_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """播放视频"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 检查用户权限
        if (video.uploader_id != current_user.id and 
            current_user.role not in ['admin', 'superadmin']):
            raise HTTPException(status_code=403, detail="无权限访问该视频")
        
        # 从数据库中的相对路径转换为绝对路径
        if video.filepath.startswith('/static/'):
            video_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), video.filepath.lstrip('/'))
        else:
            video_path = video.filepath
        
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        # 获取文件信息
        file_size = os.path.getsize(video_path)
        mime_type = "video/mp4"  # 默认MIME类型
        
        # 根据文件扩展名设置MIME类型
        ext = os.path.splitext(video_path)[1].lower()
        if ext == '.mov':
            mime_type = "video/quicktime"
        elif ext == '.avi':
            mime_type = "video/x-msvideo"
        elif ext == '.mkv':
            mime_type = "video/x-matroska"
        elif ext == '.webm':
            mime_type = "video/webm"
        
        # 检查Range请求
        range_header = request.headers.get("Range")

        logger.info(f"🎬 播放视频: {video.title} ({file_size} bytes) ({range_header})")
        
        if range_header:
            # 处理Range请求
            return await handle_range_request(video_path, range_header, mime_type, file_size, video_id, current_user.id)
        else:
            # 返回完整文件
            logger.info(f"🎬 用户 {current_user.email} 播放视频: {video.title} ({file_size} bytes)")
            
            return FileResponse(
                path=video_path,
                media_type=mime_type,
                filename=video.filename,
                headers={
                    "Content-Length": str(file_size),
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=3600"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 视频播放失败: {str(e)}")
        raise HTTPException(status_code=500, detail="视频播放失败")

async def handle_range_request(video_path: str, range_header: str, mime_type: str, file_size: int, video_id: str, user_id: str):
    """处理Range请求"""
    # 解析Range头
    range_match = re.search(r'bytes=(\d*)-(\d*)', range_header)
    if not range_match:
        raise HTTPException(status_code=400, detail="无效的Range请求")
    
    start_str, end_str = range_match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    
    # 验证范围
    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(status_code=416, detail="请求范围不满足")
    
    # 计算实际范围
    actual_end = min(end, file_size - 1)
    content_length = actual_end - start + 1
    
    def file_iterator():
        with open(video_path, 'rb') as f:
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
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600"
        },
        status_code=206
    )




