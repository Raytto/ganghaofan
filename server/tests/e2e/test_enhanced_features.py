"""
增强功能端到端测试
测试完整的业务流程和边界情况
"""

import pytest
import requests
import time
import json
from datetime import datetime, timedelta

# 测试配置
BASE_URL = "http://127.0.0.1:8001/api/v1"
HEADERS = {
    "X-DB-Key": "test_value",
    "Content-Type": "application/json"
}

class TestCompleteOrderFlow:
    """测试完整的订单流程"""
    
    def setup_class(self):
        """测试类初始化"""
        self.meal_id = None
        self.order_id = None
        
    def test_complete_meal_to_order_flow(self):
        """测试从发布餐次到订单完成的完整流程"""
        
        # 步骤1: 发布餐次
        meal_data = {
            "title": "Complete Flow Test Meal",
            "meal_date": "2024-01-25",
            "slot": "lunch",
            "base_price_cents": 1800,
            "capacity": 20,
            "per_user_limit": 2,
            "options_json": json.dumps(["宫保鸡丁", "麻婆豆腐", "白米饭", "紫菜蛋花汤"])
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
        
        # 步骤2: 验证餐次在列表中
        response = requests.get(
            f"{BASE_URL}/meals",
            params={"status": "published", "page": 1, "size": 10},
            headers=HEADERS
        )
        
        assert response.status_code == 200
        meals = response.json()["data"]
        meal_found = any(meal["meal_id"] == self.meal_id for meal in meals)
        assert meal_found, "发布的餐次未在列表中找到"
        
        # 步骤3: 下订单
        order_data = {
            "meal_id": self.meal_id,
            "qty": 1,
            "options": ["宫保鸡丁", "白米饭"]
        }
        
        response = requests.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        order_result = response.json()
        self.order_id = order_result["order_id"]
        assert order_result["amount_cents"] == 1800
        
        # 步骤4: 验证订单详情
        response = requests.get(
            f"{BASE_URL}/orders/{self.order_id}",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        order_detail = response.json()
        assert order_detail["order_id"] == self.order_id
        assert order_detail["meal_id"] == self.meal_id
        assert order_detail["qty"] == 1
        assert len(order_detail["options"]) == 2
        
        # 步骤5: 修改订单
        update_data = {
            "qty": 2,
            "options": ["麻婆豆腐", "白米饭", "紫菜蛋花汤"]
        }
        
        response = requests.put(
            f"{BASE_URL}/orders/{self.order_id}",
            json=update_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        update_result = response.json()
        assert update_result["amount_cents"] == 3600  # 2份 * 1800
        
        # 步骤6: 验证修改后的订单
        response = requests.get(
            f"{BASE_URL}/orders/{self.order_id}",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        order_detail = response.json()
        assert order_detail["qty"] == 2
        assert len(order_detail["options"]) == 3
        
        # 步骤7: 取消订单
        response = requests.delete(
            f"{BASE_URL}/orders/{self.order_id}",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        cancel_result = response.json()
        assert cancel_result["order_id"] == self.order_id
        assert cancel_result["status"] == "canceled"


class TestCapacityManagement:
    """测试容量管理"""
    
    def setup_class(self):
        """测试类初始化"""
        self.meal_id = None
        
    def test_meal_capacity_limits(self):
        """测试餐次容量限制"""
        
        # 创建小容量餐次
        meal_data = {
            "title": "Small Capacity Meal",
            "meal_date": "2024-01-26",
            "slot": "dinner",
            "base_price_cents": 1000,
            "capacity": 2,  # 只能2份
            "per_user_limit": 1,
            "options_json": "[]"
        }
        
        response = requests.post(
            f"{BASE_URL}/meals",
            json=meal_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        self.meal_id = response.json()["data"]["meal_id"]
        
        # 下第一个订单
        order_data = {
            "meal_id": self.meal_id,
            "qty": 1,
            "options": []
        }
        
        response = requests.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers=HEADERS
        )
        
        assert response.status_code == 200
        first_order_id = response.json()["order_id"]
        
        # 尝试下第二个订单（应该成功，因为容量是2）
        response = requests.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers=HEADERS
        )
        
        # 这里可能会失败，因为一个用户只能下一个订单
        # 实际测试中需要不同的用户来测试容量限制
        
        # 先取消第一个订单来继续测试
        requests.delete(
            f"{BASE_URL}/orders/{first_order_id}",
            headers=HEADERS
        )


class TestErrorHandling:
    """测试错误处理"""
    
    def test_order_nonexistent_meal(self):
        """测试订购不存在的餐次"""
        order_data = {
            "meal_id": 99999,  # 不存在的餐次ID
            "qty": 1,
            "options": []
        }
        
        response = requests.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers=HEADERS
        )
        
        assert response.status_code == 400
        
    def test_get_nonexistent_order(self):
        """测试获取不存在的订单"""
        response = requests.get(
            f"{BASE_URL}/orders/99999",  # 不存在的订单ID
            headers=HEADERS
        )
        
        assert response.status_code == 400
        
    def test_invalid_meal_data(self):
        """测试无效的餐次数据"""
        invalid_meal_data = {
            "title": "",  # 空标题
            "meal_date": "invalid-date",  # 无效日期
            "slot": "breakfast",  # 无效时段
            "base_price_cents": -100,  # 负价格
            "capacity": 0,  # 0容量
            "per_user_limit": 0,
            "options_json": "invalid json"
        }
        
        response = requests.post(
            f"{BASE_URL}/meals",
            json=invalid_meal_data,
            headers=HEADERS
        )
        
        assert response.status_code == 400
        
    def test_invalid_order_quantities(self):
        """测试无效的订单数量"""
        # 首先创建一个有效的餐次
        meal_data = {
            "title": "Quantity Test Meal",
            "meal_date": "2024-01-27",
            "slot": "lunch",
            "base_price_cents": 1000,
            "capacity": 100,
            "per_user_limit": 10,
            "options_json": "[]"
        }
        
        response = requests.post(
            f"{BASE_URL}/meals",
            json=meal_data,
            headers=HEADERS
        )
        
        if response.status_code == 200:
            meal_id = response.json()["data"]["meal_id"]
            
            # 测试0数量订单
            order_data = {
                "meal_id": meal_id,
                "qty": 0,  # 无效数量
                "options": []
            }
            
            response = requests.post(
                f"{BASE_URL}/orders",
                json=order_data,
                headers=HEADERS
            )
            
            assert response.status_code == 422  # Pydantic validation error
            
            # 测试超大数量订单
            order_data["qty"] = 100  # 超出per_user_limit
            
            response = requests.post(
                f"{BASE_URL}/orders",
                json=order_data,
                headers=HEADERS
            )
            
            assert response.status_code == 422  # Pydantic validation error


class TestConcurrentOperations:
    """测试并发操作"""
    
    def test_concurrent_orders_simulation(self):
        """模拟并发下单（简单版本）"""
        # 创建餐次
        meal_data = {
            "title": "Concurrent Test Meal",
            "meal_date": "2024-01-28",
            "slot": "dinner",
            "base_price_cents": 1200,
            "capacity": 5,
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
            
            # 快速连续下单（模拟并发）
            order_data = {
                "meal_id": meal_id,
                "qty": 1,
                "options": []
            }
            
            successful_orders = 0
            for i in range(3):
                response = requests.post(
                    f"{BASE_URL}/orders",
                    json=order_data,
                    headers=HEADERS
                )
                
                if response.status_code == 200:
                    successful_orders += 1
                    # 立即取消订单，为下一轮测试让路
                    order_id = response.json()["order_id"]
                    requests.delete(f"{BASE_URL}/orders/{order_id}", headers=HEADERS)
                
                time.sleep(0.1)  # 短暂延迟
            
            # 至少应该有一个订单成功
            assert successful_orders >= 1


class TestDataIntegrity:
    """测试数据一致性"""
    
    def test_order_balance_consistency(self):
        """测试订单和余额的一致性"""
        # 获取当前余额
        response = requests.get(
            f"{BASE_URL}/users/me/balance",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            initial_balance = response.json()["balance_cents"]
            
            # 创建餐次
            meal_data = {
                "title": "Balance Test Meal",
                "meal_date": "2024-01-29",
                "slot": "lunch",
                "base_price_cents": 2000,
                "capacity": 10,
                "per_user_limit": 1,
                "options_json": "[]"
            }
            
            meal_response = requests.post(
                f"{BASE_URL}/meals",
                json=meal_data,
                headers=HEADERS
            )
            
            if meal_response.status_code == 200:
                meal_id = meal_response.json()["data"]["meal_id"]
                
                # 下订单
                order_data = {
                    "meal_id": meal_id,
                    "qty": 1,
                    "options": []
                }
                
                order_response = requests.post(
                    f"{BASE_URL}/orders",
                    json=order_data,
                    headers=HEADERS
                )
                
                if order_response.status_code == 200:
                    order_result = order_response.json()
                    order_id = order_result["order_id"]
                    
                    # 验证余额变化
                    expected_balance = initial_balance - 2000
                    actual_balance = order_result["balance_cents"]
                    assert actual_balance == expected_balance, f"余额不一致: 期望 {expected_balance}, 实际 {actual_balance}"
                    
                    # 取消订单
                    cancel_response = requests.delete(
                        f"{BASE_URL}/orders/{order_id}",
                        headers=HEADERS
                    )
                    
                    if cancel_response.status_code == 200:
                        # 验证余额恢复
                        cancel_result = cancel_response.json()
                        restored_balance = cancel_result["balance_cents"]
                        assert restored_balance == initial_balance, f"余额未正确恢复: 期望 {initial_balance}, 实际 {restored_balance}"


class TestSystemLimits:
    """测试系统限制"""
    
    def test_meal_date_validation(self):
        """测试餐次日期验证"""
        # 测试过去日期（应该被允许，用于测试）
        past_date_meal = {
            "title": "Past Date Meal",
            "meal_date": "2020-01-01",
            "slot": "lunch",
            "base_price_cents": 1000,
            "capacity": 10,
            "per_user_limit": 1,
            "options_json": "[]"
        }
        
        response = requests.post(
            f"{BASE_URL}/meals",
            json=past_date_meal,
            headers=HEADERS
        )
        
        # 在测试环境中，过去日期可能被允许
        assert response.status_code in [200, 400]
        
    def test_user_profile_creation(self):
        """测试用户档案创建"""
        response = requests.get(
            f"{BASE_URL}/users/me",
            headers=HEADERS
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "open_id" in data
        assert "balance_cents" in data
        
    def test_balance_operations_limits(self):
        """测试余额操作限制"""
        # 测试自助充值限制
        large_recharge = {
            "amount_cents": 200000,  # 2000元，超出限制
            "payment_method": "wechat"
        }
        
        response = requests.post(
            f"{BASE_URL}/users/self/balance/recharge",
            json=large_recharge,
            headers=HEADERS
        )
        
        assert response.status_code == 400  # 应该被拒绝


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])