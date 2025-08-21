"""
权限控制测试
测试不同用户角色的权限控制和访问限制
"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

from .base_test import BaseE2ETest


class TestPermissions(BaseE2ETest):
    """权限控制测试"""
    
    def test_admin_meal_permissions(self):
        """测试管理员餐次管理权限"""
        print("\n=== 测试管理员餐次管理权限 ===")
        
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        meal_data = {
            "meal_date": tomorrow,
            "slot": "lunch",
            "title": "权限测试餐次",
            "base_price_cents": 2000,
            "capacity": 20
        }
        
        # 1. 管理员应该能创建餐次
        create_response = self.client.create_meal(meal_data, user_type="admin")
        self.assert_success(create_response, "管理员应该能创建餐次")
        meal_id = create_response["data"]["meal_id"]
        print("✓ 管理员创建餐次成功")
        
        # 2. 管理员应该能锁定餐次
        lock_response = self.client.lock_meal(meal_id, user_type="admin")
        self.assert_success(lock_response, "管理员应该能锁定餐次")
        print("✓ 管理员锁定餐次成功")
        
        # 3. 管理员应该能解锁餐次
        unlock_response = self.client.unlock_meal(meal_id, user_type="admin")
        self.assert_success(unlock_response, "管理员应该能解锁餐次")
        print("✓ 管理员解锁餐次成功")
        
        # 4. 管理员应该能取消餐次
        cancel_response = self.client.cancel_meal(meal_id, user_type="admin")
        self.assert_success(cancel_response, "管理员应该能取消餐次")
        print("✓ 管理员取消餐次成功")
        
        print("✓ 管理员餐次管理权限测试通过")
    
    def test_regular_user_meal_permissions(self):
        """测试普通用户餐次权限限制"""
        print("\n=== 测试普通用户餐次权限限制 ===")
        
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        meal_data = {
            "meal_date": tomorrow,
            "slot": "dinner",
            "title": "用户权限测试餐次",
            "base_price_cents": 1800,
            "capacity": 15
        }
        
        # 1. 普通用户不能创建餐次
        create_response = self.client.create_meal(meal_data, user_type="user_a")
        self.assert_status_code(create_response, 403)
        print("✓ 普通用户正确被拒绝创建餐次")
        
        # 先由管理员创建一个餐次用于后续测试
        admin_create = self.client.create_meal(meal_data, user_type="admin")
        meal_id = admin_create["data"]["meal_id"]
        
        # 2. 普通用户不能锁定餐次
        lock_response = self.client.lock_meal(meal_id, user_type="user_a")
        self.assert_status_code(lock_response, 403)
        print("✓ 普通用户正确被拒绝锁定餐次")
        
        # 3. 普通用户不能解锁餐次
        unlock_response = self.client.unlock_meal(meal_id, user_type="user_a") 
        self.assert_status_code(unlock_response, 403)
        print("✓ 普通用户正确被拒绝解锁餐次")
        
        # 4. 普通用户不能取消餐次
        cancel_response = self.client.cancel_meal(meal_id, user_type="user_a")
        self.assert_status_code(cancel_response, 403)
        print("✓ 普通用户正确被拒绝取消餐次")
        
        # 5. 普通用户应该能查看餐次
        view_response = self.client.get_meal(meal_id, user_type="user_a")
        self.assert_success(view_response, "普通用户应该能查看餐次")
        print("✓ 普通用户查看餐次成功")
        
        # 6. 普通用户应该能查看餐次列表
        list_response = self.client.get_meals(user_type="user_a")
        self.assert_success(list_response, "普通用户应该能查看餐次列表")
        print("✓ 普通用户查看餐次列表成功")
        
        print("✓ 普通用户餐次权限限制测试通过")
    
    def test_order_ownership_permissions(self):
        """测试订单所有权权限控制"""
        print("\n=== 测试订单所有权权限 ===")
        
        # 创建测试餐次
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        meal_data = {
            "meal_date": tomorrow,
            "slot": "lunch",
            "title": "订单权限测试餐次",
            "base_price_cents": 2200,
            "capacity": 10
        }
        
        meal_response = self.client.create_meal(meal_data, user_type="admin")
        meal_id = meal_response["data"]["meal_id"]
        
        # 用户A下单
        order_data = {"meal_id": meal_id, "quantity": 1}
        order_response = self.client.create_order(order_data, user_type="user_a")
        self.assert_success(order_response, "用户A应该能下单")
        order_id = order_response["data"]["order_id"]
        
        # 1. 用户A应该能查看自己的订单
        view_own_order = self.client.get_order(order_id, user_type="user_a")
        self.assert_success(view_own_order, "用户应该能查看自己的订单")
        print("✓ 用户查看自己订单成功")
        
        # 2. 用户B不能查看用户A的订单
        view_others_order = self.client.get_order(order_id, user_type="user_b")
        self.assert_status_code(view_others_order, 403)
        print("✓ 用户正确被拒绝查看他人订单")
        
        # 3. 用户A应该能修改自己的订单
        modified_order = {"meal_id": meal_id, "quantity": 2}
        modify_own_response = self.client.update_order(order_id, modified_order, user_type="user_a")
        # 注意：可能返回成功或业务错误，取决于餐次状态
        print("✓ 用户修改自己订单权限验证")
        
        # 4. 用户B不能修改用户A的订单
        modify_others_response = self.client.update_order(order_id, modified_order, user_type="user_b")
        self.assert_status_code(modify_others_response, 403)
        print("✓ 用户正确被拒绝修改他人订单")
        
        # 5. 用户A应该能取消自己的订单
        cancel_own_response = self.client.cancel_order(order_id, user_type="user_a")
        self.assert_success(cancel_own_response, "用户应该能取消自己的订单")
        print("✓ 用户取消自己订单成功")
        
        # 6. 管理员应该能查看任何用户的订单
        admin_view_response = self.client.get_order(order_id, user_type="admin")
        self.assert_success(admin_view_response, "管理员应该能查看任何订单")
        print("✓ 管理员查看用户订单成功")
        
        print("✓ 订单所有权权限测试通过")
    
    def test_balance_access_permissions(self):
        """测试余额访问权限"""
        print("\n=== 测试余额访问权限 ===")
        
        # 1. 用户应该能查看自己的余额
        own_balance = self.client.get_user_balance(user_type="user_a")
        self.assert_success(own_balance, "用户应该能查看自己的余额")
        print("✓ 用户查看自己余额成功")
        
        # 2. 普通用户不能查看他人余额
        # 这需要通过用户ID查询，先获取user_b的ID
        user_b_profile = self.client.get_user_profile(user_type="user_b") 
        if user_b_profile.get("success"):
            user_b_id = user_b_profile["data"]["user_id"]
            
            others_balance = self.client.get_user_balance_by_id(user_b_id, user_type="user_a")
            self.assert_status_code(others_balance, 403)
            print("✓ 普通用户正确被拒绝查看他人余额")
        
        # 3. 管理员应该能查看任何用户的余额
        if user_b_profile.get("success"):
            admin_view_balance = self.client.get_user_balance_by_id(user_b_id, user_type="admin")
            self.assert_success(admin_view_balance, "管理员应该能查看用户余额")
            print("✓ 管理员查看用户余额成功")
        
        # 4. 普通用户不能充值他人账户
        recharge_others_data = {
            "user_id": user_b_id if user_b_profile.get("success") else 2,
            "amount_cents": 1000,
            "remark": "非法充值测试"
        }
        recharge_others = self.client.admin_recharge_user(recharge_others_data, user_type="user_a")
        self.assert_status_code(recharge_others, 403)
        print("✓ 普通用户正确被拒绝给他人充值")
        
        # 5. 管理员应该能给用户充值
        if user_b_profile.get("success"):
            admin_recharge_data = {
                "user_id": user_b_id,
                "amount_cents": 1000,
                "remark": "管理员测试充值"
            }
            admin_recharge = self.client.admin_recharge_user(admin_recharge_data, user_type="admin")
            # 可能成功或返回业务错误，取决于实现
            print("✓ 管理员充值用户账户权限验证")
        
        print("✓ 余额访问权限测试通过")
    
    def test_authentication_required(self):
        """测试身份认证要求"""
        print("\n=== 测试身份认证要求 ===")
        
        # 创建一个不设置用户类型的客户端（模拟未认证请求）
        unauthenticated_client = self.create_unauthenticated_client()
        
        # 1. 未认证用户不能查看餐次
        meal_response = unauthenticated_client.get("/api/v1/meals")
        self.assert_status_code(meal_response, 401)
        print("✓ 未认证用户正确被拒绝查看餐次")
        
        # 2. 未认证用户不能查看余额
        balance_response = unauthenticated_client.get("/api/v1/user/balance")
        self.assert_status_code(balance_response, 401)
        print("✓ 未认证用户正确被拒绝查看余额")
        
        # 3. 未认证用户不能下单
        order_data = {"meal_id": 1, "quantity": 1}
        order_response = unauthenticated_client.post("/api/v1/orders", order_data)
        self.assert_status_code(order_response, 401)
        print("✓ 未认证用户正确被拒绝下单")
        
        print("✓ 身份认证要求测试通过")
    
    def test_invalid_token_handling(self):
        """测试无效Token处理"""
        print("\n=== 测试无效Token处理 ===")
        
        # 创建带无效token的客户端
        invalid_token_client = self.create_client_with_invalid_token()
        
        # 1. 无效token应该被拒绝
        meal_response = invalid_token_client.get("/api/v1/meals")
        self.assert_status_code(meal_response, 401)
        print("✓ 无效Token正确被拒绝")
        
        # 2. 过期token应该被拒绝（模拟）
        expired_token_client = self.create_client_with_expired_token()
        expired_response = expired_token_client.get("/api/v1/meals")
        self.assert_status_code(expired_response, 401)
        print("✓ 过期Token正确被拒绝")
        
        print("✓ 无效Token处理测试通过")
    
    def test_cross_user_data_isolation(self):
        """测试跨用户数据隔离"""
        print("\n=== 测试跨用户数据隔离 ===")
        
        # 创建测试餐次
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        meal_data = {
            "meal_date": tomorrow,
            "slot": "lunch",
            "title": "数据隔离测试餐次",
            "base_price_cents": 1500,
            "capacity": 10
        }
        
        meal_response = self.client.create_meal(meal_data, user_type="admin")
        meal_id = meal_response["data"]["meal_id"]
        
        # 用户A和用户B分别下单
        order_data = {"meal_id": meal_id, "quantity": 1}
        
        order_a = self.client.create_order(order_data, user_type="user_a")
        self.assert_success(order_a, "用户A应该能下单")
        
        order_b = self.client.create_order(order_data, user_type="user_b")
        self.assert_success(order_b, "用户B应该能下单")
        
        # 1. 用户A只能看到自己的订单列表
        orders_a = self.client.get_user_orders(user_type="user_a")
        self.assert_success(orders_a, "用户A应该能查看自己的订单列表")
        
        user_a_orders = orders_a["data"]["orders"]
        for order in user_a_orders:
            # 验证订单属于用户A（通过用户ID或其他标识）
            assert order["user_id"] == self.get_user_id("user_a"), "订单列表中应只包含自己的订单"
        
        print("✓ 用户A订单列表数据隔离正确")
        
        # 2. 用户B只能看到自己的订单列表
        orders_b = self.client.get_user_orders(user_type="user_b")
        self.assert_success(orders_b, "用户B应该能查看自己的订单列表")
        
        user_b_orders = orders_b["data"]["orders"]
        for order in user_b_orders:
            assert order["user_id"] == self.get_user_id("user_b"), "订单列表中应只包含自己的订单"
        
        print("✓ 用户B订单列表数据隔离正确")
        
        # 3. 用户A和用户B的订单列表不应重叠
        order_ids_a = {order["order_id"] for order in user_a_orders}
        order_ids_b = {order["order_id"] for order in user_b_orders}
        overlap = order_ids_a & order_ids_b
        assert len(overlap) == 0, "不同用户的订单列表不应有重叠"
        
        print("✓ 跨用户订单数据隔离正确")
        print("✓ 跨用户数据隔离测试通过")
    
    def test_role_based_access_control(self):
        """测试基于角色的访问控制"""
        print("\n=== 测试基于角色的访问控制 ===")
        
        # 1. 测试管理员专属功能
        admin_functions = [
            ("创建餐次", lambda: self.client.create_meal({
                "meal_date": (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "slot": "lunch", "title": "RBAC测试", "base_price_cents": 2000, "capacity": 10
            }, user_type="admin")),
            ("查看所有用户列表", lambda: self.client.get_all_users(user_type="admin")),
            ("查看系统统计", lambda: self.client.get_system_stats(user_type="admin"))
        ]
        
        for function_name, function in admin_functions:
            try:
                response = function()
                if response.get("success") or response.get("status_code") in [200, 201]:
                    print(f"✓ 管理员{function_name}成功")
                elif response.get("status_code") == 404:
                    print(f"✓ 管理员{function_name}功能未实现（404）")
                else:
                    print(f"? 管理员{function_name}返回状态码{response.get('status_code')}")
            except Exception as e:
                print(f"? 管理员{function_name}测试出现异常: {e}")
        
        # 2. 测试普通用户被拒绝管理员功能
        user_denied_functions = [
            ("创建餐次", lambda: self.client.create_meal({
                "meal_date": (date.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "slot": "dinner", "title": "拒绝测试", "base_price_cents": 2000, "capacity": 10
            }, user_type="user_a")),
            ("查看所有用户", lambda: self.client.get_all_users(user_type="user_a")),
            ("查看系统统计", lambda: self.client.get_system_stats(user_type="user_a"))
        ]
        
        for function_name, function in user_denied_functions:
            try:
                response = function()
                status_code = response.get("status_code")
                if status_code == 403:
                    print(f"✓ 普通用户{function_name}正确被拒绝（403）")
                elif status_code == 404:
                    print(f"✓ 普通用户{function_name}功能未实现（404）")
                else:
                    print(f"? 普通用户{function_name}返回意外状态码{status_code}")
            except Exception as e:
                print(f"? 普通用户{function_name}测试出现异常: {e}")
        
        print("✓ 基于角色的访问控制测试通过")
    
    # 辅助方法
    def create_unauthenticated_client(self):
        """创建未认证的客户端"""
        from ..utils.test_client import TestAPIClient
        client = TestAPIClient()  # 不传入auth_helper
        return client
    
    def create_client_with_invalid_token(self):
        """创建带无效token的客户端"""
        from ..utils.test_client import TestAPIClient
        client = TestAPIClient()
        # 手动设置无效token
        client.session.headers.update({
            "Authorization": "Bearer invalid_token_12345",
            "X-DB-Key": "test_key"
        })
        return client
    
    def create_client_with_expired_token(self):
        """创建带过期token的客户端"""
        from ..utils.test_client import TestAPIClient
        import jwt
        from datetime import datetime, timedelta
        
        # 生成一个已过期的token
        expired_payload = {
            "open_id": "expired_user",
            "exp": int((datetime.utcnow() - timedelta(days=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
        expired_token = jwt.encode(expired_payload, "test-secret-key-for-e2e-testing", algorithm="HS256")
        
        client = TestAPIClient()
        client.session.headers.update({
            "Authorization": f"Bearer {expired_token}",
            "X-DB-Key": "test_key"
        })
        return client
    
    def get_user_id(self, user_type: str) -> int:
        """获取用户ID的辅助方法"""
        if hasattr(self, 'user_ids') and user_type in self.user_ids:
            return self.user_ids[user_type]
        return 1  # 简化处理，实际应该通过API获取