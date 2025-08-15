"""审计日志中间件"""
import time
import json
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
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
            "/static"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否需要跳过记录
        if self._should_skip_logging(request):
            return await call_next(request)
        
        start_time = time.time()
        
        # 获取用户信息
        user = await self._get_user_from_request(request)
        
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
    
    def _should_skip_logging(self, request: Request) -> bool:
        """判断是否应该跳过日志记录"""
        path = request.url.path
        
        # 跳过静态文件和文档路径
        for skip_path in self.skip_paths:
            if path.startswith(skip_path):
                return True
        
        # 跳过健康检查
        if path == "/" and request.method == "GET":
            return True
            
        return False
    
    async def _get_user_from_request(self, request: Request) -> Optional[User]:
        """从请求中获取用户信息"""
        try:
            # 从Authorization头获取token
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            jwt_handler = JWTHandler()
            payload = jwt_handler.verify_token(token)
            
            if not payload:
                return None
            
            user_id = payload.get("user_id")
            if not user_id:
                return None
            
            # 从数据库获取用户信息
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                return user
            finally:
                db.close()
                
        except Exception as e:
            print(f"Failed to get user from request: {str(e)}")
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
        try:
            db = SessionLocal()
            try:
                # 构建详细信息
                details = {
                    "query_params": dict(request.query_params),
                    "path_params": dict(request.path_params) if hasattr(request, 'path_params') else {},
                }
                
                # 如果是POST/PUT请求，尝试记录请求体（敏感信息除外）
                if request.method in ["POST", "PUT", "PATCH"]:
                    try:
                        # 注意：这里不能直接读取request.body()，因为它已经被消费了
                        # 在实际应用中，可能需要在更早的阶段捕获请求体
                        pass
                    except:
                        pass
                
                # 记录响应状态码
                if response:
                    details["response_status"] = response.status_code
                
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