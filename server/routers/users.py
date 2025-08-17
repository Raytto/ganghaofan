from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..utils.security import get_open_id
from ..db import get_conn

router = APIRouter()


class RechargeReq(BaseModel):
    amount_cents: int
    remark: str | None = None


@router.get("/users/me/balance")
def get_my_balance(open_id: str = Depends(get_open_id)):
    con = get_conn()
    row = con.execute(
        "SELECT id, balance_cents FROM users WHERE open_id = ?", [open_id]
    ).fetchone()
    if not row:
        con.execute("INSERT INTO users(open_id) VALUES (?)", [open_id])
        row = con.execute(
            "SELECT id, balance_cents FROM users WHERE open_id = ?", [open_id]
        ).fetchone()
    return {"user_id": row[0], "balance_cents": row[1]}


@router.post("/users/{user_id}/recharge")
def recharge(user_id: int, body: RechargeReq, open_id: str = Depends(get_open_id)):
    # TODO: check admin
    con = get_conn()
    if body.amount_cents <= 0:
        raise HTTPException(400, "amount_cents must be > 0")
    con.execute("BEGIN")
    try:
        con.execute(
            "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
            [body.amount_cents, user_id],
        )
        con.execute(
            "INSERT INTO ledger(user_id, type, amount_cents, ref_type, remark) VALUES (?,?,?,?,?)",
            [user_id, "recharge", body.amount_cents, "manual", body.remark],
        )
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [user_id, None, "recharge", "{}"],
        )
        con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        raise
    bal = con.execute(
        "SELECT balance_cents FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]
    return {"user_id": user_id, "balance_cents": bal}
