"""审计日志中间件"""
import time
import json
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from models.database import SessionLocal
from models.user import User
from services.audit_service import AuditService
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
            "/api/superadmin/permissions",  # 排除权限查询接口
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

        if method == "HEADS" or method == "OPTIONS":
            return True

        # 登录操作始终记录，即使是超级管理员
        if path == "/auth/login" and method == "POST":
            return False
        # 登出操作始终记录，即使是超级管理员
        if path == "/auth/logout" and method == "POST":
            return False
            
        # 跳过超级管理员的其他操作
        if user and str(user.role) == 'superadmin' and method == "GET" :
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
            # 登录请求不使用token获取用户，改为从请求体的用户名解析
            if request.url.path.endswith("/login") and request.method.upper() == "POST":
                username = await self._get_username_from_request_body(request)
                print(f"Username from request body: {username}")

                if username:
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.username == username).first()
                        if user:
                            return user
                        user = db.query(User).filter(User.email == username).first()
                        if user:
                            return user
                        user = db.query(User).filter(User.phone == username).first()
                        if user:
                            return user
                    finally:
                        db.close()

            # 从多种位置尝试提取token
            token = self._extract_token(request)
            if token:
                # 验证token并获取用户ID
                payload = JWTHandler().verify_token(token)
                if payload:
                    # JWT token中使用'sub'字段存储用户ID
                    user_id = payload.get("sub") or payload.get("user_id")
                    if user_id:
                        print(f"User ID from token: {user_id}")
                        # 从数据库获取用户信息
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.id == user_id).first()
                            if user:
                                return user
                        finally:
                            db.close()
                
        except Exception as e:
            pass
            
        return None
    


    async def _get_username_from_request_body(self, request: Request) -> Optional[str]:
        """安全地读取请求体并从中提取用户名（不消耗请求体）"""
        try:
            # 读取原始body
            body_bytes = await request.body()
            if not body_bytes:
                return None

            # 解析JSON
            try:
                body_json = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body_json = None

            # 重置request使下游还能读取body
            async def receive() -> Dict[str, Any]:
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            # Starlette 使用 _receive 作为内部接收器
            setattr(request, "_receive", receive)

            if not isinstance(body_json, dict):
                return None

            # 支持 username 优先，其次 login 字段
            username = body_json.get("username") or body_json.get("login")

            if isinstance(username, str) and username.strip():
                return username.strip()
            return None
        except Exception:
            return None

    def _extract_token(self, request: Request) -> Optional[str]:
        """从请求中尽可能提取访问令牌"""
        # 1) Authorization 头
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
            # 如果没有Bearer前缀，尝试当作原始token使用
            if len(parts) == 1 and parts[0]:
                return parts[0].strip()

        # 2) 自定义头
        x_token = request.headers.get("X-Access-Token") or request.headers.get("x-access-token")
        if x_token and x_token.strip():
            return x_token.strip()

        # 3) 查询参数
        token_q = request.query_params.get("access_token") or request.query_params.get("token")
        if token_q and token_q.strip():
            return token_q.strip()

        # 4) Cookies
        cookie_auth = request.cookies.get("Authorization") or request.cookies.get("authorization")
        if cookie_auth:
            parts = cookie_auth.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
            if len(parts) == 1 and parts[0]:
                return parts[0].strip()
        cookie_token = request.cookies.get("access_token") or request.cookies.get("token")
        if cookie_token and cookie_token.strip():
            return cookie_token.strip()

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
        elif method == "get" or method == "head" or method == "options" :
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
                
                # 确保日志中有明确的用户名



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
                    start_time=start_time,
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