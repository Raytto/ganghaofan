"""
用户管理路由模块
重构自原 routers/users.py，使用新的架构
"""

from fastapi import APIRouter, Depends, HTTPException

from ...schemas.user import (
    UserProfileResponse,
    UserBalanceResponse, 
    UserRechargeRequest,
    UserRechargeResponse,
    UserUpdateRequest
)
from ...core.security import get_open_id
from ...core.database import db_manager
from ...core.exceptions import DatabaseError, ValidationError

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