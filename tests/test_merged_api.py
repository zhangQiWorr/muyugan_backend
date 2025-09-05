#!/usr/bin/env python3
"""
测试合并后的课程管理API
验证courses_merged.py中的接口是否正常工作
"""

import requests
import json
from typing import Dict, Any, Optional

# API基础配置
BASE_URL = "http://localhost:8001"
HEADERS = {
    "Content-Type": "application/json"
}

# 测试用户凭据
TEST_CREDENTIALS = {
    "admin": {
        "login": "admin@muyugan.com",
        "password": "admin123"
    },
    "teacher": {
        "login": "zhang@muyugan.com", 
        "password": "teacher123"
    }
}

def login_user(user_type: str) -> str:
    """用户登录获取token"""
    try:
        credentials = TEST_CREDENTIALS[user_type]
        response = requests.post(
            f"{BASE_URL}/auth/login",
            headers=HEADERS,
            json=credentials
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✅ {user_type} 登录成功")
            return token or ""
        else:
            print(f"❌ {user_type} 登录失败: {response.status_code} - {response.text}")
            return ""
            
    except Exception as e:
        print(f"❌ {user_type} 登录异常: {str(e)}")
        return ""

def test_api_endpoint(endpoint: str, method: str = "GET", token: str = "", data: Optional[Dict[Any, Any]] = None) -> bool:
    """测试API接口"""
    try:
        headers = HEADERS.copy()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data or {})
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data or {})
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            print(f"❌ 不支持的HTTP方法: {method}")
            return False
            
        if response.status_code in [200, 201]:
            print(f"✅ {method} {endpoint} - 成功 ({response.status_code})")
            return True
        else:
            print(f"❌ {method} {endpoint} - 失败 ({response.status_code}): {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ {method} {endpoint} - 异常: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试合并后的课程管理API")
    print("=" * 50)
    
    # 1. 测试用户登录
    print("\n📝 测试用户登录...")
    admin_token = login_user("admin")
    teacher_token = login_user("teacher")
    
    if not admin_token:
        print("❌ 管理员登录失败，无法继续测试")
        return
    
    # 2. 测试基础接口
    print("\n🔍 测试基础接口...")
    test_cases = [
        # 健康检查
        ("/health", "GET", None),
        
        # 课程分类接口
        ("/courses/categories", "GET", admin_token),
        
        # 课程列表接口
        ("/courses", "GET", admin_token),
        
        # 课程标签接口
        ("/courses/tags", "GET", admin_token),
        
        # 课程统计接口
        ("/courses/statistics", "GET", admin_token),
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for endpoint, method, token in test_cases:
        if test_api_endpoint(endpoint, method, token):
            success_count += 1
    
    # 3. 测试创建操作
    print("\n📝 测试创建操作...")
    
    # 测试创建分类
    category_data = {
        "name": "测试分类",
        "description": "这是一个测试分类",
        "parent_id": None
    }
    
    if test_api_endpoint("/courses/categories", "POST", admin_token, category_data):
        success_count += 1
    total_count += 1
    
    # 测试创建标签
    tag_data = {
        "name": "测试标签",
        "description": "这是一个测试标签",
        "color": "#FF5722"
    }
    
    if test_api_endpoint("/courses/tags", "POST", admin_token, tag_data):
        success_count += 1
    total_count += 1
    
    # 4. 输出测试结果
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_count} 接口测试通过")
    
    if success_count == total_count:
        print("🎉 所有API接口测试通过！合并成功！")
    else:
        print(f"⚠️ 有 {total_count - success_count} 个接口测试失败，需要检查")
    
    print("\n🔗 可用的API接口:")
    print("- 课程管理: http://localhost:8001/courses")
    print("- 分类管理: http://localhost:8001/courses/categories")
    print("- 标签管理: http://localhost:8001/courses/tags")
    print("- 统计信息: http://localhost:8001/courses/statistics")
    print("- API文档: http://localhost:8001/docs")

if __name__ == "__main__":
    main()