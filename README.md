# Muyugan 后端系统

一个基于 FastAPI 构建的综合性后端系统，集成了 AI 智能聊天对话平台和知识付费应用功能。

## 🚀 项目概述

Muyugan 后端系统是一个现代化的 Web 应用后端，提供两种运行模式：

1. **完整模式** (`main.py`) - 包含 AI 智能聊天对话平台功能
2. **简化模式** (`main_simple.py`) - 专注于知识付费应用功能

## 📁 项目结构

```
muyugan_backend/
├── main.py                 # 完整模式入口（AI + 知识付费）
├── main_simple.py          # 简化模式入口（仅知识付费）
├── start_server.py         # 服务器启动脚本
├── requirements.txt        # 生产环境依赖
├── requirements-dev.txt    # 开发环境依赖
├── .gitignore             # Git忽略文件
│
├── models/                 # 数据模型层
│   ├── __init__.py        # 模型导出
│   ├── database.py        # 数据库配置
│   ├── user.py            # 用户模型
│   ├── schemas.py         # Pydantic Schema定义
│   ├── course.py          # 课程相关模型
│   ├── payment.py         # 支付相关模型
│   ├── membership.py      # 会员相关模型
│   ├── conversation.py    # 对话模型
│   ├── agent.py           # 智能体模型
│   └── video.py           # 视频模型
│
├── api/                   # API路由层
│   ├── __init__.py        # API路由导出
│   ├── auth.py            # 用户认证API
│   ├── courses.py         # 课程管理API
│   ├── orders.py          # 订单支付API
│   ├── learning.py        # 学习跟踪API
│   ├── membership.py      # 会员管理API
│   ├── chat.py            # 聊天对话API
│   ├── agents.py          # 智能体管理API
│   ├── conversations.py   # 对话管理API
│   ├── video.py           # 视频管理API
│   ├── images.py          # 图片管理API
│   ├── health.py          # 健康检查API
│   └── admin.py           # 管理员API
│
├── auth/                  # 认证模块
│   ├── __init__.py        # 认证模块导出
│   ├── auth_handler.py    # 认证处理器
│   ├── jwt_handler.py     # JWT处理器
│   ├── password_handler.py # 密码处理器
│   └── oauth_handler.py   # OAuth处理器
│
├── agents/                # 智能体模块
│   ├── __init__.py        # 智能体模块导出
│   ├── agent_manager.py   # 智能体管理器
│   ├── agent_factory.py   # 智能体工厂
│   └── default_agents.py  # 默认智能体配置
│
├── utils/                 # 工具模块
│   ├── logger.py          # 日志工具
│   ├── middleware.py      # 中间件
│   ├── file_upload.py     # 文件上传工具
│   ├── auth_utils.py      # 认证工具
│   ├── summarization.py   # 摘要工具
│   └── create_default_avatar.py # 默认头像生成
│
├── database/              # 数据库模块
│   ├── migrate_knowledge_app.py # 知识付费应用迁移
│   └── migrate_video_size_bigint.py # 视频大小字段迁移
│
├── static/                # 静态文件
├── logs/                  # 日志文件
└── .git/                  # Git版本控制
```

## 🎯 核心功能模块

### 1. 用户认证系统 (`auth/`)
- **多种登录方式**: 用户名/邮箱/手机号 + 密码、手机验证码登录
- **第三方登录**: 微信、支付宝、Google、GitHub OAuth
- **JWT认证**: 安全的令牌认证机制
- **权限控制**: 基于角色的访问控制 (RBAC)
- **安全特性**: 密码加密、Token黑名单、会话管理

### 2. 知识付费系统

#### 课程管理 (`api/courses.py`)
- **课程CRUD**: 创建、编辑、发布、下架课程
- **分类管理**: 课程分类和标签系统
- **课时管理**: 支持视频、音频、图文等多种内容类型
- **权限控制**: 免费课程、付费课程、会员专享课程

#### 订单支付 (`api/orders.py`)
- **订单管理**: 订单创建、状态跟踪、订单历史
- **多种支付方式**: 支付宝、微信支付、余额支付
- **优惠券系统**: 创建、发放、使用优惠券
- **退款处理**: 订单退款、部分退款支持

#### 会员系统 (`api/membership.py`)
- **会员等级**: 月度/季度/年度/终身会员
- **权益管理**: 会员权益配置和使用
- **自动续费**: 会员自动续费功能
- **等级管理**: 会员等级CRUD操作

#### 学习跟踪 (`api/learning.py`)
- **课程报名**: 用户课程报名管理
- **学习进度**: 课程学习进度跟踪
- **学习统计**: 总学习时长、每日学习时长
- **评价收藏**: 课程评价、收藏功能
- **学习证书**: 课程完成证书生成

### 3. AI智能聊天系统

#### 智能体管理 (`agents/`)
- **智能体CRUD**: 创建、配置、管理智能体
- **模型集成**: 支持多种AI模型
- **工具管理**: 智能体工具配置
- **默认智能体**: 预设常用智能体

#### 对话管理 (`api/chat.py`)
- **实时对话**: WebSocket实时聊天
- **对话历史**: 对话记录管理
- **多模态支持**: 文本、图片、视频、音频
- **流式响应**: 流式AI响应

#### 对话记录 (`api/conversations.py`)
- **对话CRUD**: 对话创建、编辑、删除
- **标签管理**: 对话标签系统
- **搜索功能**: 对话内容搜索

### 4. 媒体管理

#### 视频管理 (`api/video.py`)
- **视频上传**: 支持多种视频格式
- **视频处理**: 自动生成缩略图、提取元数据
- **视频播放**: 视频流式播放
- **视频管理**: 视频CRUD操作

#### 图片管理 (`api/images.py`)
- **图片上传**: 支持多种图片格式
- **图片处理**: 自动生成缩略图、压缩
- **图片管理**: 图片CRUD操作

### 5. 系统管理

#### 健康检查 (`api/health.py`)
- **系统状态**: 服务健康状态检查
- **平台统计**: 用户、对话、智能体统计
- **性能监控**: 系统性能指标

#### 管理员功能 (`api/admin.py`)
- **日志管理**: 日志级别配置
- **系统配置**: 系统参数配置
- **摘要配置**: AI摘要功能配置

## 🛠 技术栈

### 后端框架
- **FastAPI**: 现代化Python Web框架
- **SQLAlchemy**: ORM数据库操作
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和会话存储

### AI和机器学习
- **LangChain**: AI应用开发框架
- **LangGraph**: 智能体工作流框架
- **OpenAI API**: GPT模型集成
- **Tavily**: 网络搜索工具

### 认证和安全
- **JWT**: JSON Web Token认证
- **Passlib**: 密码加密
- **OAuth2**: 第三方登录
- **CORS**: 跨域资源共享

### 文件处理
- **Pillow**: 图像处理
- **FFmpeg**: 视频处理
- **OpenCV**: 计算机视觉

### 开发和部署
- **Uvicorn**: ASGI服务器
- **Alembic**: 数据库迁移
- **Pydantic**: 数据验证
- **Rich**: 终端美化

## 🚀 快速开始

### 环境要求
- Python 3.11+ (推荐3.11，避免LangGraph兼容性问题)
- PostgreSQL 12+
- Redis 6+
- FFmpeg (视频处理)

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd muyugan_backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 环境配置

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# JWT配置
JWT_SECRET_KEY=your-secret-key-here

# AI API配置
OPENAI_API_KEY=your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key

# 日志配置
CONSOLE_LOG_LEVEL=INFO
FILE_LOG_LEVEL=INFO

# 其他配置
MAX_TOKENS=30000
MAX_SUMMARY_TOKENS=4096
```

### 数据库初始化

```bash
# 运行数据库迁移
python database/migrate_knowledge_app.py
```

### 启动服务

#### 简化模式（推荐）
```bash
# 启动知识付费应用
python main_simple.py
```

#### 完整模式
```bash
# 启动完整AI聊天平台
python main.py
```

#### 使用启动脚本
```bash
# 使用启动脚本
python start_server.py
```

### 访问服务

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

## 📚 API文档

### 认证相关
- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `POST /auth/login/phone` - 手机验证码登录
- `POST /auth/sms/send` - 发送短信验证码
- `GET /auth/me` - 获取当前用户信息
- `PUT /auth/me` - 更新用户信息

### 课程管理
- `GET /courses/` - 获取课程列表
- `POST /courses/` - 创建课程
- `GET /courses/{course_id}` - 获取课程详情
- `PUT /courses/{course_id}` - 更新课程
- `POST /courses/{course_id}/publish` - 发布课程
- `POST /courses/{course_id}/unpublish` - 下架课程

### 订单支付
- `POST /orders/` - 创建订单
- `GET /orders/` - 获取订单列表
- `GET /orders/{order_id}` - 获取订单详情
- `POST /orders/{order_id}/pay` - 支付订单
- `POST /orders/{order_id}/cancel` - 取消订单

### 会员管理
- `GET /membership/levels` - 获取会员等级列表
- `POST /membership/purchase` - 购买会员
- `GET /membership/my` - 获取我的会员信息
- `POST /membership/cancel` - 取消会员
- `POST /membership/renew` - 续费会员

### 学习跟踪
- `POST /learning/enroll/{course_id}` - 报名课程
- `GET /learning/enrollments` - 获取我的报名课程
- `POST /learning/progress` - 更新学习进度
- `GET /learning/progress/{course_id}` - 获取课程学习进度
- `POST /learning/reviews` - 创建课程评价
- `GET /learning/statistics` - 获取学习统计

### AI聊天
- `GET /agents/` - 获取智能体列表
- `POST /agents/` - 创建智能体
- `GET /agents/{agent_id}` - 获取智能体详情
- `POST /chat/stream` - 流式聊天
- `GET /conversations/` - 获取对话列表
- `POST /conversations/` - 创建对话

## 🔧 开发指南

### 代码规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 遵循 PEP 8 编码规范
- 使用类型注解

### 数据库迁移
```bash
# 创建新的迁移文件
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head
```

### 测试
```bash
# 运行测试
pytest

# 运行特定测试
pytest tests/test_auth.py
```

### 日志配置
系统使用结构化日志，支持以下级别：
- DEBUG: 调试信息
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

## 🚀 部署

### Docker部署
```bash
# 构建镜像
docker build -t muyugan-backend .

# 运行容器
docker run -p 8000:8000 muyugan-backend
```

### 生产环境配置
1. 修改环境变量中的敏感信息
2. 配置HTTPS证书
3. 设置反向代理（Nginx）
4. 配置数据库连接池
5. 启用日志轮转

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

- 项目维护者: [Your Name]
- 邮箱: [your.email@example.com]
- 项目链接: [https://github.com/yourusername/muyugan-backend]

## 🙏 致谢

感谢以下开源项目的支持：
- FastAPI
- LangChain
- SQLAlchemy
- PostgreSQL
- Redis
- 以及其他所有依赖库的贡献者
