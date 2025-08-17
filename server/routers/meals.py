from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from ..db import get_conn
import json
from ..utils.security import get_open_id

router = APIRouter()


class MealOption(BaseModel):
    id: str
    name: str
    price_cents: int


class MealReq(BaseModel):
    date: date
    slot: str
    title: str | None = None
    description: str | None = None
    base_price_cents: int
    options: list[MealOption] = []
    capacity: int
    per_user_limit: int = 1


@router.get("/calendar")
def get_calendar(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    open_id: str = Depends(get_open_id),
):
    con = get_conn()
    # try map open_id to user id (may not exist yet)
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    uid = urow[0] if urow else None
    y, m = month.split("-")
    first = f"{y}-{m}-01"
    # duckdb supports date_trunc; get that month range
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
        # parse options_json to list
        opts = r[5]
        try:
            opts = json.loads(opts) if isinstance(opts, str) else (opts or [])
        except Exception:
            opts = []
        # compute my_ordered (boolean) for current user
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
    # validate and normalize months
    parts = [m.strip() for m in months.split(",") if m.strip()]
    if not parts:
        raise HTTPException(400, "months required")
    for m in parts:
        if len(m) != 7 or m[4] != "-" or not (m[:4].isdigit() and m[5:].isdigit()):
            raise HTTPException(400, f"invalid month: {m}")
    con = get_conn()
    # build IN clause placeholders dynamically
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
    # current user id (if exists)
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    uid = urow[0] if urow else None
    result: dict[str, list[dict]] = {m: [] for m in parts}
    for r in rows:
        ym = r[0]
        # parse options_json
        opts = r[6]
        try:
            opts = json.loads(opts) if isinstance(opts, str) else (opts or [])
        except Exception:
            opts = []
        # my_ordered
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
    # parse options_json
    opts = r[6]
    try:
        opts = json.loads(opts) if isinstance(opts, str) else (opts or [])
    except Exception:
        opts = []
    # my_ordered for current user
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
    con = get_conn()
    if body.slot not in ("lunch", "dinner"):
        raise HTTPException(400, "slot must be lunch or dinner")
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
                None,
            ],
        )
    except Exception as e:
        raise HTTPException(409, "meal exists for date+slot or invalid data")
    meal = con.execute(
        "SELECT * FROM meals WHERE date=? AND slot=?", [body.date, body.slot]
    ).fetchone()
    return {"meal_id": meal[0]}


@router.patch("/meals/{meal_id}")
def update_meal_patch(meal_id: int, body: MealReq, open_id: str = Depends(get_open_id)):
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
    return {"meal_id": meal_id}


@router.put("/meals/{meal_id}")
def update_meal_put(meal_id: int, body: MealReq, open_id: str = Depends(get_open_id)):
    return update_meal_patch(meal_id, body, open_id)


@router.post("/meals/{meal_id}/lock")
def lock_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    con = get_conn()
    con.execute("BEGIN")
    try:
        st = con.execute(
            "SELECT status FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        if not st or st[0] != "published":
            con.execute("ROLLBACK")
            raise HTTPException(400, "meal not in published state")
        con.execute(
            "UPDATE meals SET status='locked', updated_at=now() WHERE meal_id=?",
            [meal_id],
        )
        con.execute(
            "UPDATE orders SET locked_at=now() WHERE meal_id=? AND status='active'",
            [meal_id],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"meal_id": meal_id, "status": "locked"}


@router.post("/meals/{meal_id}/complete")
def complete_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    con = get_conn()
    con.execute(
        "UPDATE meals SET status='completed', updated_at=now() WHERE meal_id=? AND status='locked'",
        [meal_id],
    )
    return {"meal_id": meal_id, "status": "completed"}


@router.post("/meals/{meal_id}/cancel")
def cancel_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    con = get_conn()
    con.execute("BEGIN")
    try:
        st = con.execute(
            "SELECT status FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        if not st or st[0] not in ("published", "locked"):
            con.execute("ROLLBACK")
            raise HTTPException(400, "meal cannot be canceled in current state")
        con.execute(
            "UPDATE meals SET status='canceled', updated_at=now() WHERE meal_id=?",
            [meal_id],
        )
        # refund all active orders
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
                [uid, "refund", amt, "order", oid, "meal canceled"],
            )
            con.execute(
                "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
                [amt, uid],
            )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"meal_id": meal_id, "status": "canceled"}


@router.post("/meals/{meal_id}/repost")
def repost_meal(meal_id: int, body: MealReq, open_id: str = Depends(get_open_id)):
    """
    Treat dangerous edits as cancel-and-repost while keeping the same meal_id:
    - Only allowed when meal is in 'published' state.
    - Update meal fields (title, description, price, options, capacity, per_user_limit).
    - Cancel and refund all active orders for this meal.
    """
    con = get_conn()
    con.execute("BEGIN")
    try:
        st = con.execute(
            "SELECT status FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        if not st or st[0] != "published":
            con.execute("ROLLBACK")
            raise HTTPException(400, "meal not in published state")
        # Update meal details
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
        # Cancel and refund all active orders
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
    return {"meal_id": meal_id, "status": "published"}
