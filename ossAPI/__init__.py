"""OSS API模块

提供阿里云OSS存储服务的封装接口
"""

from .oss_client import OSSClient, get_oss_client
from .listObjectV2 import list_all_objects_v2, list_objects_paginated
from .getObjectV2 import get_object_v2, get_object_info

__all__ = [
    'OSSClient',
    'get_oss_client',
    'list_all_objects_v2',
    'list_objects_paginated', 
    'get_object_v2',
    'get_object_info'
]