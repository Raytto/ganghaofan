"""
用户管理路由模块
重构自原 routers/users.py，使用新的架构
增强版本 - Phase 2
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from typing import Optional, Dict, Any
import json

from ...schemas.user import (
    UserProfileResponse,
    UserBalanceResponse, 
    UserRechargeRequest,
    UserRechargeResponse,
    UserUpdateRequest
)
from ...core.security import get_open_id, get_current_user_id, check_admin_permission
from ...core.database import db_manager
from ...core.exceptions import DatabaseError, ValidationError, PermissionDeniedError
from ...services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(open_id: str = Depends(get_open_id)):
    """
    获取当前用户档案信息
    若用户不存在则自动创建
    """
    try:
        # 查询用户信息
        user_row = db_manager.execute_one(
            "SELECT id, open_id, nickname, is_admin, balance_cents FROM users WHERE open_id = ?",
            [open_id]
        )
        
        if not user_row:
            # 创建新用户（使用 INSERT OR IGNORE 避免竞态条件）
            try:
                db_manager.execute_query(
                    "INSERT INTO users(open_id) VALUES (?)",
                    [open_id]
                )
            except Exception:
                # 忽略重复插入错误，可能是并发创建
                pass
            
            # 重新查询用户信息
            user_row = db_manager.execute_one(
                "SELECT id, open_id, nickname, is_admin, balance_cents FROM users WHERE open_id = ?",
                [open_id]
            )
        
        if not user_row:
            raise HTTPException(status_code=500, detail="用户创建失败")
        
        return UserProfileResponse(
            user_id=user_row[0],
            open_id=user_row[1],
            nickname=user_row[2],
            is_admin=bool(user_row[3]),
            balance_cents=user_row[4]
        )
        
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@router.get("/me/balance", response_model=UserBalanceResponse)
def get_my_balance(open_id: str = Depends(get_open_id)):
    """获取当前用户余额"""
    try:
        user_row = db_manager.execute_one(
            "SELECT id, balance_cents FROM users WHERE open_id = ?",
            [open_id]
        )
        
        if not user_row:
            # 创建新用户（使用异常处理避免竞态条件）
            try:
                db_manager.execute_query(
                    "INSERT INTO users(open_id) VALUES (?)",
                    [open_id]
                )
            except Exception:
                # 忽略重复插入错误，可能是并发创建
                pass
            
            # 重新查询用户信息
            user_row = db_manager.execute_one(
                "SELECT id, balance_cents FROM users WHERE open_id = ?",
                [open_id]
            )
            
            if user_row:
                return UserBalanceResponse(user_id=user_row[0], balance_cents=user_row[1])
            else:
                return UserBalanceResponse(user_id=0, balance_cents=0)
        
        return UserBalanceResponse(
            user_id=user_row[0],
            balance_cents=user_row[1]
        )
        
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取余额失败: {str(e)}")


@router.post("/{user_id}/recharge", response_model=UserRechargeResponse)
def recharge_user(
    user_id: int, 
    req: UserRechargeRequest,
    open_id: str = Depends(get_open_id)
):
    """
    用户充值（管理员功能）
    TODO: 添加管理员权限验证
    """
    try:
        if req.amount_cents <= 0:
            raise ValidationError("充值金额必须大于0")
        
        # 使用事务处理充值
        db_manager.begin_transaction()
        try:
            # 更新用户余额
            db_manager.execute_query(
                "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
                [req.amount_cents, user_id]
            )
            
            # 记录账本
            db_manager.execute_query(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, remark) VALUES (?,?,?,?,?)",
                [user_id, "recharge", req.amount_cents, "manual", req.remark]
            )
            
            # 记录日志
            db_manager.execute_query(
                "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
                [user_id, None, "recharge", json.dumps({"amount_cents": req.amount_cents, "remark": req.remark})]
            )
            
            db_manager.commit_transaction()
            
            # 获取充值后余额
            balance_row = db_manager.execute_one(
                "SELECT balance_cents FROM users WHERE id = ?",
                [user_id]
            )
            
            return UserRechargeResponse(
                user_id=user_id,
                balance_cents=balance_row[0] if balance_row else 0
            )
            
        except Exception:
            db_manager.rollback_transaction()
            raise
            
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"充值失败: {str(e)}")


@router.put("/me", response_model=UserProfileResponse)
def update_my_profile(
    req: UserUpdateRequest,
    open_id: str = Depends(get_open_id)
):
    """更新当前用户信息"""
    try:
        # 构建更新字段
        update_fields = []
        params = []
        
        if req.nickname is not None:
            update_fields.append("nickname = ?")
            params.append(req.nickname)
        
        if req.avatar is not None:
            update_fields.append("avatar = ?")
            params.append(req.avatar)
        
        if not update_fields:
            raise ValidationError("没有需要更新的字段")
        
        params.append(open_id)
        
        # 更新用户信息
        db_manager.execute_query(
            f"UPDATE users SET {', '.join(update_fields)} WHERE open_id = ?",
            params
        )
        
        # 返回更新后的用户信息
        return get_my_profile(open_id)
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")


# 新增的增强功能 API - Phase 2

@router.get("/profile")
async def get_user_profile(
    current_user_id: int = Depends(get_current_user_id)
):
    """获取用户资料摘要"""
    try:
        user_service = UserService()
        return user_service.get_user_profile_summary(current_user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户资料失败: {str(e)}")


@router.get("/orders/history")
async def get_order_history(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    status: Optional[str] = Query(None, description="订单状态"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取用户订单历史"""
    try:
        user_service = UserService()
        return user_service.get_user_order_history(
            user_id=current_user_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取订单历史失败: {str(e)}")


@router.get("/balance/history")
async def get_balance_history(
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取余额变动历史"""
    try:
        user_service = UserService()
        return user_service.get_user_balance_history(
            user_id=current_user_id,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取余额历史失败: {str(e)}")


@router.post("/balance/recharge")
async def recharge_balance(
    user_id: int,
    amount_cents: int,
    current_user_id: int = Depends(get_current_user_id),
    is_admin: bool = Depends(check_admin_permission)
):
    """充值用户余额（管理员操作）"""
    try:
        if not is_admin:
            raise PermissionDeniedError("需要管理员权限")
        
        user_service = UserService()
        return user_service.recharge_balance(user_id, amount_cents, current_user_id)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"充值失败: {str(e)}")


# 管理员专用用户管理API

@router.get("/admin/users", response_model=Dict[str, Any])
def get_all_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    open_id: str = Depends(get_open_id)
):
    """获取所有用户列表（管理员功能）"""
    try:
        # 检查管理员权限
        admin_user = db_manager.execute_one(
            "SELECT is_admin FROM users WHERE open_id = ?",
            [open_id]
        )
        if not admin_user or not admin_user[0]:
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        # 构建查询条件
        where_clause = ""
        params = []
        
        if search:
            where_clause = "WHERE (nickname LIKE ? OR open_id LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])
        
        # 查询用户总数
        count_query = f"SELECT COUNT(*) FROM users {where_clause}"
        total = db_manager.execute_one(count_query, params)[0]
        
        # 查询用户列表
        offset = (page - 1) * size
        query = f"""
            SELECT id, open_id, nickname, is_admin, balance_cents, created_at, updated_at
            FROM users 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([size, offset])
        
        users = db_manager.execute_all(query, params)
        
        # 格式化结果
        user_list = []
        for user in users:
            user_list.append({
                "user_id": user[0],
                "open_id": user[1],
                "nickname": user[2],
                "is_admin": bool(user[3]),
                "balance_cents": user[4],
                "created_at": str(user[5]),
                "updated_at": str(user[6]) if user[6] else None
            })
        
        return {
            "success": True,
            "data": user_list,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.put("/admin/users/{user_id}/admin", response_model=Dict[str, Any])
def set_user_admin(
    user_id: int,
    is_admin: bool,
    open_id: str = Depends(get_open_id)
):
    """设置用户管理员权限（管理员功能）"""
    try:
        # 检查当前用户管理员权限
        admin_user = db_manager.execute_one(
            "SELECT id, is_admin FROM users WHERE open_id = ?",
            [open_id]
        )
        if not admin_user or not admin_user[1]:
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        current_admin_id = admin_user[0]
        
        # 检查目标用户是否存在
        target_user = db_manager.execute_one(
            "SELECT open_id, nickname, is_admin FROM users WHERE id = ?",
            [user_id]
        )
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 防止取消自己的管理员权限
        if user_id == current_admin_id and not is_admin:
            raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")
        
        # 更新用户管理员状态
        db_manager.execute_query(
            "UPDATE users SET is_admin = ?, updated_at = now() WHERE id = ?",
            [is_admin, user_id]
        )
        
        # 记录操作日志
        action = "grant_admin" if is_admin else "revoke_admin"
        db_manager.execute_query(
            "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
            [user_id, current_admin_id, action, json.dumps({"is_admin": is_admin})]
        )
        
        return {
            "success": True,
            "message": f"已{'设置' if is_admin else '取消'} {target_user[1] or target_user[0]} 的管理员权限"
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置管理员权限失败: {str(e)}")


@router.get("/admin/stats", response_model=Dict[str, Any])
def get_system_stats(open_id: str = Depends(get_open_id)):
    """获取系统统计信息（管理员功能）"""
    try:
        # 检查管理员权限
        admin_user = db_manager.execute_one(
            "SELECT is_admin FROM users WHERE open_id = ?",
            [open_id]
        )
        if not admin_user or not admin_user[0]:
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        # 获取统计数据
        stats = {}
        
        # 用户统计
        user_stats = db_manager.execute_one(
            "SELECT COUNT(*) as total, SUM(CASE WHEN is_admin THEN 1 ELSE 0 END) as admins FROM users"
        )
        stats["users"] = {
            "total": user_stats[0],
            "admins": user_stats[1],
            "regular": user_stats[0] - user_stats[1]
        }
        
        # 餐次统计
        meal_stats = db_manager.execute_all(
            "SELECT status, COUNT(*) FROM meals GROUP BY status"
        )
        stats["meals"] = {row[0]: row[1] for row in meal_stats}
        
        # 订单统计
        order_stats = db_manager.execute_all(
            "SELECT status, COUNT(*) FROM orders GROUP BY status"
        )
        stats["orders"] = {row[0]: row[1] for row in order_stats}
        
        # 财务统计
        financial = db_manager.execute_one(
            """SELECT 
                SUM(balance_cents) as total_balance,
                (SELECT SUM(amount_cents) FROM ledger WHERE type = 'recharge') as total_recharge,
                (SELECT SUM(amount_cents) FROM ledger WHERE type = 'debit') as total_spent
               FROM users"""
        )
        stats["financial"] = {
            "total_balance_cents": financial[0] or 0,
            "total_recharge_cents": financial[1] or 0,
            "total_spent_cents": financial[2] or 0
        }
        
        return {
            "success": True,
            "data": stats
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统统计失败: {str(e)}")


# 余额管理API扩展

@router.post("/admin/balance/adjust", response_model=Dict[str, Any])
def adjust_user_balance(
    user_id: int,
    amount_cents: int,
    reason: str,
    open_id: str = Depends(get_open_id)
):
    """调整用户余额（管理员功能）"""
    try:
        # 检查管理员权限
        admin_user = db_manager.execute_one(
            "SELECT id, is_admin FROM users WHERE open_id = ?",
            [open_id]
        )
        if not admin_user or not admin_user[1]:
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        admin_id = admin_user[0]
        
        # 检查目标用户是否存在
        target_user = db_manager.execute_one(
            "SELECT id, nickname, balance_cents FROM users WHERE id = ?",
            [user_id]
        )
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        old_balance = target_user[2]
        
        if amount_cents == 0:
            raise HTTPException(status_code=400, detail="调整金额不能为0")
        
        # 使用事务处理余额调整
        db_manager.begin_transaction()
        try:
            # 更新用户余额
            db_manager.execute_query(
                "UPDATE users SET balance_cents = balance_cents + ?, updated_at = now() WHERE id = ?",
                [amount_cents, user_id]
            )
            
            # 记录账本
            ledger_type = "adjustment_credit" if amount_cents > 0 else "adjustment_debit"
            db_manager.execute_query(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, ref_id, remark) VALUES (?,?,?,?,?,?)",
                [user_id, ledger_type, abs(amount_cents), "admin_adjustment", admin_id, reason]
            )
            
            # 记录操作日志
            db_manager.execute_query(
                "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
                [user_id, admin_id, "balance_adjustment", 
                 json.dumps({"amount_cents": amount_cents, "old_balance": old_balance, "reason": reason})]
            )
            
            db_manager.commit_transaction()
            
            # 获取调整后余额
            new_balance = db_manager.execute_one(
                "SELECT balance_cents FROM users WHERE id = ?",
                [user_id]
            )[0]
            
            return {
                "success": True,
                "message": f"用户余额调整成功",
                "data": {
                    "user_id": user_id,
                    "old_balance_cents": old_balance,
                    "adjustment_cents": amount_cents,
                    "new_balance_cents": new_balance,
                    "reason": reason
                }
            }
            
        except Exception:
            db_manager.rollback_transaction()
            raise
            
    except HTTPException:
        raise
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调整余额失败: {str(e)}")


@router.get("/admin/balance/transactions", response_model=Dict[str, Any])
def get_balance_transactions(
    user_id: Optional[int] = Query(None, description="用户ID过滤"),
    transaction_type: Optional[str] = Query(None, description="交易类型过滤"),
    date_from: Optional[str] = Query(None, description="开始日期"),
    date_to: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    open_id: str = Depends(get_open_id)
):
    """获取余额交易记录（管理员功能）"""
    try:
        # 检查管理员权限
        admin_user = db_manager.execute_one(
            "SELECT is_admin FROM users WHERE open_id = ?",
            [open_id]
        )
        if not admin_user or not admin_user[0]:
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        # 构建查询条件
        conditions = []
        params = []
        
        if user_id:
            conditions.append("l.user_id = ?")
            params.append(user_id)
        
        if transaction_type:
            conditions.append("l.type = ?")
            params.append(transaction_type)
        
        if date_from:
            conditions.append("DATE(l.created_at) >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("DATE(l.created_at) <= ?")
            params.append(date_to)
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # 查询交易总数
        count_query = f"SELECT COUNT(*) FROM ledger l {where_clause}"
        total = db_manager.execute_one(count_query, params)[0]
        
        # 查询交易记录
        offset = (page - 1) * size
        query = f"""
            SELECT l.id, l.user_id, u.nickname, l.type, l.amount_cents, 
                   l.ref_type, l.ref_id, l.remark, l.created_at
            FROM ledger l
            LEFT JOIN users u ON l.user_id = u.id
            {where_clause}
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([size, offset])
        
        transactions = db_manager.execute_all(query, params)
        
        # 格式化结果
        transaction_list = []
        for txn in transactions:
            transaction_list.append({
                "id": txn[0],
                "user_id": txn[1],
                "user_nickname": txn[2],
                "type": txn[3],
                "amount_cents": txn[4],
                "ref_type": txn[5],
                "ref_id": txn[6],
                "remark": txn[7],
                "created_at": str(txn[8])
            })
        
        return {
            "success": True,
            "data": transaction_list,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
        
    except HTTPException:
        raise
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交易记录失败: {str(e)}")


@router.post("/self/balance/recharge", response_model=Dict[str, Any])
def self_recharge(
    amount_cents: int,
    payment_method: str = "wechat",
    open_id: str = Depends(get_open_id)
):
    """用户自助充值（模拟功能）"""
    try:
        # 获取用户信息
        user_row = db_manager.execute_one(
            "SELECT id, nickname FROM users WHERE open_id = ?",
            [open_id]
        )
        if not user_row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        user_id = user_row[0]
        
        if amount_cents <= 0:
            raise HTTPException(status_code=400, detail="充值金额必须大于0")
        
        if amount_cents > 100000:  # 1000元限制
            raise HTTPException(status_code=400, detail="单次充值金额不能超过1000元")
        
        # 使用事务处理充值
        db_manager.begin_transaction()
        try:
            # 更新用户余额
            db_manager.execute_query(
                "UPDATE users SET balance_cents = balance_cents + ?, updated_at = now() WHERE id = ?",
                [amount_cents, user_id]
            )
            
            # 记录账本
            db_manager.execute_query(
                "INSERT INTO ledger(user_id, type, amount_cents, ref_type, remark) VALUES (?,?,?,?,?)",
                [user_id, "recharge", amount_cents, "self_recharge", f"用户自助充值 - {payment_method}"]
            )
            
            # 记录操作日志
            db_manager.execute_query(
                "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
                [user_id, user_id, "self_recharge", 
                 json.dumps({"amount_cents": amount_cents, "payment_method": payment_method})]
            )
            
            db_manager.commit_transaction()
            
            # 获取充值后余额
            new_balance = db_manager.execute_one(
                "SELECT balance_cents FROM users WHERE id = ?",
                [user_id]
            )[0]
            
            return {
                "success": True,
                "message": "充值成功",
                "data": {
                    "user_id": user_id,
                    "amount_cents": amount_cents,
                    "new_balance_cents": new_balance,
                    "payment_method": payment_method
                }
            }
            
        except Exception:
            db_manager.rollback_transaction()
            raise
            
    except HTTPException:
        raise
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"充值失败: {str(e)}")