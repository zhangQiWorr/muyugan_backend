"""媒体文件处理工具
处理音频和视频文件的时长检测等功能
"""

import os
import tempfile
from typing import Optional
from pathlib import Path
import ffmpeg

# 延迟导入重型依赖，避免无关路径增大启动/内存占用
cv2 = None
librosa = None

MOVIEPY_AVAILABLE = False
VideoFileClip = None
AudioFileClip = None

try:
    import moviepy.editor as mp
    VideoFileClip = mp.VideoFileClip
    AudioFileClip = mp.AudioFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    pass

from services.logger import get_logger

logger = get_logger("media_utils")

def get_media_duration(file_path: str, content_type: str) -> None | int | float:
    """
    获取音频或视频文件的时长（秒）
    
    Args:
        file_path: 文件路径
        content_type: 内容类型 ('video' 或 'audio')
    
    Returns:
        时长（秒），如果无法获取则返回None
    """


    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    try:
        if content_type == 'video':
            return get_video_duration(file_path)
        elif content_type == 'audio':
            return get_audio_duration(file_path)

            
    except Exception as e:
        logger.error(f"Error getting media duration for {file_path}: {str(e)}")
        return None

def get_media_duration_from_upload(file_content: bytes, filename: str, content_type: str) -> Optional[int]:
    """
    从上传的文件内容获取媒体时长
    
    Args:
        file_content: 文件二进制内容
        filename: 原始文件名
        content_type: 内容类型 ('video' 或 'audio')
    
    Returns:
        时长（秒），如果无法获取则返回None
    """
    if not MOVIEPY_AVAILABLE:
        logger.warning("MoviePy not available, cannot get media duration")
        return None
    
    # 创建临时文件
    temp_file = None
    try:
        # 获取文件扩展名
        file_extension = Path(filename).suffix
        if not file_extension:
            # 根据content_type推断扩展名
            if content_type.lower() == 'video':
                file_extension = '.mp4'
            elif content_type.lower() == 'audio':
                file_extension = '.mp3'
            else:
                file_extension = '.tmp'
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        # 获取时长
        duration = get_media_duration(temp_file_path, content_type)
        return duration
        
    except Exception as e:
        logger.error(f"Error processing uploaded media file {filename}: {str(e)}")
        return None
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_file.name}: {str(e)}")

def is_media_file(content_type: str) -> bool:
    """
    判断是否为音频或视频文件
    
    Args:
        content_type: 内容类型
    
    Returns:
        是否为媒体文件
    """
    return content_type.lower() in ['video', 'audio']

def format_duration(seconds: int) -> str:
    """
    格式化时长显示
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化的时长字符串 (如: "1:23:45" 或 "5:30")
    """
    if seconds < 0:
        return "0:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


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
        global cv2
        if cv2 is None:
            try:
                import cv2 as _cv2
                cv2 = _cv2
            except Exception as e:
                logger.error(f"❌ OpenCV 未安装: {str(e)}")
                return None

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



def get_audio_duration(file_path: str) -> int:
    global librosa
    if librosa is None:
        try:
            import librosa as _librosa
            librosa = _librosa
        except Exception as e:
            logger.error(f"❌ librosa 未安装: {str(e)}")
            return None

    audio, sr = librosa.load(file_path)
    return int(len(audio) / sr)