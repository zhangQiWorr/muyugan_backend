"""审计日志中间件"""
import time
import json
from typing import Callable, Optional, Dict, Any, Union
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.user import User
from utils.audit_service import AuditService
from auth.jwt_handler import JWTHandler


class AuditMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""
    
    def __init__(self, app, skip_paths: Optional[list] = None):
        super().__init__(app)
        # 跳过记录的路径
        self.skip_paths = skip_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/health",
            "/static",
            "/api/superadmin/audit-logs",  # 排除审计日志查询接口
            "api/superadmin/permissions",  # 排除权限查询接口
            "/api/roles/permissions",  # 排除权限查询接口
            "/api/superadmin/roles",

            "/api/admin",  # 排除管理员接口
            "/metrics",  # 排除监控指标接口
            "/ping"  # 排除ping接口
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # 获取用户信息
        user = await self._get_user_from_request(request)

        print("AuditMiddleware:", request.method, request.url.path, user)
        
        # 检查是否需要跳过记录（包括超级管理员检查）
        if self._should_skip_logging(request, user):
            return await call_next(request)
        
        # 提取请求信息
        action = self._extract_action(request)
        resource_info = self._extract_resource_info(request)
        
        response = None
        status = "success"
        error_message = None
        
        try:
            response = await call_next(request)
            
            # 根据HTTP状态码判断操作状态
            if response.status_code >= 400:
                status = "failed" if response.status_code < 500 else "error"
                
        except Exception as e:
            status = "error"
            error_message = str(e)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
        
        # 记录审计日志
        print(f"About to log audit: path={request.url.path}, user={user}, skip={self._should_skip_logging(request, user)}")
        await self._log_request(
            request=request,
            user=user,
            action=action,
            resource_type=resource_info.get("type"),
            resource_id=resource_info.get("id"),
            resource_name=resource_info.get("name"),
            status=status,
            error_message=error_message,
            start_time=start_time,
            response=response
        )
        
        return response
    
    def _should_skip_logging(self, request: Request, user: Optional[User] = None) -> bool:
        """判断是否应该跳过日志记录"""
        path = request.url.path
        method = request.method
        
        # 登录操作始终记录，即使是超级管理员
        if path == "/auth/login" and method == "POST":
            return False
            
        # 跳过超级管理员的其他操作
        if user and str(user.role) == 'superadmin':
            return True
        
        # 跳过静态文件和文档路径
        for skip_path in self.skip_paths:
            if path.startswith(skip_path):
                return True
        
        # 跳过健康检查
        if path == "/" and method == "GET":
            return True
        
        # 跳过简单的GET查询请求（减少日志量）
        if method == "GET":
            # 跳过列表查询接口（除非有特殊参数）
            if any(keyword in path for keyword in ["/list", "/search", "/query"]):
                # 如果没有重要的查询参数，跳过记录
                query_params = dict(request.query_params)
                important_params = {'user_id', 'course_id', 'order_id', 'payment_id'}
                if not any(param in query_params for param in important_params):
                    return True
        
        # 跳过频繁的状态检查接口
        if path.endswith('/status') or path.endswith('/info'):
            return True
            
        return False
    
    async def _get_user_from_request(self, request: Request) -> Optional[User]:
        """从请求中获取用户信息"""
        try:
            # 首先尝试从Authorization头获取token
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
                # 验证token并获取用户ID
                payload = JWTHandler().verify_token(token)
                
                if payload:
                    # JWT token中使用'sub'字段存储用户ID
                    user_id = payload.get("sub") or payload.get("user_id")
                    if user_id:
                        # 从数据库获取用户信息
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.id == user_id).first()
                            if user:
                                return user
                        finally:
                            db.close()
            
            # 如果无法从token获取用户信息，且是登录请求，尝试从请求体获取
            if request.url.path.endswith("/login") and request.method.upper() == "POST":
                return await self._get_user_from_login_request(request)
                
        except Exception as e:
            pass
            
        return None
    
    async def _get_user_from_login_request(self, request: Request) -> Optional[User]:
        """从登录请求中获取用户信息"""
        try:
            # 对于登录请求，我们无法在中间件中安全地读取请求体
            # 因为这会消耗请求体，导致后续的路由处理器无法读取
            # 所以对于登录请求，我们返回None，让后续处理在响应后进行
            return None
                
        except Exception as e:
            pass
            
        return None
    
    async def _get_user_from_login_response(self, response: Any) -> Optional[User]:
        """从登录响应中获取用户信息"""
        try:
            print(f"Attempting to extract user from login response. Response type: {type(response)}")
            
            # 处理StreamingResponse (检查是否有body_iterator属性)
            if hasattr(response, 'body_iterator'):
                print("Found StreamingResponse with body_iterator")
                # 收集所有响应块
                body_parts = []
                async for chunk in response.body_iterator:
                    body_parts.append(chunk)
                
                # 合并所有块
                if body_parts:
                    body = b''.join(body_parts)
                    body_str = body.decode('utf-8')
                    print(f"StreamingResponse body content: {body_str[:200]}...")
                    
                    # 解析JSON响应
                    response_data = json.loads(body_str)
                    user_info = response_data.get('user')
                    print(f"User info from response: {user_info}")
                    
                    if user_info and user_info.get('id'):
                        # 从数据库获取完整的用户信息
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.id == user_info['id']).first()
                            print(f"Found user in database: {user}")
                            return user
                        finally:
                            db.close()
                            
            # 处理普通Response
            elif hasattr(response, 'body'):
                print("Found regular Response with body")
                body = response.body
                print(f"Response body type: {type(body)}, length: {len(body) if body else 0}")
                if body:
                    # 将body转换为字符串
                    if isinstance(body, (bytes, bytearray)):
                        body_str = body.decode('utf-8')
                    else:
                        # 处理memoryview等其他类型
                        body_str = bytes(body).decode('utf-8')
                    
                    print(f"Response body content: {body_str[:200]}...")  # 只打印前200个字符
                    
                    # 解析JSON响应
                    response_data = json.loads(body_str)
                    user_info = response_data.get('user')
                    print(f"User info from response: {user_info}")
                    
                    if user_info and user_info.get('id'):
                        # 从数据库获取完整的用户信息
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.id == user_info['id']).first()
                            print(f"Found user in database: {user}")
                            return user
                        finally:
                            db.close()
            else:
                print("Response has no body or body_iterator attribute")
                
        except Exception as e:
            print(f"Error extracting user from login response: {e}")
            
        return None
    
    def _extract_action(self, request: Request) -> str:
        """从请求中提取操作类型"""
        method = request.method.lower()
        path = request.url.path
        
        # 根据HTTP方法和路径推断操作类型
        if method == "post":
            if "login" in path:
                return "login"
            elif "logout" in path:
                return "logout"
            elif "register" in path:
                return "register"
            else:
                return "create"
        elif method == "put" or method == "patch":
            return "update"
        elif method == "delete":
            return "delete"
        elif method == "get":
            return "view"
        else:
            return "unknown"
    
    def _extract_resource_info(self, request: Request) -> Dict[str, Optional[str]]:
        """从请求中提取资源信息"""
        path = request.url.path
        path_parts = [part for part in path.split("/") if part]
        
        resource_type = None
        resource_id = None
        
        # 尝试从路径中提取资源类型和ID
        if len(path_parts) >= 2:
            if path_parts[0] == "api":
                if len(path_parts) >= 3:
                    resource_type = path_parts[2]  # 例如: /api/superadmin/users -> users
                    if len(path_parts) >= 4 and path_parts[3] not in ["search", "export"]:
                        resource_id = path_parts[3]  # 例如: /api/superadmin/users/123 -> 123
            else:
                resource_type = path_parts[0]
                if len(path_parts) >= 2:
                    resource_id = path_parts[1]
        
        return {
            "type": resource_type,
            "id": resource_id,
            "name": None  # 资源名称需要从业务逻辑中获取
        }
    
    async def _log_request(
        self,
        request: Request,
        user: Optional[User],
        action: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        resource_name: Optional[str],
        status: str,
        error_message: Optional[str],
        start_time: float,
        response: Optional[Response]
    ):
        """记录请求日志"""
        print(f"_log_request called: action={action}, user={user}")
        try:
            db = SessionLocal()
            try:
                # 构建详细信息（减少冗余数据）
                details = {}
                
                # 只记录重要的查询参数
                query_params = dict(request.query_params)
                important_query_keys = {'user_id', 'course_id', 'order_id', 'payment_id', 'page', 'size'}
                filtered_query_params = {k: v for k, v in query_params.items() if k in important_query_keys}
                if filtered_query_params:
                    details["query_params"] = filtered_query_params
                
                # 只记录路径参数（如果存在）
                if hasattr(request, 'path_params') and request.path_params:
                    details["path_params"] = dict(request.path_params)
                
                # 记录响应状态码（仅在非200状态时）
                if response and response.status_code != 200:
                    details["response_status"] = response.status_code
                
                print(f"Calling AuditService.log_from_request with user={user}")
                AuditService.log_from_request(
                    db=db,
                    request=request,
                    user=user,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    details=details,
                    status=status,
                    error_message=error_message,
                    start_time=start_time
                )
                print(f"AuditService.log_from_request completed successfully")
            finally:
                db.close()
        except Exception as e:
            print(f"Failed to log request: {str(e)}")


# 审计装饰器
def audit_action(
    action: str,
    resource_type: Optional[str] = None,
    get_resource_id: Optional[Callable] = None,
    get_resource_name: Optional[Callable] = None
):
    """审计操作装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里可以实现更精细的审计逻辑
            # 在实际使用中，可以根据需要扩展
            return await func(*args, **kwargs)
        return wrapper
    return decorator