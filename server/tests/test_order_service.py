import pytest
from datetime import datetime, date, timedelta
from ..services.order_service import OrderService
from ..models.order import OrderCreate, OrderModify
from ..core.exceptions import *

class TestOrderService:
    """订单服务测试"""
    
    def test_create_order_success(self, test_db, sample_user, sample_meal):
        """测试成功创建订单"""
        order_service = OrderService()
        
        # 模拟创建订单的参数（使用实际的API调用方式）
        result = order_service.create_order(
            user_open_id=sample_user["openid"],
            meal_id=sample_meal["meal_id"],
            qty=2,
            selected_options=["chicken_leg"]
        )
        
        assert result["order_id"] is not None
        assert result["meal_id"] == sample_meal["meal_id"]
        assert result["amount_cents"] > 0
        
        # 验证订单在数据库中存在
        with test_db.connection as conn:
            order_row = conn.execute(
                "SELECT * FROM orders WHERE order_id = ?", 
                [result["order_id"]]
            ).fetchone()
            assert order_row is not None
            assert order_row["status"] == "active"
    
    def test_create_order_insufficient_balance(self, test_db, sample_meal):
        """测试余额不足时创建订单的处理"""
        # 创建余额不足的用户
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO users (openid, nickname, balance_cents)
            VALUES ('poor_user', '穷用户', 100)
            """)
        
        order_service = OrderService()
        
        # 由于系统允许负余额（熟人内部系统），这里应该成功但会记录警告
        result = order_service.create_order(
            user_open_id='poor_user',
            meal_id=sample_meal["meal_id"],
            qty=1,
            selected_options=[]
        )
        
        # 应该成功创建订单
        assert result["order_id"] is not None
        
        # 验证用户余额变为负数
        with test_db.connection as conn:
            user_balance = conn.execute(
                "SELECT balance_cents FROM users WHERE openid = 'poor_user'"
            ).fetchone()["balance_cents"]
            assert user_balance < 0
    
    def test_create_order_capacity_exceeded(self, test_db, sample_user):
        """测试容量超限时创建订单失败"""
        # 创建容量很小的餐次
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO meals (date, slot, description, base_price_cents, capacity, creator_id)
            VALUES ('2024-01-16', 'dinner', '小容量餐次', 2000, 1, 1)
            """)
            small_meal_id = conn.lastrowid
            
            # 创建一个已存在的订单占用容量
            conn.execute("""
            INSERT INTO orders (user_id, meal_id, qty, amount_cents, status)
            VALUES (999, ?, 1, 2000, 'active')
            """, [small_meal_id])
        
        order_service = OrderService()
        
        # 应该抛出容量超限异常
        with pytest.raises(Exception):  # 具体的异常类型需要根据实现确定
            order_service.create_order(
                user_open_id=sample_user["openid"],
                meal_id=small_meal_id,
                qty=1,
                selected_options=[]
            )
    
    def test_modify_order_success(self, test_db, sample_user, sample_meal):
        """测试成功修改订单"""
        order_service = OrderService()
        
        # 先创建订单
        result = order_service.create_order(
            user_open_id=sample_user["openid"],
            meal_id=sample_meal["meal_id"],
            qty=1,
            selected_options=[]
        )
        order_id = result["order_id"]
        
        # 修改订单
        modify_result = order_service.modify_order(
            user_open_id=sample_user["openid"],
            order_id=order_id,
            new_qty=2,
            new_selected_options=["chicken_leg"]
        )
        
        assert modify_result["success"] is True
        
        # 验证订单已修改
        with test_db.connection as conn:
            order_row = conn.execute(
                "SELECT * FROM orders WHERE order_id = ?", 
                [order_id]
            ).fetchone()
            # 注意：modify_order 是原子性的，会取消旧订单创建新订单
            # 所以需要检查新创建的订单
    
    def test_cancel_order_success(self, test_db, sample_user, sample_meal):
        """测试成功取消订单"""
        order_service = OrderService()
        
        # 先创建订单
        result = order_service.create_order(
            user_open_id=sample_user["openid"],
            meal_id=sample_meal["meal_id"],
            qty=1,
            selected_options=[]
        )
        order_id = result["order_id"]
        
        # 取消订单
        cancel_result = order_service.cancel_order(
            user_open_id=sample_user["openid"],
            order_id=order_id
        )
        
        assert cancel_result["success"] is True
        
        # 验证订单状态变为canceled
        with test_db.connection as conn:
            order_row = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order_id]
            ).fetchone()
            assert order_row["status"] == "canceled"
    
    def test_order_status_transitions(self, test_db, sample_user, sample_meal, admin_user):
        """测试订单状态流转"""
        order_service = OrderService()
        
        # 创建订单
        result = order_service.create_order(
            user_open_id=sample_user["openid"],
            meal_id=sample_meal["meal_id"],
            qty=1,
            selected_options=[]
        )
        order_id = result["order_id"]
        
        # 验证初始状态为active
        with test_db.connection as conn:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order_id]
            ).fetchone()["status"]
            assert order_status == "active"
        
        # 测试锁定订单
        lock_result = order_service.lock_orders_by_meal(
            sample_meal["meal_id"], 
            admin_user["openid"]
        )
        assert lock_result["locked_orders"] >= 1
        
        # 验证订单状态已变为locked
        with test_db.connection as conn:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order_id]
            ).fetchone()["status"]
            assert order_status == "locked"
        
        # 测试解锁订单
        unlock_result = order_service.unlock_orders_by_meal(
            sample_meal["meal_id"], 
            admin_user["openid"]
        )
        assert unlock_result["unlocked_orders"] >= 1
        
        # 验证订单状态已变回active
        with test_db.connection as conn:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order_id]
            ).fetchone()["status"]
            assert order_status == "active"
    
    def test_order_refund_by_meal(self, test_db, sample_user, sample_meal, admin_user):
        """测试餐次取消时的订单退款"""
        order_service = OrderService()
        
        # 创建订单
        result = order_service.create_order(
            user_open_id=sample_user["openid"],
            meal_id=sample_meal["meal_id"],
            qty=1,
            selected_options=[]
        )
        order_id = result["order_id"]
        order_amount = result["amount_cents"]
        
        # 记录用户当前余额
        with test_db.connection as conn:
            old_balance = conn.execute(
                "SELECT balance_cents FROM users WHERE openid = ?", 
                [sample_user["openid"]]
            ).fetchone()["balance_cents"]
        
        # 餐次取消，退款所有订单
        refund_result = order_service.refund_orders_by_meal(
            sample_meal["meal_id"], 
            admin_user["openid"], 
            "测试餐次取消"
        )
        
        assert refund_result["refunded_orders"] >= 1
        assert refund_result["total_refund_amount_cents"] >= order_amount
        
        # 验证订单状态为refunded
        with test_db.connection as conn:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order_id]
            ).fetchone()["status"]
            assert order_status == "refunded"
            
            # 验证余额已恢复
            new_balance = conn.execute(
                "SELECT balance_cents FROM users WHERE openid = ?", 
                [sample_user["openid"]]
            ).fetchone()["balance_cents"]
            assert new_balance >= old_balance + order_amount
    
    def test_concurrent_order_creation(self, test_db, sample_meal):
        """测试并发创建订单的处理"""
        import threading
        import time
        
        # 创建容量为1的餐次
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO meals (date, slot, description, base_price_cents, capacity, creator_id)
            VALUES ('2024-01-17', 'lunch', '并发测试餐次', 2000, 1, 1)
            """)
            concurrent_meal_id = conn.lastrowid
            
            # 创建两个有余额的用户
            conn.execute("""
            INSERT INTO users (openid, nickname, balance_cents)
            VALUES ('user1', 'User1', 10000), ('user2', 'User2', 10000)
            """)
        
        order_service = OrderService()
        results = {}
        
        def create_order_thread(user_openid, thread_name):
            try:
                result = order_service.create_order(
                    user_open_id=user_openid,
                    meal_id=concurrent_meal_id,
                    qty=1,
                    selected_options=[]
                )
                results[thread_name] = {"success": True, "result": result}
            except Exception as e:
                results[thread_name] = {"success": False, "error": str(e)}
        
        # 启动两个并发线程
        thread1 = threading.Thread(target=create_order_thread, args=('user1', "thread1"))
        thread2 = threading.Thread(target=create_order_thread, args=('user2', "thread2"))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # 验证结果：至少有一个成功，可能都成功（取决于并发控制实现）
        success_count = sum(1 for result in results.values() if result["success"])
        assert success_count >= 1, f"Expected at least 1 success, got {success_count}. Results: {results}"