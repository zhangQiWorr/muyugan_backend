"""
增强日志模块 - 支持结构化日志、性能监控、错误追踪
"""
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any, Dict, Optional, Union
from contextlib import contextmanager

class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础信息
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage()
        }
        
        # 添加异常信息
        if record.exc_info:
            exc_type = record.exc_info[0]
            log_data["exception"] = {
                "type": getattr(exc_type, '__name__', str(exc_type)) if exc_type else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # 添加额外字段
        extra_fields = getattr(record, 'extra_fields', None)
        if extra_fields:
            log_data.update(extra_fields)
        
        # 添加性能指标
        performance_data = getattr(record, 'performance', None)
        if performance_data:
            log_data['performance'] = performance_data
        
        return json.dumps(log_data, ensure_ascii=False, default=str)

class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = time.time()
        self.start_memory = self._get_memory_usage()
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量（MB）"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def finish(self, success: bool = True, extra_info: Optional[Dict[str, Any]] = None):
        """完成性能记录"""
        duration = time.time() - self.start_time
        end_memory = self._get_memory_usage()
        memory_diff = end_memory - self.start_memory
        
        performance_data = {
            'operation': self.operation,
            'duration_ms': round(duration * 1000, 2),
            'memory_start_mb': round(self.start_memory, 2),
            'memory_end_mb': round(end_memory, 2),
            'memory_diff_mb': round(memory_diff, 2),
            'success': success
        }
        
        if extra_info:
            performance_data.update(extra_info)
        
        # 根据性能选择日志级别
        if duration > 1.0:  # 超过1秒
            level = logging.WARNING
        elif duration > 0.5:  # 超过500ms
            level = logging.INFO
        else:
            level = logging.DEBUG
        
        self.logger.log(level, f"Performance: {self.operation}", 
                       extra={'performance': performance_data})

@contextmanager
def performance_logger(logger: logging.Logger, operation: str):
    """性能日志上下文管理器"""
    perf_logger = PerformanceLogger(logger, operation)
    try:
        yield perf_logger
        perf_logger.finish(success=True)
    except Exception as e:
        perf_logger.finish(success=False, extra_info={'error': str(e)})
        raise

class EnhancedLogger:
    """增强日志管理器"""
    
    _instance = None
    _loggers = {}
    _handlers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._setup_logging()
        return cls._instance
    
    @classmethod
    def _setup_logging(cls):
        """设置日志系统"""
        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置根日志级别
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 创建格式化器
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s'
        )
        
        structured_formatter = StructuredFormatter()
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._get_log_level_from_env("CONSOLE_LOG_LEVEL", "INFO"))
        console_handler.setFormatter(console_formatter)
        cls._handlers['console'] = console_handler
        
        # 应用日志文件处理器
        app_handler = RotatingFileHandler(
            f"{log_dir}/muyugan_app.log",
            maxBytes=100*1024*1024,  # 100MB
            backupCount=10,
            encoding='utf-8'
        )
        app_handler.setLevel(cls._get_log_level_from_env("FILE_LOG_LEVEL", "DEBUG"))
        app_handler.setFormatter(structured_formatter)
        cls._handlers['app'] = app_handler
        
        # 错误日志文件处理器
        error_handler = RotatingFileHandler(
            f"{log_dir}/muyugan_errors.log",
            maxBytes=50*1024*1024,  # 50MB
            backupCount=20,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(structured_formatter)
        cls._handlers['error'] = error_handler
        
        # 性能日志文件处理器
        perf_handler = TimedRotatingFileHandler(
            f"{log_dir}/muyugan_performance.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(structured_formatter)
        cls._handlers['performance'] = perf_handler
        
        # API访问日志文件处理器
        api_handler = TimedRotatingFileHandler(
            f"{log_dir}/muyugan_api.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        api_handler.setLevel(logging.INFO)
        api_handler.setFormatter(structured_formatter)
        cls._handlers['api'] = api_handler
    
    @classmethod
    def _get_log_level_from_env(cls, env_var: str, default_level: str = "INFO") -> int:
        """从环境变量获取日志级别"""
        level_str = os.getenv(env_var, default_level).upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_str, logging.INFO)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        # 确保日志系统已初始化
        if not cls._handlers:
            cls._setup_logging()
            
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            
            # 避免重复添加处理器
            if not logger.handlers:
                # 添加所有处理器
                for handler in cls._handlers.values():
                    logger.addHandler(handler)
                
                # 设置传播
                logger.propagate = False
            
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def get_app_logger(cls) -> logging.Logger:
        """获取应用主日志器"""
        return cls.get_logger("muyugan.app")
    
    @classmethod
    def get_api_logger(cls) -> logging.Logger:
        """获取API日志器"""
        return cls.get_logger("muyugan.api")
    
    @classmethod
    def get_db_logger(cls) -> logging.Logger:
        """获取数据库日志器"""
        return cls.get_logger("muyugan.database")
    
    @classmethod
    def get_auth_logger(cls) -> logging.Logger:
        """获取认证日志器"""
        return cls.get_logger("muyugan.auth")
    
    @classmethod
    def get_performance_logger(cls) -> logging.Logger:
        """获取性能日志器"""
        return cls.get_logger("muyugan.performance")
    
    @classmethod
    def log_request(cls, request_info: Dict[str, Any]):
        """记录API请求"""
        logger = cls.get_api_logger()
        logger.info("API Request", extra={'extra_fields': request_info})
    
    @classmethod
    def log_response(cls, response_info: Dict[str, Any]):
        """记录API响应"""
        logger = cls.get_api_logger()
        logger.info("API Response", extra={'extra_fields': response_info})
    
    @classmethod
    def log_error(cls, error: Exception, context: Optional[Dict[str, Any]] = None):
        """记录错误信息"""
        logger = cls.get_app_logger()
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        if context:
            error_info.update(context)
        
        logger.error("Application Error", extra={'extra_fields': error_info})

# 兼容性函数
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志器（兼容旧版本）"""
    if name is None:
        name = "muyugan.app"
    return EnhancedLogger.get_logger(name)

def get_api_logger() -> logging.Logger:
    """获取API日志器（兼容旧版本）"""
    return EnhancedLogger.get_api_logger()

# 性能日志装饰器
def log_performance(operation: str):
    """性能日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(f"muyugan.performance.{func.__module__}")
            with performance_logger(logger, operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator