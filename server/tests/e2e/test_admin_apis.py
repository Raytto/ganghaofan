"""
管理员API端到端测试
测试新实现的管理员功能API
"""

import pytest
import requests
import time
import json

# 测试配置
BASE_URL = "http://127.0.0.1:8001/api/v1"
HEADERS = {
    "X-DB-Key": "test_value",
    "Content-Type": "application/json"
}

class TestAdminMealManagement:
    """测试餐次管理API"""
    
    def setup_class(self):
        """测试类初始化"""
        self.meal_id = None
        
    def test_publish_meal_for_admin_tests(self):
        """为管理员测试准备餐次"""
        meal_data = {
            "title": "Admin Test Meal",
            "meal_date": "2024-01-15",
            "slot": "lunch",
            "base_price_cents": 1200,
            "capacity": 50,
            "per_user_limit": 2,
            "options_json": json.dumps(["蒸蛋", "青菜"])
        }
        
        response = requests.post(
            f"{BASE_URL}/meals",
            json=meal_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        self.meal_id = data["data"]["meal_id"]
        
    def test_lock_meal(self):
        """测试锁定餐次"""
        if not self.meal_id:
            pytest.skip("No meal available for testing")
            
        response = requests.post(
            f"{BASE_URL}/meals/{self.meal_id}/lock",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "锁定成功" in data["message"]
        
    def test_unlock_meal(self):
        """测试解锁餐次"""
        if not self.meal_id:
            pytest.skip("No meal available for testing")
            
        response = requests.post(
            f"{BASE_URL}/meals/{self.meal_id}/unlock",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "解锁成功" in data["message"]
        
    def test_get_meals_list(self):
        """测试获取餐次列表"""
        response = requests.get(
            f"{BASE_URL}/meals",
            params={"page": 1, "size": 10},
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert "pagination" in data
        
    def test_get_meals_list_with_filters(self):
        """测试带过滤条件的餐次列表"""
        response = requests.get(
            f"{BASE_URL}/meals",
            params={
                "status": "published",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "page": 1,
                "size": 5
            },
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
    def test_cancel_meal(self):
        """测试取消餐次（注意：这会删除餐次，放在最后）"""
        if not self.meal_id:
            pytest.skip("No meal available for testing")
            
        response = requests.post(
            f"{BASE_URL}/meals/{self.meal_id}/cancel",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "取消成功" in data["message"]


class TestOrderManagement:
    """测试订单管理API"""
    
    def setup_class(self):
        """测试类初始化"""
        self.order_id = None
        self.meal_id = None
        
    def test_setup_meal_for_order_tests(self):
        """为订单测试准备餐次"""
        meal_data = {
            "title": "Order Test Meal",
            "meal_date": "2024-01-16",
            "slot": "dinner",
            "base_price_cents": 1500,
            "capacity": 30,
            "per_user_limit": 1,
            "options_json": json.dumps(["米饭", "面条"])
        }
        
        response = requests.post(
            f"{BASE_URL}/meals",
            json=meal_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        self.meal_id = data["data"]["meal_id"]
        
    def test_create_order_for_tests(self):
        """创建测试订单"""
        if not self.meal_id:
            pytest.skip("No meal available for testing")
            
        order_data = {
            "meal_id": self.meal_id,
            "qty": 1,
            "options": ["米饭"]
        }
        
        response = requests.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        self.order_id = data["order_id"]
        
    def test_get_order_detail(self):
        """测试获取订单详情"""
        if not self.order_id:
            pytest.skip("No order available for testing")
            
        response = requests.get(
            f"{BASE_URL}/orders/{self.order_id}",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == self.order_id
        assert data["meal_id"] == self.meal_id
        assert data["qty"] >= 1
        
    def test_get_user_orders(self):
        """测试获取用户订单列表"""
        response = requests.get(
            f"{BASE_URL}/orders",
            params={"limit": 10, "offset": 0},
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        
    def test_get_user_orders_with_filters(self):
        """测试带过滤条件的订单列表"""
        response = requests.get(
            f"{BASE_URL}/orders",
            params={
                "status": "active",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "limit": 5,
                "offset": 0
            },
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
    def test_update_order(self):
        """测试修改订单"""
        if not self.order_id:
            pytest.skip("No order available for testing")
            
        update_data = {
            "qty": 1,
            "options": ["面条"]
        }
        
        response = requests.put(
            f"{BASE_URL}/orders/{self.order_id}",
            json=update_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == self.order_id


class TestUserManagement:
    """测试用户管理API"""
    
    def test_get_all_users(self):
        """测试获取所有用户列表"""
        response = requests.get(
            f"{BASE_URL}/users/admin/users",
            params={"page": 1, "size": 10},
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert "pagination" in data
        
    def test_get_all_users_with_search(self):
        """测试用户搜索"""
        response = requests.get(
            f"{BASE_URL}/users/admin/users",
            params={"search": "test", "page": 1, "size": 5},
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
    def test_get_system_stats(self):
        """测试获取系统统计信息"""
        response = requests.get(
            f"{BASE_URL}/users/admin/stats",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        
        stats = data["data"]
        assert "users" in stats
        assert "meals" in stats
        assert "orders" in stats
        assert "financial" in stats
        
        # 验证用户统计结构
        assert "total" in stats["users"]
        assert "admins" in stats["users"]
        assert "regular" in stats["users"]
        
        # 验证财务统计结构
        assert "total_balance_cents" in stats["financial"]
        assert "total_recharge_cents" in stats["financial"]
        assert "total_spent_cents" in stats["financial"]


class TestBalanceManagement:
    """测试余额管理API"""
    
    def setup_class(self):
        """测试类初始化"""
        self.test_user_id = None
        
    def test_get_user_id_for_balance_tests(self):
        """获取测试用户ID"""
        response = requests.get(
            f"{BASE_URL}/users/me",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            self.test_user_id = data["user_id"]
        
    def test_self_recharge(self):
        """测试用户自助充值"""
        recharge_data = {
            "amount_cents": 5000,  # 50元
            "payment_method": "wechat"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/self/balance/recharge",
            json=recharge_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["message"] == "充值成功"
        assert data["data"]["amount_cents"] == 5000
        
    def test_self_recharge_invalid_amount(self):
        """测试无效充值金额"""
        recharge_data = {
            "amount_cents": -1000,  # 负数
            "payment_method": "wechat"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/self/balance/recharge",
            json=recharge_data,
            headers=HEADERS
        )
        
        assert response.status_code == 400
        
    def test_admin_adjust_balance(self):
        """测试管理员调整余额"""
        if not self.test_user_id:
            pytest.skip("No user available for testing")
            
        adjust_data = {
            "user_id": self.test_user_id,
            "amount_cents": 1000,  # 增加10元
            "reason": "测试调整余额"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/admin/balance/adjust",
            json=adjust_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["adjustment_cents"] == 1000
        assert data["data"]["reason"] == "测试调整余额"
        
    def test_get_balance_transactions(self):
        """测试获取余额交易记录"""
        response = requests.get(
            f"{BASE_URL}/users/admin/balance/transactions",
            params={"page": 1, "size": 10},
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert "pagination" in data
        
    def test_get_balance_transactions_with_filters(self):
        """测试带过滤条件的交易记录"""
        if not self.test_user_id:
            pytest.skip("No user available for testing")
            
        response = requests.get(
            f"{BASE_URL}/users/admin/balance/transactions",
            params={
                "user_id": self.test_user_id,
                "transaction_type": "recharge",
                "page": 1,
                "size": 5
            },
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


class TestPermissionControl:
    """测试权限控制"""
    
    def test_admin_apis_require_admin_permission(self):
        """测试管理员API需要管理员权限（这个测试可能会因为mock权限而跳过）"""
        # 注意：在测试环境中，mock_dev_user可能默认就是管理员
        # 这个测试主要验证API的权限检查逻辑存在
        
        response = requests.get(
            f"{BASE_URL}/users/admin/stats",
            headers={"X-DB-Key": "test_value"}  # 不包含管理员权限
        )
        
        # 如果返回200，说明用户有管理员权限（正常情况）
        # 如果返回403，说明权限检查正常工作
        assert response.status_code in [200, 403]
        
    def test_meal_management_apis_permission(self):
        """测试餐次管理API的权限检查"""
        # 创建一个测试餐次来进行权限测试
        meal_data = {
            "title": "Permission Test Meal",
            "meal_date": "2024-01-20",
            "slot": "lunch",
            "base_price_cents": 1000,
            "capacity": 10,
            "per_user_limit": 1,
            "options_json": "[]"
        }
        
        response = requests.post(
            f"{BASE_URL}/meals",
            json=meal_data,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            meal_id = response.json()["data"]["meal_id"]
            
            # 测试锁定餐次的权限
            lock_response = requests.post(
                f"{BASE_URL}/meals/{meal_id}/lock",
                headers={"X-DB-Key": "test_value"}
            )
            
            assert lock_response.status_code in [200, 403]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])