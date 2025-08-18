"""
餐次管理工具模块
提供餐次相关业务逻辑的模块化实现

主要子模块：
- models: Pydantic数据模型定义
- helpers: 通用辅助函数
- queries: 查询相关业务逻辑
- management: 管理操作相关业务逻辑
"""

from .models import MealOption, MealReq
from .helpers import (
    parse_meal_options,
    check_user_ordered_status,
    get_user_id_from_openid,
    ensure_user_exists,
    log_meal_action,
)
from .queries import (
    get_calendar_data,
    get_calendar_batch_data,
    get_meal_detail,
)
from .management import (
    create_meal_logic,
    update_meal_patch_logic,
    lock_meal_logic,
    unlock_meal_logic,
    complete_meal_logic,
    cancel_meal_logic,
    repost_meal_logic,
)

__all__ = [
    # Models
    "MealOption",
    "MealReq", 
    # Helpers
    "parse_meal_options",
    "check_user_ordered_status",
    "get_user_id_from_openid",
    "ensure_user_exists",
    "log_meal_action",
    # Queries
    "get_calendar_data",
    "get_calendar_batch_data",
    "get_meal_detail",
    # Management
    "create_meal_logic",
    "update_meal_patch_logic",
    "lock_meal_logic",
    "unlock_meal_logic", 
    "complete_meal_logic",
    "cancel_meal_logic",
    "repost_meal_logic",
]