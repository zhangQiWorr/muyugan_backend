"""
中间件模块
"""
import time
import uuid
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json
try:
    import orjson
except Exception:
    orjson = None

from services.logger import get_logger, EnhancedLogger

logger = get_logger("middleware")
api_logger = EnhancedLogger.get_api_logger()

class APILoggingMiddleware(BaseHTTPMiddleware):
    """API调用日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求和响应"""
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求信息
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # 获取请求体（如果是POST请求）
        request_body = None
        if method in ["POST", "PUT", "PATCH"] and request.headers.get("content-type", "").startswith("application/json"):
            try:
                # 读取请求体
                body = await request.body()
                if body:
                    if orjson:
                        request_body = orjson.loads(body)
                    else:
                        request_body = json.loads(body.decode())
                    # 隐藏敏感信息
                    if isinstance(request_body, dict):
                        sensitive_fields = ["password", "token", "api_key", "secret"]
                        for field in sensitive_fields:
                            if field in request_body:
                                request_body[field] = "***"
            except Exception as e:
                logger.warning(f"Failed to parse request body: {e}")
        
        # 记录请求开始
        api_logger.info(
            f"🚀 [REQ-{request_id}] {method} {url} | IP: {client_ip} | UA: {user_agent[:50]}..."
        )
        
        if request_body:
            try:
                serialized = orjson.dumps(request_body).decode() if orjson else json.dumps(request_body, ensure_ascii=False)
                if len(serialized) > 2000:
                    serialized = serialized[:2000] + "..."
                api_logger.debug(f"📋 [REQ-{request_id}] Request body: {serialized}")
            except Exception:
                pass
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应
            status_code = response.status_code
            status_emoji = "✅" if status_code < 400 else "⚠️" if status_code < 500 else "❌"
            
            api_logger.info(
                f"{status_emoji} [REQ-{request_id}] {method} {url} | "
                f"Status: {status_code} | Time: {process_time:.3f}s"
            )
            
            # 如果是错误响应，记录更多信息
            if status_code >= 400:
                try:
                    # 尝试读取响应体
                    response_body = b""
                    async for chunk in response.body_iterator:
                        response_body += chunk
                    
                    # 重新创建响应
                    response = Response(
                        content=response_body,
                        status_code=status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                    
                    # 记录错误响应
                    if response_body:
                        try:
                            error_data = orjson.loads(response_body) if orjson else json.loads(response_body.decode())
                            api_logger.error(f"❌ [REQ-{request_id}] Error response: {error_data}")
                        except:
                            api_logger.error(f"❌ [REQ-{request_id}] Error response: {response_body.decode()[:500]}")
                
                except Exception as e:
                    logger.warning(f"Failed to read error response: {e}")
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            api_logger.error(f"❌ [REQ-{request_id}] Exception: {str(e)} | Time: {process_time:.3f}s")
            
            # 返回错误响应
            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            error_response.headers["X-Request-ID"] = request_id
            error_response.headers["X-Process-Time"] = str(process_time)
            
            return error_response

class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求上下文"""
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        
        # 添加请求ID到请求状态
        request.state.request_id = request_id
        
        # 添加请求开始时间
        request.state.start_time = time.time()
        
        # 记录请求上下文
        logger.debug(f"📝 [REQ-{request_id}] Request context initialized")
        
        # 处理请求
        response = await call_next(request)
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理错误"""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 记录错误
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
            
            # 返回错误响应
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理安全相关"""
        # 添加安全头
        response = await call_next(request)
        
        # 安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response 