"""
用户管理路由模块
重构自原 routers/users.py，使用新的架构
增强版本 - Phase 2
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from typing import Optional

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


@router.get("/users/me", response_model=UserProfileResponse)
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
            # 创建新用户
            db_manager.execute_query(
                "INSERT INTO users(open_id) VALUES (?)",
                [open_id]
            )
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


@router.get("/users/me/balance", response_model=UserBalanceResponse)
def get_my_balance(open_id: str = Depends(get_open_id)):
    """获取当前用户余额"""
    try:
        user_row = db_manager.execute_one(
            "SELECT id, balance_cents FROM users WHERE open_id = ?",
            [open_id]
        )
        
        if not user_row:
            # 创建新用户
            db_manager.execute_query(
                "INSERT INTO users(open_id) VALUES (?)",
                [open_id]
            )
            return UserBalanceResponse(user_id=0, balance_cents=0)
        
        return UserBalanceResponse(
            user_id=user_row[0],
            balance_cents=user_row[1]
        )
        
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取余额失败: {str(e)}")


@router.post("/users/{user_id}/recharge", response_model=UserRechargeResponse)
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
                [user_id, None, "recharge", f'{{"amount_cents": {req.amount_cents}, "remark": "{req.remark}"}}']
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


@router.put("/users/me", response_model=UserProfileResponse)
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