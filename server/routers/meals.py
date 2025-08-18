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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from ..db import get_conn
import json
from ..utils.security import get_open_id
from ..routers.users import _ensure_user

router = APIRouter()


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
    con = get_conn()
    # 尝试获取用户ID，可能不存在（新用户首次访问）
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    uid = urow[0] if urow else None

    # 解析月份参数并构造查询条件
    y, m = month.split("-")
    first = f"{y}-{m}-01"

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
        opts = r[5]
        try:
            opts = json.loads(opts) if isinstance(opts, str) else (opts or [])
        except Exception:
            opts = []  # 解析失败时使用空列表

        # 计算当前用户的订餐状态
        my_ordered = False
        if uid:
            row = con.execute(
                "SELECT 1 FROM orders WHERE user_id=? AND meal_id=? AND status='active' LIMIT 1",
                [uid, r[0]],
            ).fetchone()
            my_ordered = bool(row)

        data.append(
            {
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
            }
        )
    return {"month": month, "meals": data}


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
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    uid = urow[0] if urow else None

    # 按月份组织返回数据
    result: dict[str, list[dict]] = {m: [] for m in parts}
    for r in rows:
        ym = r[0]  # 年月字符串

        # 解析配菜选项JSON
        opts = r[6]
        try:
            opts = json.loads(opts) if isinstance(opts, str) else (opts or [])
        except Exception:
            opts = []

        # 计算用户订餐状态
        my_ordered = False
        if uid:
            row = con.execute(
                "SELECT 1 FROM orders WHERE user_id=? AND meal_id=? AND status='active' LIMIT 1",
                [uid, r[1]],
            ).fetchone()
            my_ordered = bool(row)

        result.setdefault(ym, []).append(
            {
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
            }
        )
    return {"months": result}


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
    opts = r[6]
    try:
        opts = json.loads(opts) if isinstance(opts, str) else (opts or [])
    except Exception:
        opts = []

    # 计算当前用户的订餐状态
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    uid = urow[0] if urow else None
    my_ordered = False
    if uid:
        row = con.execute(
            "SELECT 1 FROM orders WHERE user_id=? AND meal_id=? AND status='active' LIMIT 1",
            [uid, meal_id],
        ).fetchone()
        my_ordered = bool(row)

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
    # resolve actor id
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    if not urow:
        _ensure_user(con, open_id, None)
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    actor_id = urow[0] if urow else None
    # log meal publish (actor only)
    try:
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [
                None,
                actor_id,
                "meal_publish",
                json.dumps(
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
                ),
            ],
        )
    except Exception:
        pass
    return {"meal_id": meal[0]}


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
    try:
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        if not urow:
            _ensure_user(con, open_id, None)
            urow = con.execute(
                "SELECT id FROM users WHERE open_id=?", [open_id]
            ).fetchone()
        actor_id = urow[0] if urow else None
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [
                None,
                actor_id,
                "meal_edit",
                json.dumps(
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
                ),
            ],
        )
    except Exception:
        pass
    return {"meal_id": meal_id}


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
    # log lock
    try:
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        actor_id = urow[0] if urow else None
        m = con.execute(
            "SELECT date, slot, title FROM meals WHERE meal_id=?",
            [meal_id],
        ).fetchone()
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [
                None,
                actor_id,
                "meal_lock",
                json.dumps(
                    {
                        "meal_id": meal_id,
                        "date": str(m[0]) if m else None,
                        "slot": m[1] if m else None,
                        "title": m[2] if m else None,
                    }
                ),
            ],
        )
    except Exception:
        pass
    return {"meal_id": meal_id, "status": "locked"}


@router.post("/meals/{meal_id}/unlock")
def unlock_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    """
    取消锁定餐次（管理员功能）
    将状态从 locked 恢复为 published，并允许订单再次修改。
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
    # log unlock
    try:
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        actor_id = urow[0] if urow else None
        m = con.execute(
            "SELECT date, slot, title FROM meals WHERE meal_id=?",
            [meal_id],
        ).fetchone()
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [
                None,
                actor_id,
                "meal_unlock",
                json.dumps(
                    {
                        "meal_id": meal_id,
                        "date": str(m[0]) if m else None,
                        "slot": m[1] if m else None,
                        "title": m[2] if m else None,
                    }
                ),
            ],
        )
    except Exception:
        pass
    return {"meal_id": meal_id, "status": "published"}


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
    con = get_conn()
    con.execute(
        "UPDATE meals SET status='completed', updated_at=now() WHERE meal_id=? AND status='locked'",
        [meal_id],
    )
    try:
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        actor_id = urow[0] if urow else None
        m = con.execute(
            "SELECT date, slot, title FROM meals WHERE meal_id=?",
            [meal_id],
        ).fetchone()
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [
                None,
                actor_id,
                "meal_complete",
                json.dumps(
                    {
                        "meal_id": meal_id,
                        "date": str(m[0]) if m else None,
                        "slot": m[1] if m else None,
                        "title": m[2] if m else None,
                    }
                ),
            ],
        )
    except Exception:
        pass
    return {"meal_id": meal_id, "status": "completed"}


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
    con = get_conn()
    # 解析操作者并获取餐次基础信息（用于日志）
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    if not urow:
        _ensure_user(con, open_id, None)
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    actor_id = urow[0] if urow else None
    mrow = con.execute(
        "SELECT date, slot, title, options_json FROM meals WHERE meal_id=?",
        [meal_id],
    ).fetchone()
    meal_date = str(mrow[0]) if mrow else None
    meal_slot = mrow[1] if mrow else None
    meal_title = mrow[2] if mrow else None
    meal_opts = []
    try:
        meal_opts = (
            json.loads(mrow[3])
            if (mrow and isinstance(mrow[3], str))
            else (mrow[3] or [])
        )
    except Exception:
        meal_opts = []

    # 构建 options 映射，便于通过订单的选项ID反查名称和价格
    opt_by_id = {}
    try:
        for o in meal_opts or []:
            oid = (o.get("id") if isinstance(o, dict) else None) or None
            if oid:
                opt_by_id[str(oid)] = o
    except Exception:
        opt_by_id = {}

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
            selected_options = []
            try:
                sel_ids = json.loads(ojson) if isinstance(ojson, str) else (ojson or [])
                if isinstance(sel_ids, list):
                    for sid in sel_ids:
                        so = opt_by_id.get(str(sid))
                        if so:
                            # 仅挑选对展示友好的字段
                            selected_options.append(
                                {
                                    "id": so.get("id"),
                                    "name": so.get("name"),
                                    "price_cents": so.get("price_cents"),
                                }
                            )
            except Exception:
                selected_options = []

            # 每个用户写入一条取消订单日志，actor 为管理员
            try:
                con.execute(
                    "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
                    [
                        uid,
                        actor_id,
                        "order_cancel",
                        json.dumps(
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
                        ),
                    ],
                )
            except Exception:
                pass
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    try:
        # 汇总并写入餐次取消日志（概要），包含受影响的用户列表
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
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [
                None,
                actor_id,
                "meal_cancel",
                json.dumps(
                    {
                        "meal_id": meal_id,
                        "date": meal_date,
                        "slot": meal_slot,
                        "title": meal_title,
                        "affected_count": len(user_ids),
                        "affected_users": names,
                    }
                ),
            ],
        )
    except Exception:
        pass
    return {"meal_id": meal_id, "status": "canceled"}


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
    try:
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        actor_id = urow[0] if urow else None
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [
                None,
                actor_id,
                "meal_publish",
                json.dumps(
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
                ),
            ],
        )
    except Exception:
        pass
    return {"meal_id": meal_id, "status": "published"}
