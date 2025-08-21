"""
认证系统Mock辅助工具
负责模拟不同用户身份和生成JWT token
"""

import os
import json
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .config_manager import get_config_manager


class AuthHelper:
    """认证辅助工具"""
    
    def __init__(self, auth_config: Dict[str, Any] = None, users_config: Dict[str, Any] = None):
        """初始化认证辅助工具"""
        config_mgr = get_config_manager()
        
        self.auth_config = auth_config or config_mgr.get_auth_config()
        self.users_config = users_config or config_mgr.users
        self.current_user: Optional[str] = None
        
        # JWT配置
        self.jwt_secret = self.auth_config["jwt_secret"]
        self.jwt_algorithm = "HS256"
        self.token_expire_hours = self.auth_config["token_expire_hours"]
        
        # 保存原始环境变量
        self._original_env = {}
    
    def set_mock_user(self, user_type: str) -> Dict[str, Any]:
        """设置当前模拟用户"""
        if user_type not in self.users_config:
            raise ValueError(f"Unknown user type: {user_type}")
        
        user_config = self.users_config[user_type]
        
        # 准备Mock认证环境变量
        mock_auth = {
            "mock_enabled": True,
            "open_id": user_config["openid"],
            "nickname": user_config["nickname"],
            "unique_per_login": False,  # 使用固定的openid
            "is_admin": user_config.get("is_admin", False)
        }
        
        # 设置环境变量
        self._set_env_var("GHF_MOCK_AUTH", json.dumps(mock_auth))
        
        # 记录当前用户
        self.current_user = user_type
        
        print(f"✓ Mock user set to: {user_type} ({user_config['openid']})")
        return user_config
    
    def generate_jwt_token(self, user_type: str = None) -> str:
        """为指定用户生成JWT token"""
        if user_type is None:
            user_type = self.current_user
        
        if user_type is None:
            raise RuntimeError("No user type specified and no current user set")
        
        if user_type not in self.users_config:
            raise ValueError(f"Unknown user type: {user_type}")
        
        user_config = self.users_config[user_type]
        
        # 创建JWT payload
        payload = {
            "open_id": user_config["openid"],
            "exp": datetime.utcnow() + timedelta(hours=self.token_expire_hours),
            "iat": datetime.utcnow(),
            "is_admin": user_config.get("is_admin", False)
        }
        
        # 生成token
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return token
    
    def get_auth_headers(self, user_type: str = None) -> Dict[str, str]:
        """获取认证请求头"""
        if user_type and user_type != self.current_user:
            # 临时切换用户
            original_user = self.current_user
            self.set_mock_user(user_type)
            token = self.generate_jwt_token()
            if original_user:
                self.set_mock_user(original_user)
        else:
            token = self.generate_jwt_token(user_type)
        
        return {
            "Authorization": f"Bearer {token}",
            "X-DB-Key": "test_key",  # 测试用的passphrase
            "Content-Type": "application/json"
        }
    
    def switch_user(self, user_type: str) -> Dict[str, Any]:
        """切换当前用户上下文"""
        return self.set_mock_user(user_type)
    
    def clear_mock_user(self):
        """清除模拟用户设置"""
        # 恢复原始环境变量
        for key, value in self._original_env.items():
            if value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = value
        
        self._original_env.clear()
        self.current_user = None
        
        print("✓ Mock user cleared")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证JWT token（用于测试）"""
        try:
            # 移除Bearer前缀
            if token.startswith("Bearer "):
                token = token[7:]
            
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise RuntimeError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise RuntimeError(f"Invalid token: {e}")
    
    def create_login_request(self, user_type: str, code: str = "test_code") -> Dict[str, Any]:
        """创建登录请求（模拟前端登录）"""
        # 设置Mock用户
        self.set_mock_user(user_type)
        
        return {
            "code": code
        }
    
    def get_user_info_from_token(self, token: str) -> Dict[str, Any]:
        """从token中提取用户信息"""
        payload = self.verify_token(token)
        open_id = payload.get("open_id")
        
        # 查找对应的用户配置
        for user_type, user_config in self.users_config.items():
            if user_config["openid"] == open_id:
                return {
                    "user_type": user_type,
                    "openid": open_id,
                    "nickname": user_config["nickname"],
                    "is_admin": payload.get("is_admin", False)
                }
        
        return {
            "user_type": "unknown",
            "openid": open_id,
            "nickname": "",
            "is_admin": payload.get("is_admin", False)
        }
    
    def setup_test_passphrase(self):
        """设置测试用的passphrase配置"""
        # 临时设置passphrase映射
        passphrase_map = {
            "test_key": "test_value"
        }
        
        self._set_env_var("GHF_PASSPHRASE_MAP", json.dumps(passphrase_map))
        print("✓ Test passphrase configured")
    
    def _set_env_var(self, key: str, value: str):
        """设置环境变量并备份原值"""
        if key not in self._original_env:
            self._original_env[key] = os.environ.get(key)
        
        os.environ[key] = value
    
    def get_current_user_type(self) -> Optional[str]:
        """获取当前用户类型"""
        return self.current_user
    
    def get_all_user_types(self) -> list:
        """获取所有可用的用户类型"""
        return list(self.users_config.keys())
    
    def create_test_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """创建常用测试场景"""
        scenarios = {}
        
        # 管理员场景
        if "admin" in self.users_config:
            scenarios["admin_scenario"] = {
                "user_type": "admin",
                "description": "管理员用户，可以创建餐次、管理订单",
                "headers": self.get_auth_headers("admin")
            }
        
        # 普通用户场景
        normal_users = [ut for ut in self.users_config if not self.users_config[ut].get("is_admin", False)]
        if normal_users:
            scenarios["normal_user_scenario"] = {
                "user_type": normal_users[0],
                "description": "普通用户，可以下单、查看餐次",
                "headers": self.get_auth_headers(normal_users[0])
            }
        
        # 富有用户场景
        if "rich_user" in self.users_config:
            scenarios["rich_user_scenario"] = {
                "user_type": "rich_user", 
                "description": "有余额的用户，用于测试订单支付",
                "headers": self.get_auth_headers("rich_user")
            }
        
        # 新用户场景（余额为0）
        zero_balance_users = [
            ut for ut in self.users_config 
            if self.users_config[ut].get("initial_balance_cents", 0) == 0
            and not self.users_config[ut].get("is_admin", False)
        ]
        if zero_balance_users:
            scenarios["new_user_scenario"] = {
                "user_type": zero_balance_users[0],
                "description": "新用户，余额为0，测试余额不足场景",
                "headers": self.get_auth_headers(zero_balance_users[0])
            }
        
        return scenarios
    
    def __enter__(self):
        """上下文管理器入口"""
        self.setup_test_passphrase()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.clear_mock_user()


if __name__ == "__main__":
    # 测试认证辅助工具
    try:
        print("Testing authentication helper...")
        
        with AuthHelper() as auth:
            # 测试用户切换
            auth.set_mock_user("admin")
            
            # 生成token
            token = auth.generate_jwt_token()
            print(f"✓ JWT token generated: {token[:20]}...")
            
            # 验证token
            payload = auth.verify_token(token)
            print(f"✓ Token verified: {payload['open_id']}")
            
            # 获取认证头
            headers = auth.get_auth_headers()
            print(f"✓ Auth headers: {list(headers.keys())}")
            
            # 切换用户
            auth.switch_user("user_a")
            user_info = auth.get_user_info_from_token(auth.generate_jwt_token())
            print(f"✓ User info: {user_info['user_type']}")
            
            # 测试场景
            scenarios = auth.create_test_scenarios()
            print(f"✓ Test scenarios: {list(scenarios.keys())}")
            
            print("✓ Authentication helper test passed")
            
    except Exception as e:
        print(f"✗ Authentication helper test failed: {e}")