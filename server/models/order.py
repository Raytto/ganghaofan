"""
订单相关数据模型
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum
from .base import BaseEntity, TimestampMixin


class OrderStatus(str, Enum):
    """订单状态枚举"""
    ACTIVE = "active"       # 有效
    CANCELED = "canceled"   # 已取消


class LedgerType(str, Enum):
    """账本类型枚举"""
    RECHARGE = "recharge"   # 充值
    DEBIT = "debit"        # 扣费
    REFUND = "refund"      # 退款
    ADJUST = "adjust"      # 调整


class RefType(str, Enum):
    """关联类型枚举"""
    ORDER = "order"         # 订单
    MEAL = "meal"          # 餐次
    MANUAL = "manual"      # 手工


class OrderBase(BaseModel):
    """订单基础字段"""
    qty: int = Field(1, ge=1, description="数量")
    options: List[str] = Field(default_factory=list, description="选择的配菜选项ID列表")


class OrderCreate(OrderBase):
    """订单创建模型"""
    meal_id: int = Field(..., description="餐次ID")


class OrderUpdate(OrderBase):
    """订单更新模型"""
    pass


class Order(OrderBase, BaseEntity, TimestampMixin):
    """订单完整模型"""
    order_id: int = Field(..., description="订单ID")
    user_id: int = Field(..., description="用户ID")
    meal_id: int = Field(..., description="餐次ID")
    amount_cents: int = Field(..., description="订单总金额（分）")
    status: OrderStatus = Field(..., description="订单状态")
    locked_at: Optional[datetime] = Field(None, description="锁定时间")
    
    @property
    def amount_yuan(self) -> float:
        """订单金额（元）"""
        return self.amount_cents / 100
    
    @property
    def is_locked(self) -> bool:
        """是否已锁定"""
        return self.locked_at is not None


class OrderDetail(BaseModel):
    """订单详情（包含餐次信息）"""
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
    
    @property
    def amount_yuan(self) -> float:
        """订单金额（元）"""
        return self.amount_cents / 100


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: int = Field(..., description="订单ID")
    amount_cents: int = Field(..., description="订单金额（分）")
    balance_cents: int = Field(..., description="余额（分）")
    
    @property
    def amount_yuan(self) -> float:
        """订单金额（元）"""
        return self.amount_cents / 100
    
    @property
    def balance_yuan(self) -> float:
        """余额（元）"""
        return self.balance_cents / 100


class LedgerEntry(BaseEntity, TimestampMixin):
    """账本条目"""
    ledger_id: int = Field(..., description="账本ID")
    user_id: int = Field(..., description="用户ID")
    type: LedgerType = Field(..., description="类型")
    amount_cents: int = Field(..., description="金额（分）")
    ref_type: Optional[RefType] = Field(None, description="关联类型")
    ref_id: Optional[int] = Field(None, description="关联ID")
    remark: Optional[str] = Field(None, description="备注")
    
    @property
    def amount_yuan(self) -> float:
        """金额（元）"""
        return self.amount_cents / 100


class OrderExportItem(BaseModel):
    """订单导出项"""
    order_id: int = Field(..., description="订单ID")
    user_nickname: Optional[str] = Field(None, description="用户昵称")
    user_open_id: str = Field(..., description="用户OpenID")
    qty: int = Field(..., description="数量")
    selected_options: List[dict] = Field(..., description="选择的配菜详情")
    amount_cents: int = Field(..., description="订单金额（分）")
    created_at: datetime = Field(..., description="下单时间")
    
    @property
    def amount_yuan(self) -> float:
        """订单金额（元）"""
        return self.amount_cents / 100


class OrderExportSummary(BaseModel):
    """订单导出汇总"""
    meal_info: dict = Field(..., description="餐次信息")
    orders: List[OrderExportItem] = Field(..., description="订单列表")
    option_stats: dict = Field(..., description="配菜选项统计")
    total_orders: int = Field(..., description="总订单数")
    total_amount_cents: int = Field(..., description="总金额（分）")
    
    @property
    def total_amount_yuan(self) -> float:
        """总金额（元）"""
        return self.total_amount_cents / 100