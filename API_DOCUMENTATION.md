# AI智能聊天 + 知识付费App后端系统 API文档

## 系统概述
- **系统名称**: AI智能聊天 + 知识付费App后端系统
- **版本**: 2.0.0
- **基础URL**: `http://localhost:8000`
- **认证方式**: Bearer Token (JWT)

## 主要功能模块
1. **用户认证系统** (`/api/auth`)
2. **健康检查** (`/api/health`)
3. **课程管理** (`/api/courses`)
4. **订单支付** (`/api/orders`)
5. **学习管理** (`/api/learning`)
6. **会员管理** (`/api/membership`)
7. **媒体文件** (`/api/media`)
8. **聊天对话** (`/api/chat`)
9. **对话管理** (`/api/conversations`)
10. **智能体管理** (`/api/agents`)
11. **图片管理** (`/api/images`)
12. **超级管理员** (`/api/superadmin`)

---

## 1. 用户认证系统 (`/api/auth`)

### 1.1 用户注册
**POST** `/api/auth/register`

**请求参数:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "用户姓名",
  "role": "user"
}
```

**响应:**
```json
{
  "user": {
    "id": "user_id",
    "username": "username",
    "email": "user@example.com",
    "is_active": true,
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

### 1.2 用户登录
**POST** `/api/auth/login`

**请求参数:**
```json
{
  "login": "username_or_email",
  "password": "password123"
}
```

### 1.3 手机验证码登录
**POST** `/api/auth/login/phone`

**请求参数:**
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

### 1.4 发送短信验证码
**POST** `/api/auth/sms/send`

**请求参数:**
```json
{
  "phone": "13800138000"
}
```

### 1.5 获取当前用户信息
**GET** `/api/auth/me`

**请求头:**
```
Authorization: Bearer <token>
```

### 1.6 更新用户资料
**PUT** `/api/auth/me`

**请求参数:**
```json
{
  "full_name": "新姓名",
  "avatar_url": "头像URL",
  "preferences": {}
}
```

### 1.7 上传头像
**POST** `/api/auth/avatar`

**请求参数:**
- `file`: 图片文件 (multipart/form-data)

---

## 2. 健康检查 (`/api/health`)

### 2.1 根路径
**GET** `/api/health/`

**响应:**
```json
{
  "message": "AI智能聊天对话平台",
  "version": "2.0.0",
  "status": "running"
}
```

### 2.2 健康检查
**GET** `/api/health/health`

**响应:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "2.0.0"
}
```

### 2.3 平台统计
**GET** `/api/health/stats`

**响应:**
```json
{
  "total_users": 1000,
  "total_agents": 10,
  "total_conversations": 5000,
  "total_messages": 50000,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## 3. 课程管理 (`/api/courses`)

### 3.1 获取课程分类列表
**GET** `/api/courses/categories`

**查询参数:**
- `include_inactive`: boolean (是否包含未激活的分类)
- `sort_by`: string (排序字段: sort_order, name, created_at, course_count)
- `sort_order`: string (排序方向: asc, desc)

### 3.2 创建课程分类
**POST** `/api/courses/categories`

**请求参数:**
```json
{
  "name": "分类名称",
  "description": "分类描述",
  "icon": "图标",
  "sort_order": 0,
  "parent_id": "父分类ID"
}
```

### 3.3 获取课程列表
**GET** `/api/courses/`

**查询参数:**
- `page`: int (页码，默认1)
- `size`: int (每页数量，默认20)
- `search`: string (搜索关键词)
- `category_id`: string (分类ID)
- `status`: string (课程状态)
- `featured`: boolean (是否精选)
- `hot`: boolean (是否热门)
- `difficulty`: string (难度级别)
- `price_min`: float (最低价格)
- `price_max`: float (最高价格)
- `sort_by`: string (排序字段)
- `sort_order`: string (排序方向)

### 3.4 创建课程
**POST** `/api/courses/`

**请求参数:**
```json
{
  "title": "课程标题",
  "subtitle": "课程副标题",
  "description": "课程描述",
  "cover_image": "封面图片URL",
  "category_id": "分类ID",
  "tags": ["标签1", "标签2"],
  "price": 99.0,
  "original_price": 199.0,
  "is_free": false,
  "is_member_only": false,
  "difficulty_level": "beginner",
  "language": "zh-CN"
}
```

### 3.5 获取课程详情
**GET** `/api/courses/{course_id}`

### 3.6 更新课程
**PUT** `/api/courses/{course_id}`

### 3.7 删除课程
**DELETE** `/api/courses/{course_id}`

**请求参数:**
```json
{
  "isDeleteLesson": true
}
```

### 3.8 发布课程
**POST** `/api/courses/{course_id}/publish`

### 3.9 下架课程
**POST** `/api/courses/{course_id}/unpublish`

### 3.10 课时管理

#### 创建课时
**POST** `/api/courses/{course_id}/lessons`

**请求参数:**
```json
{
  "title": "课时标题",
  "description": "课时描述",
  "duration": 1800,
  "sort_order": 1,
  "is_free": false,
  "media_ids": ["媒体文件ID列表"]
}
```

#### 获取课时列表
**GET** `/api/courses/{course_id}/lessons`

#### 获取课时详情
**GET** `/api/courses/lessons/{lesson_id}`

#### 更新课时
**PUT** `/api/courses/lessons/{lesson_id}`

#### 删除课时
**DELETE** `/api/courses/lessons/{lesson_id}`

### 3.11 标签管理

#### 获取标签列表
**GET** `/api/courses/tags`

#### 创建标签
**POST** `/api/courses/tags`

**请求参数:**
```json
{
  "name": "标签名称",
  "description": "标签描述",
  "color": "#3B82F6",
  "icon": "标签图标"
}
```

#### 更新标签
**PUT** `/api/courses/tags/{tag_id}`

#### 删除标签
**DELETE** `/api/courses/tags/{tag_id}`

---

## 4. 订单支付 (`/api/orders`)

### 4.1 创建订单
**POST** `/api/orders/`

**请求参数:**
```json
{
  "items": [
    {
      "course_id": "课程ID",
      "quantity": 1
    }
  ],
  "coupon_code": "优惠券代码",
  "remark": "备注"
}
```

### 4.2 获取订单列表
**GET** `/api/orders/`

**查询参数:**
- `page`: int (页码)
- `size`: int (每页数量)
- `status`: string (订单状态)

### 4.3 获取订单详情
**GET** `/api/orders/{order_id}`

### 4.4 取消订单
**POST** `/api/orders/{order_id}/cancel`

### 4.5 创建支付记录
**POST** `/api/orders/{order_id}/pay`

**请求参数:**
```json
{
  "payment_method": "alipay",
  "amount": 99.0
}
```

### 4.6 支付回调
**POST** `/api/orders/{order_id}/pay/callback`

### 4.7 优惠券管理

#### 创建优惠券
**POST** `/api/orders/coupons`

#### 获取优惠券列表
**GET** `/api/orders/coupons`

#### 领取优惠券
**POST** `/api/orders/coupons/{coupon_code}/claim`

#### 获取我的优惠券
**GET** `/api/orders/my-coupons`

---

## 5. 学习管理 (`/api/learning`)

### 5.1 开始学习课时
**POST** `/api/learning/lesson/start`

**请求参数:**
- `lesson_id`: string (课时ID)

### 5.2 更新媒体观看进度
**POST** `/api/learning/media/progress`

**请求参数:**
```json
{
  "media_id": "媒体文件ID",
  "watch_duration": 300,
  "total_duration": 1800
}
```

### 5.3 更新课时学习进度
**POST** `/api/learning/lesson/progress`

**请求参数:**
```json
{
  "lesson_id": "课时ID",
  "watch_duration": 300,
  "total_duration": 1800
}
```

### 5.4 获取最近学习课程
**GET** `/api/learning/courses/recent`

**查询参数:**
- `limit`: int (返回数量限制)
- `user_id`: string (用户ID，管理员可指定)

### 5.5 获取学习统计
**GET** `/api/learning/statistics`

**查询参数:**
- `user_id`: string (用户ID，管理员可指定)

### 5.6 获取继续学习课程
**GET** `/api/learning/courses/continue`

### 5.7 获取已完成课程
**GET** `/api/learning/courses/completed`

### 5.8 获取课程课时进度
**GET** `/api/learning/courses/{course_id}/lessons/statistics`

### 5.9 获取已报名课程列表
**GET** `/api/learning/courses/enrolled`

**查询参数:**
- `page`: int (页码，默认1)
- `size`: int (每页数量，默认10，最大50)
- `user_id`: string (用户ID，管理员可指定)

**响应示例:**
```json
{
  "courses": [
    {
      "course_id": "course_id",
      "title": "课程标题",
      "subtitle": "课程副标题",
      "description": "课程描述",
      "cover_image": "封面图片URL",
      "duration": 3600,
      "lesson_count": 10,
      "difficulty_level": "beginner",
      "is_featured": true,
      "is_hot": false,
      "price": 99.0,
      "original_price": 199.0,
      "enrolled_at": "2025-01-01T00:00:00",
      "last_watch_at": "2025-01-15T10:30:00",
      "course_progress": {
        "progress_percentage": 75.5,
        "total_watch_duration": 2700,
        "total_duration": 3600,
        "completed_lessons": 7,
        "total_lessons": 10,
        "is_completed": false
      },
      "category": {
        "id": "category_id",
        "name": "编程",
        "description": "编程相关课程",
        "icon": "icon_url"
      }
    }
  ],
  "total": 5,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

---

## 6. 会员管理 (`/api/membership`)

### 6.1 会员等级管理

#### 创建会员等级
**POST** `/api/membership/levels`

**请求参数:**
```json
{
  "name": "会员等级名称",
  "description": "等级描述",
  "monthly_price": 29.0,
  "quarterly_price": 79.0,
  "yearly_price": 299.0,
  "lifetime_price": 999.0,
  "max_courses": 100,
  "max_storage": 1000,
  "benefits": {}
}
```

#### 获取会员等级列表
**GET** `/api/membership/levels`

#### 获取会员等级详情
**GET** `/api/membership/levels/{level_id}`

#### 更新会员等级
**PUT** `/api/membership/levels/{level_id}`

#### 删除会员等级
**DELETE** `/api/membership/levels/{level_id}`

### 6.2 会员购买

#### 购买会员
**POST** `/api/membership/purchase`

**请求参数:**
```json
{
  "level_id": "等级ID",
  "membership_type": "monthly",
  "auto_renew": false
}
```

#### 获取我的会员信息
**GET** `/api/membership/my`

#### 取消会员
**POST** `/api/membership/cancel`

#### 续费会员
**POST** `/api/membership/renew`

### 6.3 会员权益管理

#### 创建会员权益
**POST** `/api/membership/benefits`

#### 获取会员权益列表
**GET** `/api/membership/benefits`

#### 更新会员权益
**PUT** `/api/membership/benefits/{benefit_id}`

---

## 7. 媒体文件 (`/api/media`)

### 7.1 获取媒体文件列表
**GET** `/api/media`

**查询参数:**
- `page`: int (页码)
- `size`: int (每页数量)
- `search`: string (搜索关键词)
- `media_type`: string (媒体类型: video/audio/image/document)
- `file_types`: string (文件类型过滤)
- `course_id`: string (课程ID过滤)
- `lesson_id`: string (课时ID过滤)
- `exclude_associated`: boolean (是否排除已关联的媒体文件)

### 7.2 获取媒体文件信息
**GET** `/api/media/info/{media_id}`

### 7.3 删除媒体文件
**DELETE** `/api/media/{media_id}`

### 7.4 同步OSS对象
**POST** `/api/media/sync-oss`

**请求参数:**
```json
{
  "prefix": "对象前缀",
  "max_keys": 1000,
  "force_update": false
}
```

### 7.5 生成预签名URL
**GET** `/api/media/presign/{media_id}`

**查询参数:**
- `expires_in_hours`: int (URL过期时间，默认1小时)

### 7.6 预览媒体文件
**GET** `/api/media/preview/{media_id}`

### 7.7 上报播放事件
**POST** `/api/media/report`

**请求参数:**
```json
{
  "user_id": "用户ID",
  "media_id": "媒体文件ID",
  "event_type": "play",
  "current_time": 30.5,
  "previous_time": 25.0,
  "duration_time": 1800.0,
  "progress": 0.02,
  "playback_rate": 1.0,
  "volume": 0.8,
  "is_fullscreen": false,
  "is_ended": false,
  "device_info": {},
  "extra_data": {}
}
```

---

## 8. 聊天对话 (`/api/chat`)

### 8.1 流式聊天
**POST** `/api/chat/stream`

**请求参数:**
```json
{
  "message": "用户消息",
  "agent_id": "智能体ID",
  "conversation_id": "对话ID",
  "attachments": [
    {
      "type": "image",
      "url": "图片URL"
    }
  ]
}
```

**响应:** Server-Sent Events (SSE) 流式响应

### 8.2 WebSocket聊天
**WebSocket** `/api/chat/ws/{conversation_id}`

---

## 9. 对话管理 (`/api/conversations`)

### 9.1 获取对话列表
**GET** `/api/conversations`

**查询参数:**
- `skip`: int (跳过数量)
- `limit`: int (限制数量)
- `search`: string (搜索关键词)

### 9.2 创建对话
**POST** `/api/conversations`

**请求参数:**
```json
{
  "title": "对话标题",
  "agent_id": "智能体ID"
}
```

### 9.3 获取对话详情
**GET** `/api/conversations/{conversation_id}`

### 9.4 更新对话
**PUT** `/api/conversations/{conversation_id}`

**请求参数:**
```json
{
  "title": "新标题",
  "tags": ["标签1", "标签2"]
}
```

### 9.5 删除对话
**DELETE** `/api/conversations/{conversation_id}`

---

## 10. 智能体管理 (`/api/agents`)

### 10.1 获取智能体列表
**GET** `/api/agents`

**查询参数:**
- `category`: string (分类)
- `search`: string (搜索关键词)
- `skip`: int (跳过数量)
- `limit`: int (限制数量)

### 10.2 获取智能体详情
**GET** `/api/agents/{agent_id}`

### 10.3 创建智能体
**POST** `/api/agents`

**请求参数:**
```json
{
  "name": "智能体名称",
  "display_name": "显示名称",
  "description": "描述",
  "model_name": "模型名称",
  "system_prompt": "系统提示",
  "temperature": 0.7,
  "max_tokens": 2048,
  "tools_enabled": ["工具列表"],
  "category": "general",
  "tags": ["标签"],
  "suggested_topics": ["建议话题"]
}
```

### 10.4 更新智能体
**PUT** `/api/agents/{agent_id}`

### 10.5 删除智能体
**DELETE** `/api/agents/{agent_id}`

### 10.6 获取可用模型
**GET** `/api/agents/models/available`

### 10.7 获取可用工具
**GET** `/api/agents/tools/available`

---

## 11. 图片管理 (`/api/images`)

### 11.1 上传图片
**POST** `/api/images/upload`

**请求参数:**
- `file`: 图片文件 (multipart/form-data)
- `image_type`: string (图片类型)
- `description`: string (描述)

### 11.2 获取图片信息
**GET** `/api/images/{image_id}`

### 11.3 删除图片
**DELETE** `/api/images/{image_id}`

### 11.4 获取图片列表
**GET** `/api/images/list`

---

## 12. 超级管理员 (`/api/superadmin`)

### 12.1 用户管理

#### 获取所有用户
**GET** `/api/superadmin/users`

**查询参数:**
- `page`: int (页码)
- `size`: int (每页数量)
- `search`: string (搜索关键词)
- `role`: string (角色筛选)
- `is_active`: boolean (状态筛选)
- `sort_by`: string (排序字段)
- `sort_order`: string (排序顺序)

#### 创建用户
**POST** `/api/superadmin/users`

**请求参数:**
```json
{
  "username": "用户名",
  "email": "邮箱",
  "phone": "手机号",
  "role": "user",
  "is_active": true,
  "password": "密码"
}
```

#### 更新用户
**PUT** `/api/superadmin/users/{user_id}`

#### 删除用户
**DELETE** `/api/superadmin/users/{user_id}`

### 12.2 权限管理

#### 获取角色权限配置
**GET** `/api/superadmin/roles/permissions`

#### 获取所有角色
**GET** `/api/superadmin/roles`

#### 获取所有权限
**GET** `/api/superadmin/permissions`

### 12.3 审计日志
**GET** `/api/superadmin/audit-logs`

### 12.4 仪表板统计
**GET** `/api/superadmin/dashboard/stats`

### 12.5 课程报名管理

#### 批量创建报名
**POST** `/api/superadmin/enrollments/batch`

**请求参数:**
```json
{
  "user_id": "用户ID",
  "course_ids": ["课程ID列表"]
}
```

#### 批量删除报名
**DELETE** `/api/superadmin/enrollments/batch`

#### 获取报名列表
**GET** `/api/superadmin/enrollments`

#### 停用报名
**PUT** `/api/superadmin/enrollments/{enrollment_id}/deactivate`

---

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

### 错误响应
```json
{
  "success": false,
  "error": "错误信息",
  "detail": "详细错误描述"
}
```

### 分页响应
```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

---

## 认证说明

所有需要认证的API都需要在请求头中包含JWT token：

```
Authorization: Bearer <your_jwt_token>
```

## 错误码说明

- `200`: 成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 快速开始

1. 启动服务器：`python main.py`
2. 访问API文档：`http://localhost:8000/docs`
3. 使用Swagger UI进行API测试

## 注意事项

1. 所有时间格式均为ISO 8601格式
2. 分页参数从1开始
3. 文件上传使用multipart/form-data格式
4. 流式聊天使用Server-Sent Events (SSE)
5. WebSocket连接需要先建立认证
