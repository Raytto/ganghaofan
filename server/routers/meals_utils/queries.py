"""
餐次查询相关的业务逻辑
提供日历查询、餐次详情等查询功能
"""

from typing import Dict, List, Any, Optional
from fastapi import HTTPException
from ...db import get_conn
from .helpers import (
    parse_meal_options,
    check_user_ordered_status,
    get_user_id_from_openid,
)


def get_calendar_data(month: str, open_id: str) -> dict:
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
    con = get_conn()
    # 尝试获取用户ID，可能不存在（新用户首次访问）
    uid = get_user_id_from_openid(open_id)

    # 查询指定月份的所有餐次，同时计算已订数量
    meals = con.execute(
        """
        SELECT meal_id, date, slot, title, base_price_cents, options_json, capacity, per_user_limit, status,
               (SELECT COALESCE(SUM(qty),0) FROM orders o WHERE o.meal_id = m.meal_id AND o.status='active') AS ordered_qty
        FROM meals m
        WHERE strftime(date, '%Y-%m') = ?
        ORDER BY date, slot
        """,
        [month],
    ).fetchall()

    data = []
    for r in meals:
        # 解析JSON格式的配菜选项
        opts = parse_meal_options(r[5])
        
        # 计算当前用户的订餐状态
        my_ordered = check_user_ordered_status(uid, r[0])

        data.append({
            "meal_id": r[0],
            "date": str(r[1]),
            "slot": r[2],
            "title": r[3],
            "base_price_cents": r[4],
            "options": opts,
            "capacity": r[6],
            "per_user_limit": r[7],
            "status": r[8],
            "ordered_qty": r[9],
            "my_ordered": my_ordered,
        })
    return {"month": month, "meals": data}


def get_calendar_batch_data(months: str, open_id: str) -> dict:
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
    # 验证并标准化月份参数
    parts = [m.strip() for m in months.split(",") if m.strip()]
    if not parts:
        raise HTTPException(400, "months required")
    for m in parts:
        if len(m) != 7 or m[4] != "-" or not (m[:4].isdigit() and m[5:].isdigit()):
            raise HTTPException(400, f"invalid month: {m}")

    con = get_conn()
    # 动态构建IN子句的占位符，避免SQL注入
    placeholders = ",".join(["?"] * len(parts))
    rows = con.execute(
        f"""
        SELECT strftime(date, '%Y-%m') AS ym,
               meal_id, date, slot, title, base_price_cents, options_json, capacity, per_user_limit, status,
               (SELECT COALESCE(SUM(qty),0) FROM orders o WHERE o.meal_id = m.meal_id AND o.status='active') AS ordered_qty
        FROM meals m
        WHERE strftime(date, '%Y-%m') IN ({placeholders})
        ORDER BY date, slot
        """,
        parts,
    ).fetchall()

    # 获取当前用户ID（如果存在）
    uid = get_user_id_from_openid(open_id)

    # 按月份组织返回数据
    result: dict[str, list[dict]] = {m: [] for m in parts}
    for r in rows:
        ym = r[0]  # 年月字符串

        # 解析配菜选项JSON
        opts = parse_meal_options(r[6])
        
        # 计算用户订餐状态
        my_ordered = check_user_ordered_status(uid, r[1])

        result.setdefault(ym, []).append({
            "meal_id": r[1],
            "date": str(r[2]),
            "slot": r[3],
            "title": r[4],
            "base_price_cents": r[5],
            "options": opts,
            "capacity": r[7],
            "per_user_limit": r[8],
            "status": r[9],
            "ordered_qty": r[10],
            "my_ordered": my_ordered,
        })
    return {"months": result}


def get_meal_detail(meal_id: int, open_id: str) -> dict:
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
    con = get_conn()
    r = con.execute(
        """
        SELECT meal_id, date, slot, title, description, base_price_cents, options_json, capacity, per_user_limit, status,
               (SELECT COALESCE(SUM(qty),0) FROM orders o WHERE o.meal_id = m.meal_id AND o.status='active') AS ordered_qty
        FROM meals m WHERE meal_id=?
        """,
        [meal_id],
    ).fetchone()
    if not r:
        raise HTTPException(404, "meal not found")

    # 解析配菜选项
    opts = parse_meal_options(r[6])
    
    # 计算当前用户的订餐状态
    uid = get_user_id_from_openid(open_id)
    my_ordered = check_user_ordered_status(uid, meal_id)

    return {
        "meal_id": r[0],
        "date": str(r[1]),
        "slot": r[2],
        "title": r[3],
        "description": r[4],
        "base_price_cents": r[5],
        "options": opts,
        "capacity": r[7],
        "per_user_limit": r[8],
        "status": r[9],
        "ordered_qty": r[10],
        "my_ordered": my_ordered,
    }