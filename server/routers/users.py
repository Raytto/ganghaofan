from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
from ..utils.security import get_open_id
from ..db import get_conn
from ..config import get_mock_settings

router = APIRouter()


def _ensure_user(con, open_id: str, nickname: str | None = None):
    """Idempotently create a user if not exists.
    Avoids race conditions on unique(open_id) by using a WHERE NOT EXISTS guard.
    """
    try:
        con.execute(
            """
            INSERT INTO users(open_id, nickname)
            SELECT ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE open_id = ?)
            """,
            [open_id, nickname, open_id],
        )
    except Exception:
        # In case of a rare race, ignore and proceed.
        pass


class RechargeReq(BaseModel):
    amount_cents: int
    remark: str | None = None


@router.get("/users/me")
def get_my_profile(open_id: str = Depends(get_open_id)):
    """
    返回当前登录用户的基本信息：id、open_id、昵称、是否管理员、余额。
    若用户不存在则自动创建。
    """
    if not open_id:
        # 认证成功但open_id缺失，视为无效token
        raise HTTPException(401, "invalid token")
    con = get_conn()
    row = con.execute(
        "SELECT id, open_id, nickname, is_admin, balance_cents FROM users WHERE open_id = ?",
        [open_id],
    ).fetchone()
    if not row:
        # 如果开启 mock，带上 nickname 创建；使用幂等插入避免并发冲突
        mock = get_mock_settings()
        nick = (
            (mock.get("nickname") or None)
            if (mock.get("mock_enabled") and mock.get("open_id") == open_id)
            else None
        )
        _ensure_user(con, open_id, nick)
        row = con.execute(
            "SELECT id, open_id, nickname, is_admin, balance_cents FROM users WHERE open_id = ?",
            [open_id],
        ).fetchone()
        if not row:
            # 最后一搏：直接尝试插入（并忽略冲突），然后再次查询
            try:
                if nick is not None:
                    con.execute(
                        "INSERT INTO users(open_id, nickname) VALUES (?,?)",
                        [open_id, nick],
                    )
                else:
                    con.execute(
                        "INSERT INTO users(open_id) VALUES (?)",
                        [open_id],
                    )
            except Exception:
                pass
            row = con.execute(
                "SELECT id, open_id, nickname, is_admin, balance_cents FROM users WHERE open_id = ?",
                [open_id],
            ).fetchone()
        if not row:
            raise HTTPException(500, "failed to ensure user")
    return {
        "user_id": row[0],
        "open_id": row[1],
        "nickname": row[2],
        "is_admin": bool(row[3]),
        "balance_cents": row[4],
    }


@router.get("/users/me/balance")
def get_my_balance(open_id: str = Depends(get_open_id)):
    con = get_conn()
    row = con.execute(
        "SELECT id, balance_cents FROM users WHERE open_id = ?", [open_id]
    ).fetchone()
    if not row:
        mock = get_mock_settings()
        nick = (
            (mock.get("nickname") or None)
            if (mock.get("mock_enabled") and mock.get("open_id") == open_id)
            else None
        )
        _ensure_user(con, open_id, nick)
        # Retry select up to 3 times in case of race
        for _ in range(3):
            row = con.execute(
                "SELECT id, balance_cents FROM users WHERE open_id = ?", [open_id]
            ).fetchone()
            if row:
                break
        if not row:
            # As a last fallback, return zeros instead of 500 to keep UI flowing
            return {"user_id": 0, "balance_cents": 0}
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
            [
                user_id,
                None,
                "recharge",
                json.dumps(
                    {
                        "amount_cents": body.amount_cents,
                        "remark": body.remark,
                        "operation": "manual_recharge",
                    }
                ),
            ],
        )
        con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        raise
    bal = con.execute(
        "SELECT balance_cents FROM users WHERE id = ?", [user_id]
    ).fetchone()[0]
    return {"user_id": user_id, "balance_cents": bal}
