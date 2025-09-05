"""
性能测试模块
"""
import pytest
import time
from fastapi.testclient import TestClient


@pytest.mark.performance
def test_api_response_time(client: TestClient):
    """测试API响应时间"""
    endpoints = [
        "/health",
        "/courses/",
        "/courses/categories",
        "/membership/levels"
    ]
    
    for endpoint in endpoints:
        start_time = time.time()
        response = client.get(endpoint)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        # 响应时间应该在合理范围内
        assert response_time < 1000, f"端点 {endpoint} 响应时间过长: {response_time:.2f}ms"
        assert response.status_code == 200, f"端点 {endpoint} 返回错误状态码: {response.status_code}"
        
        print(f"✅ {endpoint}: {response_time:.2f}ms")

@pytest.mark.performance
def test_concurrent_user_registration(client: TestClient):
    """测试并发用户注册性能"""
    import threading
    import queue
    
    results = queue.Queue()
    
    def register_user(user_id: int):
        """注册单个用户"""
        user_data = {
            "username": f"testuser{user_id}",
            "email": f"test{user_id}@example.com",
            "password": "testpassword123",
            "full_name": f"Test User {user_id}",
            "phone": f"138001380{user_id:02d}"
        }
        
        start_time = time.time()
        response = client.post("/auth/register", json=user_data)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        results.put((user_id, response.status_code, response_time))
    
    # 创建多个线程并发注册用户
    threads = []
    num_users = 10
    
    for i in range(num_users):
        thread = threading.Thread(target=register_user, args=(i,))
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 收集结果
    total_time = 0
    success_count = 0
    
    while not results.empty():
        user_id, status_code, response_time = results.get()
        total_time += response_time
        
        if status_code == 201:
            success_count += 1
        
        print(f"用户 {user_id}: 状态码 {status_code}, 响应时间 {response_time:.2f}ms")
    
    avg_time = total_time / num_users
    
    print(f"并发注册 {num_users} 个用户:")
    print(f"成功: {success_count}/{num_users}")
    print(f"平均响应时间: {avg_time:.2f}ms")
    print(f"总响应时间: {total_time:.2f}ms")
    
    # 性能断言
    assert avg_time < 500, f"平均响应时间过长: {avg_time:.2f}ms"
    assert success_count >= num_users * 0.8, f"成功率过低: {success_count}/{num_users}"

@pytest.mark.performance
def test_database_query_performance(client: TestClient, test_user_data: dict):
    """测试数据库查询性能"""
    # 注册用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试课程列表查询性能
    query_times = []
    
    for i in range(10):
        start_time = time.time()
        response = client.get("/courses/", headers=headers)
        end_time = time.time()
        
        query_time = (end_time - start_time) * 1000
        query_times.append(query_time)
        
        assert response.status_code == 200
    
    avg_query_time = sum(query_times) / len(query_times)
    max_query_time = max(query_times)
    min_query_time = min(query_times)
    
    print(f"数据库查询性能测试:")
    print(f"平均查询时间: {avg_query_time:.2f}ms")
    print(f"最大查询时间: {max_query_time:.2f}ms")
    print(f"最小查询时间: {min_query_time:.2f}ms")
    
    # 性能断言
    assert avg_query_time < 200, f"平均查询时间过长: {avg_query_time:.2f}ms"
    assert max_query_time < 500, f"最大查询时间过长: {max_query_time:.2f}ms"

@pytest.mark.performance
def test_memory_usage():
    """测试内存使用情况"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    memory_mb = memory_info.rss / 1024 / 1024
    
    print(f"当前内存使用: {memory_mb:.2f} MB")
    
    # 内存使用应该在合理范围内
    assert memory_mb < 500, f"内存使用过高: {memory_mb:.2f} MB"

@pytest.mark.performance
def test_file_upload_performance(client: TestClient, test_user_data: dict):
    """测试文件上传性能"""
    # 注册用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试不同大小的文件上传
    file_sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB
    
    for size in file_sizes:
        # 生成测试文件内容
        file_content = b"0" * size
        
        start_time = time.time()
        files = {"file": (f"test_{size}.txt", file_content, "text/plain")}
        response = client.post("/auth/avatar", files=files, headers=headers)
        end_time = time.time()
        
        upload_time = (end_time - start_time) * 1000
        speed = size / upload_time * 1000  # KB/s
        
        print(f"文件大小 {size} bytes: 上传时间 {upload_time:.2f}ms, 速度 {speed:.2f} KB/s")
        
        # 上传应该成功
        assert response.status_code in [200, 201], f"文件上传失败: {response.status_code}"

@pytest.mark.performance
def test_concurrent_course_creation(client: TestClient, test_user_data: dict):
    """测试并发课程创建性能"""
    # 注册用户
    register_response = client.post("/auth/register", json=test_user_data)
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    import threading
    import queue
    
    results = queue.Queue()
    
    def create_course(course_id: int):
        """创建单个课程"""
        course_data = {
            "title": f"测试课程 {course_id}",
            "description": f"这是测试课程 {course_id} 的描述",
            "price": 99.0,
            "is_free": False,
            "difficulty_level": "beginner",
            "language": "zh-CN"
        }
        
        start_time = time.time()
        response = client.post("/courses/", json=course_data, headers=headers)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        results.put((course_id, response.status_code, response_time))
    
    # 创建多个线程并发创建课程
    threads = []
    num_courses = 5
    
    for i in range(num_courses):
        thread = threading.Thread(target=create_course, args=(i,))
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 收集结果
    total_time = 0
    success_count = 0
    
    while not results.empty():
        course_id, status_code, response_time = results.get()
        total_time += response_time
        
        if status_code == 201:
            success_count += 1
        
        print(f"课程 {course_id}: 状态码 {status_code}, 响应时间 {response_time:.2f}ms")
    
    avg_time = total_time / num_courses
    
    print(f"并发创建 {num_courses} 个课程:")
    print(f"成功: {success_count}/{num_courses}")
    print(f"平均响应时间: {avg_time:.2f}ms")
    
    # 性能断言
    assert avg_time < 1000, f"平均响应时间过长: {avg_time:.2f}ms"
    assert success_count >= num_courses * 0.8, f"成功率过低: {success_count}/{num_courses}"

@pytest.mark.performance
def test_search_performance(client: TestClient):
    """测试搜索性能"""
    search_queries = ["python", "java", "javascript", "react", "vue"]
    
    search_times = []
    
    for query in search_queries:
        start_time = time.time()
        response = client.get(f"/courses/?search={query}")
        end_time = time.time()
        
        search_time = (end_time - start_time) * 1000
        search_times.append(search_time)
        
        assert response.status_code == 200
    
    avg_search_time = sum(search_times) / len(search_times)
    max_search_time = max(search_times)
    
    print(f"搜索性能测试:")
    print(f"平均搜索时间: {avg_search_time:.2f}ms")
    print(f"最大搜索时间: {max_search_time:.2f}ms")
    
    # 性能断言
    assert avg_search_time < 300, f"平均搜索时间过长: {avg_search_time:.2f}ms"
    assert max_search_time < 800, f"最大搜索时间过长: {max_search_time:.2f}ms"

@pytest.mark.performance
def test_pagination_performance(client: TestClient):
    """测试分页性能"""
    page_sizes = [10, 20, 50, 100]
    
    pagination_times = []
    
    for size in page_sizes:
        start_time = time.time()
        response = client.get(f"/courses/?page=1&size={size}")
        end_time = time.time()
        
        pagination_time = (end_time - start_time) * 1000
        pagination_times.append(pagination_time)
        
        assert response.status_code == 200
    
    avg_pagination_time = sum(pagination_times) / len(pagination_times)
    
    print(f"分页性能测试:")
    print(f"平均分页时间: {avg_pagination_time:.2f}ms")
    
    # 性能断言
    assert avg_pagination_time < 400, f"平均分页时间过长: {avg_pagination_time:.2f}ms"

@pytest.mark.performance
def test_authentication_performance(client: TestClient, test_user_data: dict):
    """测试认证性能"""
    # 注册用户
    client.post("/auth/register", json=test_user_data)
    
    # 测试多次登录性能
    login_times = []
    
    for i in range(10):
        login_data = {
            "login": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        start_time = time.time()
        response = client.post("/auth/login", json=login_data)
        end_time = time.time()
        
        login_time = (end_time - start_time) * 1000
        login_times.append(login_time)
        
        assert response.status_code == 200
    
    avg_login_time = sum(login_times) / len(login_times)
    max_login_time = max(login_times)
    
    print(f"认证性能测试:")
    print(f"平均登录时间: {avg_login_time:.2f}ms")
    print(f"最大登录时间: {max_login_time:.2f}ms")
    
    # 性能断言
    assert avg_login_time < 200, f"平均登录时间过长: {avg_login_time:.2f}ms"
    assert max_login_time < 500, f"最大登录时间过长: {max_login_time:.2f}ms"
