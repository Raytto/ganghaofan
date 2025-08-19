"""
餐次管理的通用辅助函数
提供跨多个业务模块使用的共享功能
"""

import json
from typing import Any, Optional
from ...db import get_conn
from ..users import _ensure_user


def parse_meal_options(options_json: Any) -> list[dict]:
    """
    解析餐次配菜选项JSON
    
    Args:
        options_json: 从数据库读取的选项数据，可能是字符串或列表
        
    Returns:
        list[dict]: 解析后的选项列表，解析失败时返回空列表
    """
    try:
        if isinstance(options_json, str):
            return json.loads(options_json)
        return options_json or []
    except Exception:
        return []


def check_user_ordered_status(user_id: Optional[int], meal_id: int) -> bool:
    """
    检查用户是否已经订餐
    
    Args:
        user_id: 用户ID，为None时表示用户不存在
        meal_id: 餐次ID
        
    Returns:
        bool: 用户是否已经订餐
    """
    if not user_id:
        return False
    
    con = get_conn()
    row = con.execute(
        "SELECT 1 FROM orders WHERE user_id=? AND meal_id=? AND status='active' LIMIT 1",
        [user_id, meal_id],
    ).fetchone()
    return bool(row)


def get_user_id_from_openid(open_id: str) -> Optional[int]:
    """
    根据微信openid获取用户ID
    
    Args:
        open_id: 微信openid
        
    Returns:
        Optional[int]: 用户ID，如果用户不存在则返回None
    """
    con = get_conn()
    urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
    return urow[0] if urow else None


def ensure_user_exists(open_id: str) -> int:
    """
    确保用户存在，不存在则创建
    
    Args:
        open_id: 微信openid
        
    Returns:
        int: 用户ID
    """
    con = get_conn()
    user_id = get_user_id_from_openid(open_id)
    if not user_id:
        _ensure_user(con, open_id, None)
        user_id = get_user_id_from_openid(open_id)
    return user_id


def log_meal_action(action: str, actor_id: Optional[int], detail_data: dict) -> None:
    """
    记录餐次相关操作日志
    
    Args:
        action: 操作类型，如 'meal_publish', 'meal_lock' 等
        actor_id: 操作者用户ID
        detail_data: 详细信息字典
    """
    try:
        con = get_conn()
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [None, actor_id, action, json.dumps(detail_data)],
        )
    except Exception:
        pass  # 日志记录失败不应影响主要业务逻辑


def get_meal_basic_info(meal_id: int) -> Optional[tuple]:
    """
    获取餐次基本信息
    
    Args:
        meal_id: 餐次ID
        
    Returns:
        Optional[tuple]: (date, slot, title, options_json) 或 None
    """
    con = get_conn()
    return con.execute(
        "SELECT date, slot, title, options_json FROM meals WHERE meal_id=?",
        [meal_id],
    ).fetchone()


def build_option_mapping(meal_options: list[dict]) -> dict[str, dict]:
    """
    构建配菜选项ID到选项信息的映射
    
    Args:
        meal_options: 餐次配菜选项列表
        
    Returns:
        dict[str, dict]: 选项ID到选项信息的映射
    """
    opt_by_id = {}
    try:
        for o in meal_options or []:
            oid = (o.get("id") if isinstance(o, dict) else None) or None
            if oid:
                opt_by_id[str(oid)] = o
    except Exception:
        pass
    return opt_by_id


def parse_selected_options(options_json: Any, option_mapping: dict[str, dict]) -> list[dict]:
    """
    解析用户选择的配菜选项
    
    Args:
        options_json: 用户选择的选项ID列表（JSON格式）
        option_mapping: 选项ID到选项信息的映射
        
    Returns:
        list[dict]: 包含名称和价格的选项信息列表
    """
    selected_options = []
    try:
        sel_ids = json.loads(options_json) if isinstance(options_json, str) else (options_json or [])
        if isinstance(sel_ids, list):
            for sid in sel_ids:
                so = option_mapping.get(str(sid))
                if so:
                    selected_options.append({
                        "id": so.get("id"),
                        "name": so.get("name"),
                        "price_cents": so.get("price_cents"),
                    })
    except Exception:
        pass
    return selected_options