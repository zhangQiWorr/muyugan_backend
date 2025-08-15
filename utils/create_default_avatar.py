"""
创建默认头像
生成一个简单的默认头像图片
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_default_avatar():
    """创建默认头像"""
    # 确保目录存在
    avatar_dir = Path("static/avatars")
    avatar_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建不同尺寸的默认头像
    sizes = {
        "small": (64, 64),
        "medium": (128, 128),
        "large": (256, 256)
    }
    
    for size_name, (width, height) in sizes.items():
        # 创建图片
        image = Image.new('RGB', (width, height), (200, 200, 200))
        draw = ImageDraw.Draw(image)
        
        # 绘制圆形背景
        circle_bbox = (width * 0.1, height * 0.1, width * 0.9, height * 0.9)
        draw.ellipse(circle_bbox, fill=(100, 150, 200))
        
        # 绘制用户图标（简单的"U"字母）
        try:
            # 尝试使用系统字体
            font_size = int(width * 0.4)
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
        
        # 计算文字位置
        text = "U"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # 绘制文字
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        # 保存文件
        filename = f"default_avatar_{size_name}.png"
        file_path = avatar_dir / filename
        image.save(file_path, 'PNG')
        
        print(f"✅ 创建默认头像: {filename}")
    
    # 创建主默认头像
    main_image = Image.new('RGB', (128, 128), (200, 200, 200))
    draw = ImageDraw.Draw(main_image)
    
    # 绘制圆形背景
    draw.ellipse((12, 12, 116, 116), fill=(100, 150, 200))
    
    # 绘制用户图标
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    text = "U"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (128 - text_width) // 2
    y = (128 - text_height) // 2
    
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    # 保存主默认头像
    main_file_path = avatar_dir / "default_avatar.png"
    main_image.save(main_file_path, 'PNG')
    
    print(f"✅ 创建主默认头像: default_avatar.png")

if __name__ == "__main__":
    create_default_avatar() 