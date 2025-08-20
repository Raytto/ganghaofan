"""
基础数据模型
定义通用的模型基类和常用字段
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any, Dict


class TimestampMixin(BaseModel):
    """时间戳混入类"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BaseEntity(BaseModel):
    """基础实体模型"""
    
    model_config = {"from_attributes": True, "use_enum_values": True}


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=10, ge=1, le=100, description="每页大小")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: list[Any]
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(cls, items: list, total: int, pagination: PaginationParams):
        """创建分页响应"""
        pages = (total + pagination.size - 1) // pagination.size
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages
        )


class ResponseWrapper(BaseModel):
    """统一响应包装器"""
    success: bool = True
    data: Any = None
    message: str = "操作成功"
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "操作成功"):
        """成功响应"""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_response(
        cls, 
        message: str, 
        error_code: str = None, 
        details: Dict[str, Any] = None
    ):
        """错误响应"""
        return cls(
            success=False,
            message=message,
            error_code=error_code,
            details=details
        )