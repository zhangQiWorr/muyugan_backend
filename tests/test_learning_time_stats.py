"""
学习时间统计接口测试
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient

def test_get_learning_time_stats_week(client: TestClient, test_user_data: dict):
    """测试获取周学习时间统计"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取周学习时间统计
    response = client.get("/learning/time-statistics?period=week", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["period"] == "week"
    assert "period_name" in data
    assert "total_duration" in data
    assert "formatted_total_duration" in data
    assert "daily_data" in data
    assert len(data["daily_data"]) == 7  # 一周7天

def test_get_learning_time_stats_month(client: TestClient, test_user_data: dict):
    """测试获取月学习时间统计"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取月学习时间统计
    response = client.get("/learning/time-statistics?period=month", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["period"] == "month"
    assert "period_name" in data
    assert "total_duration" in data
    assert "formatted_total_duration" in data
    assert "daily_data" in data
    assert len(data["daily_data"]) >= 28  # 至少28天

def test_get_learning_time_stats_year(client: TestClient, test_user_data: dict):
    """测试获取年学习时间统计"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取年学习时间统计
    response = client.get("/learning/time-statistics?period=year", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert data["period"] == "year"
    assert "period_name" in data
    assert "total_duration" in data
    assert "formatted_total_duration" in data
    assert "monthly_data" in data
    assert len(data["monthly_data"]) == 12  # 一年12个月

def test_get_learning_time_stats_invalid_period(client: TestClient, test_user_data: dict):
    """测试无效统计周期参数"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 无效统计周期
    response = client.get("/learning/time-statistics?period=invalid", headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "统计周期参数错误" in response.json()["detail"]

def test_get_learning_time_stats_unauthorized(client: TestClient):
    """测试未授权访问学习时间统计"""
    response = client.get("/learning/time-statistics?period=week")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_learning_time_stats_missing_period(client: TestClient, test_user_data: dict):
    """测试缺少统计周期参数"""
    # 注册并登录用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 缺少period参数
    response = client.get("/learning/time-statistics", headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
