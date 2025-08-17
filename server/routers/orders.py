from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import json
from ..db import get_conn
from ..utils.security import get_open_id

router = APIRouter()


class CreateOrderReq(BaseModel):
    meal_id: int
    qty: int
    options: List[str] = []  # list of option_id (boolean options)


class UpdateOrderReq(BaseModel):
    qty: int
    options: List[str] = []


@router.post("/orders")
def create_order(body: CreateOrderReq, open_id: str = Depends(get_open_id)):
    con = get_conn()
    # find user id
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    if not urow:
        con.execute("INSERT INTO users(open_id) VALUES (?)", [open_id])
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    uid = urow[0]

    # fetch meal
    m = con.execute(
        "SELECT meal_id, base_price_cents, options_json, capacity, per_user_limit, status FROM meals WHERE meal_id=?",
        [body.meal_id],
    ).fetchone()
    if not m:
        raise HTTPException(404, "meal not found")
    if m[5] != "published":
        raise HTTPException(400, "meal not open for orders")

    capacity = m[3]
    # 强制每单数量为 1（每人每餐只能点一份）
    if body.qty != 1:
        raise HTTPException(400, "qty must be 1")

    # per-user one per meal: if user already has an active order for this meal, reject
    existing = con.execute(
        "SELECT 1 FROM orders WHERE user_id=? AND meal_id=? AND status='active'",
        [uid, body.meal_id],
    ).fetchone()
    if existing:
        raise HTTPException(409, "already ordered")

    # capacity check
    total_qty = con.execute(
        "SELECT COALESCE(SUM(qty),0) FROM orders WHERE meal_id=? AND status='active'",
        [body.meal_id],
    ).fetchone()[0]
    if total_qty + body.qty > capacity:
        raise HTTPException(409, "capacity exceeded")

    # compute amount
    base_price = m[1]
    # options_json stored as string repr for now; no strict validation for brevity
    options_total = 0
    # TODO: validate options against meal options_json
    amount = base_price * body.qty + options_total

    con.execute("BEGIN")
    try:
        # insert order
        order = con.execute(
            "INSERT INTO orders(user_id, meal_id, qty, options_json, amount_cents, status) VALUES (?,?,?,?,?,?) RETURNING order_id",
            [uid, body.meal_id, body.qty, json.dumps(body.options), amount, "active"],
        ).fetchone()
        order_id = order[0]
        # ledger debit and balance update (immediate charge)
        con.execute(
            "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
            [uid, "debit", amount, "order", order_id, "order create debit"],
        )
        con.execute(
            "UPDATE users SET balance_cents = balance_cents - ? WHERE id=?",
            [amount, uid],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    bal = con.execute("SELECT balance_cents FROM users WHERE id=?", [uid]).fetchone()[0]
    return {"order_id": order_id, "amount_cents": amount, "balance_cents": bal}


@router.patch("/orders/{order_id}")
def update_order(
    order_id: int, body: UpdateOrderReq, open_id: str = Depends(get_open_id)
):
    # modify == cancel old + create new
    con = get_conn()
    ord_row = con.execute(
        "SELECT user_id, meal_id, status FROM orders WHERE order_id=?", [order_id]
    ).fetchone()
    if not ord_row:
        raise HTTPException(404, "order not found")
    uid, meal_id, st = ord_row
    mrow = con.execute("SELECT status FROM meals WHERE meal_id=?", [meal_id]).fetchone()
    if not mrow or mrow[0] != "published":
        raise HTTPException(400, "meal not open for modification")

    # cancel old
    con.execute("BEGIN")
    try:
        amt = con.execute(
            "SELECT amount_cents FROM orders WHERE order_id=? AND status='active'",
            [order_id],
        ).fetchone()
        if not amt:
            con.execute("ROLLBACK")
            raise HTTPException(400, "order not active")
        old_amt = amt[0]
        con.execute(
            "UPDATE orders SET status='canceled', updated_at=now() WHERE order_id=?",
            [order_id],
        )
        con.execute(
            "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
            [uid, "refund", old_amt, "order", order_id, "order update refund"],
        )
        con.execute(
            "UPDATE users SET balance_cents = balance_cents + ? WHERE id=?",
            [old_amt, uid],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    # create new
    return create_order(
        CreateOrderReq(meal_id=meal_id, qty=body.qty, options=body.options), open_id
    )


@router.delete("/orders/{order_id}")
def delete_order(order_id: int, open_id: str = Depends(get_open_id)):
    con = get_conn()
    row = con.execute(
        "SELECT user_id, meal_id, amount_cents FROM orders WHERE order_id=? AND status='active'",
        [order_id],
    ).fetchone()
    if not row:
        raise HTTPException(404, "order not active or not found")
    uid, meal_id, amount = row
    st = con.execute("SELECT status FROM meals WHERE meal_id=?", [meal_id]).fetchone()
    if not st or st[0] != "published":
        raise HTTPException(400, "cannot cancel after lock")

    con.execute("BEGIN")
    try:
        con.execute(
            "UPDATE orders SET status='canceled', updated_at=now() WHERE order_id=?",
            [order_id],
        )
        con.execute(
            "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
            [uid, "refund", amount, "order", order_id, "order cancel refund"],
        )
        con.execute(
            "UPDATE users SET balance_cents = balance_cents + ? WHERE id=?",
            [amount, uid],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    bal = con.execute("SELECT balance_cents FROM users WHERE id=?", [uid]).fetchone()[0]
    return {"order_id": order_id, "balance_cents": bal, "status": "canceled"}
