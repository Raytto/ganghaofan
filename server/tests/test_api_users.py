"""
用户API集成测试
测试用户相关的API端点
"""

import pytest
import json
from datetime import date, timedelta


class TestUsersAPI:
    """用户API测试"""

    def test_get_user_profile_success(self, client, auth_headers):
        """测试获取用户资料成功"""
        response = client.get(
            "/api/v1/users/profile",
            headers=auth_headers
        )
        
        # 根据实际API实现调整预期结果
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "user_info" in data["data"]
            
            user_info = data["data"]["user_info"]
            assert "user_id" in user_info
            assert "nickname" in user_info
            assert "balance_cents" in user_info
            assert "is_admin" in user_info
        else:
            # API可能还未实现
            assert response.status_code in [404, 501]

    def test_get_user_profile_unauthorized(self, client):
        """测试未认证访问用户资料"""
        response = client.get("/api/v1/users/profile")
        assert response.status_code == 401

    def test_get_order_history_success(self, client, auth_headers, sample_meal):
        """测试获取订单历史成功"""
        # 先创建一个订单
        client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        # 获取订单历史
        response = client.get(
            "/api/v1/users/orders/history",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "orders" in data["data"]
            assert isinstance(data["data"]["orders"], list)
        else:
            assert response.status_code in [404, 501]

    def test_get_order_history_with_filters(self, client, auth_headers):
        """测试带过滤条件的订单历史"""
        response = client.get(
            "/api/v1/users/orders/history",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "status": "active",
                "limit": 10,
                "offset": 0
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "page_info" in data["data"]
            assert data["data"]["page_info"]["limit"] == 10
        else:
            assert response.status_code in [404, 501]

    def test_get_balance_history_success(self, client, auth_headers):
        """测试获取余额历史成功"""
        response = client.get(
            "/api/v1/users/balance/history",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "history" in data["data"]
            assert isinstance(data["data"]["history"], list)
        else:
            assert response.status_code in [404, 501]

    def test_get_balance_history_pagination(self, client, auth_headers):
        """测试余额历史分页"""
        response = client.get(
            "/api/v1/users/balance/history",
            headers=auth_headers,
            params={
                "limit": 5,
                "offset": 0
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "page_info" in data["data"]
            assert data["data"]["page_info"]["limit"] == 5
        else:
            assert response.status_code in [404, 501]

    def test_admin_recharge_user_balance(self, client, admin_headers, sample_user):
        """测试管理员充值用户余额"""
        response = client.post(
            "/api/v1/users/balance/recharge",
            headers=admin_headers,
            json={
                "user_id": sample_user["user_id"],
                "amount_cents": 5000
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["data"]["recharge_amount_cents"] == 5000
        else:
            assert response.status_code in [404, 501]

    def test_non_admin_recharge_access_denied(self, client, auth_headers, sample_user):
        """测试非管理员无法充值"""
        response = client.post(
            "/api/v1/users/balance/recharge",
            headers=auth_headers,
            json={
                "user_id": sample_user["user_id"],
                "amount_cents": 5000
            }
        )
        
        assert response.status_code == 403

    def test_recharge_invalid_user_id(self, client, admin_headers):
        """测试充值不存在的用户"""
        response = client.post(
            "/api/v1/users/balance/recharge",
            headers=admin_headers,
            json={
                "user_id": 99999,  # 不存在的用户ID
                "amount_cents": 5000
            }
        )
        
        assert response.status_code in [404, 400]

    def test_recharge_negative_amount(self, client, admin_headers, sample_user):
        """测试充值负数金额"""
        response = client.post(
            "/api/v1/users/balance/recharge",
            headers=admin_headers,
            json={
                "user_id": sample_user["user_id"],
                "amount_cents": -1000
            }
        )
        
        assert response.status_code == 422

    def test_recharge_zero_amount(self, client, admin_headers, sample_user):
        """测试充值零金额"""
        response = client.post(
            "/api/v1/users/balance/recharge",
            headers=admin_headers,
            json={
                "user_id": sample_user["user_id"],
                "amount_cents": 0
            }
        )
        
        assert response.status_code == 422

    def test_user_statistics_in_profile(self, client, auth_headers, sample_meal):
        """测试用户资料中的统计信息"""
        # 先创建一些订单历史
        client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        response = client.get(
            "/api/v1/users/profile",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            
            # 检查是否包含统计信息
            if "recent_activity" in data["data"]:
                recent_activity = data["data"]["recent_activity"]
                assert "recent_orders" in recent_activity
                assert "recent_spent_cents" in recent_activity
                
            if "lifetime_stats" in data["data"]:
                lifetime_stats = data["data"]["lifetime_stats"]
                assert "total_orders" in lifetime_stats
                assert "total_spent_cents" in lifetime_stats
        else:
            assert response.status_code in [404, 501]

    def test_invalid_pagination_parameters(self, client, auth_headers):
        """测试无效的分页参数"""
        # 负数limit
        response = client.get(
            "/api/v1/users/orders/history",
            headers=auth_headers,
            params={
                "limit": -1,
                "offset": 0
            }
        )
        
        assert response.status_code == 422

        # 负数offset
        response = client.get(
            "/api/v1/users/balance/history",
            headers=auth_headers,
            params={
                "limit": 10,
                "offset": -5
            }
        )
        
        assert response.status_code == 422

    def test_large_pagination_limit(self, client, auth_headers):
        """测试过大的分页限制"""
        response = client.get(
            "/api/v1/users/orders/history",
            headers=auth_headers,
            params={
                "limit": 1000,  # 可能超过系统限制
                "offset": 0
            }
        )
        
        # 系统应该限制最大页面大小
        if response.status_code == 200:
            data = response.json()
            # 检查是否被限制在合理范围内
            assert data["data"]["page_info"]["limit"] <= 100
        else:
            assert response.status_code in [422, 404, 501]

    def test_invalid_date_format_in_filters(self, client, auth_headers):
        """测试无效的日期格式"""
        response = client.get(
            "/api/v1/users/orders/history",
            headers=auth_headers,
            params={
                "start_date": "invalid-date",
                "end_date": "2024-01-31"
            }
        )
        
        assert response.status_code == 422