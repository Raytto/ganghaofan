"""
餐次管理操作的业务逻辑
提供餐次创建、修改、状态管理等核心功能
"""

import json
from typing import Dict, Any
from fastapi import HTTPException
from ...db import get_conn
from .models import MealReq
from .helpers import (
    get_user_id_from_openid,
    ensure_user_exists,
    log_meal_action,
    get_meal_basic_info,
    parse_meal_options,
    build_option_mapping,
    parse_selected_options,
)


def create_meal_logic(body: MealReq, open_id: str) -> dict:
    """
    创建新餐次的业务逻辑（管理员功能）
    
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
    con = get_conn()
    if body.slot not in ("lunch", "dinner"):
        raise HTTPException(400, "slot must be lunch or dinner")

    # 如果已存在被取消的餐次，允许直接覆盖以便重新发布
    existing = con.execute(
        "SELECT meal_id, status FROM meals WHERE date=? AND slot=?",
        [body.date, body.slot],
    ).fetchone()
    if existing:
        if existing[1] == "canceled":
            con.execute(
                "UPDATE meals SET title=?, description=?, base_price_cents=?, options_json=?, capacity=?, per_user_limit=?, status='published', updated_at=now() WHERE meal_id=?",
                [
                    body.title,
                    body.description,
                    body.base_price_cents,
                    json.dumps([o.model_dump() for o in body.options]),
                    body.capacity,
                    body.per_user_limit,
                    existing[0],
                ],
            )
            meal = (existing[0],)
        else:
            # 其它状态不允许覆盖
            raise HTTPException(409, "meal exists for date+slot")
    else:
        # 正常创建
        # resolve actor id for created_by
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        created_by = urow[0] if urow else None
        try:
            con.execute(
                "INSERT INTO meals(date, slot, title, description, base_price_cents, options_json, capacity, per_user_limit, status, created_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [
                    body.date,
                    body.slot,
                    body.title,
                    body.description,
                    body.base_price_cents,
                    json.dumps([o.model_dump() for o in body.options]),
                    body.capacity,
                    body.per_user_limit,
                    "published",
                    created_by,
                ],
            )
        except Exception as e:
            # 唯一索引冲突或其他数据约束错误
            raise HTTPException(409, "meal exists for date+slot or invalid data")
        meal = con.execute(
            "SELECT meal_id FROM meals WHERE date=? AND slot= ?", [body.date, body.slot]
        ).fetchone()
    
    # 确保用户存在并记录日志
    actor_id = ensure_user_exists(open_id)
    log_meal_action(
        "meal_publish",
        actor_id,
        {
            "meal_id": meal[0],
            "date": str(body.date),
            "slot": body.slot,
            "title": body.title,
            "description": body.description,
            "base_price_cents": body.base_price_cents,
            "options": [o.model_dump() for o in body.options],
            "capacity": body.capacity,
            "per_user_limit": body.per_user_limit,
        }
    )
    return {"meal_id": meal[0]}


def update_meal_patch_logic(meal_id: int, body: MealReq, open_id: str) -> dict:
    """
    直接修改餐次信息的业务逻辑（安全修改）
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
    con = get_conn()
    con.execute(
        "UPDATE meals SET title=?, description=?, base_price_cents=?, options_json=?, capacity=?, per_user_limit=?, updated_at=now() WHERE meal_id=? AND status='published'",
        [
            body.title,
            body.description,
            body.base_price_cents,
            json.dumps([o.model_dump() for o in body.options]),
            body.capacity,
            body.per_user_limit,
            meal_id,
        ],
    )
    
    # 确保用户存在并记录日志
    actor_id = ensure_user_exists(open_id)
    log_meal_action(
        "meal_edit",
        actor_id,
        {
            "meal_id": meal_id,
            "edited": True,
            "date": str(body.date),
            "slot": body.slot,
            "title": body.title,
            "description": body.description,
            "base_price_cents": body.base_price_cents,
            "options": [o.model_dump() for o in body.options],
            "capacity": body.capacity,
            "per_user_limit": body.per_user_limit,
        }
    )
    return {"meal_id": meal_id}


def lock_meal_logic(meal_id: int, open_id: str) -> dict:
    """
    锁定餐次的业务逻辑（管理员功能）
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
    con = get_conn()
    con.execute("BEGIN")
    try:
        # 检查餐次当前状态
        st = con.execute(
            "SELECT status FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        if not st or st[0] != "published":
            con.execute("ROLLBACK")
            raise HTTPException(400, "meal not in published state")

        # 更新餐次状态为锁定
        con.execute(
            "UPDATE meals SET status='locked', updated_at=now() WHERE meal_id=?",
            [meal_id],
        )

        # 为所有活跃订单记录锁定时间，防止后续修改
        con.execute(
            "UPDATE orders SET locked_at=now() WHERE meal_id=? AND status='active'",
            [meal_id],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    
    # 记录日志
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    actor_id = urow[0] if urow else None
    m = con.execute(
        "SELECT date, slot, title FROM meals WHERE meal_id=?",
        [meal_id],
    ).fetchone()
    log_meal_action(
        "meal_lock",
        actor_id,
        {
            "meal_id": meal_id,
            "date": str(m[0]) if m else None,
            "slot": m[1] if m else None,
            "title": m[2] if m else None,
        }
    )
    return {"meal_id": meal_id, "status": "locked"}


def unlock_meal_logic(meal_id: int, open_id: str) -> dict:
    """
    取消锁定餐次的业务逻辑（管理员功能）
    将状态从 locked 恢复为 published，并允许订单再次修改
    """
    con = get_conn()
    con.execute("BEGIN")
    try:
        st = con.execute(
            "SELECT status FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        if not st or st[0] != "locked":
            con.execute("ROLLBACK")
            raise HTTPException(400, "meal not in locked state")

        con.execute(
            "UPDATE meals SET status='published', updated_at=now() WHERE meal_id=?",
            [meal_id],
        )
        # 清除所有活跃订单上的锁定时间，允许用户后续修改
        con.execute(
            "UPDATE orders SET locked_at=NULL WHERE meal_id=? AND status='active'",
            [meal_id],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    
    # 记录日志
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    actor_id = urow[0] if urow else None
    m = con.execute(
        "SELECT date, slot, title FROM meals WHERE meal_id=?",
        [meal_id],
    ).fetchone()
    log_meal_action(
        "meal_unlock",
        actor_id,
        {
            "meal_id": meal_id,
            "date": str(m[0]) if m else None,
            "slot": m[1] if m else None,
            "title": m[2] if m else None,
        }
    )
    return {"meal_id": meal_id, "status": "published"}


def complete_meal_logic(meal_id: int, open_id: str) -> dict:
    """
    标记餐次为已完成的业务逻辑（管理员功能）
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
    con = get_conn()
    con.execute(
        "UPDATE meals SET status='completed', updated_at=now() WHERE meal_id=? AND status='locked'",
        [meal_id],
    )
    
    # 记录日志
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    actor_id = urow[0] if urow else None
    m = con.execute(
        "SELECT date, slot, title FROM meals WHERE meal_id=?",
        [meal_id],
    ).fetchone()
    log_meal_action(
        "meal_complete",
        actor_id,
        {
            "meal_id": meal_id,
            "date": str(m[0]) if m else None,
            "slot": m[1] if m else None,
            "title": m[2] if m else None,
        }
    )
    return {"meal_id": meal_id, "status": "completed"}


def cancel_meal_logic(meal_id: int, open_id: str) -> dict:
    """
    取消餐次并退款所有订单的业务逻辑（管理员功能）
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
    con = get_conn()
    # 解析操作者并获取餐次基础信息（用于日志）
    actor_id = ensure_user_exists(open_id)
    mrow = get_meal_basic_info(meal_id)
    meal_date = str(mrow[0]) if mrow else None
    meal_slot = mrow[1] if mrow else None
    meal_title = mrow[2] if mrow else None
    meal_opts = parse_meal_options(mrow[3] if mrow else None)

    # 构建 options 映射，便于通过订单的选项ID反查名称和价格
    opt_by_id = build_option_mapping(meal_opts)

    con.execute("BEGIN")
    try:
        # 验证餐次状态
        st = con.execute(
            "SELECT status FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        if not st or st[0] not in ("published", "locked"):
            con.execute("ROLLBACK")
            raise HTTPException(400, "meal cannot be canceled in current state")

        # 更新餐次状态为已取消
        con.execute(
            "UPDATE meals SET status='canceled', updated_at=now() WHERE meal_id=?",
            [meal_id],
        )

        # 批量退款所有活跃订单，并记录每个用户的取消日志（操作者为管理员）
        orders = con.execute(
            "SELECT order_id, user_id, amount_cents, options_json FROM orders WHERE meal_id=? AND status='active'",
            [meal_id],
        ).fetchall()
        for oid, uid, amt, ojson in orders:
            # 余额前后
            bal_before_row = con.execute(
                "SELECT balance_cents FROM users WHERE id=?",
                [uid],
            ).fetchone()
            bal_before = bal_before_row[0] if bal_before_row else 0
            bal_after = bal_before + (amt or 0)

            # 取消订单状态
            con.execute(
                "UPDATE orders SET status='canceled', updated_at=now() WHERE order_id=?",
                [oid],
            )
            # 记录退款账单
            con.execute(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [uid, "refund", amt, "order", oid, "meal canceled"],
            )
            # 增加用户余额
            con.execute(
                "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
                [amt, uid],
            )

            # 解析订单选项并映射为包含名称和价格的结构
            selected_options = parse_selected_options(ojson, opt_by_id)

            # 每个用户写入一条取消订单日志，actor 为管理员
            log_meal_action(
                "order_cancel",
                actor_id,
                {
                    "order_id": oid,
                    "meal_id": meal_id,
                    "date": meal_date,
                    "slot": meal_slot,
                    "title": meal_title,
                    "selected_options": selected_options,
                    "amount_cents": amt,
                    "balance_before_cents": bal_before,
                    "balance_after_cents": bal_after,
                }
            )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    
    # 汇总并写入餐次取消日志（概要），包含受影响的用户列表
    try:
        aff = con.execute(
            "SELECT user_id FROM orders WHERE meal_id=? AND status='canceled'",
            [meal_id],
        ).fetchall()
        user_ids = [r[0] for r in aff]
        names = []
        if user_ids:
            placeholders = ",".join(["?"] * len(user_ids))
            rows = con.execute(
                f"SELECT id, nickname, open_id FROM users WHERE id IN ({placeholders})",
                user_ids,
            ).fetchall()
            names = [{"user_id": r[0], "nickname": r[1], "open_id": r[2]} for r in rows]
        log_meal_action(
            "meal_cancel",
            actor_id,
            {
                "meal_id": meal_id,
                "date": meal_date,
                "slot": meal_slot,
                "title": meal_title,
                "affected_count": len(user_ids),
                "affected_users": names,
            }
        )
    except Exception:
        pass
    return {"meal_id": meal_id, "status": "canceled"}


def repost_meal_logic(meal_id: int, body: MealReq, open_id: str) -> dict:
    """
    危险修改：取消并重新发布餐次的业务逻辑
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
    con = get_conn()
    con.execute("BEGIN")
    try:
        # 验证餐次状态
        st = con.execute(
            "SELECT status FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        if not st or st[0] != "published":
            con.execute("ROLLBACK")
            raise HTTPException(400, "meal not in published state")

        # 更新餐次详细信息
        con.execute(
            "UPDATE meals SET title=?, description=?, base_price_cents=?, options_json=?, capacity=?, per_user_limit=?, updated_at=now() WHERE meal_id=? AND status='published'",
            [
                body.title,
                body.description,
                body.base_price_cents,
                json.dumps([o.model_dump() for o in body.options]),
                body.capacity,
                body.per_user_limit,
                meal_id,
            ],
        )

        # 取消并退款所有现有订单
        orders = con.execute(
            "SELECT order_id, user_id, amount_cents FROM orders WHERE meal_id=? AND status='active'",
            [meal_id],
        ).fetchall()
        for oid, uid, amt in orders:
            con.execute(
                "UPDATE orders SET status='canceled', updated_at=now() WHERE order_id=?",
                [oid],
            )
            con.execute(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [uid, "refund", amt, "order", oid, "meal repost"],
            )
            con.execute(
                "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
                [amt, uid],
            )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    
    # 记录日志
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    actor_id = urow[0] if urow else None
    log_meal_action(
        "meal_publish",
        actor_id,
        {
            "meal_id": meal_id,
            "date": str(body.date),
            "slot": body.slot,
            "title": body.title,
            "description": body.description,
            "base_price_cents": body.base_price_cents,
            "options": [o.model_dump() for o in body.options],
            "capacity": body.capacity,
            "per_user_limit": body.per_user_limit,
        }
    )
    return {"meal_id": meal_id, "status": "published"}