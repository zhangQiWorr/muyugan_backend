import argparse
import os
from typing import Optional, BinaryIO
from .oss_client import get_oss_client, OSSClient

try:
    import alibabacloud_oss_v2 as oss
except ImportError:
    raise ImportError("请安装 alibabacloud-oss-v2 SDK: pip install alibabacloud-oss-v2")

def get_object_v2(bucket: str, 
                  key: str,
                  range_header: Optional[str] = None,
                  output_path: Optional[str] = None,
                  region: Optional[str] = None,
                  endpoint: Optional[str] = None) -> oss.GetObjectResult:
    """
    获取OSS对象
    
    Args:
        bucket: 存储桶名称
        key: 对象键名
        range_header: 范围头，例如 "bytes=0-1023"
        output_path: 输出文件路径，如果提供则保存到文件
        region: OSS区域
        endpoint: 自定义端点
        
    Returns:
        OSS获取对象结果
    """
    try:
        # 获取OSS客户端
        if region or endpoint:
            client = OSSClient(region=region, endpoint=endpoint)
        else:
            client = get_oss_client()
        
        if client is None:
            raise ValueError("无法获取OSS客户端，请检查配置")
        
        # 获取对象
        result = client.get_object(bucket=bucket, key=key, range_header=range_header)
        
        # 如果指定了输出路径，则保存到文件
        if output_path and result.body is not None:
            with result.body as body_stream:
                data = body_stream.read()
                with open(output_path, 'wb') as f:
                    f.write(data)
                print(f"✅ 文件已保存到: {output_path} ({len(data)} bytes)")
        
        return result
        
    except Exception as e:
        print(f"❌ 获取对象失败: {str(e)}")
        raise


def get_object_info(bucket: str, 
                   key: str,
                   region: Optional[str] = None,
                   endpoint: Optional[str] = None) -> dict:
    """
    获取OSS对象信息
    
    Args:
        bucket: 存储桶名称
        key: 对象键名
        region: OSS区域
        endpoint: 自定义端点
        
    Returns:
        对象信息字典
    """
    try:
        # 获取OSS客户端
        if region or endpoint:
            client = OSSClient(region=region, endpoint=endpoint)
        else:
            client = get_oss_client()
        
        # 获取对象信息
        return client.get_object_info(bucket=bucket, key=key)
        
    except Exception as e:
        print(f"❌ 获取对象信息失败: {str(e)}")
        raise


def download_object_chunked(bucket: str, 
                           key: str,
                           output_path: str,
                           chunk_size: int = 256 * 1024,
                           region: Optional[str] = None,
                           endpoint: Optional[str] = None) -> int:
    """
    分块下载OSS对象
    
    Args:
        bucket: 存储桶名称
        key: 对象键名
        output_path: 输出文件路径
        chunk_size: 块大小（字节）
        region: OSS区域
        endpoint: 自定义端点
        
    Returns:
        下载的总字节数
    """
    try:
        # 获取OSS客户端
        if region or endpoint:
            client = OSSClient(region=region, endpoint=endpoint)
        else:
            client = get_oss_client()
        
        if client is None:
            raise ValueError("无法获取OSS客户端，请检查配置")
        
        # 获取对象
        result = client.get_object(bucket=bucket, key=key)
        
        total_size = 0
        if result.body is not None:
            with result.body as body_stream:
                with open(output_path, 'wb') as f:
                    for chunk in body_stream.iter_bytes(block_size=chunk_size):
                        f.write(chunk)
                        total_size += len(chunk)
                        print(f"📥 已下载: {len(chunk)} bytes | 累计: {total_size} bytes")
        
        print(f"✅ 文件下载完成: {output_path} ({total_size} bytes)")
        return total_size
        
    except Exception as e:
        print(f"❌ 分块下载失败: {str(e)}")
        raise


def main():
    """命令行入口函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="Get object range sample")
    parser.add_argument('--region', help='The region in which the bucket is located.', 
                       required=False, default="cn-guangzhou")
    parser.add_argument('--bucket', help='The name of the bucket.', required=True)
    parser.add_argument('--endpoint', help='The domain names that other services can use to access OSS')
    parser.add_argument('--key', help='The name of the object.', required=True)
    parser.add_argument('--range', help='Specify the scope of file transfer. Example value: bytes=0-9')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--chunked', action='store_true', help='Use chunked download')
    parser.add_argument('--chunk-size', type=int, default=256*1024, help='Chunk size for chunked download')
    
    args = parser.parse_args()
    
    print(f"区域: {args.region}")
    print(f"存储桶: {args.bucket}")
    print(f"端点: {args.endpoint or '默认'}")
    print(f"对象键: {args.key}")
    print(f"范围: {args.range or '完整文件'}")
    print(f"输出路径: {args.output or '不保存'}")
    print("-" * 50)
    
    try:
        if args.chunked and args.output:
            # 分块下载
            total_size = download_object_chunked(
                bucket=args.bucket,
                key=args.key,
                output_path=args.output,
                chunk_size=args.chunk_size,
                region=args.region,
                endpoint=args.endpoint
            )
            print(f"✅ 分块下载完成，总大小: {total_size} bytes")
        else:
            # 普通下载
            result = get_object_v2(
                bucket=args.bucket,
                key=args.key,
                range_header=args.range,
                output_path=args.output,
                region=args.region,
                endpoint=args.endpoint
            )
            
            # 打印对象信息
            print(f"✅ 获取对象成功:")
            print(f"  状态码: {result.status_code}")
            print(f"  请求ID: {result.request_id}")
            print(f"  内容长度: {result.content_length}")
            print(f"  内容类型: {result.content_type}")
            print(f"  ETag: {result.etag}")
            print(f"  最后修改时间: {result.last_modified}")
            print(f"  存储类型: {result.storage_class}")
            
            if args.range:
                print(f"  内容范围: {result.content_range}")
        
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())