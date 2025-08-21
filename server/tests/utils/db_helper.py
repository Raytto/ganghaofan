"""
数据库操作辅助工具
提供常用的测试数据操作和验证函数
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date

from .database_manager import TestDatabaseManager
from .config_manager import get_config_manager


class DatabaseHelper:
    """数据库操作辅助类"""
    
    def __init__(self, db_manager: TestDatabaseManager):
        self.db = db_manager
    
    def create_test_user(self, user_config: Dict[str, Any]) -> int:
        """创建测试用户，返回用户ID"""
        try:
            conn = self.db.get_connection()
            
            # 检查用户是否已存在
            existing = conn.execute(
                "SELECT id FROM users WHERE open_id = ?",
                [user_config["openid"]]
            ).fetchone()
            
            if existing:
                return existing[0]
            
            # 创建新用户
            result = conn.execute("""
                INSERT INTO users (open_id, nickname, is_admin, balance_cents)
                VALUES (?, ?, ?, ?)
                RETURNING id
            """, [
                user_config["openid"],
                user_config.get("nickname", ""),
                user_config.get("is_admin", False),
                user_config.get("initial_balance_cents", 0)
            ])
            
            user_id = result.fetchone()[0]
            
            # 如果有初始余额，创建充值记录
            initial_balance = user_config.get("initial_balance_cents", 0)
            if initial_balance > 0:
                conn.execute("""
                    INSERT INTO ledger (user_id, type, amount_cents, ref_type, remark)
                    VALUES (?, 'recharge', ?, 'manual', 'Initial balance for testing')
                """, [user_id, initial_balance])
            
            return user_id
            
        except Exception as e:
            raise RuntimeError(f"Failed to create test user: {e}")
    
    def get_user_by_openid(self, openid: str) -> Optional[Dict[str, Any]]:
        """根据openid获取用户信息"""
        try:
            conn = self.db.get_connection()
            result = conn.execute("""
                SELECT id, open_id, nickname, is_admin, balance_cents, created_at
                FROM users WHERE open_id = ?
            """, [openid]).fetchone()
            
            if result:
                return {
                    "id": result[0],
                    "open_id": result[1],
                    "nickname": result[2],
                    "is_admin": result[3],
                    "balance_cents": result[4],
                    "created_at": result[5]
                }
            return None
            
        except Exception as e:
            raise RuntimeError(f"Failed to get user: {e}")
    
    def get_user_balance(self, user_id: int) -> int:
        """获取用户余额（分为单位）"""
        try:
            conn = self.db.get_connection()
            result = conn.execute(
                "SELECT balance_cents FROM users WHERE id = ?",
                [user_id]
            ).fetchone()
            
            return result[0] if result else 0
            
        except Exception as e:
            raise RuntimeError(f"Failed to get user balance: {e}")
    
    def update_user_balance(self, user_id: int, amount_cents: int, 
                           record_type: str = "adjust", remark: str = "") -> bool:
        """更新用户余额并记录到账本"""
        try:
            conn = self.db.get_connection()
            
            # 更新用户余额
            conn.execute("""
                UPDATE users SET balance_cents = balance_cents + ?
                WHERE id = ?
            """, [amount_cents, user_id])
            
            # 记录到账本
            conn.execute("""
                INSERT INTO ledger (user_id, type, amount_cents, ref_type, remark)
                VALUES (?, ?, ?, 'manual', ?)
            """, [user_id, record_type, amount_cents, remark])
            
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to update user balance: {e}")
    
    def create_test_meal(self, date_str: str, slot: str, title: str, 
                        description: str, base_price_cents: int, 
                        capacity: int = 50, options: List[Dict] = None, 
                        created_by: int = None) -> int:
        """创建测试餐次，返回餐次ID"""
        try:
            conn = self.db.get_connection()
            
            options_json = json.dumps(options) if options else None
            
            result = conn.execute("""
                INSERT INTO meals (date, slot, title, description, base_price_cents, 
                                 options_json, capacity, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'published', ?)
                RETURNING meal_id
            """, [
                date_str, slot, title, description, base_price_cents,
                options_json, capacity, created_by
            ])
            
            return result.fetchone()[0]
            
        except Exception as e:
            raise RuntimeError(f"Failed to create test meal: {e}")
    
    def get_meal_by_id(self, meal_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取餐次信息"""
        try:
            conn = self.db.get_connection()
            result = conn.execute("""
                SELECT meal_id, date, slot, title, description, base_price_cents,
                       options_json, capacity, status, created_by, created_at
                FROM meals WHERE meal_id = ?
            """, [meal_id]).fetchone()
            
            if result:
                options = None
                if result[6]:  # options_json
                    try:
                        options = json.loads(result[6])
                    except json.JSONDecodeError:
                        pass
                
                return {
                    "meal_id": result[0],
                    "date": result[1],
                    "slot": result[2],
                    "title": result[3],
                    "description": result[4],
                    "base_price_cents": result[5],
                    "options": options,
                    "capacity": result[7],
                    "status": result[8],
                    "created_by": result[9],
                    "created_at": result[10]
                }
            return None
            
        except Exception as e:
            raise RuntimeError(f"Failed to get meal: {e}")
    
    def create_test_order(self, user_id: int, meal_id: int, qty: int = 1,
                         selected_options: List[str] = None, 
                         amount_cents: int = None) -> int:
        """创建测试订单，返回订单ID"""
        try:
            conn = self.db.get_connection()
            
            # 如果没有指定金额，计算订单金额
            if amount_cents is None:
                meal = self.get_meal_by_id(meal_id)
                if not meal:
                    raise ValueError(f"Meal not found: {meal_id}")
                
                amount_cents = meal["base_price_cents"] * qty
                
                # 计算选项价格
                if selected_options and meal["options"]:
                    for option_id in selected_options:
                        for option in meal["options"]:
                            if option.get("id") == option_id:
                                amount_cents += option.get("price_cents", 0) * qty
                                break
            
            options_json = json.dumps(selected_options) if selected_options else None
            
            result = conn.execute("""
                INSERT INTO orders (user_id, meal_id, qty, options_json, amount_cents, status)
                VALUES (?, ?, ?, ?, ?, 'active')
                RETURNING order_id
            """, [user_id, meal_id, qty, options_json, amount_cents])
            
            order_id = result.fetchone()[0]
            
            # 扣除用户余额
            conn.execute("""
                UPDATE users SET balance_cents = balance_cents - ?
                WHERE id = ?
            """, [amount_cents, user_id])
            
            # 记录到账本
            conn.execute("""
                INSERT INTO ledger (user_id, type, amount_cents, ref_type, ref_id, remark)
                VALUES (?, 'debit', ?, 'order', ?, 'Order payment')
            """, [user_id, amount_cents, order_id])
            
            return order_id
            
        except Exception as e:
            raise RuntimeError(f"Failed to create test order: {e}")
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取订单信息"""
        try:
            conn = self.db.get_connection()
            result = conn.execute("""
                SELECT order_id, user_id, meal_id, qty, options_json, amount_cents,
                       status, locked_at, created_at, updated_at
                FROM orders WHERE order_id = ?
            """, [order_id]).fetchone()
            
            if result:
                options = None
                if result[4]:  # options_json
                    try:
                        options = json.loads(result[4])
                    except json.JSONDecodeError:
                        pass
                
                return {
                    "order_id": result[0],
                    "user_id": result[1],
                    "meal_id": result[2],
                    "qty": result[3],
                    "options": options,
                    "amount_cents": result[5],
                    "status": result[6],
                    "locked_at": result[7],
                    "created_at": result[8],
                    "updated_at": result[9]
                }
            return None
            
        except Exception as e:
            raise RuntimeError(f"Failed to get order: {e}")
    
    def count_orders_for_meal(self, meal_id: int, status: str = "active") -> int:
        """统计餐次的订单数量"""
        try:
            conn = self.db.get_connection()
            result = conn.execute("""
                SELECT COALESCE(SUM(qty), 0) FROM orders 
                WHERE meal_id = ? AND status = ?
            """, [meal_id, status]).fetchone()
            
            return result[0] if result else 0
            
        except Exception as e:
            raise RuntimeError(f"Failed to count orders: {e}")
    
    def verify_ledger_record(self, user_id: int, record_type: str, 
                           amount_cents: int, ref_id: int = None) -> bool:
        """验证账本记录是否存在"""
        try:
            conn = self.db.get_connection()
            
            sql = """
                SELECT COUNT(*) FROM ledger 
                WHERE user_id = ? AND type = ? AND amount_cents = ?
            """
            params = [user_id, record_type, amount_cents]
            
            if ref_id:
                sql += " AND ref_id = ?"
                params.append(ref_id)
            
            result = conn.execute(sql, params).fetchone()
            return result[0] > 0 if result else False
            
        except Exception as e:
            raise RuntimeError(f"Failed to verify ledger record: {e}")
    
    def get_user_orders(self, user_id: int, status: str = None) -> List[Dict[str, Any]]:
        """获取用户的订单列表"""
        try:
            conn = self.db.get_connection()
            
            sql = """
                SELECT order_id, meal_id, qty, options_json, amount_cents,
                       status, created_at
                FROM orders WHERE user_id = ?
            """
            params = [user_id]
            
            if status:
                sql += " AND status = ?"
                params.append(status)
            
            sql += " ORDER BY created_at DESC"
            
            results = conn.execute(sql, params).fetchall()
            
            orders = []
            for row in results:
                options = None
                if row[3]:  # options_json
                    try:
                        options = json.loads(row[3])
                    except json.JSONDecodeError:
                        pass
                
                orders.append({
                    "order_id": row[0],
                    "meal_id": row[1],
                    "qty": row[2],
                    "options": options,
                    "amount_cents": row[4],
                    "status": row[5],
                    "created_at": row[6]
                })
            
            return orders
            
        except Exception as e:
            raise RuntimeError(f"Failed to get user orders: {e}")
    
    def cancel_order(self, order_id: int, refund: bool = True) -> bool:
        """取消订单并可选择退款"""
        try:
            conn = self.db.get_connection()
            
            # 获取订单信息
            order = self.get_order_by_id(order_id)
            if not order:
                return False
            
            # 更新订单状态
            conn.execute("""
                UPDATE orders SET status = 'canceled', updated_at = now()
                WHERE order_id = ?
            """, [order_id])
            
            # 如果需要退款
            if refund and order["status"] == "active":
                # 退还用户余额
                conn.execute("""
                    UPDATE users SET balance_cents = balance_cents + ?
                    WHERE id = ?
                """, [order["amount_cents"], order["user_id"]])
                
                # 记录退款到账本
                conn.execute("""
                    INSERT INTO ledger (user_id, type, amount_cents, ref_type, ref_id, remark)
                    VALUES (?, 'refund', ?, 'order', ?, 'Order cancellation refund')
                """, [order["user_id"], order["amount_cents"], order_id])
            
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to cancel order: {e}")
    
    def setup_test_users(self) -> Dict[str, int]:
        """设置所有测试用户，返回用户ID映射"""
        try:
            config_mgr = get_config_manager()
            user_ids = {}
            
            for user_type in config_mgr.get_all_user_types():
                user_config = config_mgr.get_user_config(user_type)
                user_id = self.create_test_user(user_config)
                user_ids[user_type] = user_id
                
            print(f"✓ Test users created: {user_ids}")
            return user_ids
            
        except Exception as e:
            raise RuntimeError(f"Failed to setup test users: {e}")


if __name__ == "__main__":
    # 测试数据库辅助工具
    from .database_manager import TestDatabaseManager
    
    try:
        print("Testing database helper...")
        
        with TestDatabaseManager() as db_mgr:
            db_mgr.create_test_database()
            db_mgr.initialize_schema()
            
            helper = DatabaseHelper(db_mgr)
            
            # 测试用户创建
            user_ids = helper.setup_test_users()
            
            # 测试餐次创建
            meal_id = helper.create_test_meal(
                "2024-12-01", "lunch", "测试餐次", "香辣鸡腿饭",
                2000, 50, [{"id": "chicken", "name": "加鸡腿", "price_cents": 300}],
                user_ids["admin"]
            )
            
            # 测试订单创建
            order_id = helper.create_test_order(
                user_ids["user_a"], meal_id, 1, ["chicken"]
            )
            
            # 验证数据
            user_balance = helper.get_user_balance(user_ids["user_a"])
            order_count = helper.count_orders_for_meal(meal_id)
            
            print(f"✓ User balance: {user_balance}")
            print(f"✓ Order count: {order_count}")
            print("✓ Database helper test passed")
            
    except Exception as e:
        print(f"✗ Database helper test failed: {e}")