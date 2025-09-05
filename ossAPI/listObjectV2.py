import argparse
from typing import Optional, List, Dict, Any
from .oss_client import get_oss_client


def list_all_objects_v2(bucket: str,
                    prefix: Optional[str] = None,
                    region: Optional[str] = None,
                    endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出OSS存储桶中的对象
    
    Args:
        bucket: 存储桶名称
        prefix: 对象前缀过滤
        region: OSS区域
        endpoint: 自定义端点
        
    Returns:
        对象信息列表
    """
    try:
        # 获取OSS客户端
        if region or endpoint:
            from oss_client import OSSClient
            client = OSSClient(region=region, endpoint=endpoint)
        else:
            client = get_oss_client()
        
        # 获取对象列表
        result = client.list_all_objects(bucket=bucket, prefix=prefix)
        return result['objects']
        
    except Exception as e:
        print(f"❌ 列出对象失败: {str(e)}")
        raise


def list_objects_paginated(bucket: str, 
                          prefix: Optional[str] = None,
                          max_keys: int = 1000,
                          region: Optional[str] = None,
                          endpoint: Optional[str] = None):
    """
    分页列出OSS存储桶中的对象
    
    Args:
        bucket: 存储桶名称
        prefix: 对象前缀过滤
        max_keys: 每页最大对象数量
        region: OSS区域
        endpoint: 自定义端点
        
    Yields:
        每页的对象信息
    """
    try:
        # 获取OSS客户端
        if region or endpoint:
            from oss_client import OSSClient
            client = OSSClient(region=region, endpoint=endpoint)
        else:
            client = get_oss_client()
        
        # 分页获取对象列表
        for page in client.list_objects_paginated(bucket=bucket, prefix=prefix, max_keys=max_keys):
            yield page
            
    except Exception as e:
        print(f"❌ 分页列出对象失败: {str(e)}")
        raise


def main():
    """命令行入口函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="list objects v2 sample")
    parser.add_argument('--region', help='The region in which the bucket is located.', 
                       required=False, default="cn-guangzhou")
    parser.add_argument('--bucket', help='The name of the bucket.', 
                       required=False, default="zhangqi-video11")
    parser.add_argument('--endpoint', help='The domain names that other services can use to access OSS')
    parser.add_argument('--prefix', help='Object prefix filter')
    parser.add_argument('--max-keys', type=int, default=1000, help='Maximum number of objects to return')
    
    args = parser.parse_args()
    
    print(f"区域: {args.region}")
    print(f"存储桶: {args.bucket}")
    print(f"端点: {args.endpoint or '默认'}")
    print(f"前缀: {args.prefix or '无'}")
    print(f"最大对象数: {args.max_keys}")
    print("-" * 50)
    
    try:
        # 使用分页方式列出对象
        total_objects = 0
        for page in list_objects_paginated(
            bucket=args.bucket,
            prefix=args.prefix,
            max_keys=args.max_keys,
            region=args.region,
            endpoint=args.endpoint
        ):
            objects = page['objects']
            total_objects += len(objects)
            
            print(f"📄 当前页对象数量: {len(objects)}")
            for obj in objects:
                print(f"  📁 {obj['key']} ({obj['size']} bytes, {obj['last_modified']})")
            print()
        
        print(f"✅ 总计对象数量: {total_objects}")
        
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()  # 脚本入口，当文件被直接运行时调用main函数