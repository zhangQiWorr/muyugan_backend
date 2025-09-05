# OSS客户端使用说明

## 日志功能

### 启用DEBUG日志

要查看OSS客户端的详细调试信息，请设置以下环境变量：

```bash
export CONSOLE_LOG_LEVEL=DEBUG
```

或者在Python代码中设置：

```python
import os
os.environ['CONSOLE_LOG_LEVEL'] = 'DEBUG'

# 然后导入和使用OSS客户端
from ossAPI.oss_client import OSSClient
```

### 日志级别说明

- **DEBUG**: 显示所有详细的调试信息，包括：
  - 客户端初始化过程
  - 环境变量设置
  - API请求发送
  - 响应处理
  - 错误详细信息

- **INFO**: 显示重要的操作信息（默认级别）
  - 成功的操作结果
  - 基本的错误信息

- **ERROR**: 仅显示错误信息

### 日志格式

日志输出格式为：
```
时间戳 | 日志级别 | 日志器名称 | 消息内容
```

示例：
```
2025-09-01 13:45:11,025 | DEBUG | oss_client | 开始初始化OSS客户端 - 区域: cn-hangzhou
2025-09-01 13:45:11,026 | INFO  | oss_client | ✅ OSS客户端初始化成功 - 区域: cn-hangzhou, 端点: 默认
```

## 使用示例

```python
import os
from ossAPI.oss_client import OSSClient

# 启用DEBUG日志（可选）
os.environ['CONSOLE_LOG_LEVEL'] = 'DEBUG'

# 设置OSS凭证
os.environ['OSS_ACCESS_KEY_ID'] = 'your_access_key_id'
os.environ['OSS_ACCESS_KEY_SECRET'] = 'your_access_key_secret'
os.environ['OSS_REGION'] = 'cn-hangzhou'

# 创建客户端
client = OSSClient()

# 列出对象
result = client.list_all_objects('your-bucket-name')
print(f"找到 {result['count']} 个对象")
```