from fastapi import APIRouter, Depends
from ..db import get_conn
from ..utils.security import get_open_id

router = APIRouter()


@router.get("/logs/my")
def my_logs(
    cursor: int | None = None, limit: int = 10, open_id: str = Depends(get_open_id)
):
    """
    返回与当前用户相关的操作日志（主体或操作者），附带操作者的昵称和 open_id。
    """
    con = get_conn()
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    if not urow:
        return {"items": [], "next": None}
    uid = urow[0]
    if cursor is None:
        rows = con.execute(
            """
            SELECT l.log_id, l.action, l.detail_json, l.created_at,
                   au.nickname as actor_nickname, au.open_id as actor_open_id
            FROM logs l
            LEFT JOIN users au ON l.actor_id = au.id
            WHERE l.user_id = ? OR l.actor_id = ?
            ORDER BY l.log_id DESC
            LIMIT ?
            """,
            [uid, uid, limit],
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT l.log_id, l.action, l.detail_json, l.created_at,
                   au.nickname as actor_nickname, au.open_id as actor_open_id
            FROM logs l
            LEFT JOIN users au ON l.actor_id = au.id
            WHERE (l.user_id = ? OR l.actor_id = ?) AND l.log_id < ?
            ORDER BY l.log_id DESC
            LIMIT ?
            """,
            [uid, uid, cursor, limit],
        ).fetchall()
    items = [
        {
            "log_id": r[0],
            "action": r[1],
            "detail": r[2],
            "created_at": str(r[3]),
            "actor_nickname": r[4],
            "actor_open_id": r[5],
        }
        for r in rows
    ]
    next_cursor = items[-1]["log_id"] if items and len(items) == limit else None
    return {"items": items, "next": next_cursor}


@router.get("/logs/all")
def all_logs(cursor: int | None = None, limit: int = 200):
    """返回系统所有日志，按时间倒序，分页。"""
    con = get_conn()
    if cursor is None:
        rows = con.execute(
            """
            SELECT l.log_id, l.action, l.detail_json, l.created_at,
                   au.nickname as actor_nickname, au.open_id as actor_open_id
            FROM logs l
            LEFT JOIN users au ON l.actor_id = au.id
            ORDER BY l.log_id DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT l.log_id, l.action, l.detail_json, l.created_at,
                   au.nickname as actor_nickname, au.open_id as actor_open_id
            FROM logs l
            LEFT JOIN users au ON l.actor_id = au.id
            WHERE l.log_id < ?
            ORDER BY l.log_id DESC
            LIMIT ?
            """,
            [cursor, limit],
        ).fetchall()
    items = [
        {
            "log_id": r[0],
            "action": r[1],
            "detail": r[2],
            "created_at": str(r[3]),
            "actor_nickname": r[4],
            "actor_open_id": r[5],
        }
        for r in rows
    ]
    next_cursor = items[-1]["log_id"] if items and len(items) == limit else None
    return {"items": items, "next": next_cursor}
