"""
餐次相关数据模型
"""

from pydantic import BaseModel, Field, validator
from datetime import date
from typing import Optional, List
from enum import Enum
from .base import BaseEntity, TimestampMixin


class MealSlot(str, Enum):
    """餐次时段枚举"""
    LUNCH = "lunch"
    DINNER = "dinner"


class MealStatus(str, Enum):
    """餐次状态枚举"""
    PUBLISHED = "published"    # 已发布
    LOCKED = "locked"         # 已锁定
    COMPLETED = "completed"   # 已完成
    CANCELED = "canceled"     # 已取消


class MealOption(BaseModel):
    """餐次可选配菜项"""
    id: str = Field(..., description="选项唯一标识")
    name: str = Field(..., max_length=100, description="配菜名称")
    price_cents: int = Field(..., description="配菜价格（分），可为负数表示折扣")
    
    @property
    def price_yuan(self) -> float:
        """配菜价格（元）"""
        return self.price_cents / 100


class MealBase(BaseModel):
    """餐次基础字段"""
    date: date = Field(..., description="餐次日期")
    slot: MealSlot = Field(..., description="时段")
    title: Optional[str] = Field(None, max_length=200, description="餐次标题")
    description: Optional[str] = Field(None, max_length=1000, description="餐次描述")
    base_price_cents: int = Field(..., gt=0, description="基础价格（分）")
    capacity: int = Field(..., gt=0, description="容量限制")
    per_user_limit: int = Field(1, gt=0, description="每人限购数量")
    options: List[MealOption] = Field(default_factory=list, description="可选配菜列表")
    
    @property
    def base_price_yuan(self) -> float:
        """基础价格（元）"""
        return self.base_price_cents / 100
    
    @validator('options')
    def validate_options(cls, v):
        """验证配菜选项ID的唯一性"""
        if not v:
            return v
        
        ids = [option.id for option in v]
        if len(ids) != len(set(ids)):
            raise ValueError("配菜选项ID必须唯一")
        return v


class MealCreate(MealBase):
    """餐次创建模型"""
    pass


class MealUpdate(BaseModel):
    """餐次更新模型"""
    title: Optional[str] = Field(None, max_length=200, description="餐次标题")
    description: Optional[str] = Field(None, max_length=1000, description="餐次描述")
    base_price_cents: Optional[int] = Field(None, gt=0, description="基础价格（分）")
    capacity: Optional[int] = Field(None, gt=0, description="容量限制")
    options: Optional[List[MealOption]] = Field(None, description="可选配菜列表")
    
    @validator('options')
    def validate_options(cls, v):
        """验证配菜选项ID的唯一性"""
        if not v:
            return v
        
        ids = [option.id for option in v]
        if len(ids) != len(set(ids)):
            raise ValueError("配菜选项ID必须唯一")
        return v


class Meal(MealBase, BaseEntity, TimestampMixin):
    """餐次完整模型"""
    meal_id: int = Field(..., description="餐次ID")
    status: MealStatus = Field(..., description="餐次状态")
    created_by: Optional[int] = Field(None, description="创建者用户ID")
    ordered_qty: int = Field(0, description="已订数量")
    
    @property
    def available_qty(self) -> int:
        """可用数量"""
        return max(0, self.capacity - self.ordered_qty)
    
    @property
    def is_available(self) -> bool:
        """是否可订"""
        return self.status == MealStatus.PUBLISHED and self.available_qty > 0


class MealSummary(BaseModel):
    """餐次摘要（用于日历展示）"""
    meal_id: int = Field(..., description="餐次ID")
    date: date = Field(..., description="餐次日期")
    slot: MealSlot = Field(..., description="时段")
    title: Optional[str] = Field(None, description="餐次标题")
    base_price_cents: int = Field(..., description="基础价格（分）")
    capacity: int = Field(..., description="容量限制")
    status: MealStatus = Field(..., description="餐次状态")
    ordered_qty: int = Field(0, description="已订数量")
    my_ordered: bool = Field(False, description="当前用户是否已订")
    
    @property
    def base_price_yuan(self) -> float:
        """基础价格（元）"""
        return self.base_price_cents / 100
    
    @property
    def available_qty(self) -> int:
        """可用数量"""
        return max(0, self.capacity - self.ordered_qty)


class MealCalendarResponse(BaseModel):
    """餐次日历响应"""
    month: str = Field(..., description="月份 YYYY-MM")
    meals: List[MealSummary] = Field(..., description="餐次列表")


class MealBatchCalendarResponse(BaseModel):
    """批量餐次日历响应"""
    months: dict[str, List[MealSummary]] = Field(..., description="按月份分组的餐次列表")