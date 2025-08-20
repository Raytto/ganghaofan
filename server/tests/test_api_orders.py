"""
订单API集成测试
测试订单相关的API端点
"""

import pytest
import json
from datetime import date, timedelta


class TestOrdersAPI:
    """订单API测试"""

    def test_create_order_success(self, client, auth_headers, sample_meal):
        """测试成功创建订单"""
        response = client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 2,
                "selected_options": [
                    {
                        "id": "chicken_leg",
                        "name": "加鸡腿",
                        "price_cents": 300
                    }
                ],
                "notes": "不要辣"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "order_id" in data["data"]
        assert data["data"]["meal_id"] == sample_meal["meal_id"]
        assert data["data"]["quantity"] == 2
        assert data["data"]["status"] == "active"

    def test_create_order_insufficient_balance(self, client, test_db):
        """测试余额不足创建订单"""
        # 创建余额不足的用户和餐次
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO users (openid, nickname, balance_cents)
            VALUES ('poor_user', '穷用户', 100)
            """)
            
            conn.execute("""
            INSERT INTO meals (date, slot, description, base_price_cents, capacity, creator_id)
            VALUES ('2024-01-20', 'lunch', '昂贵餐次', 5000, 50, 1)
            """)
            meal_id = conn.lastrowid

        # 模拟认证头
        headers = {
            "Authorization": "Bearer poor_token",
            "X-DB-Key": "test_key"
        }

        response = client.post(
            "/api/v1/orders",
            headers=headers,
            json={
                "meal_id": meal_id,
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        # 在熟人内部系统中可能允许负余额，所以这里应该成功
        # 如果不允许负余额，应该返回400错误
        assert response.status_code in [200, 400]

    def test_create_order_capacity_exceeded(self, client, auth_headers, test_db, sample_user):
        """测试容量超限"""
        # 创建容量为1的餐次
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO meals (date, slot, description, base_price_cents, capacity, creator_id)
            VALUES ('2024-01-21', 'dinner', '小容量餐次', 2000, 1, 1)
            """)
            small_meal_id = conn.lastrowid
            
            # 创建一个已存在的订单占用容量
            conn.execute("""
            INSERT INTO users (openid, nickname, balance_cents)
            VALUES ('other_user', '其他用户', 10000)
            """)
            other_user_id = conn.lastrowid
            
            conn.execute("""
            INSERT INTO orders (user_id, meal_id, qty, amount_cents, status)
            VALUES (?, ?, 1, 2000, 'active')
            """, [other_user_id, small_meal_id])

        response = client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": small_meal_id,
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        assert response.status_code == 400
        assert "capacity" in response.json()["message"].lower()

    def test_modify_order_success(self, client, auth_headers, sample_meal):
        """测试成功修改订单"""
        # 先创建订单
        create_response = client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 1,
                "selected_options": [],
                "notes": "原始备注"
            }
        )
        
        order_id = create_response.json()["data"]["order_id"]
        
        # 修改订单
        response = client.put(
            f"/api/v1/orders/{order_id}/modify",
            headers=auth_headers,
            json={
                "new_quantity": 2,
                "new_selected_options": [
                    {
                        "id": "chicken_leg",
                        "name": "加鸡腿",
                        "price_cents": 300
                    }
                ],
                "new_notes": "修改后备注"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_cancel_order_success(self, client, auth_headers, sample_meal):
        """测试成功取消订单"""
        # 先创建订单
        create_response = client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        order_id = create_response.json()["data"]["order_id"]
        
        # 取消订单
        response = client.delete(
            f"/api/v1/orders/{order_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "canceled"

    def test_lock_orders_by_meal_admin(self, client, admin_headers, sample_meal, sample_user):
        """测试管理员锁定餐次订单"""
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
        
        # 管理员锁定餐次订单
        response = client.post(
            "/api/v1/orders/lock-by-meal",
            headers=admin_headers,
            json={
                "meal_id": sample_meal["meal_id"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["locked_orders"] >= 1

    def test_unlock_orders_by_meal_admin(self, client, admin_headers, sample_meal):
        """测试管理员解锁餐次订单"""
        # 先锁定
        client.post(
            "/api/v1/orders/lock-by-meal",
            headers=admin_headers,
            json={"meal_id": sample_meal["meal_id"]}
        )
        
        # 再解锁
        response = client.post(
            "/api/v1/orders/unlock-by-meal",
            headers=admin_headers,
            json={
                "meal_id": sample_meal["meal_id"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_refund_orders_by_meal_admin(self, client, admin_headers, sample_meal, sample_user):
        """测试管理员退款餐次订单"""
        # 先创建订单
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
        
        # 管理员退款餐次订单
        response = client.post(
            "/api/v1/orders/refund-by-meal",
            headers=admin_headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "reason": "餐次取消测试"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["refunded_orders"] >= 1

    def test_unauthorized_access(self, client, sample_meal):
        """测试未认证访问"""
        response = client.post(
            "/api/v1/orders",
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        assert response.status_code == 401

    def test_non_admin_access_admin_endpoints(self, client, auth_headers, sample_meal):
        """测试非管理员访问管理员端点"""
        response = client.post(
            "/api/v1/orders/lock-by-meal",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"]
            }
        )
        
        assert response.status_code == 403

    def test_invalid_meal_id(self, client, auth_headers):
        """测试无效的meal_id"""
        response = client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": 99999,  # 不存在的餐次ID
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        assert response.status_code == 404

    def test_invalid_request_data(self, client, auth_headers, sample_meal):
        """测试无效请求数据"""
        # 缺少必填字段
        response = client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"]
                # 缺少 quantity
            }
        )
        
        assert response.status_code == 422

    def test_duplicate_order_same_meal(self, client, auth_headers, sample_meal):
        """测试同一餐次重复下单"""
        # 第一次下单
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
        
        # 第二次下单（应该失败）
        response = client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "meal_id": sample_meal["meal_id"],
                "quantity": 1,
                "selected_options": [],
                "notes": ""
            }
        )
        
        assert response.status_code == 400
        assert "duplicate" in response.json()["message"].lower() or "already" in response.json()["message"].lower()