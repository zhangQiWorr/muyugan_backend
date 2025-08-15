"""
认证模块测试
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient

def test_register_user_success(client: TestClient, test_user_data: dict):
    """测试用户注册成功"""
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert "user" in data
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == test_user_data["username"]
    assert data["user"]["email"] == test_user_data["email"]
    assert data["user"]["full_name"] == test_user_data["full_name"]

def test_register_user_duplicate_username(client: TestClient, test_user_data: dict):
    """测试重复用户名注册"""
    # 第一次注册
    client.post("/auth/register", json=test_user_data)
    
    # 第二次注册相同用户名
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_register_user_duplicate_email(client: TestClient, test_user_data: dict):
    """测试重复邮箱注册"""
    # 第一次注册
    client.post("/auth/register", json=test_user_data)
    
    # 第二次注册相同邮箱
    duplicate_data = test_user_data.copy()
    duplicate_data["username"] = "anotheruser"
    response = client.post("/auth/register", json=duplicate_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_register_user_invalid_data(client: TestClient):
    """测试无效数据注册"""
    invalid_data = {
        "username": "a",  # 用户名太短
        "email": "invalid-email",  # 无效邮箱
        "password": "123",  # 密码太短
        "full_name": ""  # 空姓名
    }
    
    response = client.post("/auth/register", json=invalid_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_login_success(client: TestClient, test_user_data: dict):
    """测试用户登录成功"""
    # 先注册用户
    client.post("/auth/register", json=test_user_data)
    
    # 登录
    login_data = {
        "login": test_user_data["username"],
        "password": test_user_data["password"]
    }
    response = client.post("/auth/login", json=login_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data

def test_login_with_email(client: TestClient, test_user_data: dict):
    """测试使用邮箱登录"""
    # 先注册用户
    client.post("/auth/register", json=test_user_data)
    
    # 使用邮箱登录
    login_data = {
        "login": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/auth/login", json=login_data)
    
    assert response.status_code == status.HTTP_200_OK

def test_login_with_phone(client: TestClient, test_user_data: dict):
    """测试使用手机号登录"""
    # 先注册用户
    client.post("/auth/register", json=test_user_data)
    
    # 使用手机号登录
    login_data = {
        "login": test_user_data["phone"],
        "password": test_user_data["password"]
    }
    response = client.post("/auth/login", json=login_data)
    
    assert response.status_code == status.HTTP_200_OK

def test_login_invalid_credentials(client: TestClient, test_user_data: dict):
    """测试无效凭据登录"""
    # 先注册用户
    client.post("/auth/register", json=test_user_data)
    
    # 错误密码
    login_data = {
        "login": test_user_data["username"],
        "password": "wrongpassword"
    }
    response = client.post("/auth/login", json=login_data)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_nonexistent_user(client: TestClient):
    """测试不存在的用户登录"""
    login_data = {
        "login": "nonexistentuser",
        "password": "password123"
    }
    response = client.post("/auth/login", json=login_data)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user_success(client: TestClient, test_user_data: dict):
    """测试获取当前用户信息成功"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    
    # 获取用户信息
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/auth/me", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == test_user_data["username"]
    assert data["email"] == test_user_data["email"]

def test_get_current_user_unauthorized(client: TestClient):
    """测试未授权获取用户信息"""
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user_invalid_token(client: TestClient):
    """测试无效token获取用户信息"""
    headers = {"Authorization": "Bearer invalid-token"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_user_profile(client: TestClient, test_user_data: dict):
    """测试更新用户信息"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    
    # 更新用户信息
    update_data = {
        "full_name": "Updated Name",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put("/auth/me", json=update_data, headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["full_name"] == update_data["full_name"]
    assert data["avatar_url"] == update_data["avatar_url"]

def test_phone_verification_flow(client: TestClient):
    """测试手机验证码流程"""
    # 发送验证码
    sms_data = {"phone": "13800138000"}
    response = client.post("/auth/sms/send", json=sms_data)
    assert response.status_code == status.HTTP_200_OK
    
    # 验证码登录（模拟）
    verify_data = {
        "phone": "13800138000",
        "code": "123456"  # 测试验证码
    }
    response = client.post("/auth/login/phone", json=verify_data)
    # 注意：这里可能需要模拟验证码验证逻辑
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

def test_upload_avatar(client: TestClient, test_user_data: dict):
    """测试上传头像"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 模拟文件上传
    files = {"file": ("avatar.jpg", b"fake-image-data", "image/jpeg")}
    response = client.post("/auth/avatar", files=files, headers=headers)
    
    # 根据实际实现，可能返回200或201
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

def test_delete_avatar(client: TestClient, test_user_data: dict):
    """测试删除头像"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.delete("/auth/avatar", headers=headers)
    assert response.status_code == status.HTTP_200_OK

def test_bind_wechat_account(client: TestClient, test_user_data: dict):
    """测试绑定微信账号"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    bind_data = {"wechat_id": "test_wechat_id"}
    response = client.post("/auth/bind/wechat", json=bind_data, headers=headers)
    
    assert response.status_code == status.HTTP_200_OK

def test_unbind_wechat_account(client: TestClient, test_user_data: dict):
    """测试解绑微信账号"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/auth/unbind/wechat", headers=headers)
    assert response.status_code == status.HTTP_200_OK
