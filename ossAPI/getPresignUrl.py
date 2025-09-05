import argparse
import os
import sys
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ossAPI.oss_client import get_oss_client, OSSClient

try:
    import alibabacloud_oss_v2 as oss
except ImportError:
    raise ImportError("请安装 alibabacloud-oss-v2 SDK: pip install alibabacloud-oss-v2")

def generate_presigned_url(bucket: str, 
                          key: str,
                          expires_in_hours: int = 1,
                          method: str = 'GET',
                          region: Optional[str] = None,
                          endpoint: Optional[str] = None) -> dict:
    """
    生成OSS对象的预签名URL
    
    Args:
        bucket: 存储桶名称
        key: 对象键名
        expires_in_hours: 过期时间（小时），默认1小时，最大24小时
        method: HTTP方法，支持GET和PUT
        region: OSS区域
        endpoint: 自定义端点
        
    Returns:
        包含预签名URL信息的字典
    """
    try:
        # 获取OSS客户端
        if region or endpoint:
            client = OSSClient(region=region, endpoint=endpoint)
        else:
            client = get_oss_client()
        
        if client is None:
            raise ValueError("无法获取OSS客户端，请检查配置")
        
        # 生成预签名URL
        result = client.generate_presigned_url(
            bucket=bucket,
            key=key,
            expires_in_hours=expires_in_hours,
            method=method
        )
        
        return result
        
    except Exception as e:
        print(f"❌ 生成预签名URL失败: {str(e)}")
        raise


def generate_download_url(bucket: str, 
                         key: str,
                         expires_in_hours: int = 1,
                         region: Optional[str] = None,
                         endpoint: Optional[str] = None) -> dict:
    """
    生成下载用的预签名URL（GET方法）
    
    Args:
        bucket: 存储桶名称
        key: 对象键名
        expires_in_hours: 过期时间（小时）
        region: OSS区域
        endpoint: 自定义端点
        
    Returns:
        包含预签名URL信息的字典
    """
    return generate_presigned_url(
        bucket=bucket,
        key=key,
        expires_in_hours=expires_in_hours,
        method='GET',
        region=region,
        endpoint=endpoint
    )


def generate_upload_url(bucket: str, 
                       key: str,
                       expires_in_hours: int = 1,
                       region: Optional[str] = None,
                       endpoint: Optional[str] = None) -> dict:
    """
    生成上传用的预签名URL（PUT方法）
    
    Args:
        bucket: 存储桶名称
        key: 对象键名
        expires_in_hours: 过期时间（小时）
        region: OSS区域
        endpoint: 自定义端点
        
    Returns:
        包含预签名URL信息的字典
    """
    return generate_presigned_url(
        bucket=bucket,
        key=key,
        expires_in_hours=expires_in_hours,
        method='PUT',
        region=region,
        endpoint=endpoint
    )


def main():
    """命令行入口函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="Generate presigned URL for OSS objects")
    parser.add_argument('--region', help='The region in which the bucket is located.', 
                       required=False, default="cn-guangzhou")
    parser.add_argument('--bucket', help='The name of the bucket.', required=True)
    parser.add_argument('--endpoint', help='The domain names that other services can use to access OSS')
    parser.add_argument('--key', help='The name of the object.', required=True)
    parser.add_argument('--method', help='HTTP method (GET or PUT)', 
                       choices=['GET', 'PUT'], default='GET')
    parser.add_argument('--expires', type=int, help='Expiration time in hours (1-24)', 
                       default=1, choices=range(1, 25))
    
    args = parser.parse_args()
    
    print(f"区域: {args.region}")
    print(f"存储桶: {args.bucket}")
    print(f"端点: {args.endpoint or '默认'}")
    print(f"对象键: {args.key}")
    print(f"HTTP方法: {args.method}")
    print(f"过期时间: {args.expires}小时")
    print("-" * 50)
    
    try:
        # 生成预签名URL
        result = generate_presigned_url(
            bucket=args.bucket,
            key=args.key,
            expires_in_hours=args.expires,
            method=args.method,
            region=args.region,
            endpoint=args.endpoint
        )
        
        # 打印结果
        print(f"✅ 预签名URL生成成功:")
        print(f"  HTTP方法: {result['method']}")
        print(f"  URL: {result['url']}")
        print(f"  过期时间: {result['expiration_str']}")
        print(f"  签名头数量: {len(result['signed_headers'])}")
        
        if result['signed_headers']:
            print(f"  签名头:")
            for header, value in result['signed_headers'].items():
                print(f"    {header}: {value}")
        
        # 输出可直接使用的URL
        print(f"\n📋 可直接使用的URL:")
        print(result['url'])
        
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())