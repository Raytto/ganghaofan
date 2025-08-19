"""
向后兼容的安全模块
保持原有API兼容性，同时使用新的核心安全模块
"""

from fastapi import Depends, HTTPException, Header
from jose import jwt

# 导入新的安全管理器
from ..core.security import security_manager, get_open_id as new_get_open_id

# JWT配置常量（保持兼容）
SECRET = "dev-secret-key-change-me"  # 生产环境应使用环境变量
ALGO = "HS256"


def create_token(open_id: str) -> str:
    """
    为用户创建JWT访问令牌（向后兼容接口）
    使用新的安全管理器
    """
    return security_manager.create_jwt_token(open_id)


async def get_open_id(authorization: str | None = Header(default=None)) -> str:
    """
    从HTTP请求头中提取并验证用户身份（向后兼容接口）
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
        
    token = authorization.split(" ", 1)[1]
    try:
        return security_manager.get_open_id_from_token(token)
    except Exception:
        raise HTTPException(401, "invalid token")


# 额外的兼容性别名
create_access_token = create_token
