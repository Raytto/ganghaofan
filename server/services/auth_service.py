"""
认证服务
处理用户登录、JWT token管理和权限验证
"""

from datetime import datetime, timedelta
from typing import Optional
import jwt
import requests
from ..core.database import db_manager
from ..core.exceptions import AuthenticationError, ValidationError
from ..models.user import User, UserCreate
from ..config.settings import settings

class AuthService:
    """认证服务"""
    
    def __init__(self):
        self.db = db_manager
    
    async def login(self, code: str, db_key: str) -> dict:
        """微信登录"""
        try:
            # 验证数据库访问权限
            self._validate_db_access(db_key)
            
            # 获取微信用户信息
            openid = await self._get_openid_from_code(code)
            
            # 获取或创建用户
            user = self._get_or_create_user(openid)
            
            # 生成JWT token
            token = self._generate_token(user.id)
            
            return {
                "token": token,
                "user": user,
                "is_admin": user.is_admin
            }
        except Exception as e:
            raise AuthenticationError(f"登录失败: {str(e)}")
    
    def _validate_db_access(self, db_key: str):
        """验证数据库访问权限"""
        # 基于现有的口令验证逻辑
        # 这里可以从配置文件读取有效的数据库密钥
        if not db_key:
            raise ValidationError("数据库访问密钥不能为空")
        
        # 简单验证，实际环境中应该从配置文件读取
        valid_keys = ["dev_key", "test_key", "prod_key"]
        if db_key not in valid_keys:
            raise ValidationError("无效的数据库访问密钥")
    
    async def _get_openid_from_code(self, code: str) -> str:
        """从微信code获取openid"""
        # 基于现有的微信API调用逻辑
        if settings.wechat_app_id and settings.wechat_app_secret:
            # 真实的微信API调用
            url = "https://api.weixin.qq.com/sns/jscode2session"
            params = {
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
                "js_code": code,
                "grant_type": "authorization_code"
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if "openid" in data:
                return data["openid"]
            else:
                raise AuthenticationError(f"微信登录失败: {data.get('errmsg', '未知错误')}")
        else:
            # 开发模式，返回模拟的openid
            return f"dev_openid_{code}"
    
    def _get_or_create_user(self, openid: str) -> User:
        """获取或创建用户"""
        with self.db.transaction() as conn:
            # 查询用户
            user_query = "SELECT * FROM users WHERE open_id = ?"
            result = conn.execute(user_query, [openid]).fetchone()
            
            if result:
                # 用户已存在
                user_data = dict(result)
                return User(
                    id=user_data["id"],
                    open_id=user_data["open_id"],
                    nickname=user_data.get("nickname"),
                    avatar=user_data.get("avatar"),
                    is_admin=user_data.get("is_admin", False),
                    balance_cents=user_data.get("balance_cents", 0),
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at")
                )
            else:
                # 创建新用户
                insert_query = """
                INSERT INTO users (open_id, balance_cents, is_admin, created_at)
                VALUES (?, 0, FALSE, ?)
                """
                conn.execute(insert_query, [openid, datetime.now().isoformat()])
                
                # 获取新创建的用户
                new_user = conn.execute(user_query, [openid]).fetchone()
                user_data = dict(new_user)
                
                return User(
                    id=user_data["id"],
                    open_id=user_data["open_id"],
                    nickname=user_data.get("nickname"),
                    avatar=user_data.get("avatar"),
                    is_admin=user_data.get("is_admin", False),
                    balance_cents=user_data.get("balance_cents", 0),
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at")
                )
    
    def _generate_token(self, user_id: int) -> str:
        """生成JWT token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    def verify_token(self, token: str) -> Optional[int]:
        """验证token并返回用户ID"""
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token已过期")
        except jwt.InvalidTokenError:
            raise AuthenticationError("无效的token")
    
    def get_current_user(self, user_id: int) -> Optional[User]:
        """根据用户ID获取当前用户信息"""
        with self.db.connection as conn:
            user_query = "SELECT * FROM users WHERE id = ?"
            result = conn.execute(user_query, [user_id]).fetchone()
            
            if result:
                user_data = dict(result)
                return User(
                    id=user_data["id"],
                    open_id=user_data["open_id"],
                    nickname=user_data.get("nickname"),
                    avatar=user_data.get("avatar"),
                    is_admin=user_data.get("is_admin", False),
                    balance_cents=user_data.get("balance_cents", 0),
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at")
                )
            return None