# Muyugan 后端系统项目索引

## 📋 项目概述

**Muyugan 后端系统**是一个基于 FastAPI 构建的综合性后端系统，集成了 AI 智能聊天对话平台和知识付费应用功能。系统采用现代化的微服务架构，支持多种运行模式，提供完整的用户认证、课程管理、订单支付、会员系统等功能。

### 🎯 核心特性

- **双模式运行**: 支持完整模式（AI + 知识付费）和简化模式（仅知识付费）
- **AI 智能聊天**: 基于 LangGraph 框架的智能对话系统
- **知识付费平台**: 完整的在线教育课程管理系统
- **多角色权限**: 支持家长、教师、管理员三种角色
- **现代化架构**: 基于 FastAPI + SQLAlchemy + PostgreSQL + Redis

## 🏗 项目架构

### 技术栈

| 分类 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Web框架** | FastAPI | 0.115.0+ | 现代化Python Web框架 |
| **数据库** | PostgreSQL | 12+ | 主数据库 |
| **缓存** | Redis | 6+ | 会话存储和缓存 |
| **ORM** | SQLAlchemy | 2.0+ | 数据库ORM |
| **认证** | JWT | - | 用户认证 |
| **AI框架** | LangGraph | 0.6.2 | 智能体工作流 |
| **AI框架** | LangChain | 0.3.72 | AI应用开发 |
| **文件处理** | FFmpeg | - | 视频处理 |
| **图像处理** | OpenCV | 4.8+ | 计算机视觉 |

### 目录结构

```
muyugan_backend/
├── main.py                 # 完整模式入口（AI + 知识付费）
├── config.py              # 项目配置文件
├── requirements.txt        # 生产环境依赖
├── README.md              # 项目说明文档
├── PROJECT_INDEX.md       # 项目索引文档（本文件）
│
├── models/                # 数据模型层
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
│   ├── media_utils.py     # 媒体处理工具
│   └── permission_utils.py # 权限管理工具
│
├── services/              # 服务模块
│   ├── logger.py          # 增强日志服务
│   ├── middleware.py      # 中间件服务
│   ├── audit_middleware.py # 审计中间件
│   ├── audit_service.py   # 审计服务
│   └── media_play_service.py # 媒体播放服务
│
├── database/              # 数据库模块
│   ├── migrate_*.py       # 数据库迁移脚本
│   ├── postgres/          # PostgreSQL配置
│   └── redis/             # Redis配置
│
├── static/                # 静态文件
│   ├── images/            # 图片资源
│   ├── videos/            # 视频资源
│   ├── audios/            # 音频资源
│   └── documents/         # 文档资源
│
├── logs/                  # 日志文件
└── tests/                 # 测试文件
```

## 🔧 核心模块详解

### 1. 数据模型层 (models/)

#### 用户模型 (user.py)
- **User**: 用户基础信息
  - 支持邮箱、手机号、用户名多种登录方式
  - 角色权限：user, teacher, superadmin
  - 用户偏好设置和状态管理

#### 课程模型 (course.py)
- **Course**: 课程主体信息
- **CourseCategory**: 课程分类（支持层级结构）
- **CourseLesson**: 课程课时
- **CourseEnrollment**: 课程报名
- **LearningProgress**: 学习进度
- **CourseReview**: 课程评价
- **CourseFavorite**: 课程收藏

#### 支付模型 (payment.py)
- **Order**: 订单信息
- **OrderItem**: 订单项
- **PaymentRecord**: 支付记录
- **Coupon**: 优惠券
- **UserCoupon**: 用户优惠券
- **RefundRecord**: 退款记录
- **UserBalance**: 用户余额

#### 会员模型 (membership.py)
- **MembershipLevel**: 会员等级
- **UserMembership**: 用户会员
- **MembershipOrder**: 会员订单
- **MembershipBenefit**: 会员权益
- **UserBenefitUsage**: 用户权益使用

### 2. API路由层 (api/)

#### 认证API (auth.py)
```python
POST /auth/register          # 用户注册
POST /auth/login             # 用户登录
POST /auth/login/phone       # 手机验证码登录
POST /auth/sms/send          # 发送短信验证码
GET  /auth/me                # 获取当前用户信息
PUT  /auth/me                # 更新用户信息
POST /auth/upload-avatar     # 上传头像
```

#### 课程管理API (courses.py)
```python
GET    /courses/                    # 获取课程列表
POST   /courses/                    # 创建课程
GET    /courses/{course_id}         # 获取课程详情
PUT    /courses/{course_id}         # 更新课程
DELETE /courses/{course_id}         # 删除课程
POST   /courses/{course_id}/publish # 发布课程
POST   /courses/{course_id}/unpublish # 下架课程
GET    /courses/categories/         # 获取课程分类
POST   /courses/categories/         # 创建课程分类
```

#### 订单支付API (orders.py)
```python
POST /orders/                    # 创建订单
GET  /orders/                    # 获取订单列表
GET  /orders/{order_id}          # 获取订单详情
POST /orders/{order_id}/pay      # 支付订单
POST /orders/{order_id}/cancel   # 取消订单
GET  /orders/coupons/            # 获取优惠券列表
POST /orders/coupons/use         # 使用优惠券
```

#### 学习管理API (learning.py)
```python
POST /learning/enroll/{course_id}     # 报名课程
GET  /learning/enrollments            # 获取我的报名课程
POST /learning/progress               # 更新学习进度
GET  /learning/progress/{course_id}   # 获取课程学习进度
POST /learning/reviews                # 创建课程评价
GET  /learning/statistics             # 获取学习统计
```

#### 会员管理API (membership.py)
```python
GET  /membership/levels               # 获取会员等级列表
POST /membership/purchase             # 购买会员
GET  /membership/my                   # 获取我的会员信息
POST /membership/cancel               # 取消会员
POST /membership/renew                # 续费会员
```

#### AI聊天API (chat.py)
```python
POST /chat/stream                     # 流式聊天
GET  /agents/                         # 获取智能体列表
POST /agents/                         # 创建智能体
GET  /conversations/                  # 获取对话列表
POST /conversations/                  # 创建对话
```

### 3. 认证系统 (auth/)

#### 认证处理器 (auth_handler.py)
- 用户注册和登录
- 多种登录方式支持
- 密码重置和验证
- 第三方登录集成

#### JWT处理器 (jwt_handler.py)
- 访问令牌生成和验证
- 刷新令牌管理
- 令牌过期处理

#### 密码处理器 (password_handler.py)
- 密码加密和验证
- 密码强度检查
- 密码重置令牌

### 4. 权限系统 (utils/permission_utils.py)

#### 角色定义
- **普通用户（家长）**: 浏览课程、购买课程、查看学习进度
- **班主任（教师）**: 创建课程、管理学生、批改作业
- **superadmin**: 系统管理、用户管理、内容审核

#### 权限枚举
```python
class Permissions(Enum):
    # 用户管理权限
    VIEW_USERS = "view_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # 课程管理权限
    VIEW_COURSES = "view_courses"
    CREATE_COURSE = "create_course"
    UPDATE_COURSE = "update_course"
    DELETE_COURSE = "delete_course"
    PUBLISH_COURSE = "publish_course"
    
    # 订单管理权限
    VIEW_ORDERS = "view_orders"
    CREATE_ORDER = "create_order"
    PROCESS_REFUNDS = "process_refunds"
    
    # 系统管理权限
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_PERMISSIONS = "manage_permissions"
    SYSTEM_BACKUP = "system_backup"
```

### 5. 工具模块 (utils/)

#### 日志系统 (services/logger.py)
- 结构化日志记录
- 多级别日志支持
- 性能监控和错误追踪
- 日志轮转和归档

#### 文件上传 (utils/file_upload.py)
- 头像上传和处理
- 图片压缩和格式转换
- 文件类型验证
- 安全文件存储

#### 媒体处理 (utils/media_utils.py)
- 视频时长检测
- 音频时长检测
- 媒体格式转换
- 缩略图生成

#### 摘要工具 (utils/summarization.py)
- 长对话摘要
- 上下文窗口管理
- 智能内容压缩

### 6. 智能体系统 (agents/)

#### 智能体管理器 (agent_manager.py)
- 智能体生命周期管理
- 模型配置和切换
- 工具集成和管理
- 对话状态维护

#### 智能体工厂 (agent_factory.py)
- 智能体创建和配置
- 模型参数设置
- 工具链构建

#### 默认智能体 (default_agents.py)
- 预设智能体配置
- 常用工具集成
- 角色定义和提示词

## 🚀 快速开始

### 环境要求
- Python 3.11+ (推荐3.11，避免LangGraph兼容性问题)
- PostgreSQL 12+
- Redis 6+
- FFmpeg (视频处理)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd muyugan_backend
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **环境配置**
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
```

5. **数据库初始化**
```bash
python database/migrate_knowledge_app.py
```

6. **启动服务**
```bash
# 完整模式（AI + 知识付费）
python main.py

# 简化模式（仅知识付费）
python main_simple.py
```

### 访问服务
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **根路径**: http://localhost:8000/

## 📊 系统特性

### 1. 多模式运行
- **完整模式**: 包含AI聊天和知识付费功能
- **简化模式**: 仅包含知识付费功能
- **动态依赖检测**: 自动检测AI相关依赖可用性

### 2. 权限管理
- **基于角色的访问控制(RBAC)**
- **细粒度权限控制**
- **权限装饰器支持**
- **动态权限检查**

### 3. 数据管理
- **完整的CRUD操作**
- **数据验证和序列化**
- **关系映射和级联操作**
- **数据库迁移支持**

### 4. 文件处理
- **多格式文件上传**
- **图片压缩和转换**
- **视频处理和分析**
- **安全文件存储**

### 5. 日志系统
- **结构化日志记录**
- **多级别日志支持**
- **性能监控**
- **错误追踪和调试**

### 6. AI集成
- **LangGraph智能体框架**
- **多模型支持**
- **工具链集成**
- **对话状态管理**

## 🔍 开发指南

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

## 📈 性能优化

### 数据库优化
- 连接池配置
- 查询优化
- 索引优化
- 缓存策略

### 缓存策略
- Redis缓存
- 查询结果缓存
- 会话缓存
- 静态资源缓存

### 文件处理优化
- 异步文件处理
- 流式文件上传
- 图片压缩
- 视频转码

## 🛡 安全特性

### 认证安全
- JWT令牌认证
- 密码加密存储
- 令牌过期管理
- 会话安全

### 数据安全
- SQL注入防护
- XSS攻击防护
- CSRF保护
- 数据验证

### 文件安全
- 文件类型验证
- 文件大小限制
- 路径遍历防护
- 恶意文件检测

## 📝 API文档

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

## 🚀 部署指南

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

---

**最后更新**: 2024年12月
**版本**: 2.0.0
**状态**: 活跃开发中
