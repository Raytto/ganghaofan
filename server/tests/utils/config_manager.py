"""
测试配置管理器
负责加载和管理测试配置，支持环境变量覆盖
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class TestConfigManager:
    """测试配置管理器"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent / "config"
        self.config = self._load_config()
        self.users = self._load_users()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载测试配置"""
        config_file = self.config_dir / "test_config.json"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Test config file not found: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 支持环境变量覆盖
            config = self._apply_env_overrides(config)
            
            return config
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to load test config: {e}")
    
    def _load_users(self) -> Dict[str, Any]:
        """加载测试用户配置"""
        users_file = self.config_dir / "test_users.json"
        
        if not users_file.exists():
            raise FileNotFoundError(f"Test users file not found: {users_file}")
        
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to load test users: {e}")
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # 服务器配置覆盖
        if os.getenv("TEST_SERVER_PORT"):
            config["server"]["port"] = int(os.getenv("TEST_SERVER_PORT"))
        
        if os.getenv("TEST_SERVER_HOST"):
            config["server"]["host"] = os.getenv("TEST_SERVER_HOST")
        
        # 数据库配置覆盖
        if os.getenv("TEST_DB_PATH"):
            config["database"]["path"] = os.getenv("TEST_DB_PATH")
        
        # JWT配置覆盖
        if os.getenv("TEST_JWT_SECRET"):
            config["auth"]["jwt_secret"] = os.getenv("TEST_JWT_SECRET")
        
        # 测试模式标记
        if os.getenv("TESTING"):
            config["testing"] = os.getenv("TESTING").lower() == "true"
        
        return config
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self.config["server"]
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        # 将相对路径转换为绝对路径
        db_config = self.config["database"].copy()
        db_path = Path(db_config["path"])
        
        if not db_path.is_absolute():
            # 相对于server目录
            server_dir = Path(__file__).parent.parent.parent
            db_config["path"] = str((server_dir / db_path).resolve())
        
        return db_config
    
    def get_user_config(self, user_type: str) -> Dict[str, Any]:
        """获取指定用户配置"""
        if user_type not in self.users:
            raise ValueError(f"Unknown user type: {user_type}")
        
        return self.users[user_type]
    
    def get_auth_config(self) -> Dict[str, Any]:
        """获取认证配置"""
        return self.config["auth"]
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        logging_config = self.config["logging"].copy()
        
        # 生成带时间戳的日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        log_file = logging_config["file_pattern"].format(timestamp=timestamp)
        
        # 转换为绝对路径
        log_path = Path(log_file)
        if not log_path.is_absolute():
            test_dir = Path(__file__).parent.parent
            log_path = test_dir / log_path
        
        # 确保日志目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging_config["file_path"] = str(log_path)
        
        return logging_config
    
    def get_timeouts(self) -> Dict[str, int]:
        """获取超时配置"""
        return self.config["timeouts"]
    
    def get_all_user_types(self) -> list:
        """获取所有用户类型"""
        return list(self.users.keys())
    
    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 检查必需的配置项
            required_sections = ["server", "database", "auth", "logging", "timeouts"]
            for section in required_sections:
                if section not in self.config:
                    raise ValueError(f"Missing config section: {section}")
            
            # 检查服务器配置
            server_config = self.get_server_config()
            if not (1 <= server_config["port"] <= 65535):
                raise ValueError(f"Invalid server port: {server_config['port']}")
            
            # 检查数据库配置
            db_config = self.get_database_config()
            db_path = Path(db_config["path"])
            if not db_path.parent.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查用户配置
            for user_type in self.users:
                user_config = self.users[user_type]
                if not user_config.get("openid"):
                    raise ValueError(f"User {user_type} missing openid")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False
    
    def get_base_url(self) -> str:
        """获取测试服务器的基础URL"""
        server_config = self.get_server_config()
        return f"http://{server_config['host']}:{server_config['port']}"


# 全局配置管理器实例
_config_manager: Optional[TestConfigManager] = None


def get_config_manager() -> TestConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = TestConfigManager()
    return _config_manager


if __name__ == "__main__":
    # 测试配置加载
    try:
        config_mgr = TestConfigManager()
        print("✓ Configuration loaded successfully")
        
        if config_mgr.validate_config():
            print("✓ Configuration validation passed")
        else:
            print("✗ Configuration validation failed")
            
        print(f"Server URL: {config_mgr.get_base_url()}")
        print(f"Database path: {config_mgr.get_database_config()['path']}")
        print(f"Available users: {config_mgr.get_all_user_types()}")
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")