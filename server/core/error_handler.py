"""
统一错误处理模块
提供标准化的错误响应格式和错误处理中间件

主要功能：
- 统一的错误响应格式
- 自动异常捕获和日志记录
- HTTP状态码映射
- 错误分类和处理策略
"""

import json
import traceback
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from .exceptions import BaseApplicationError
from .database import db_manager


class ErrorResponse:
    """标准错误响应格式"""
    
    def __init__(self, error_code: str, message: str, 
                 details: Optional[Dict[str, Any]] = None,
                 http_status: int = 400):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.http_status = http_status
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }
    
    def to_json_response(self) -> JSONResponse:
        """转换为FastAPI JSONResponse"""
        return JSONResponse(
            status_code=self.http_status,
            content=self.to_dict()
        )


class ErrorHandler:
    """全局错误处理器"""
    
    # 错误代码到HTTP状态码的映射
    ERROR_CODE_STATUS_MAP = {
        "VALIDATION_ERROR": 400,
        "AUTHENTICATION_REQUIRED": 401,
        "PERMISSION_DENIED": 403,
        "RESOURCE_NOT_FOUND": 404,
        "DUPLICATE_RESOURCE": 409,
        "BUSINESS_RULE_VIOLATION": 422,
        "INTERNAL_ERROR": 500,
        
        # 订单相关错误
        "ORDER_NOT_FOUND": 404,
        "MEAL_NOT_FOUND": 404,
        "MEAL_NOT_AVAILABLE": 400,
        "INVALID_QUANTITY": 400,
        "DUPLICATE_ORDER": 409,
        "CAPACITY_EXCEEDED": 409,
        "ORDER_NOT_ACTIVE": 400,
        "MEAL_LOCKED": 400,
        
        # 餐次相关错误
        "MEAL_DUPLICATE": 409,
        "MEAL_INVALID_STATUS": 400,
        "MEAL_STATUS_TRANSITION_INVALID": 400,
        
        # 用户相关错误
        "USER_NOT_FOUND": 404,
        "INSUFFICIENT_BALANCE": 400,
        "ADMIN_REQUIRED": 403,
    }
    
    @classmethod
    def handle_application_error(cls, error: BaseApplicationError) -> ErrorResponse:
        """处理应用业务异常"""
        http_status = cls.ERROR_CODE_STATUS_MAP.get(error.error_code, 400)
        
        return ErrorResponse(
            error_code=error.error_code,
            message=error.message,
            details=error.details,
            http_status=http_status
        )
    
    @classmethod
    def handle_http_exception(cls, error: HTTPException) -> ErrorResponse:
        """处理FastAPI HTTP异常"""
        return ErrorResponse(
            error_code="HTTP_ERROR",
            message=str(error.detail),
            details={"status_code": error.status_code},
            http_status=error.status_code
        )
    
    @classmethod
    def handle_validation_error(cls, error: Exception) -> ErrorResponse:
        """处理Pydantic验证错误"""
        return ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="请求参数验证失败",
            details={"validation_errors": str(error)},
            http_status=422
        )
    
    @classmethod
    def handle_unknown_error(cls, error: Exception) -> ErrorResponse:
        """处理未知异常"""
        error_msg = str(error) if str(error) else "系统内部错误"
        
        # 记录详细的错误信息用于调试
        error_details = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc()
        }
        
        # 记录到系统日志
        cls._log_system_error(error_details)
        
        return ErrorResponse(
            error_code="INTERNAL_ERROR",
            message=error_msg,
            details={"error_type": type(error).__name__},
            http_status=500
        )
    
    @classmethod
    def _log_system_error(cls, error_details: Dict[str, Any]):
        """记录系统错误到数据库"""
        try:
            con = db_manager.get_connection()
            con.execute(
                "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
                [None, None, "system_error", json.dumps(error_details)]
            )
        except Exception:
            # 如果连数据库日志都写不了，就只能打印到控制台
            print(f"Failed to log error to database: {error_details}")


async def application_error_handler(request: Request, exc: BaseApplicationError) -> JSONResponse:
    """应用异常处理中间件"""
    error_response = ErrorHandler.handle_application_error(exc)
    return error_response.to_json_response()


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理中间件"""
    error_response = ErrorHandler.handle_http_exception(exc)
    return error_response.to_json_response()


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """验证异常处理中间件"""
    error_response = ErrorHandler.handle_validation_error(exc)
    return error_response.to_json_response()


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理中间件"""
    error_response = ErrorHandler.handle_unknown_error(exc)
    return error_response.to_json_response()


def create_success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建标准成功响应"""
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    return response


def create_paginated_response(items: list, total: int, page: int, 
                             page_size: int, message: str = "查询成功") -> Dict[str, Any]:
    """创建分页响应"""
    return {
        "success": True,
        "message": message,
        "data": {
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    }