"""
课程管理模块测试
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient

def test_create_course_success(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试创建课程成功"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    response = client.post("/courses/", json=test_course_data, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert data["title"] == test_course_data["title"]
    assert data["description"] == test_course_data["description"]
    assert data["price"] == test_course_data["price"]
    assert data["creator_id"] is not None

def test_create_course_unauthorized(client: TestClient, test_course_data: dict):
    """测试未授权创建课程"""
    response = client.post("/courses/", json=test_course_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_course_invalid_data(client: TestClient, test_user_data: dict):
    """测试无效数据创建课程"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 无效数据
    invalid_data = {
        "title": "",  # 空标题
        "price": -100,  # 负数价格
        "is_free": True  # 免费课程但有价格
    }
    
    response = client.post("/courses/", json=invalid_data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_get_courses_list(client: TestClient):
    """测试获取课程列表"""
    response = client.get("/courses/")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data

def test_get_courses_with_pagination(client: TestClient):
    """测试分页获取课程列表"""
    response = client.get("/courses/?page=1&size=10")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["page"] == 1
    assert data["size"] == 10

def test_get_courses_with_search(client: TestClient):
    """测试搜索课程"""
    response = client.get("/courses/?search=python")
    assert response.status_code == status.HTTP_200_OK

def test_get_courses_with_category(client: TestClient):
    """测试按分类获取课程"""
    response = client.get("/courses/?category_id=123")
    assert response.status_code == status.HTTP_200_OK

def test_get_courses_with_status(client: TestClient):
    """测试按状态获取课程"""
    response = client.get("/courses/?status=published")
    assert response.status_code == status.HTTP_200_OK

def test_get_course_detail(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试获取课程详情"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 获取课程详情
    response = client.get(f"/courses/{course_id}")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["id"] == course_id
    assert data["title"] == test_course_data["title"]

def test_get_course_detail_not_found(client: TestClient):
    """测试获取不存在的课程详情"""
    response = client.get("/courses/nonexistent-id")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_update_course_success(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试更新课程成功"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 更新课程
    update_data = {
        "title": "Updated Course Title",
        "description": "Updated description",
        "price": 199.0
    }
    response = client.put(f"/courses/{course_id}", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]
    assert data["price"] == update_data["price"]

def test_update_course_unauthorized(client: TestClient, test_course_data: dict):
    """测试未授权更新课程"""
    update_data = {"title": "Updated Title"}
    response = client.put("/courses/test-id", json=update_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_course_not_found(client: TestClient, test_user_data: dict):
    """测试更新不存在的课程"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    update_data = {"title": "Updated Title"}
    response = client.put("/courses/nonexistent-id", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_publish_course(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试发布课程"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 发布课程
    response = client.post(f"/courses/{course_id}/publish", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # 验证课程状态
    detail_response = client.get(f"/courses/{course_id}")
    assert detail_response.json()["status"] == "published"

def test_unpublish_course(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试下架课程"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 先发布课程
    client.post(f"/courses/{course_id}/publish", headers=headers)
    
    # 下架课程
    response = client.post(f"/courses/{course_id}/unpublish", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # 验证课程状态
    detail_response = client.get(f"/courses/{course_id}")
    assert detail_response.json()["status"] == "offline"

def test_create_course_category(client: TestClient, test_user_data: dict):
    """测试创建课程分类"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    category_data = {
        "name": "编程开发",
        "description": "编程相关课程",
        "icon": "code",
        "sort_order": 1
    }
    
    response = client.post("/courses/categories", json=category_data, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert data["name"] == category_data["name"]
    assert data["description"] == category_data["description"]

def test_get_course_categories(client: TestClient):
    """测试获取课程分类列表"""
    response = client.get("/courses/categories")
    assert response.status_code == status.HTTP_200_OK

def test_update_course_category(client: TestClient, test_user_data: dict):
    """测试更新课程分类"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 先创建分类
    category_data = {"name": "测试分类", "description": "测试描述"}
    create_response = client.post("/courses/categories", json=category_data, headers=headers)
    category_id = create_response.json()["id"]
    
    # 更新分类
    update_data = {"name": "Updated Category", "description": "Updated description"}
    response = client.put(f"/courses/categories/{category_id}", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK

def test_delete_course_category(client: TestClient, test_user_data: dict):
    """测试删除课程分类"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 先创建分类
    category_data = {"name": "测试分类", "description": "测试描述"}
    create_response = client.post("/courses/categories", json=category_data, headers=headers)
    category_id = create_response.json()["id"]
    
    # 删除分类
    response = client.delete(f"/courses/categories/{category_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK

def test_create_course_lesson(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试创建课程课时"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 创建课时
    lesson_data = {
        "title": "第一课时",
        "description": "课时描述",
        "content_type": "video",
        "content_url": "https://example.com/video.mp4",
        "duration": 1800,
        "sort_order": 1,
        "is_free": False
    }
    
    response = client.post(f"/courses/{course_id}/lessons", json=lesson_data, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert data["title"] == lesson_data["title"]
    assert data["course_id"] == course_id

def test_get_course_lessons(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试获取课程课时列表"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 获取课时列表
    response = client.get(f"/courses/{course_id}/lessons")
    assert response.status_code == status.HTTP_200_OK

def test_update_course_lesson(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试更新课程课时"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 创建课时
    lesson_data = {"title": "测试课时", "description": "测试描述"}
    lesson_response = client.post(f"/courses/{course_id}/lessons", json=lesson_data, headers=headers)
    lesson_id = lesson_response.json()["id"]
    
    # 更新课时
    update_data = {"title": "Updated Lesson", "description": "Updated description"}
    response = client.put(f"/courses/lessons/{lesson_id}", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK

def test_delete_course_lesson(client: TestClient, test_user_data: dict, test_course_data: dict):
    """测试删除课程课时"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 创建课程
    create_response = client.post("/courses/", json=test_course_data, headers=headers)
    course_id = create_response.json()["id"]
    
    # 创建课时
    lesson_data = {"title": "测试课时", "description": "测试描述"}
    lesson_response = client.post(f"/courses/{course_id}/lessons", json=lesson_data, headers=headers)
    lesson_id = lesson_response.json()["id"]
    
    # 删除课时
    response = client.delete(f"/courses/lessons/{lesson_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
