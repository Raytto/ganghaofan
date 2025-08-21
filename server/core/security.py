"""
安全相关功能
从原 utils/security.py 重构而来，增加更多安全功能
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    from ..config import get_passphrase_map
    from .exceptions import AuthenticationError, AuthorizationError
    from .database import db_manager
except ImportError:
    # Fallback for test environment
    from config import get_passphrase_map
    from core.exceptions import AuthenticationError, AuthorizationError
    from core.database import db_manager

# JWT配置
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")  # 从环境变量读取，开发环境有默认值
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7天


class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self.security = HTTPBearer()
    
    def create_jwt_token(self, open_id: str, additional_claims: Dict[str, Any] = None) -> str:
        """创建JWT token"""
        try:
            payload = {
                "open_id": open_id,
                "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
                "iat": datetime.utcnow(),
            }
            
            if additional_claims:
                payload.update(additional_claims)
            
            return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        except Exception as e:
            raise AuthenticationError(f"Failed to create token: {e}")
    
    def decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """解码JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
    
    def get_open_id_from_token(self, token: str) -> str:
        """从token中提取open_id"""
        payload = self.decode_jwt_token(token)
        open_id = payload.get("open_id")
        if not open_id:
            raise AuthenticationError("Token missing open_id")
        return open_id
    
    def verify_passphrase_key(self, x_db_key: Optional[str] = None) -> str:
        """验证数据库访问密钥"""
        mapping = get_passphrase_map() or {}
        valid_keys = {str(v).strip() for v in mapping.values() if str(v).strip()}
        
        # 允许在未配置口令时直接通过
        if valid_keys:
            if not x_db_key or str(x_db_key).strip() not in valid_keys:
                raise AuthorizationError("Invalid or missing passphrase")
        
        return x_db_key or ""


# 全局安全管理器实例
security_manager = SecurityManager()


async def get_open_id(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> str:
    """从Authorization header中提取并验证open_id"""
    try:
        token = credentials.credentials
        return security_manager.get_open_id_from_token(token)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")


async def verify_db_key(x_db_key: Optional[str] = Header(default=None)) -> str:
    """验证数据库访问密钥的依赖函数"""
    try:
        return security_manager.verify_passphrase_key(x_db_key)
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))


# 保持向后兼容的函数
def create_access_token(open_id: str) -> str:
    """创建访问token（向后兼容）"""
    return security_manager.create_jwt_token(open_id)


def verify_token(token: str) -> str:
    """验证token并返回open_id（向后兼容）"""
    return security_manager.get_open_id_from_token(token)


async def get_current_user_id(open_id: str = Depends(get_open_id)) -> int:
    """获取当前用户ID"""
    try:
        print(f"DEBUG: Getting user ID for open_id: {open_id}")
        conn = db_manager.get_connection()
        user_row = conn.execute(
            "SELECT id FROM users WHERE open_id = ?", 
            [open_id]
        ).fetchone()
        
        if not user_row:
            # 如果用户不存在，自动创建
            # 在测试数据库中，如果用户openid包含"admin"则设为管理员
            is_admin = False
            current_db_path = getattr(db_manager, 'db_path', '')
            if ("test" in current_db_path.lower() or "TESTING" in os.environ) and "admin" in open_id.lower():
                is_admin = True
            
            conn.execute(
                "INSERT INTO users (open_id, is_admin) VALUES (?, ?)", 
                [open_id, is_admin]
            )
            user_row = conn.execute(
                "SELECT id FROM users WHERE open_id = ?", 
                [open_id]
            ).fetchone()
        
        if not user_row:
            raise HTTPException(status_code=500, detail="用户创建失败")
        
        return user_row[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户ID失败: {str(e)}")


async def check_admin_permission(current_user_id: int = Depends(get_current_user_id)) -> bool:
    """检查管理员权限"""
    try:
        print(f"DEBUG: Checking admin permission for user_id: {current_user_id}")
        conn = db_manager.get_connection()
        user_row = conn.execute(
            "SELECT is_admin FROM users WHERE id = ?", 
            [current_user_id]
        ).fetchone()
        
        result = user_row and user_row[0]
        print(f"DEBUG: Admin permission result: {result}")
        return result
    except Exception as e:
        print(f"DEBUG: Exception in check_admin_permission: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"权限检查失败: {str(e)}")