"""
订单管理路由模块
重构自原 routers/orders.py，使用新的架构
"""

from fastapi import APIRouter, Depends, HTTPException

from ...schemas.order import (
    OrderCreateRequest,
    OrderUpdateRequest,
    OrderResponse,
    OrderDetailResponse,
    OrderCancelResponse
)
from ...core.security import get_open_id
from ...core.database import db_manager
from ...core.exceptions import (
    DatabaseError, 
    ValidationError, 
    OrderNotFoundError,
    MealNotFoundError,
    CapacityExceededError,
    DuplicateOrderError,
    InsufficientBalanceError
)

router = APIRouter()


@router.post("/orders", response_model=OrderResponse)
def create_order(req: OrderCreateRequest, open_id: str = Depends(get_open_id)):
    """创建订单"""
    try:
        # 获取用户ID
        user_row = db_manager.execute_one(
            "SELECT id FROM users WHERE open_id=?", 
            [open_id]
        )
        if not user_row:
            raise ValidationError("用户不存在")
        
        user_id = user_row[0]
        
        # 获取餐次信息
        meal_row = db_manager.execute_one(
            "SELECT meal_id, base_price_cents, options_json, capacity, per_user_limit, status FROM meals WHERE meal_id=?",
            [req.meal_id]
        )
        if not meal_row:
            raise MealNotFoundError("餐次不存在")
        
        if meal_row[5] != "published":
            raise ValidationError("餐次未开放订餐")
        
        # 检查是否已有订单
        existing = db_manager.execute_one(
            "SELECT 1 FROM orders WHERE user_id=? AND meal_id=? AND status='active'",
            [user_id, req.meal_id]
        )
        if existing:
            raise DuplicateOrderError("已存在有效订单")
        
        # 检查容量
        total_qty = db_manager.execute_one(
            "SELECT COALESCE(SUM(qty),0) FROM orders WHERE meal_id=? AND status='active'",
            [req.meal_id]
        )[0]
        
        if total_qty + req.qty > meal_row[3]:
            raise CapacityExceededError("容量不足")
        
        # 计算金额（简化版，不考虑配菜）
        amount = meal_row[1] * req.qty
        
        # 检查余额
        balance_row = db_manager.execute_one(
            "SELECT balance_cents FROM users WHERE id=?",
            [user_id]
        )
        balance = balance_row[0] if balance_row else 0
        
        if balance < amount:
            raise InsufficientBalanceError("余额不足")
        
        # 使用事务创建订单
        db_manager.begin_transaction()
        try:
            # 创建订单
            order_row = db_manager.execute_one(
                "INSERT INTO orders(user_id, meal_id, qty, options_json, amount_cents, status) VALUES (?,?,?,?,?,?) RETURNING order_id",
                [user_id, req.meal_id, req.qty, str(req.options), amount, "active"]
            )
            order_id = order_row[0]
            
            # 扣费
            db_manager.execute_query(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [user_id, "debit", amount, "order", order_id, "订单扣费"]
            )
            
            # 更新余额
            db_manager.execute_query(
                "UPDATE users SET balance_cents = balance_cents - ? WHERE id=?",
                [amount, user_id]
            )
            
            db_manager.commit_transaction()
            
            # 获取最新余额
            new_balance = db_manager.execute_one(
                "SELECT balance_cents FROM users WHERE id=?",
                [user_id]
            )[0]
            
            return OrderResponse(
                order_id=order_id,
                amount_cents=amount,
                balance_cents=new_balance
            )
            
        except Exception:
            db_manager.rollback_transaction()
            raise
            
    except (ValidationError, MealNotFoundError, DuplicateOrderError, 
            CapacityExceededError, InsufficientBalanceError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")


@router.delete("/orders/{order_id}", response_model=OrderCancelResponse)
def cancel_order(order_id: int, open_id: str = Depends(get_open_id)):
    """取消订单"""
    try:
        # 获取订单信息
        order_row = db_manager.execute_one(
            "SELECT user_id, meal_id, amount_cents FROM orders WHERE order_id=? AND status='active'",
            [order_id]
        )
        if not order_row:
            raise OrderNotFoundError("订单不存在或已取消")
        
        user_id, meal_id, amount = order_row
        
        # 检查餐次状态
        meal_status = db_manager.execute_one(
            "SELECT status FROM meals WHERE meal_id=?",
            [meal_id]
        )
        if not meal_status or meal_status[0] != "published":
            raise ValidationError("餐次已锁定，无法取消订单")
        
        # 使用事务取消订单
        db_manager.begin_transaction()
        try:
            # 更新订单状态
            db_manager.execute_query(
                "UPDATE orders SET status='canceled', updated_at=now() WHERE order_id=?",
                [order_id]
            )
            
            # 退款
            db_manager.execute_query(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [user_id, "refund", amount, "order", order_id, "订单取消退款"]
            )
            
            # 更新余额
            db_manager.execute_query(
                "UPDATE users SET balance_cents = balance_cents + ? WHERE id=?",
                [amount, user_id]
            )
            
            db_manager.commit_transaction()
            
            # 获取最新余额
            new_balance = db_manager.execute_one(
                "SELECT balance_cents FROM users WHERE id=?",
                [user_id]
            )[0]
            
            return OrderCancelResponse(
                order_id=order_id,
                balance_cents=new_balance,
                status="canceled"
            )
            
        except Exception:
            db_manager.rollback_transaction()
            raise
            
    except (ValidationError, OrderNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消订单失败: {str(e)}")


# TODO: 实现订单修改、查询等功能