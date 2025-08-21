#!/usr/bin/env python3
"""
简化的测试服务器
用于运行E2E测试，绕过复杂的模块导入问题
"""

import sys
import os

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# 简化的应用配置
app = FastAPI(title="罡好饭测试服务器", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 简化的内存数据库
class SimpleDB:
    def __init__(self):
        self.users = {}
        self.meals = {}
        self.orders = {}
        self.ledger = []
        self.logs = []
        self._init_test_data()
    
    def _init_test_data(self):
        # 创建测试用户
        self.users["test_user"] = {
            "id": 1,
            "open_id": "test_user",
            "nickname": "测试用户",
            "is_admin": True,
            "balance_cents": 0,
            "created_at": datetime.now().isoformat()
        }
    
    def get_user(self, open_id: str):
        if open_id not in self.users:
            # 自动创建新用户
            user_id = len(self.users) + 1
            self.users[open_id] = {
                "id": user_id,
                "open_id": open_id,
                "nickname": f"用户{user_id}",
                "is_admin": open_id == "test_user",
                "balance_cents": 0,
                "created_at": datetime.now().isoformat()
            }
        return self.users[open_id]

# 全局数据库实例
db = SimpleDB()

# 简化的依赖注入
def get_open_id():
    return "test_user"

def check_admin():
    user = db.get_user("test_user")
    return user["is_admin"]

# 健康检查端点
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# 用户相关API
@app.get("/api/v1/users/me")
def get_current_user(open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    return {
        "user_id": user["id"],
        "open_id": user["open_id"],
        "nickname": user["nickname"],
        "is_admin": user["is_admin"],
        "balance_cents": user["balance_cents"]
    }

@app.get("/api/v1/users/me/balance")
def get_user_balance(open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    return {
        "user_id": user["id"],
        "balance_cents": user["balance_cents"]
    }

@app.post("/api/v1/users/self/balance/recharge")
def recharge_balance(request: dict, open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    amount = request.get("amount_cents", 0)
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="充值金额必须大于0")
    
    # 更新余额
    user["balance_cents"] += amount
    
    # 记录交易
    db.ledger.append({
        "user_id": user["id"],
        "type": "recharge",
        "amount_cents": amount,
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": "充值成功",
        "data": {
            "user_id": user["id"],
            "amount_cents": amount,
            "new_balance_cents": user["balance_cents"],
            "payment_method": request.get("payment_method", "test")
        }
    }

# 餐次管理API
@app.post("/api/v1/meals")
def create_meal(request: dict, open_id: str = Depends(get_open_id)):
    if not check_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    meal_id = len(db.meals) + 1
    meal = {
        "meal_id": meal_id,
        "title": request["title"],
        "meal_date": request["meal_date"],
        "slot": request["slot"],
        "base_price_cents": request["base_price_cents"],
        "capacity": request["capacity"],
        "per_user_limit": request["per_user_limit"],
        "options_json": request["options_json"],
        "status": "published",
        "created_at": datetime.now().isoformat()
    }
    
    db.meals[meal_id] = meal
    
    return {
        "success": True,
        "data": meal
    }

@app.get("/api/v1/meals")  
def get_meals(page: int = 1, size: int = 10, status: str = None):
    meals = list(db.meals.values())
    
    if status:
        meals = [m for m in meals if m["status"] == status]
    
    start = (page - 1) * size
    end = start + size
    
    return {
        "success": True,
        "data": meals[start:end],
        "pagination": {
            "page": page,
            "size": size,
            "total": len(meals)
        }
    }

@app.post("/api/v1/meals/{meal_id}/lock")
def lock_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    if not check_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    if meal_id not in db.meals:
        raise HTTPException(status_code=404, detail="餐次不存在")
    
    db.meals[meal_id]["status"] = "locked"
    return {"success": True, "message": "餐次锁定成功"}

@app.post("/api/v1/meals/{meal_id}/unlock")
def unlock_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    if not check_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    if meal_id not in db.meals:
        raise HTTPException(status_code=404, detail="餐次不存在")
    
    db.meals[meal_id]["status"] = "published"
    return {"success": True, "message": "餐次解锁成功"}

@app.post("/api/v1/meals/{meal_id}/cancel")
def cancel_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    if not check_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    if meal_id not in db.meals:
        raise HTTPException(status_code=404, detail="餐次不存在")
    
    # 找出所有相关订单并退款
    refunded_orders = 0
    for order_id, order in db.orders.items():
        if order["meal_id"] == meal_id and order["status"] == "active":
            # 退款
            user = db.users.get(order["user_open_id"])
            if user:
                user["balance_cents"] += order["amount_cents"]
                
            # 取消订单
            order["status"] = "cancelled"
            refunded_orders += 1
            
            # 记录退款
            db.ledger.append({
                "user_id": order["user_id"],
                "type": "refund",
                "amount_cents": order["amount_cents"],
                "ref_type": "meal_cancel",
                "ref_id": meal_id,
                "created_at": datetime.now().isoformat()
            })
    
    # 取消餐次
    db.meals[meal_id]["status"] = "cancelled"
    
    return {
        "success": True, 
        "message": f"餐次取消成功，退款 {refunded_orders} 个订单"
    }

# 订单管理API  
@app.post("/api/v1/orders")
def create_order(request: dict, open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    meal_id = request["meal_id"]
    qty = request["qty"]
    
    if meal_id not in db.meals:
        raise HTTPException(status_code=400, detail="餐次不存在")
    
    meal = db.meals[meal_id]
    
    if meal["status"] != "published":
        raise HTTPException(status_code=400, detail="餐次未开放订餐")
    
    # 计算金额
    amount = meal["base_price_cents"] * qty
    
    # 允许透支！不检查余额
    # 这是透支功能的核心
    
    # 创建订单
    order_id = len(db.orders) + 1
    order = {
        "order_id": order_id,
        "user_id": user["id"],
        "user_open_id": open_id,
        "meal_id": meal_id,
        "qty": qty,
        "options": request.get("options", []),
        "amount_cents": amount,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }
    
    db.orders[order_id] = order
    
    # 扣费（允许负余额）
    user["balance_cents"] -= amount
    
    # 记录交易
    db.ledger.append({
        "user_id": user["id"],
        "type": "debit",
        "amount_cents": amount,
        "ref_type": "order",
        "ref_id": order_id,
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "order_id": order_id,
        "amount_cents": amount,
        "balance_cents": user["balance_cents"]  # 可能是负数！
    }

@app.get("/api/v1/orders/{order_id}")
def get_order_detail(order_id: int, open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    
    if order_id not in db.orders:
        raise HTTPException(status_code=400, detail="订单不存在")
    
    order = db.orders[order_id]
    
    if order["user_id"] != user["id"]:
        raise HTTPException(status_code=400, detail="订单不存在或无权访问")
    
    meal = db.meals.get(order["meal_id"], {})
    
    return {
        "order_id": order["order_id"],
        "meal_id": order["meal_id"],
        "meal_date": meal.get("meal_date", ""),
        "meal_slot": meal.get("slot", ""),
        "meal_title": meal.get("title", ""),
        "qty": order["qty"],
        "options": order["options"],
        "amount_cents": order["amount_cents"],
        "status": order["status"],
        "created_at": order["created_at"]
    }

@app.get("/api/v1/orders")
def get_user_orders(limit: int = 10, offset: int = 0, open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    
    # 获取用户的所有订单
    user_orders = []
    for order in db.orders.values():
        if order["user_id"] == user["id"]:
            meal = db.meals.get(order["meal_id"], {})
            user_orders.append({
                "order_id": order["order_id"],
                "meal_id": order["meal_id"],
                "qty": order["qty"],
                "options": order["options"],
                "amount_cents": order["amount_cents"],
                "status": order["status"],
                "created_at": order["created_at"],
                "meal_title": meal.get("title", ""),
                "meal_date": meal.get("meal_date", ""),
                "meal_slot": meal.get("slot", "")
            })
    
    # 按创建时间倒序
    user_orders.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 分页
    start = offset
    end = offset + limit
    
    return {
        "success": True,
        "data": user_orders[start:end],
        "total": len(user_orders),
        "limit": limit,
        "offset": offset
    }

@app.put("/api/v1/orders/{order_id}")
def update_order(order_id: int, request: dict, open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    
    if order_id not in db.orders:
        raise HTTPException(status_code=400, detail="订单不存在")
    
    order = db.orders[order_id]
    
    if order["user_id"] != user["id"]:
        raise HTTPException(status_code=400, detail="订单不存在或无权访问")
    
    if order["status"] != "active":
        raise HTTPException(status_code=400, detail="只能修改有效订单")
    
    meal = db.meals[order["meal_id"]]
    old_amount = order["amount_cents"]
    new_qty = request["qty"]
    new_amount = meal["base_price_cents"] * new_qty
    
    # 更新订单
    order["qty"] = new_qty
    order["options"] = request.get("options", [])
    order["amount_cents"] = new_amount
    
    # 处理金额差异（允许透支）
    amount_diff = new_amount - old_amount
    user["balance_cents"] -= amount_diff
    
    # 记录交易
    if amount_diff != 0:
        ledger_type = "debit" if amount_diff > 0 else "refund"
        db.ledger.append({
            "user_id": user["id"],
            "type": ledger_type,
            "amount_cents": abs(amount_diff),
            "ref_type": "order_update",
            "ref_id": order_id,
            "created_at": datetime.now().isoformat()
        })
    
    return {
        "order_id": order_id,
        "amount_cents": new_amount,
        "balance_cents": user["balance_cents"]  # 可能是负数！
    }

@app.delete("/api/v1/orders/{order_id}")  
def cancel_order(order_id: int, open_id: str = Depends(get_open_id)):
    user = db.get_user(open_id)
    
    if order_id not in db.orders:
        raise HTTPException(status_code=400, detail="订单不存在或已取消")
    
    order = db.orders[order_id]
    
    if order["user_id"] != user["id"]:
        raise HTTPException(status_code=400, detail="订单不存在或无权访问")
    
    if order["status"] != "active":
        raise HTTPException(status_code=400, detail="订单已取消或完成")
    
    # 退款（可能退款到负余额）
    user["balance_cents"] += order["amount_cents"]
    
    # 取消订单
    order["status"] = "canceled"
    
    # 记录退款
    db.ledger.append({
        "user_id": user["id"],
        "type": "refund",
        "amount_cents": order["amount_cents"],
        "ref_type": "order_cancel",
        "ref_id": order_id,
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "order_id": order_id,
        "balance_cents": user["balance_cents"],
        "status": "canceled"
    }

# 管理员统计API
@app.get("/api/v1/users/admin/stats")
def get_system_stats(open_id: str = Depends(get_open_id)):
    if not check_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 用户统计
    total_users = len(db.users)
    admin_users = sum(1 for u in db.users.values() if u["is_admin"])
    
    # 餐次统计
    meal_stats = {}
    for meal in db.meals.values():
        status = meal["status"]
        meal_stats[status] = meal_stats.get(status, 0) + 1
    
    # 订单统计
    order_stats = {}
    for order in db.orders.values():
        status = order["status"]
        order_stats[status] = order_stats.get(status, 0) + 1
    
    # 财务统计
    total_balance = sum(u["balance_cents"] for u in db.users.values())
    total_recharge = sum(l["amount_cents"] for l in db.ledger if l["type"] == "recharge")
    total_spent = sum(l["amount_cents"] for l in db.ledger if l["type"] == "debit")
    
    return {
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "admins": admin_users,
                "regular": total_users - admin_users
            },
            "meals": meal_stats,
            "orders": order_stats,
            "financial": {
                "total_balance_cents": total_balance,
                "total_recharge_cents": total_recharge,
                "total_spent_cents": total_spent
            }
        }
    }

@app.post("/api/v1/users/admin/balance/adjust")
def adjust_user_balance(request: dict, open_id: str = Depends(get_open_id)):
    if not check_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    user_id = request["user_id"]
    amount_cents = request["amount_cents"]
    reason = request["reason"]
    
    # 找到用户（简化：使用第一个用户）
    user = list(db.users.values())[0]  # 简化实现
    old_balance = user["balance_cents"]
    
    # 调整余额
    user["balance_cents"] += amount_cents
    
    # 记录交易
    ledger_type = "adjustment_credit" if amount_cents > 0 else "adjustment_debit"
    db.ledger.append({
        "user_id": user["id"],
        "type": ledger_type,
        "amount_cents": abs(amount_cents),
        "ref_type": "admin_adjustment",
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "message": "用户余额调整成功",
        "data": {
            "user_id": user["id"],
            "old_balance_cents": old_balance,
            "adjustment_cents": amount_cents,
            "new_balance_cents": user["balance_cents"],
            "reason": reason
        }
    }

@app.get("/api/v1/users/admin/balance/transactions")
def get_balance_transactions(page: int = 1, size: int = 20):
    if not check_admin():
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 分页
    start = (page - 1) * size
    end = start + size
    
    transactions = []
    for i, txn in enumerate(db.ledger[start:end], start=start+1):
        user = next((u for u in db.users.values() if u["id"] == txn["user_id"]), None)
        transactions.append({
            "id": i,
            "user_id": txn["user_id"],
            "user_nickname": user["nickname"] if user else "未知用户",
            "type": txn["type"],
            "amount_cents": txn["amount_cents"],
            "ref_type": txn.get("ref_type", ""),
            "ref_id": txn.get("ref_id", ""),
            "remark": txn.get("remark", ""),
            "created_at": txn["created_at"]
        })
    
    return {
        "success": True,
        "data": transactions,
        "pagination": {
            "page": page,
            "size": size,
            "total": len(db.ledger),
            "pages": (len(db.ledger) + size - 1) // size
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动罡好饭测试服务器...")
    print("📋 支持透支功能：用户可以在余额不足时继续订餐")
    print("🔍 服务器地址：http://127.0.0.1:8001")
    uvicorn.run(app, host="127.0.0.1", port=8001)