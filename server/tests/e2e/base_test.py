"""
基础测试类
提供E2E测试的基础设施和通用功能
"""

import pytest
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..utils.config_manager import TestConfigManager, get_config_manager
from ..utils.database_manager import TestDatabaseManager
from ..utils.auth_helper import AuthHelper  
from ..utils.test_client import TestAPIClient
from ..utils.db_helper import DatabaseHelper


class BaseE2ETest:
    """E2E测试基类"""
    
    @classmethod
    def setup_class(cls):
        """测试类级别的设置"""
        print(f"\n=== Setting up {cls.__name__} ===")
        
        # 初始化配置管理器
        cls.config = get_config_manager()
        
        # 验证配置
        if not cls.config.validate_config():
            raise RuntimeError("Test configuration validation failed")
        
        # 初始化数据库管理器
        cls.db_manager = TestDatabaseManager()
        
        # 初始化认证助手
        cls.auth_helper = AuthHelper()
        
        # 初始化API客户端
        cls.client = TestAPIClient(auth_helper=cls.auth_helper)
        
        # 初始化数据库助手
        cls.db_helper = DatabaseHelper(cls.db_manager)
        
        # 类级别的用户ID映射
        cls.user_ids = {}
        
        print("✓ Test infrastructure initialized")
    
    @classmethod
    def teardown_class(cls):
        """测试类级别的清理"""
        print(f"\n=== Tearing down {cls.__name__} ===")
        
        # 清理认证设置
        if hasattr(cls, 'auth_helper'):
            cls.auth_helper.clear_mock_user()
        
        print("✓ Test cleanup completed")
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 只设置认证，不创建数据库
        # 测试依赖服务器API进行所有数据操作
        self.auth_helper.setup_test_passphrase()
        
        # 通过API确保测试环境就绪
        if not self.client.health_check():
            raise RuntimeError("Test server not available")
        
        print(f"✓ Test method setup completed")
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理认证
        self.auth_helper.clear_mock_user()
        
        print(f"✓ Test method cleanup completed")
    
    def pytest_runtest_makereport(self, item, call):
        """pytest钩子：获取测试结果"""
        if call.when == "call":
            self._test_failed = call.excinfo is not None
    
    # 辅助方法
    def get_user_id(self, user_type: str) -> int:
        """获取测试用户ID - 通过API查询"""
        # 通过API获取用户信息，而不是依赖本地数据库
        profile_response = self.client.get_user_profile(user_type=user_type)
        if profile_response.get("success"):
            return profile_response["data"]["user_id"]
        else:
            raise ValueError(f"Cannot get user_id for {user_type}: {profile_response}")
    
    def switch_user(self, user_type: str):
        """切换当前测试用户"""
        self.auth_helper.switch_user(user_type)
    
    def assert_success(self, response: Dict[str, Any], message: str = ""):
        """断言API响应成功"""
        assert response["success"], f"API call failed{': ' + message if message else ''}: {response.get('error', 'Unknown error')}"
    
    def assert_status_code(self, response: Dict[str, Any], expected_code: int):
        """断言状态码"""
        assert response["status_code"] == expected_code, f"Expected status {expected_code}, got {response['status_code']}"
    
    def assert_response_data(self, response: Dict[str, Any], expected_keys: List[str]):
        """断言响应数据包含指定字段"""
        self.assert_success(response)
        
        data = response["data"]
        assert isinstance(data, dict), f"Expected dict response data, got {type(data)}"
        
        missing_keys = [key for key in expected_keys if key not in data]
        assert not missing_keys, f"Missing expected keys in response: {missing_keys}"
    
    def assert_user_balance(self, user_type: str, expected_balance: int):
        """断言用户余额"""
        balance_response = self.client.get_user_balance(user_type=user_type)
        if not balance_response.get("success"):
            raise AssertionError(f"Cannot get balance for {user_type}: {balance_response}")
        actual_balance = balance_response["data"]["balance_cents"]
        assert actual_balance == expected_balance, f"Expected balance {expected_balance}, got {actual_balance} for user {user_type}"
    
    def create_test_meal(self, date_str: str = None, slot: str = "lunch",
                        title: str = "测试餐次", description: str = "测试用餐次",
                        base_price_cents: int = 2000, capacity: int = 50,
                        options: List[Dict] = None) -> int:
        """创建测试餐次 - 通过API"""
        if options is None:
            options = [{"id": "chicken_leg", "name": "加鸡腿", "price_cents": 300}]
        
        # 如果没有指定日期，生成唯一日期
        if date_str is None:
            import time
            import datetime
            timestamp = int(time.time() * 1000) % 100000  # 使用时间戳的后5位
            base_date = datetime.date(2024, 12, 1)
            days_offset = timestamp % 365  # 确保在一年内
            test_date = base_date + datetime.timedelta(days=days_offset)
            date_str = test_date.strftime("%Y-%m-%d")
        
        meal_data = {
            "meal_date": date_str,
            "slot": slot,
            "title": title,
            "description": description,
            "base_price_cents": base_price_cents,
            "capacity": capacity,
            "options": options
        }
        
        response = self.client.create_meal(meal_data, user_type="admin")
        if not response.get("success"):
            raise RuntimeError(f"Failed to create test meal: {response}")
        
        return response["data"]["meal_id"]
    
    def create_test_order(self, user_type: str, meal_id: int, qty: int = 1,
                         selected_options: List[str] = None) -> int:
        """创建测试订单 - 通过API"""
        order_data = {
            "meal_id": meal_id,
            "quantity": qty
        }
        
        if selected_options:
            order_data["selected_options"] = [{"id": opt, "quantity": 1} for opt in selected_options]
        
        response = self.client.create_order(order_data, user_type=user_type)
        if not response.get("success"):
            raise RuntimeError(f"Failed to create test order: {response}")
        
        return response["data"]["order_id"]
    
    def wait_for_condition(self, condition_func, timeout: int = 10, interval: float = 0.1) -> bool:
        """等待条件满足"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        
        return False
    
    def print_test_summary(self, test_name: str, **stats):
        """打印测试摘要"""
        print(f"\n=== {test_name} Summary ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
    
    def get_test_data_dir(self) -> Path:
        """获取测试数据目录"""
        return Path(__file__).parent.parent / "fixtures"
    
    def load_test_data(self, filename: str) -> Dict[str, Any]:
        """加载测试数据文件"""
        import json
        
        data_file = self.get_test_data_dir() / filename
        if not data_file.exists():
            raise FileNotFoundError(f"Test data file not found: {data_file}")
        
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_meal_options(self, chicken: bool = True, rice: bool = True) -> List[Dict[str, Any]]:
        """创建标准的餐次选项"""
        options = []
        
        if chicken:
            options.append({
                "id": "chicken_leg",
                "name": "加鸡腿", 
                "price_cents": 300
            })
        
        if rice:
            options.append({
                "id": "extra_rice",
                "name": "加饭",
                "price_cents": 100
            })
        
        return options


class TestHealthMixin:
    """健康检查测试混入类"""
    
    def test_server_health(self):
        """测试服务器健康检查"""
        # 此测试需要服务器运行，这里仅提供框架
        pass


if __name__ == "__main__":
    # 测试基础测试类
    try:
        print("Testing base test class...")
        
        # 创建测试实例
        class DummyTest(BaseE2ETest):
            pass
        
        test_instance = DummyTest()
        
        # 测试类设置
        test_instance.setup_class()
        print("✓ Class setup successful")
        
        # 测试方法设置
        test_instance.setup_method()
        print("✓ Method setup successful")
        
        # 测试辅助方法
        user_id = test_instance.get_user_id("admin")
        print(f"✓ Admin user ID: {user_id}")
        
        # 测试餐次创建
        meal_id = test_instance.create_test_meal()
        print(f"✓ Test meal created: {meal_id}")
        
        # 测试方法清理
        test_instance.teardown_method()
        print("✓ Method cleanup successful")
        
        # 测试类清理
        test_instance.teardown_class()
        print("✓ Class cleanup successful")
        
        print("✓ Base test class test passed")
        
    except Exception as e:
        print(f"✗ Base test class test failed: {e}")
        import traceback
        traceback.print_exc()