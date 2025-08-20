from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """通用API响应格式"""
    success: bool = Field(description="请求是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    error_code: Optional[str] = Field(None, description="错误码")
    timestamp: Optional[str] = Field(None, description="响应时间戳")

class ErrorResponse(BaseModel):
    """错误响应格式"""
    success: bool = Field(False, description="请求失败")
    message: str = Field(description="错误消息")
    error_code: str = Field(description="错误码")
    timestamp: str = Field(description="错误时间戳")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "余额不足",
                "error_code": "INSUFFICIENT_BALANCE",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }

class PaginationInfo(BaseModel):
    """分页信息"""
    limit: int = Field(description="每页数量")
    offset: int = Field(description="偏移量")
    total_count: int = Field(description="总记录数")
    has_more: bool = Field(description="是否有更多数据")

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    items: List[T] = Field(description="数据列表")
    pagination: PaginationInfo = Field(description="分页信息")