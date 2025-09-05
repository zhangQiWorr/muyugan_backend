import os
from typing import Optional, Dict, Any, Iterator
from datetime import timedelta
import logging

try:
    import alibabacloud_oss_v2 as oss
except ImportError:
    raise ImportError("请安装 alibabacloud-oss-v2 SDK: pip install alibabacloud-oss-v2")

from services.logger import get_logger

# 获取OSS专用日志器
logger = get_logger("oss_client")

# 设置日志级别为DEBUG以便调试
logger.setLevel(logging.DEBUG)

# 强制添加DEBUG级别的控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s')
console_handler.setFormatter(formatter)

# 检查是否已经有相同的处理器，避免重复添加
has_console_handler = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
if not has_console_handler:
    logger.addHandler(console_handler)
    logger.info("OSS客户端日志器已初始化")
    logger.debug("DEBUG级别日志已启用")

class OSSClient:
    """阿里云OSS客户端封装类"""
    
    def __init__(self, 
                 access_key_id: Optional[str] = None,
                 access_key_secret: Optional[str] = None,
                 region: Optional[str] = None,
                 endpoint: Optional[str] = None):
        """
        初始化OSS客户端
        
        Args:
            access_key_id: 访问密钥ID，如果为None则从环境变量获取
            access_key_secret: 访问密钥Secret，如果为None则从环境变量获取
            region: 区域，如果为None则从环境变量获取
            endpoint: 自定义端点，可选
        """
        self.access_key_id = access_key_id or os.getenv('OSS_ACCESS_KEY_ID')
        self.access_key_secret = access_key_secret or os.getenv('OSS_ACCESS_KEY_SECRET')
        self.region = region or os.getenv('OSS_REGION', 'cn-guangzhou')
        self.endpoint = endpoint or os.getenv('OSS_ENDPOINT')
        
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError("OSS凭证未配置，请设置OSS_ACCESS_KEY_ID和OSS_ACCESS_KEY_SECRET环境变量")
        
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """初始化OSS客户端"""
        logger.debug(f"开始初始化OSS客户端 - 区域: {self.region}")
        
        try:
            # 设置环境变量供SDK使用
            if self.access_key_id:
                os.environ['OSS_ACCESS_KEY_ID'] = self.access_key_id
                logger.debug("已设置OSS_ACCESS_KEY_ID环境变量")
            if self.access_key_secret:
                os.environ['OSS_ACCESS_KEY_SECRET'] = self.access_key_secret
                logger.debug("已设置OSS_ACCESS_KEY_SECRET环境变量")
            
            # 从环境变量中加载凭证信息
            credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
            logger.debug("已创建环境变量凭证提供者")
            
            # 加载SDK的默认配置
            cfg = oss.config.load_default()
            cfg.credentials_provider = credentials_provider
            cfg.region = self.region
            logger.debug(f"已设置配置区域: {self.region}")
            
            if self.endpoint:
                cfg.endpoint = self.endpoint
                logger.debug(f"已设置自定义端点: {self.endpoint}")
            
            # 创建OSS客户端
            self._client = oss.Client(cfg)
            logger.debug("OSS客户端对象创建成功")
            
            logger.info(f"✅ OSS客户端初始化成功 - 区域: {self.region}, 端点: {self.endpoint or '默认'}")
            
        except Exception as e:
            logger.error(f"❌ OSS客户端初始化失败: {str(e)}")
            logger.debug(f"初始化失败详细信息: {type(e).__name__}: {str(e)}")
            raise
    
    @property
    def client(self):
        """获取OSS客户端实例"""
        if not self._client:
            self._init_client()
        if not self._client:
            raise RuntimeError("OSS客户端初始化失败")
        return self._client
    
    def list_all_objects(self,
                    bucket: str, 
                    prefix: Optional[str] = None,
                    continuation_token: Optional[str] = None) -> Dict[str, Any]:
        """
        列出OSS对象
        
        Args:
            bucket: 存储桶名称
            prefix: 对象前缀过滤
            continuation_token: 分页令牌
            
        Returns:
            包含对象列表和分页信息的字典
        """
        logger.debug(f"开始列出OSS对象 - 存储桶: {bucket}, 前缀: {prefix}, 令牌: {continuation_token}")
        
        try:
            request = oss.ListObjectsV2Request(
                bucket=bucket
            )
            
            if prefix:
                request.prefix = prefix
                logger.debug(f"设置对象前缀过滤: {prefix}")
            if continuation_token:
                request.continuation_token = continuation_token
                logger.debug(f"设置分页令牌: {continuation_token}")
            
            logger.debug("发送ListObjectsV2请求")
            response = self.client.list_objects_v2(request)
            logger.debug(f"收到响应，处理对象列表")
            
            objects = []
            if response.contents:
                logger.debug(f"响应包含 {len(response.contents)} 个对象")
                for obj in response.contents:
                    objects.append({
                        'key': obj.key,
                        'size': obj.size,
                        'etag': obj.etag.strip('"') if obj.etag else None,
                        'last_modified': obj.last_modified,
                        'storage_class': obj.storage_class,
                        'object_type': obj.object_type
                    })
            else:
                logger.debug("响应不包含任何对象")
            
            result = {
                'objects': objects,
                'count': len(objects),
                'is_truncated': getattr(response, 'is_truncated', False),
                'next_continuation_token': getattr(response, 'next_continuation_token', None)
            }
            
            logger.info(f"✅ 成功获取OSS对象列表 - 存储桶: {bucket}, 对象数量: {len(objects)}")
            logger.debug(f"列表结果: 截断={result['is_truncated']}, 下一个令牌={result['next_continuation_token']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 获取OSS对象列表失败 - 存储桶: {bucket}, 错误: {str(e)}")
            logger.debug(f"列表失败详细信息: {type(e).__name__}: {str(e)}")
            raise
    
    def list_objects_paginated(self, 
                              bucket: str, 
                              prefix: Optional[str] = None,
                              max_keys: int = 1000) -> Iterator[Dict[str, Any]]:
        """
        分页获取OSS对象列表
        
        Args:
            bucket: 存储桶名称
            prefix: 对象前缀过滤
            max_keys: 每页最大对象数量
            
        Yields:
            每页的对象信息字典
        """
        try:
            paginator = self.client.list_objects_v2_paginator()
            
            request = oss.ListObjectsV2Request(
                bucket=bucket,
                max_keys=max_keys
            )
            
            if prefix:
                request.prefix = prefix
            
            for page in paginator.iter_page(request):
                if page.contents:
                    objects = []
                    for obj in page.contents:
                        objects.append({
                            'key': obj.key,
                            'size': obj.size,
                            'etag': obj.etag.strip('"') if obj.etag else None,
                            'last_modified': obj.last_modified,
                            'storage_class': obj.storage_class,
                            'object_type': obj.object_type
                        })
                    
                    yield {
                        'objects': objects,
                        'count': len(objects)
                    }
                    
                    logger.debug(f"📄 获取OSS对象页 - 存储桶: {bucket}, 对象数量: {len(objects)}")
                    
        except Exception as e:
            logger.error(f"❌ 分页获取OSS对象列表失败 - 存储桶: {bucket}, 错误: {str(e)}")
            raise

    # 下载对象
    def get_object(self, 
                   bucket: str, 
                   key: str,
                   range_header: Optional[str] = None) -> oss.GetObjectResult:
        """
        获取OSS对象
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            range_header: 范围头，例如 "bytes=0-1023"
            
        Returns:
            OSS获取对象结果
        """
        logger.info(f"开始获取OSS对象 - 存储桶: {bucket}, 对象: {key}, 范围: {range_header}")
        
        try:
            request = oss.GetObjectRequest(
                bucket=bucket,
                key=key
            )
            logger.debug(f"创建GetObject请求: bucket={bucket}, key={key}")
            
            if range_header:
                request.range_header = range_header
                logger.debug(f"设置范围头: {range_header}")
            
            logger.debug("发送GetObject请求")
            result = self.client.get_object(request)
            logger.debug(f"收到响应，对象获取成功")
            
            logger.info(f"✅ 成功获取OSS对象 - 存储桶: {bucket}, 对象: {key}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 获取OSS对象失败 - 存储桶: {bucket}, 对象: {key}, 错误: {str(e)}")
            logger.debug(f"获取对象失败详细信息: {type(e).__name__}: {str(e)}")
            raise
    
    def get_object_info(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        获取OSS对象信息（不下载内容）
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            对象信息字典
        """
        try:
            request = oss.HeadObjectRequest(
                bucket=bucket,
                key=key
            )
            
            result = self.client.head_object(request)
            
            info = {
                'key': key,
                'size': result.content_length,
                'etag': result.etag.strip('"') if result.etag else None,
                'last_modified': result.last_modified,
                'content_type': result.content_type,
                'storage_class': result.storage_class,
                'object_type': getattr(result, 'object_type', None)
            }
            
            logger.info(f"✅ 成功获取OSS对象信息 - 存储桶: {bucket}, 对象: {key}")
            return info
            
        except Exception as e:
            logger.error(f"❌ 获取OSS对象信息失败 - 存储桶: {bucket}, 对象: {key}, 错误: {str(e)}")
            raise
    
    def object_exists(self, bucket: str, key: str) -> bool:
        """
        检查OSS对象是否存在
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            
        Returns:
            对象是否存在
        """
        try:
            self.get_object_info(bucket, key)
            return True
        except Exception:
            return False
    
    def generate_presigned_url(self, 
                              bucket: str, 
                              key: str,
                              expires_in_hours: int = 1,
                              method: str = 'GET') -> Dict[str, Any]:
        """
        生成OSS对象的预签名URL
        
        Args:
            bucket: 存储桶名称
            key: 对象键名
            expires_in_hours: 过期时间（小时），默认1小时
            method: HTTP方法，支持GET和PUT
            
        Returns:
            包含预签名URL信息的字典
        """
        logger.info(f"开始生成预签名URL - 存储桶: {bucket}, 对象: {key}, 方法: {method}, 过期时间: {expires_in_hours}小时")
        
        try:
            # 根据方法类型创建相应的请求对象
            if method.upper() == 'GET':
                request = oss.GetObjectRequest(
                    bucket=bucket,
                    key=key
                )
            elif method.upper() == 'PUT':
                request = oss.PutObjectRequest(
                    bucket=bucket,
                    key=key
                )
            else:
                raise ValueError(f"不支持的HTTP方法: {method}，仅支持GET和PUT")
            
            logger.debug(f"创建{method}请求对象: bucket={bucket}, key={key}")
            
            # 设置过期时间
            expires = timedelta(hours=expires_in_hours)
            logger.debug(f"设置过期时间: {expires_in_hours}小时")
            
            # 生成预签名URL
            logger.debug("发送预签名请求")
            pre_result = self.client.presign(request, expires=expires)
            logger.debug(f"收到预签名响应")
            
            # 构建返回结果
            result = {
                'method': pre_result.method,
                'url': pre_result.url,
                'expiration': pre_result.expiration,
                'expiration_str': pre_result.expiration.strftime("%Y-%m-%dT%H:%M:%S.000Z") if pre_result.expiration else None,
                'signed_headers': dict(pre_result.signed_headers) if pre_result.signed_headers else {}
            }
            
            logger.info(f"✅ 成功生成预签名URL - 存储桶: {bucket}, 对象: {key}, 方法: {result['method']}")
            logger.debug(f"预签名URL: {result['url']}")
            logger.debug(f"过期时间: {result['expiration_str']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 生成预签名URL失败 - 存储桶: {bucket}, 对象: {key}, 错误: {str(e)}")
            logger.debug(f"预签名失败详细信息: {type(e).__name__}: {str(e)}")
            raise

# 全局OSS客户端实例
_oss_client = None

def get_oss_client() -> OSSClient:
    """获取全局OSS客户端实例"""
    global _oss_client
    if _oss_client is None:
        _oss_client = OSSClient()
    return _oss_client