"""
订单相关的请求/响应模式
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from ..models.order import OrderStatus


class OrderCreateRequest(BaseModel):
    """订单创建请求"""
    meal_id: int = Field(..., description="餐次ID")
    qty: int = Field(1, ge=1, le=10, description="数量")
    options: List[str] = Field(default_factory=list, description="选择的配菜选项ID")


class OrderUpdateRequest(BaseModel):
    """订单更新请求"""
    qty: int = Field(1, ge=1, le=10, description="数量")
    options: List[str] = Field(default_factory=list, description="选择的配菜选项ID")


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: int = Field(..., description="订单ID")
    amount_cents: int = Field(..., description="订单金额（分）")
    balance_cents: int = Field(..., description="用户余额（分）")


class OrderDetailResponse(BaseModel):
    """订单详情响应"""
    order_id: int = Field(..., description="订单ID")
    meal_id: int = Field(..., description="餐次ID")
    meal_date: str = Field(..., description="餐次日期")
    meal_slot: str = Field(..., description="餐次时段")
    meal_title: Optional[str] = Field(None, description="餐次标题")
    qty: int = Field(..., description="数量")
    options: List[str] = Field(..., description="选择的配菜选项")
    amount_cents: int = Field(..., description="订单金额（分）")
    status: OrderStatus = Field(..., description="订单状态")
    created_at: datetime = Field(..., description="创建时间")


class OrderCancelResponse(BaseModel):
    """订单取消响应"""
    order_id: int = Field(..., description="订单ID")
    balance_cents: int = Field(..., description="退款后余额（分）")
    status: OrderStatus = Field(..., description="订单状态")


class OrderListRequest(BaseModel):
    """订单列表请求"""
    meal_id: Optional[int] = Field(None, description="餐次ID过滤")
    status: Optional[OrderStatus] = Field(None, description="状态过滤")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=100, description="每页大小")