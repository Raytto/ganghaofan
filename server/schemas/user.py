"""
用户相关的请求/响应模式
"""

from pydantic import BaseModel, Field
from typing import Optional


class UserProfileResponse(BaseModel):
    """用户档案响应"""
    user_id: int = Field(..., description="用户ID")
    open_id: str = Field(..., description="微信OpenID")
    nickname: Optional[str] = Field(None, description="昵称")
    is_admin: bool = Field(..., description="是否为管理员")
    balance_cents: int = Field(..., description="余额（分）")


class UserBalanceResponse(BaseModel):
    """用户余额响应"""
    user_id: int = Field(..., description="用户ID")
    balance_cents: int = Field(..., description="余额（分）")


class UserRechargeRequest(BaseModel):
    """用户充值请求"""
    amount_cents: int = Field(..., gt=0, description="充值金额（分）")
    remark: Optional[str] = Field(None, description="备注")


class UserRechargeResponse(BaseModel):
    """用户充值响应"""
    user_id: int = Field(..., description="用户ID")
    balance_cents: int = Field(..., description="充值后余额（分）")


class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")