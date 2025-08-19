"""
日志管理路由模块
重构自原 routers/logs.py，使用新的架构
"""

from fastapi import APIRouter, Depends, HTTPException

from ...core.security import get_open_id
from ...core.database import db_manager
from ...core.exceptions import DatabaseError

router = APIRouter()


@router.get("/logs/my")
def get_my_logs(
    page: int = 1,
    size: int = 10,
    open_id: str = Depends(get_open_id)
):
    """获取当前用户相关的日志"""
    try:
        # 获取用户ID
        user_row = db_manager.execute_one(
            "SELECT id FROM users WHERE open_id=?",
            [open_id]
        )
        if not user_row:
            return {"logs": [], "total": 0, "page": page, "size": size}
        
        user_id = user_row[0]
        offset = (page - 1) * size
        
        # 查询日志总数
        total_row = db_manager.execute_one(
            "SELECT COUNT(*) FROM logs WHERE user_id=? OR actor_id=?",
            [user_id, user_id]
        )
        total = total_row[0] if total_row else 0
        
        # 查询日志列表
        logs = db_manager.execute_query(
            """
            SELECT log_id, user_id, actor_id, action, detail_json, created_at
            FROM logs 
            WHERE user_id=? OR actor_id=?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [user_id, user_id, size, offset]
        )
        
        log_list = []
        for row in logs:
            log_list.append({
                "log_id": row[0],
                "user_id": row[1],
                "actor_id": row[2],
                "action": row[3],
                "detail_json": row[4],
                "created_at": str(row[5])
            })
        
        return {
            "logs": log_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.get("/logs/all")
def get_all_logs(
    page: int = 1,
    size: int = 10,
    open_id: str = Depends(get_open_id)
):
    """获取系统所有日志（管理员功能）"""
    try:
        # TODO: 添加管理员权限验证
        
        offset = (page - 1) * size
        
        # 查询日志总数
        total_row = db_manager.execute_one("SELECT COUNT(*) FROM logs")
        total = total_row[0] if total_row else 0
        
        # 查询日志列表
        logs = db_manager.execute_query(
            """
            SELECT log_id, user_id, actor_id, action, detail_json, created_at
            FROM logs 
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [size, offset]
        )
        
        log_list = []
        for row in logs:
            log_list.append({
                "log_id": row[0],
                "user_id": row[1],
                "actor_id": row[2],
                "action": row[3],
                "detail_json": row[4],
                "created_at": str(row[5])
            })
        
        return {
            "logs": log_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
        
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}")