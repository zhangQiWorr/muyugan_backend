"""
文件上传工具
处理用户头像等文件上传功能
"""
import os
import uuid
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io
from services.logger import get_logger

logger = get_logger("file_upload")

# 配置
UPLOAD_DIR = "static/images/src_avatars"
AVATAR_DIR = "static/images/avatars"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
AVATAR_SIZES = {
    "small": (64, 64),
    "medium": (128, 128),
    "large": (256, 256)
}


def ensure_directories():
    """确保上传目录存在"""
    for directory in [UPLOAD_DIR, AVATAR_DIR]:
        Path(directory).mkdir(parents=True, exist_ok=True)


def validate_image_file(file: UploadFile) -> Tuple[bool, str]:
    """
    验证图片文件
    
    Args:
        file: 上传的文件
        
    Returns:
        (is_valid, error_message)
    """
    # 检查文件大小
    if file.size and file.size > MAX_FILE_SIZE:
        return False, f"文件大小超过限制 ({MAX_FILE_SIZE / 1024 / 1024}MB)"
    
    # 检查文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return False, f"不支持的文件类型: {file.content_type}"
    
    return True, ""


def process_avatar_image(image_data: bytes, filename: str) -> dict:
    """
    处理头像图片，生成不同尺寸的版本
    
    Args:
        image_data: 图片数据
        filename: 文件名
        
    Returns:
        包含不同尺寸文件路径的字典
    """
    try:
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB模式（如果是RGBA，去除透明背景）
        if image.mode in ('RGBA', 'LA'):
            # 创建白色背景
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 生成不同尺寸的图片
        avatar_paths = {}
        base_name = Path(filename).stem
        
        for size_name, (width, height) in AVATAR_SIZES.items():
            # 调整图片尺寸，保持宽高比
            resized_image = image.copy()
            resized_image.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # 创建正方形画布
            canvas = Image.new('RGB', (width, height), (255, 255, 255))
            
            # 计算居中位置
            x = (width - resized_image.width) // 2
            y = (height - resized_image.height) // 2
            
            # 粘贴调整后的图片
            canvas.paste(resized_image, (x, y))
            
            # 保存文件
            size_filename = f"{base_name}_{size_name}.jpg"
            file_path = os.path.join(AVATAR_DIR, size_filename)
            canvas.save(file_path, 'JPEG', quality=85, optimize=True)
            
            avatar_paths[size_name] = f"/{file_path}"
        
        logger.info(f"✅ 头像处理完成: {filename}")
        return avatar_paths
        
    except Exception as e:
        logger.error(f"❌ 头像处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像处理失败: {str(e)}"
        )


async def save_avatar_file(file: UploadFile, user_id: str) -> dict:
    """
    保存用户头像文件
    
    Args:
        file: 上传的文件
        user_id: 用户ID
        
    Returns:
        包含头像URL的字典
    """
    # 确保目录存在
    ensure_directories()
    
    # 验证文件
    is_valid, error_message = validate_image_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 生成唯一文件名
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"avatar_{user_id}_{uuid.uuid4().hex}{file_extension}"
        
        # 处理头像图片
        avatar_paths = process_avatar_image(content, unique_filename)
        
        # 保存原始文件
        original_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(original_path, "wb") as f:
            f.write(content)
        
        logger.info(f"✅ 头像文件保存成功: {unique_filename}")
        
        return {
            "original": f"/static/uploads/{unique_filename}",
            "small": avatar_paths["small"],
            "medium": avatar_paths["medium"],
            "large": avatar_paths["large"],
            "filename": unique_filename
        }
        
    except Exception as e:
        logger.error(f"❌ 头像文件保存失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像文件保存失败: {str(e)}"
        )

def delete_avatar_files(avatar_url: str):
    """
    删除头像文件
    
    Args:
        avatar_url: 头像URL (可能是任何尺寸的头像URL)
    """
    try:
        if not avatar_url:
            return
            
        # 从URL中提取文件名
        filename = Path(avatar_url).name
        logger.info(f"要删除的头像URL: {avatar_url}")
        logger.info(f"提取的文件名: {filename}")
        
        # 从文件名中提取基础名称（去掉尺寸后缀）
        base_name = Path(filename).stem
        logger.info(f"原始基础文件名: {base_name}")
        
        # 如果文件名包含尺寸后缀，去掉它
        for size_name in AVATAR_SIZES.keys():
            if base_name.endswith(f"_{size_name}"):
                base_name = base_name[:-len(f"_{size_name}")]
                logger.info(f"去掉尺寸后缀后的基础文件名: {base_name}")
                break
        
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        
        # 删除原始文件（尝试不同的扩展名）
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            original_filename = f"{base_name}{ext}"
            original_path = project_root / UPLOAD_DIR / original_filename
            logger.info(f"尝试原始文件路径: {original_path}")
            
            if original_path.exists():
                original_path.unlink()
                logger.info(f"✅ 原始文件已删除: {original_filename}")
                break
        else:
            logger.warning(f"⚠️ 原始文件不存在，尝试了所有扩展名")
        
        # 删除不同尺寸的文件
        for size_name in AVATAR_SIZES.keys():
            size_filename = f"{base_name}_{size_name}.jpg"
            size_path = project_root / AVATAR_DIR / size_filename
            logger.info(f"{size_name}文件路径: {size_path}")
            
            if size_path.exists():
                size_path.unlink()
                logger.info(f"✅ {size_name}文件已删除: {size_filename}")
            else:
                logger.warning(f"⚠️ {size_name}文件不存在: {size_path}")
        
        logger.info(f"✅ 头像文件删除完成: {filename}")
        
    except Exception as e:
        logger.error(f"❌ 头像文件删除失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")


def get_default_avatar_url() -> str:
    """获取默认头像URL"""
    return "/static/avatars/default_avatar.png"