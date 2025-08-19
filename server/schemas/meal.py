"""
餐次相关的请求/响应模式
"""

from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional
from ..models.meal import MealOption, MealSlot, MealStatus


class MealOptionSchema(BaseModel):
    """餐次配菜选项模式"""
    id: str = Field(..., description="选项ID")
    name: str = Field(..., description="配菜名称")
    price_cents: int = Field(..., description="价格（分）")


class MealCreateRequest(BaseModel):
    """餐次创建请求"""
    date: date = Field(..., description="餐次日期")
    slot: MealSlot = Field(..., description="时段")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    base_price_cents: int = Field(..., gt=0, description="基础价格（分）")
    options: List[MealOptionSchema] = Field(default_factory=list, description="配菜选项")
    capacity: int = Field(..., gt=0, description="容量")
    per_user_limit: int = Field(1, description="每人限购")


class MealUpdateRequest(BaseModel):
    """餐次更新请求"""
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    base_price_cents: Optional[int] = Field(None, gt=0, description="基础价格（分）")
    options: Optional[List[MealOptionSchema]] = Field(None, description="配菜选项")
    capacity: Optional[int] = Field(None, gt=0, description="容量")


class MealResponse(BaseModel):
    """餐次响应"""
    meal_id: int = Field(..., description="餐次ID")
    date: date = Field(..., description="日期")
    slot: MealSlot = Field(..., description="时段")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="描述")
    base_price_cents: int = Field(..., description="基础价格（分）")
    options: List[MealOptionSchema] = Field(..., description="配菜选项")
    capacity: int = Field(..., description="容量")
    per_user_limit: int = Field(..., description="每人限购")
    status: MealStatus = Field(..., description="状态")
    ordered_qty: int = Field(..., description="已订数量")
    my_ordered: bool = Field(..., description="我是否已订")


class MealCalendarRequest(BaseModel):
    """餐次日历请求"""
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="月份 YYYY-MM")


class MealBatchCalendarRequest(BaseModel):
    """批量餐次日历请求"""
    months: str = Field(..., description="逗号分隔的月份列表")


class MealOperationResponse(BaseModel):
    """餐次操作响应"""
    meal_id: int = Field(..., description="餐次ID")
    status: MealStatus = Field(..., description="新状态")
    message: str = Field(..., description="操作结果消息")