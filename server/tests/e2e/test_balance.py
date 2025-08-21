"""
余额管理测试
测试用户余额充值、扣除、退款等操作
"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

from .base_test import BaseE2ETest


class TestBalance(BaseE2ETest):
    """余额管理测试"""
    
    def test_user_balance_query(self):
        """测试用户余额查询"""
        print("\n=== 测试用户余额查询 ===")
        
        # 测试各种用户的余额查询
        test_users = ["user_a", "user_b", "rich_user", "admin"]
        
        for user in test_users:
            balance_response = self.client.get_user_balance(user_type=user)
            self.assert_success(balance_response, f"应该能查询{user}的余额")
            
            balance_data = balance_response["data"]
            self.assert_response_data(balance_response, ["balance_cents", "user_id"])
            
            # 验证余额为正数
            balance_cents = balance_data["balance_cents"]
            assert balance_cents >= 0, f"{user}的余额不能为负数"
            
            print(f"✓ {user}余额查询成功: {balance_cents/100}元")
        
        print("✓ 用户余额查询测试通过")
    
    def test_balance_recharge(self):
        """测试余额充值"""
        print("\n=== 测试余额充值 ===")
        
        # 获取充值前余额
        initial_response = self.client.get_user_balance(user_type="user_a")
        initial_balance = initial_response["data"]["balance_cents"]
        
        # 充值操作
        recharge_amount = 5000  # 充值50元
        recharge_data = {
            "amount_cents": recharge_amount,
            "payment_method": "alipay",
            "remark": "测试充值"
        }
        
        recharge_response = self.client.recharge_balance(recharge_data, user_type="user_a")
        self.assert_success(recharge_response, "充值操作应该成功")
        
        # 验证充值结果
        transaction_id = recharge_response["data"]["transaction_id"]
        new_balance = recharge_response["data"]["new_balance_cents"]
        expected_balance = initial_balance + recharge_amount
        
        assert new_balance == expected_balance, f"充值后余额应为{expected_balance}分，实际为{new_balance}分"
        print(f"✓ 充值成功，交易ID: {transaction_id}, 新余额: {new_balance/100}元")
        
        # 再次查询验证余额
        verify_response = self.client.get_user_balance(user_type="user_a")
        verify_balance = verify_response["data"]["balance_cents"]
        assert verify_balance == new_balance, "余额查询结果应与充值后余额一致"
        
        print("✓ 余额充值测试通过")
    
    def test_balance_transaction_history(self):
        """测试余额交易记录"""
        print("\n=== 测试余额交易记录 ===")
        
        # 执行一些交易操作来产生记录
        user = "user_b"
        
        # 1. 充值操作
        recharge_data = {"amount_cents": 3000, "payment_method": "wechat", "remark": "测试充值"}
        recharge_response = self.client.recharge_balance(recharge_data, user_type=user)
        self.assert_success(recharge_response, "充值应该成功")
        
        # 2. 创建餐次并下单（产生扣费记录）
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        meal_data = {
            "meal_date": tomorrow,
            "slot": "lunch",
            "title": "交易测试餐",
            "base_price_cents": 1500,
            "capacity": 10
        }
        
        meal_response = self.client.create_meal(meal_data, user_type="admin")
        meal_id = meal_response["data"]["meal_id"]
        
        order_data = {"meal_id": meal_id, "quantity": 1}
        order_response = self.client.create_order(order_data, user_type=user)
        self.assert_success(order_response, "下单应该成功")
        order_id = order_response["data"]["order_id"]
        
        # 3. 取消订单（产生退款记录）
        cancel_response = self.client.cancel_order(order_id, user_type=user)
        self.assert_success(cancel_response, "取消订单应该成功")
        
        # 4. 查询交易记录
        history_response = self.client.get_balance_history(user_type=user)
        self.assert_success(history_response, "应该能获取交易记录")
        
        transactions = history_response["data"]["transactions"]
        assert len(transactions) >= 3, "应该至少有3条交易记录（充值、扣费、退款）"
        
        # 验证交易记录包含必要字段
        for transaction in transactions:
            required_fields = ["transaction_id", "type", "amount_cents", "created_at", "remark"]
            for field in required_fields:
                assert field in transaction, f"交易记录应包含{field}字段"
            
            # 验证交易类型
            assert transaction["type"] in ["recharge", "debit", "refund"], "交易类型应为recharge/debit/refund之一"
        
        print(f"✓ 交易记录查询成功，共{len(transactions)}条记录")
        print("✓ 余额交易记录测试通过")
    
    def test_admin_balance_management(self):
        """测试管理员余额管理功能"""
        print("\n=== 测试管理员余额管理 ===")
        
        target_user = "user_a"
        
        # 获取目标用户当前余额
        initial_response = self.client.get_user_balance(user_type=target_user)
        initial_balance = initial_response["data"]["balance_cents"]
        
        # 1. 管理员给用户调整余额（增加余额）
        adjust_amount = 2000  # 增加20元
        adjust_data = {
            "user_id": self.get_user_id(target_user),
            "amount_cents": adjust_amount,
            "type": "adjust",
            "remark": "管理员调整余额测试"
        }
        
        adjust_response = self.client.admin_adjust_balance(adjust_data, user_type="admin")
        self.assert_success(adjust_response, "管理员应该能调整用户余额")
        
        # 验证调整结果
        after_adjust_response = self.client.get_user_balance(user_type=target_user)
        new_balance = after_adjust_response["data"]["balance_cents"]
        expected_balance = initial_balance + adjust_amount
        
        assert new_balance == expected_balance, f"调整后余额应为{expected_balance}分"
        print(f"✓ 管理员增加余额成功，新余额: {new_balance/100}元")
        
        # 2. 管理员减少用户余额
        reduce_amount = -500  # 减少5元
        reduce_data = {
            "user_id": self.get_user_id(target_user),
            "amount_cents": reduce_amount,
            "type": "adjust", 
            "remark": "管理员减少余额测试"
        }
        
        reduce_response = self.client.admin_adjust_balance(reduce_data, user_type="admin")
        self.assert_success(reduce_response, "管理员应该能减少用户余额")
        
        final_response = self.client.get_user_balance(user_type=target_user)
        final_balance = final_response["data"]["balance_cents"]
        expected_final = new_balance + reduce_amount
        
        assert final_balance == expected_final, f"最终余额应为{expected_final}分"
        print(f"✓ 管理员减少余额成功，最终余额: {final_balance/100}元")
        
        # 3. 测试非管理员用户无法调整余额
        unauthorized_response = self.client.admin_adjust_balance(adjust_data, user_type="user_a")
        self.assert_status_code(unauthorized_response, 403)
        print("✓ 非管理员用户正确被拒绝调整余额")
        
        print("✓ 管理员余额管理测试通过")
    
    def test_balance_edge_cases(self):
        """测试余额边界情况"""
        print("\n=== 测试余额边界情况 ===")
        
        # 1. 测试充值金额验证
        invalid_amounts = [-1000, 0, 1000000000]  # 负数、零、过大金额
        
        for amount in invalid_amounts:
            recharge_data = {"amount_cents": amount, "payment_method": "alipay"}
            response = self.client.recharge_balance(recharge_data, user_type="user_a")
            self.assert_status_code(response, 400)
            print(f"✓ 无效充值金额{amount}分正确被拒绝")
        
        # 2. 测试余额不足时的下单
        # 创建高价餐次
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        expensive_meal = {
            "meal_date": tomorrow,
            "slot": "dinner",
            "title": "昂贵套餐",
            "base_price_cents": 50000,  # 500元
            "capacity": 5
        }
        
        meal_response = self.client.create_meal(expensive_meal, user_type="admin")
        meal_id = meal_response["data"]["meal_id"]
        
        # 用余额不足的用户下单
        order_data = {"meal_id": meal_id, "quantity": 1}
        order_response = self.client.create_order(order_data, user_type="user_a")
        self.assert_status_code(order_response, 400)
        print("✓ 余额不足时下单正确被拒绝")
        
        # 3. 测试查询不存在用户的余额
        invalid_balance_response = self.client.get_user_balance_by_id(99999, user_type="admin")
        self.assert_status_code(invalid_balance_response, 404)
        print("✓ 查询不存在用户余额正确返回404")
        
        print("✓ 余额边界情况测试通过")
    
    def test_concurrent_balance_operations(self):
        """测试并发余额操作（简化版）"""
        print("\n=== 测试并发余额操作 ===")
        
        # 注意：这是简化的并发测试，实际并发需要更复杂的设置
        user = "rich_user"
        
        # 获取初始余额
        initial_response = self.client.get_user_balance(user_type=user)
        initial_balance = initial_response["data"]["balance_cents"]
        
        # 创建测试餐次
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        meal_data = {
            "meal_date": tomorrow,
            "slot": "lunch", 
            "title": "并发测试餐",
            "base_price_cents": 1000,
            "capacity": 10
        }
        
        meal_response = self.client.create_meal(meal_data, user_type="admin")
        meal_id = meal_response["data"]["meal_id"]
        
        # 模拟快速连续下单操作
        order_responses = []
        for i in range(3):
            order_data = {"meal_id": meal_id, "quantity": 1}
            response = self.client.create_order(order_data, user_type=user)
            order_responses.append(response)
        
        # 统计成功订单数
        successful_orders = [r for r in order_responses if r.get("success")]
        
        # 验证余额扣除的一致性
        final_response = self.client.get_user_balance(user_type=user)
        final_balance = final_response["data"]["balance_cents"]
        expected_deduction = len(successful_orders) * 1000
        expected_balance = initial_balance - expected_deduction
        
        assert final_balance == expected_balance, f"余额扣除不一致：期望{expected_balance}分，实际{final_balance}分"
        print(f"✓ 并发操作后余额一致性验证通过，成功订单{len(successful_orders)}个")
        
        print("✓ 并发余额操作测试通过")
    
    def get_user_id(self, user_type: str) -> int:
        """获取用户ID的辅助方法"""
        if hasattr(self, 'user_ids') and user_type in self.user_ids:
            return self.user_ids[user_type]
        
        # 如果没有缓存，通过API获取
        profile_response = self.client.get_user_profile(user_type=user_type)
        if profile_response.get("success"):
            user_id = profile_response["data"]["user_id"]
            if not hasattr(self, 'user_ids'):
                self.user_ids = {}
            self.user_ids[user_type] = user_id
            return user_id
        
        raise ValueError(f"Cannot get user_id for {user_type}")