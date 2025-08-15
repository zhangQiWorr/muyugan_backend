"""
图片上传相关API
提供图片上传、管理等功能，支持聊天对话中的图片识别
"""

import os
import uuid
import shutil
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import re
from PIL import Image
import io

from models.user import User
from api.auth import get_current_user
from models import get_db
from utils.logger import get_logger

logger = get_logger("image_api")

router = APIRouter(prefix="/images", tags=["图片"])

# 静态文件存储目录
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# 图片文件存储目录
IMAGE_DIR = os.path.join(STATIC_DIR, 'images')
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# 支持的图片格式
SUPPORTED_IMAGE_TYPES = {
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg', 
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp'
}

# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_image_file(file: UploadFile) -> tuple[bool, str]:
    """
    验证图片文件
    
    Args:
        file: 上传的文件
        
    Returns:
        (是否有效, 错误信息)
    """
    # 检查文件大小
    if file.size and file.size > MAX_FILE_SIZE:
        return False, f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)"
    
    # 检查文件类型
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        supported_types = ', '.join(SUPPORTED_IMAGE_TYPES.keys())
        return False, f"不支持的图片格式，支持的格式: {supported_types}"
    
    return True, ""


def save_image_file(file: UploadFile, filename: str) -> str:
    """
    保存图片文件
    
    Args:
        file: 上传的文件
        filename: 文件名
        
    Returns:
        保存的文件路径
    """
    filepath = os.path.join(IMAGE_DIR, filename)
    
    try:
        # 读取文件内容
        content = file.file.read()
        
        # 验证图片格式
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()  # 验证图片完整性
        except Exception as e:
            raise HTTPException(status_code=400, detail="无效的图片文件")
        
        # 保存文件
        with open(filepath, "wb") as buffer:
            buffer.write(content)
            
        return filepath
        
    except Exception as e:
        logger.error(f"❌ 图片保存失败: {str(e)}")
        # 清理已保存的文件
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail="图片保存失败")


def cleanup_uploaded_files(local_vars: dict):
    """清理上传过程中创建的文件"""
    filepath = local_vars.get('filepath')
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            logger.info(f"🧹 清理临时文件: {filepath}")
        except Exception as e:
            logger.warning(f"⚠️ 清理文件失败: {str(e)}")


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传图片"""
    try:

        logger.info(f"🚀 图片上传开始")

        # 验证文件
        is_valid, error_msg = validate_image_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_extension = SUPPORTED_IMAGE_TYPES.get(file.content_type, '.jpg')
        image_id = str(uuid.uuid4())
        filename = f"{timestamp}_{image_id}{file_extension}"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # 保存文件
        try:
            filepath = save_image_file(file, filename)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ 图片保存失败: {str(e)}")
            raise HTTPException(status_code=500, detail="图片保存失败")
        
        # 构建访问URL
        image_url = f"/static/images/{filename}"
        
        # 获取文件大小
        file_size = os.path.getsize(filepath)
        
        # 记录上传信息
        upload_info = {
            "id": image_id,
            "filename": filename,
            "filepath": filepath,
            "url": image_url,
            "size": file_size,
            "content_type": file.content_type,
            "uploader_id": current_user.id,
            "description": description,
            "upload_time": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ 图片上传成功: {filename} (ID: {image_id})")
        logger.info(f"📊 文件大小: {file_size // 1024}KB")
        logger.info(f"🔗 访问URL: {image_url}")
        
        return {
            "success": True,
            "message": "图片上传成功",
            "data": {
                "id": image_id,
                "filename": filename,
                "url": image_url,
                "size": file_size,
                "content_type": file.content_type,
                "uploader_id": current_user.id,
                "description": description,
                "upload_time": upload_info["upload_time"]
            }
        }
        
    except HTTPException as e:
        # 上传失败时删除本地文件
        cleanup_uploaded_files(locals())
        raise e
    except Exception as e:
        # 上传失败时删除本地文件
        cleanup_uploaded_files(locals())
        logger.error(f"❌ 图片上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图片上传失败: {str(e)}")


@router.get("/{image_id}")
async def get_image_info(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取图片信息"""
    try:
        # 这里可以添加数据库查询逻辑来获取图片信息
        # 目前简化处理，直接返回文件信息
        
        # 查找图片文件
        image_files = []
        for filename in os.listdir(IMAGE_DIR):
            if image_id in filename:
                filepath = os.path.join(IMAGE_DIR, filename)
                if os.path.isfile(filepath):
                    image_files.append({
                        "id": image_id,
                        "filename": filename,
                        "url": f"/static/images/{filename}",
                        "size": os.path.getsize(filepath),
                        "upload_time": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    })
        
        if not image_files:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        return {
            "success": True,
            "data": image_files[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取图片信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图片信息失败: {str(e)}")


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除图片"""
    try:
        # 查找并删除图片文件
        deleted_files = []
        for filename in os.listdir(IMAGE_DIR):
            if image_id in filename:
                filepath = os.path.join(IMAGE_DIR, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                        deleted_files.append(filename)
                        logger.info(f"🗑️ 删除图片文件: {filename}")
                    except Exception as e:
                        logger.error(f"❌ 删除文件失败: {str(e)}")
        
        if not deleted_files:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        return {
            "success": True,
            "message": f"成功删除 {len(deleted_files)} 个图片文件",
            "deleted_files": deleted_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除图片失败: {str(e)}")


@router.get("/list")
async def list_images(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户上传的图片列表"""
    try:
        # 获取当前用户上传的图片
        image_list = []
        for filename in os.listdir(IMAGE_DIR):
            if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                filepath = os.path.join(IMAGE_DIR, filename)
                if os.path.isfile(filepath):
                    # 这里可以添加用户权限检查
                    # 目前简化处理，返回所有图片
                    image_list.append({
                        "filename": filename,
                        "url": f"/static/images/{filename}",
                        "size": os.path.getsize(filepath),
                        "upload_time": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    })
        
        # 按上传时间排序
        image_list.sort(key=lambda x: x["upload_time"], reverse=True)
        
        return {
            "success": True,
            "data": {
                "images": image_list,
                "total": len(image_list)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 获取图片列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图片列表失败: {str(e)}") 