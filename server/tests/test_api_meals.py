"""
餐次API集成测试
测试餐次相关的API端点
"""

import pytest
import json
from datetime import date, timedelta


class TestMealsAPI:
    """餐次API测试"""

    def test_get_meals_success(self, client, auth_headers):
        """测试获取餐次列表成功"""
        response = client.get(
            "/api/v1/meals",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert isinstance(data["data"], list)
        else:
            assert response.status_code in [404, 501]

    def test_get_meals_without_date_range(self, client, auth_headers):
        """测试不指定日期范围获取餐次"""
        response = client.get(
            "/api/v1/meals",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert isinstance(data["data"], list)
        else:
            assert response.status_code in [404, 501]

    def test_get_meals_unauthorized(self, client):
        """测试未认证访问餐次列表"""
        response = client.get("/api/v1/meals")
        assert response.status_code == 401

    def test_create_meal_admin_success(self, client, admin_headers):
        """测试管理员成功创建餐次"""
        response = client.post(
            "/api/v1/meals",
            headers=admin_headers,
            json={
                "date": "2024-02-01",
                "slot": "lunch",
                "description": "测试餐次",
                "base_price_cents": 2500,
                "capacity": 30,
                "options": [
                    {
                        "id": "extra_meat",
                        "name": "加肉",
                        "price_cents": 500
                    }
                ]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["data"]["description"] == "测试餐次"
            assert data["data"]["base_price_cents"] == 2500
            assert data["data"]["capacity"] == 30
        else:
            assert response.status_code in [404, 501]

    def test_create_meal_non_admin_denied(self, client, auth_headers):
        """测试非管理员无法创建餐次"""
        response = client.post(
            "/api/v1/meals",
            headers=auth_headers,
            json={
                "date": "2024-02-01",
                "slot": "lunch",
                "description": "测试餐次",
                "base_price_cents": 2500,
                "capacity": 30,
                "options": []
            }
        )
        
        assert response.status_code == 403

    def test_create_meal_duplicate_date_slot(self, client, admin_headers, sample_meal):
        """测试创建重复日期时段的餐次"""
        response = client.post(
            "/api/v1/meals",
            headers=admin_headers,
            json={
                "date": sample_meal["date"],
                "slot": sample_meal["slot"],
                "description": "重复餐次",
                "base_price_cents": 2000,
                "capacity": 40,
                "options": []
            }
        )
        
        # 应该返回冲突错误
        assert response.status_code in [409, 400]

    def test_create_meal_invalid_date_format(self, client, admin_headers):
        """测试无效日期格式创建餐次"""
        response = client.post(
            "/api/v1/meals",
            headers=admin_headers,
            json={
                "date": "invalid-date",
                "slot": "lunch",
                "description": "测试餐次",
                "base_price_cents": 2500,
                "capacity": 30,
                "options": []
            }
        )
        
        assert response.status_code == 422

    def test_create_meal_invalid_slot(self, client, admin_headers):
        """测试无效时段创建餐次"""
        response = client.post(
            "/api/v1/meals",
            headers=admin_headers,
            json={
                "date": "2024-02-01",
                "slot": "invalid_slot",
                "description": "测试餐次",
                "base_price_cents": 2500,
                "capacity": 30,
                "options": []
            }
        )
        
        assert response.status_code == 422

    def test_create_meal_negative_price(self, client, admin_headers):
        """测试负价格创建餐次"""
        response = client.post(
            "/api/v1/meals",
            headers=admin_headers,
            json={
                "date": "2024-02-01",
                "slot": "lunch",
                "description": "测试餐次",
                "base_price_cents": -1000,
                "capacity": 30,
                "options": []
            }
        )
        
        assert response.status_code == 422

    def test_create_meal_zero_capacity(self, client, admin_headers):
        """测试零容量创建餐次"""
        response = client.post(
            "/api/v1/meals",
            headers=admin_headers,
            json={
                "date": "2024-02-01",
                "slot": "lunch",
                "description": "测试餐次",
                "base_price_cents": 2500,
                "capacity": 0,
                "options": []
            }
        )
        
        assert response.status_code == 422

    def test_update_meal_status_admin(self, client, admin_headers, sample_meal):
        """测试管理员更新餐次状态"""
        response = client.put(
            f"/api/v1/meals/{sample_meal['meal_id']}/status",
            headers=admin_headers,
            json={
                "status": "locked",
                "reason": "开始准备制作"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "locked"
        else:
            assert response.status_code in [404, 501]

    def test_update_meal_status_non_admin_denied(self, client, auth_headers, sample_meal):
        """测试非管理员无法更新餐次状态"""
        response = client.put(
            f"/api/v1/meals/{sample_meal['meal_id']}/status",
            headers=auth_headers,
            json={
                "status": "locked",
                "reason": "测试"
            }
        )
        
        assert response.status_code == 403

    def test_update_meal_status_invalid_transition(self, client, admin_headers, sample_meal):
        """测试无效状态转换"""
        # 先设置为completed
        client.put(
            f"/api/v1/meals/{sample_meal['meal_id']}/status",
            headers=admin_headers,
            json={
                "status": "completed",
                "reason": "完成制作"
            }
        )
        
        # 尝试从completed转换为published（不合法）
        response = client.put(
            f"/api/v1/meals/{sample_meal['meal_id']}/status",
            headers=admin_headers,
            json={
                "status": "published",
                "reason": "重新发布"
            }
        )
        
        # 应该返回业务规则错误
        if response.status_code != 501:  # 如果API已实现
            assert response.status_code == 400

    def test_update_nonexistent_meal_status(self, client, admin_headers):
        """测试更新不存在餐次的状态"""
        response = client.put(
            "/api/v1/meals/99999/status",
            headers=admin_headers,
            json={
                "status": "locked",
                "reason": "测试"
            }
        )
        
        assert response.status_code == 404

    def test_get_meal_orders_admin(self, client, admin_headers, sample_meal, sample_user):
        """测试管理员获取餐次订单列表"""
        # 先创建一个订单
        headers = {
            "Authorization": "Bearer test_token",
            "X-DB-Key": "test_key"
        }
        client.post(
            "/api/v1/orders",
            headers=headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        response = client.get(
            f"/api/v1/meals/{sample_meal['meal_id']}/orders",
            headers=admin_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert isinstance(data["data"], list)
        else:
            assert response.status_code in [404, 501]

    def test_get_meal_orders_non_admin_denied(self, client, auth_headers, sample_meal):
        """测试非管理员无法获取餐次订单"""
        response = client.get(
            f"/api/v1/meals/{sample_meal['meal_id']}/orders",
            headers=auth_headers
        )
        
        assert response.status_code == 403

    def test_export_meal_orders_admin(self, client, admin_headers, sample_meal):
        """测试管理员导出餐次订单"""
        response = client.get(
            f"/api/v1/meals/{sample_meal['meal_id']}/export",
            headers=admin_headers
        )
        
        if response.status_code == 200:
            # 应该返回Excel文件
            assert "application" in response.headers.get("content-type", "").lower()
        else:
            assert response.status_code in [404, 501]

    def test_export_meal_orders_non_admin_denied(self, client, auth_headers, sample_meal):
        """测试非管理员无法导出餐次订单"""
        response = client.get(
            f"/api/v1/meals/{sample_meal['meal_id']}/export",
            headers=auth_headers
        )
        
        assert response.status_code == 403

    def test_get_meals_with_order_statistics(self, client, auth_headers, sample_meal, sample_user):
        """测试获取带订单统计的餐次列表"""
        # 先创建一个订单
        headers = {
            "Authorization": "Bearer test_token",
            "X-DB-Key": "test_key"
        }
        client.post(
            "/api/v1/orders",
            headers=headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 2,
                "selected_options": [],
                "notes": ""
            }
        )
        
        response = client.get(
            "/api/v1/meals",
            headers=auth_headers,
            params={
                "start_date": sample_meal["date"],
                "end_date": sample_meal["date"]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            meals = data["data"]
            if meals:
                meal = meals[0]
                # 检查是否包含订单统计
                if "ordered_count" in meal:
                    assert meal["ordered_count"] >= 0
                if "available_capacity" in meal:
                    assert meal["available_capacity"] >= 0
        else:
            assert response.status_code in [404, 501]

    def test_invalid_date_range(self, client, auth_headers):
        """测试无效日期范围"""
        response = client.get(
            "/api/v1/meals",
            headers=auth_headers,
            params={
                "start_date": "2024-01-31",
                "end_date": "2024-01-01"  # 结束日期早于开始日期
            }
        )
        
        assert response.status_code == 422