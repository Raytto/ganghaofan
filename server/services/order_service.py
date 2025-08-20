"""
订单服务模块
提供订单相关的核心业务逻辑，包括创建、修改、取消和查询功能

主要功能：
- 订单创建和验证
- 订单修改（取消旧订单+创建新订单）
- 订单取消和退款处理
- 库存和容量控制
- 余额操作和账单记录

业务规则：
- 每用户每餐只能下一单
- 订单数量固定为1
- 即时扣费模式
- 原子性事务保证数据一致性
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from ..core.database import db_manager
from ..core.exceptions import BaseApplicationError


class OrderServiceError(BaseApplicationError):
    """订单服务相关异常"""
    pass


class OrderNotFoundError(OrderServiceError):
    """订单不存在"""
    def __init__(self):
        super().__init__("ORDER_NOT_FOUND", "订单不存在")


class MealNotFoundError(OrderServiceError):
    """餐次不存在"""
    def __init__(self):
        super().__init__("MEAL_NOT_FOUND", "餐次不存在")


class MealNotAvailableError(OrderServiceError):
    """餐次不可下单"""
    def __init__(self, status: str):
        super().__init__("MEAL_NOT_AVAILABLE", f"餐次状态为{status}，无法下单")


class InvalidQuantityError(OrderServiceError):
    """订单数量无效"""
    def __init__(self):
        super().__init__("INVALID_QUANTITY", "订单数量必须为1")


class DuplicateOrderError(OrderServiceError):
    """重复下单"""
    def __init__(self):
        super().__init__("DUPLICATE_ORDER", "您已在此餐次下单")


class CapacityExceededError(OrderServiceError):
    """超过容量限制"""
    def __init__(self):
        super().__init__("CAPACITY_EXCEEDED", "餐次容量已满")


class OrderNotActiveError(OrderServiceError):
    """订单非活跃状态"""
    def __init__(self):
        super().__init__("ORDER_NOT_ACTIVE", "订单不在活跃状态")


class MealLockedError(OrderServiceError):
    """餐次已锁定"""
    def __init__(self):
        super().__init__("MEAL_LOCKED", "餐次已锁定，无法修改订单")


class OrderService:
    """订单服务类，封装所有订单相关的业务逻辑"""
    
    def __init__(self):
        self.db = db_manager
    
    def create_order(self, user_open_id: str, meal_id: int, qty: int, 
                    selected_options: List[str]) -> Dict[str, Any]:
        """
        创建新订单
        
        Args:
            user_open_id: 用户微信openid
            meal_id: 餐次ID
            qty: 订单数量（必须为1）
            selected_options: 选择的配菜选项ID列表
            
        Returns:
            dict: 包含order_id、金额和余额的订单信息
            
        Raises:
            InvalidQuantityError: 数量不为1时
            MealNotFoundError: 餐次不存在时
            MealNotAvailableError: 餐次不可下单时
            DuplicateOrderError: 用户已下单时
            CapacityExceededError: 超过容量限制时
        """
        if qty != 1:
            raise InvalidQuantityError()
        
        con = self.db.get_connection()
        
        # 获取或创建用户
        user_id = self._get_or_create_user(con, user_open_id)
        
        # 验证餐次
        meal_info = self._get_meal_info(con, meal_id)
        if meal_info['status'] != 'published':
            raise MealNotAvailableError(meal_info['status'])
        
        # 检查重复订单
        if self._has_active_order(con, user_id, meal_id):
            raise DuplicateOrderError()
        
        # 检查容量
        if self._check_capacity_exceeded(con, meal_id, qty, meal_info['capacity']):
            raise CapacityExceededError()
        
        # 计算金额
        amount_cents, selected_option_details = self._calculate_order_amount(
            meal_info, qty, selected_options)
        
        # 获取用户余额
        balance_before = self._get_user_balance(con, user_id)
        
        # 执行事务
        return self._execute_create_order_transaction(
            con, user_id, meal_id, qty, selected_options, amount_cents,
            selected_option_details, balance_before, meal_info)
    
    def update_order(self, user_open_id: str, order_id: int, qty: int,
                    selected_options: List[str]) -> Dict[str, Any]:
        """
        修改订单（通过取消旧订单+创建新订单实现）
        
        Args:
            user_open_id: 用户微信openid  
            order_id: 要修改的订单ID
            qty: 新的订单数量
            selected_options: 新的配菜选项
            
        Returns:
            dict: 新订单的信息
            
        Raises:
            OrderNotFoundError: 订单不存在时
            MealLockedError: 餐次已锁定时
            OrderNotActiveError: 订单非活跃状态时
        """
        con = self.db.get_connection()
        
        # 验证订单
        order_info = self._get_order_info(con, order_id)
        if not order_info:
            raise OrderNotFoundError()
        
        user_id, meal_id, status = order_info
        
        # 验证餐次状态
        meal_status = self._get_meal_status(con, meal_id)
        if meal_status != 'published':
            raise MealLockedError()
        
        # 取消旧订单
        self._cancel_order_internal(con, order_id, user_id, meal_id)
        
        # 记录修改日志
        self._log_order_modify(con, user_id, order_id)
        
        # 创建新订单
        return self.create_order(user_open_id, meal_id, qty, selected_options)
    
    def cancel_order(self, user_open_id: str, order_id: int) -> Dict[str, Any]:
        """
        取消订单并退款
        
        Args:
            user_open_id: 用户微信openid
            order_id: 要取消的订单ID
            
        Returns:
            dict: 包含取消结果和余额的信息
            
        Raises:
            OrderNotFoundError: 订单不存在或非活跃状态时
            MealLockedError: 餐次已锁定时
        """
        con = self.db.get_connection()
        
        # 获取订单信息
        row = con.execute(
            "SELECT user_id, meal_id, amount_cents, options_json FROM orders WHERE order_id=? AND status='active'",
            [order_id]
        ).fetchone()
        
        if not row:
            raise OrderNotFoundError()
        
        user_id, meal_id, amount_cents, options_json = row
        
        # 检查餐次状态
        meal_status = self._get_meal_status(con, meal_id)
        if meal_status != 'published':
            raise MealLockedError()
        
        # 获取余额
        balance_before = self._get_user_balance(con, user_id)
        
        # 执行取消事务
        return self._execute_cancel_order_transaction(
            con, order_id, user_id, meal_id, amount_cents, options_json, balance_before)
    
    def _get_or_create_user(self, con, open_id: str) -> int:
        """获取或创建用户，返回用户ID"""
        urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        if not urow:
            con.execute("INSERT INTO users(open_id) VALUES (?)", [open_id])
            urow = con.execute("SELECT id FROM users WHERE open_id=?", [open_id]).fetchone()
        return urow[0]
    
    def _get_meal_info(self, con, meal_id: int) -> Dict[str, Any]:
        """获取餐次信息"""
        row = con.execute(
            "SELECT meal_id, base_price_cents, options_json, capacity, per_user_limit, status FROM meals WHERE meal_id=?",
            [meal_id]
        ).fetchone()
        
        if not row:
            raise MealNotFoundError()
        
        return {
            'meal_id': row[0],
            'base_price_cents': row[1],
            'options_json': row[2],
            'capacity': row[3],
            'per_user_limit': row[4],
            'status': row[5]
        }
    
    def _has_active_order(self, con, user_id: int, meal_id: int) -> bool:
        """检查用户是否已在该餐次下单"""
        existing = con.execute(
            "SELECT 1 FROM orders WHERE user_id=? AND meal_id=? AND status='active'",
            [user_id, meal_id]
        ).fetchone()
        return existing is not None
    
    def _check_capacity_exceeded(self, con, meal_id: int, qty: int, capacity: int) -> bool:
        """检查容量是否超限"""
        total_qty = con.execute(
            "SELECT COALESCE(SUM(qty),0) FROM orders WHERE meal_id=? AND status='active'",
            [meal_id]
        ).fetchone()[0]
        return total_qty + qty > capacity
    
    def _calculate_order_amount(self, meal_info: Dict, qty: int, 
                              selected_options: List[str]) -> Tuple[int, List[Dict]]:
        """计算订单金额和选项详情"""
        base_price = meal_info['base_price_cents']
        options_total = 0
        selected_option_details = []
        
        try:
            meal_opts = json.loads(meal_info['options_json']) if isinstance(meal_info['options_json'], str) else (meal_info['options_json'] or [])
            opt_by_id = {}
            
            for o in meal_opts or []:
                oid = (o.get("id") if isinstance(o, dict) else None) or None
                if oid:
                    opt_by_id[str(oid)] = o
            
            for sid in selected_options or []:
                so = opt_by_id.get(str(sid))
                if so:
                    price_cents = so.get("price_cents", 0)
                    options_total += price_cents
                    selected_option_details.append({
                        "id": so.get("id"),
                        "name": so.get("name"),
                        "price_cents": price_cents,
                    })
        except Exception:
            selected_option_details = []
        
        amount_cents = base_price * qty + options_total
        return amount_cents, selected_option_details
    
    def _get_user_balance(self, con, user_id: int) -> int:
        """获取用户余额"""
        bal_row = con.execute("SELECT balance_cents FROM users WHERE id=?", [user_id]).fetchone()
        return bal_row[0] if bal_row else 0
    
    def _execute_create_order_transaction(self, con, user_id: int, meal_id: int, 
                                        qty: int, selected_options: List[str],
                                        amount_cents: int, selected_option_details: List[Dict],
                                        balance_before: int, meal_info: Dict) -> Dict[str, Any]:
        """执行创建订单的事务"""
        con.execute("BEGIN")
        try:
            # 插入订单
            order = con.execute(
                "INSERT INTO orders(user_id, meal_id, qty, options_json, amount_cents, status) VALUES (?,?,?,?,?,?) RETURNING order_id",
                [user_id, meal_id, qty, json.dumps(selected_options), amount_cents, "active"],
            ).fetchone()
            order_id = order[0]
            
            # 扣费和记录账单
            con.execute(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [user_id, "debit", amount_cents, "order", order_id, "order create debit"],
            )
            con.execute(
                "UPDATE users SET balance_cents = balance_cents - ? WHERE id=?",
                [amount_cents, user_id],
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        
        # 记录日志
        self._log_order_create(con, user_id, meal_id, selected_option_details, 
                              amount_cents, balance_before, meal_info)
        
        # 获取最新余额
        balance_after = self._get_user_balance(con, user_id)
        
        return {
            "order_id": order_id,
            "amount_cents": amount_cents,
            "balance_cents": balance_after
        }
    
    def _get_order_info(self, con, order_id: int) -> Optional[Tuple[int, int, str]]:
        """获取订单基本信息"""
        row = con.execute(
            "SELECT user_id, meal_id, status FROM orders WHERE order_id=?", [order_id]
        ).fetchone()
        return row if row else None
    
    def _get_meal_status(self, con, meal_id: int) -> str:
        """获取餐次状态"""
        row = con.execute("SELECT status FROM meals WHERE meal_id=?", [meal_id]).fetchone()
        return row[0] if row else ""
    
    def _cancel_order_internal(self, con, order_id: int, user_id: int, meal_id: int):
        """内部取消订单逻辑（不包含日志记录）"""
        amt_row = con.execute(
            "SELECT amount_cents FROM orders WHERE order_id=? AND status='active'",
            [order_id],
        ).fetchone()
        
        if not amt_row:
            raise OrderNotActiveError()
        
        old_amount = amt_row[0]
        
        con.execute("BEGIN")
        try:
            con.execute(
                "UPDATE orders SET status='canceled', updated_at=now() WHERE order_id=?",
                [order_id],
            )
            con.execute(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [user_id, "refund", old_amount, "order", order_id, "order update refund"],
            )
            con.execute(
                "UPDATE users SET balance_cents = balance_cents + ? WHERE id=?",
                [old_amount, user_id],
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    
    def _execute_cancel_order_transaction(self, con, order_id: int, user_id: int,
                                        meal_id: int, amount_cents: int, 
                                        options_json: str, balance_before: int) -> Dict[str, Any]:
        """执行取消订单的事务"""
        con.execute("BEGIN")
        try:
            con.execute(
                "UPDATE orders SET status='canceled', updated_at=now() WHERE order_id=?",
                [order_id],
            )
            con.execute(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [user_id, "refund", amount_cents, "order", order_id, "order cancel refund"],
            )
            con.execute(
                "UPDATE users SET balance_cents = balance_cents + ? WHERE id=?",
                [amount_cents, user_id],
            )
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        
        # 记录取消日志
        self._log_order_cancel(con, user_id, order_id, meal_id, amount_cents, 
                              options_json, balance_before)
        
        # 获取最新余额
        balance_after = self._get_user_balance(con, user_id)
        
        return {
            "order_id": order_id,
            "balance_cents": balance_after,
            "status": "canceled"
        }
    
    def _log_order_create(self, con, user_id: int, meal_id: int, 
                         selected_options: List[Dict], amount_cents: int,
                         balance_before: int, meal_info: Dict):
        """记录订单创建日志"""
        meal_row = con.execute(
            "SELECT date, slot, title FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        
        balance_after = self._get_user_balance(con, user_id)
        
        log_detail = {
            "meal_id": meal_id,
            "date": str(meal_row[0]) if meal_row else None,
            "slot": meal_row[1] if meal_row else None,
            "title": meal_row[2] if meal_row else None,
            "selected_options": selected_options,
            "amount_cents": amount_cents,
            "balance_before_cents": balance_before,
            "balance_after_cents": balance_after,
        }
        
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [user_id, user_id, "order_create", json.dumps(log_detail)],
        )
    
    def _log_order_modify(self, con, user_id: int, order_id: int):
        """记录订单修改日志"""
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [user_id, user_id, "order_modify", json.dumps({"order_id": order_id})],
        )
    
    def _log_order_cancel(self, con, user_id: int, order_id: int, meal_id: int,
                         amount_cents: int, options_json: str, balance_before: int):
        """记录订单取消日志"""
        # 构建选项详情
        selected_options = []
        try:
            sel_ids = json.loads(options_json) if isinstance(options_json, str) else (options_json or [])
            meal_row = con.execute(
                "SELECT options_json FROM meals WHERE meal_id=?", [meal_id]
            ).fetchone()
            
            if meal_row:
                meal_opts = json.loads(meal_row[0]) if isinstance(meal_row[0], str) else (meal_row[0] or [])
                opt_by_id = {}
                
                for o in meal_opts or []:
                    oid = (o.get("id") if isinstance(o, dict) else None) or None
                    if oid:
                        opt_by_id[str(oid)] = o
                
                if isinstance(sel_ids, list):
                    for sid in sel_ids:
                        so = opt_by_id.get(str(sid))
                        if so:
                            selected_options.append({
                                "id": so.get("id"),
                                "name": so.get("name"),
                                "price_cents": so.get("price_cents"),
                            })
        except Exception:
            selected_options = []
        
        # 获取餐次信息
        meal_row = con.execute(
            "SELECT date, slot, title FROM meals WHERE meal_id=?", [meal_id]
        ).fetchone()
        
        balance_after = self._get_user_balance(con, user_id)
        
        log_detail = {
            "order_id": order_id,
            "meal_id": meal_id,
            "date": str(meal_row[0]) if meal_row else None,
            "slot": meal_row[1] if meal_row else None,
            "title": meal_row[2] if meal_row else None,
            "amount_cents": amount_cents,
            "selected_options": selected_options,
            "balance_before_cents": balance_before,
            "balance_after_cents": balance_after,
        }
        
        con.execute(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [user_id, user_id, "order_cancel", json.dumps(log_detail)],
        )


# 全局服务实例
order_service = OrderService()