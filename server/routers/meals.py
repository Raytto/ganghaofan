"""
餐次管理路由模块
提供餐次的创建、查询、修改、锁定、取消等核心业务接口
主要服务于前端日历页面和管理员操作

核心功能：
- 单月和批量月份的餐次日历查询
- 餐次详情查询（包含用户订餐状态）
- 管理员餐次发布和编辑
- 餐次状态管理（锁定、完成、取消）
- 危险修改的取消重发机制

业务规则：
- 每个日期+时段组合只能有一个餐次
- 餐次状态流转：published -> locked -> completed
- 取消操作会自动退款所有有效订单
"""

from fastapi import APIRouter, Depends, Query
from ..utils.security import get_open_id
from .meals_utils import (
    MealOption,
    MealReq,
    get_calendar_data,
    get_calendar_batch_data,
    get_meal_detail,
    create_meal_logic,
    update_meal_patch_logic,
    lock_meal_logic,
    unlock_meal_logic,
    complete_meal_logic,
    cancel_meal_logic,
    repost_meal_logic,
)

router = APIRouter()


@router.get("/calendar")
def get_calendar(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    open_id: str = Depends(get_open_id),
):
    """
    获取指定月份的餐次日历数据

    Args:
        month: 月份字符串，格式为 YYYY-MM
        open_id: 用户微信openid，通过JWT认证获取

    Returns:
        dict: 包含month和meals列表的字典
        meals中每项包含餐次基本信息和用户订餐状态

    Note:
        自动计算当前用户在每个餐次的订餐状态(my_ordered)
        如用户不存在则my_ordered为False
    """
    return get_calendar_data(month, open_id)


@router.get("/calendar/batch")
def get_calendar_batch(
    months: str,  # comma-separated YYYY-MM list
    open_id: str = Depends(get_open_id),
):
    """
    批量获取多个月份的餐次日历数据
    主要用于首页9周窗口的数据预加载，减少网络请求次数

    Args:
        months: 逗号分隔的月份列表，格式 "YYYY-MM,YYYY-MM,YYYY-MM"
        open_id: 用户微信openid，用于计算用户订餐状态

    Returns:
        dict: 包含 months 字段的字典，key为月份，value为该月餐次列表

    Raises:
        HTTPException: 当月份格式错误时返回 400

    Note:
        严格校验月份格式，必须为 YYYY-MM 格式
        自动计算用户在每个餐次的订餐状态(my_ordered)
        使用IN查询提升批量查询性能
    """
    return get_calendar_batch_data(months, open_id)


@router.get("/meals/{meal_id}")
def get_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    """
    获取单个餐次的详细信息
    用于下单页面和餐次详情查看

    Args:
        meal_id: 餐次ID
        open_id: 用户微信openid

    Returns:
        dict: 餐次完整信息，包含用户订餐状态

    Raises:
        HTTPException: 餐次不存在时返回 404
    """
    return get_meal_detail(meal_id, open_id)


@router.post("/meals")
def create_meal(body: MealReq, open_id: str = Depends(get_open_id)):
    """
    创建新餐次（管理员功能）

    Args:
        body: 餐次创建请求体，包含日期、时段、价格、配菜选项等
        open_id: 管理员的微信openid

    Returns:
        dict: 包含新创建餐次ID的字典

    Raises:
        HTTPException:
            400 - 时段参数错误
            409 - 该日期+时段已存在餐次或数据无效

    Note:
        餐次创建后状态自动设为 'published'
        date+slot组合必须唯一（数据库约束）
        配菜选项序列化为JSON存储
    """
    return create_meal_logic(body, open_id)


@router.patch("/meals/{meal_id}")
def update_meal_patch(meal_id: int, body: MealReq, open_id: str = Depends(get_open_id)):
    """
    直接修改餐次信息（安全修改）
    仅适用于不影响已有订单的修改操作

    Args:
        meal_id: 要修改的餐次ID
        body: 修改后的餐次信息
        open_id: 管理员openid

    Returns:
        dict: 包含餐次ID的确认信息

    Note:
        只能修改状态为 'published' 的餐次
        此操作不会影响已有订单，适用于描述更新、容量增加等安全修改
        危险修改（如价格变动、容量减少）应使用 repost 接口
    """
    return update_meal_patch_logic(meal_id, body, open_id)


@router.put("/meals/{meal_id}")
def update_meal_put(meal_id: int, body: MealReq, open_id: str = Depends(get_open_id)):
    return update_meal_patch(meal_id, body, open_id)


@router.post("/meals/{meal_id}/lock")
def lock_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    """
    锁定餐次（管理员功能）
    锁定后用户无法下单或修改订单，管理员也无法修改餐次信息

    Args:
        meal_id: 要锁定的餐次ID
        open_id: 管理员openid

    Returns:
        dict: 包含餐次ID和新状态的确认信息

    Raises:
        HTTPException: 餐次不存在或不在可锁定状态时返回 400

    Note:
        使用事务确保餐次状态和订单锁定时间的一致性
        只有 'published' 状态的餐次可以被锁定
        锁定时同时记录所有活跃订单的锁定时间戳
    """
    return lock_meal_logic(meal_id, open_id)


@router.post("/meals/{meal_id}/unlock")
def unlock_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    """
    取消锁定餐次（管理员功能）
    将状态从 locked 恢复为 published，并允许订单再次修改。
    """
    return unlock_meal_logic(meal_id, open_id)


@router.post("/meals/{meal_id}/complete")
def complete_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    """
    标记餐次为已完成（管理员功能）
    表示该餐次的配送或服务已完成

    Args:
        meal_id: 要完成的餐次ID
        open_id: 管理员openid

    Returns:
        dict: 包含餐次ID和新状态的确认信息

    Note:
        只有 'locked' 状态的餐次可以标记为完成
        完成后的餐次无法再修改状态
    """
    return complete_meal_logic(meal_id, open_id)


@router.post("/meals/{meal_id}/cancel")
def cancel_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    """
    取消餐次并退款所有订单（管理员功能）
    用于餐次无法正常提供时的紧急处理

    Args:
        meal_id: 要取消的餐次ID
        open_id: 管理员openid

    Returns:
        dict: 包含餐次ID和新状态的确认信息

    Raises:
        HTTPException: 餐次不在可取消状态时返回 400

    Note:
        使用事务确保餐次取消和所有订单退款的原子性
        自动处理余额退款和账单记录
        只有 'published' 或 'locked' 状态的餐次可以被取消
    """
    return cancel_meal_logic(meal_id, open_id)


@router.post("/meals/{meal_id}/repost")
def repost_meal(meal_id: int, body: MealReq, open_id: str = Depends(get_open_id)):
    """
    危险修改：取消并重新发布餐次
    用于价格调整、容量大幅减少等会影响已有订单的修改

    Args:
        meal_id: 要重新发布的餐次ID
        body: 新的餐次信息
        open_id: 管理员openid

    Returns:
        dict: 包含餐次ID和状态的确认信息

    Raises:
        HTTPException: 餐次不在可修改状态时返回 400

    Note:
        保持相同的meal_id，但更新所有餐次信息
        自动取消并退款所有现有订单
        适用于价格变动、配菜选项删除、容量大幅减少等场景
        重发后餐次状态保持为 'published'，用户可重新下单
    """
    return repost_meal_logic(meal_id, body, open_id)
