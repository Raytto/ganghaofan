from fastapi import APIRouter, Depends
from ..db import get_conn
from ..utils.security import get_open_id

router = APIRouter()


@router.get("/logs/my")
def my_logs(
    cursor: int | None = None, limit: int = 10, open_id: str = Depends(get_open_id)
):
    con = get_conn()
    uid = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    if not uid:
        return {"items": [], "next": None}
    uid = uid[0]
    if cursor is None:
        rows = con.execute(
            "SELECT log_id, action, detail_json, created_at FROM logs WHERE user_id=? ORDER BY log_id DESC LIMIT ?",
            [uid, limit],
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT log_id, action, detail_json, created_at FROM logs WHERE user_id=? AND log_id < ? ORDER BY log_id DESC LIMIT ?",
            [uid, cursor, limit],
        ).fetchall()
    items = [
        {"log_id": r[0], "action": r[1], "detail": r[2], "created_at": str(r[3])}
        for r in rows
    ]
    next_cursor = items[-1]["log_id"] if items and len(items) == limit else None
    return {"items": items, "next": next_cursor}
