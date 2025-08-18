"""
餐次管理相关的数据模型定义
定义了API请求和响应的Pydantic模型
"""

from pydantic import BaseModel
from datetime import date


class MealOption(BaseModel):
    """餐次可选配菜项定义"""

    id: str  # 选项唯一标识
    name: str  # 配菜名称，如"鸡腿"
    price_cents: int  # 配菜价格（分），可为负数表示折扣


class MealReq(BaseModel):
    """餐次创建/更新请求体"""

    date: date  # 餐次日期
    slot: str  # 时段：lunch/dinner
    title: str | None = None  # 餐次标题（可选）
    description: str | None = None  # 餐次描述
    base_price_cents: int  # 基础价格（分）
    options: list[MealOption] = []  # 可选配菜列表
    capacity: int  # 容量限制
    per_user_limit: int = 1  # 每人限购数量（当前固定为1）