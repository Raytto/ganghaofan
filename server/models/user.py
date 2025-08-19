"""
用户相关数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional
from .base import BaseEntity, TimestampMixin


class UserBase(BaseModel):
    """用户基础字段"""
    nickname: Optional[str] = Field(None, max_length=100, description="用户昵称")
    avatar: Optional[str] = Field(None, description="头像URL")


class UserCreate(UserBase):
    """用户创建模型"""
    open_id: str = Field(..., description="微信OpenID")


class UserUpdate(UserBase):
    """用户更新模型"""
    pass


class User(UserBase, BaseEntity, TimestampMixin):
    """用户完整模型"""
    id: int = Field(..., description="用户ID")
    open_id: str = Field(..., description="微信OpenID")
    is_admin: bool = Field(False, description="是否为管理员")
    balance_cents: int = Field(0, description="余额（分）")
    
    @property
    def balance_yuan(self) -> float:
        """余额（元）"""
        return self.balance_cents / 100


class UserProfile(BaseModel):
    """用户档案（脱敏后的用户信息）"""
    user_id: int = Field(..., description="用户ID")
    open_id: str = Field(..., description="微信OpenID")
    nickname: Optional[str] = Field(None, description="用户昵称")
    is_admin: bool = Field(False, description="是否为管理员")
    balance_cents: int = Field(0, description="余额（分）")
    
    @property
    def balance_yuan(self) -> float:
        """余额（元）"""
        return self.balance_cents / 100


class BalanceInfo(BaseModel):
    """余额信息"""
    user_id: int = Field(..., description="用户ID")
    balance_cents: int = Field(..., description="余额（分）")
    
    @property
    def balance_yuan(self) -> float:
        """余额（元）"""
        return self.balance_cents / 100


class RechargeRequest(BaseModel):
    """充值请求"""
    amount_cents: int = Field(..., gt=0, description="充值金额（分）")
    remark: Optional[str] = Field(None, max_length=200, description="备注")
    
    @property
    def amount_yuan(self) -> float:
        """充值金额（元）"""
        return self.amount_cents / 100