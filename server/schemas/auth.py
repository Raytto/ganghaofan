"""
认证相关的请求/响应模式
"""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """登录请求"""
    code: str = Field(description="微信登录凭证", example="061234567890123456789")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "061234567890123456789"
            }
        }

class TokenInfo(BaseModel):
    """Token信息"""
    token: str = Field(description="访问令牌")
    expires_in: int = Field(description="过期时间(秒)")
    token_type: str = Field(default="Bearer", description="令牌类型")

class UserInfo(BaseModel):
    """用户信息"""
    user_id: int = Field(description="用户ID")
    openid: str = Field(description="微信OpenID")
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    balance_cents: int = Field(description="余额(分)")
    is_admin: bool = Field(description="是否为管理员")

# 向后兼容的简单登录响应
class LoginResponse(BaseModel):
    """登录响应"""
    token: str = Field(description="JWT访问令牌")
    user_id: int = Field(description="用户ID")
    is_admin: bool = Field(description="是否为管理员")


class PassphraseResolveRequest(BaseModel):
    """口令解析请求"""
    passphrase: str = Field(..., description="访问口令")


class PassphraseResolveResponse(BaseModel):
    """口令解析响应"""
    key: str = Field(..., description="数据库访问密钥")


class MockConfigResponse(BaseModel):
    """Mock配置响应"""
    mock_enabled: bool = Field(False, description="是否启用Mock")
    open_id: str = Field("", description="Mock的OpenID")
    nickname: str = Field("", description="Mock的昵称")
    unique_per_login: bool = Field(False, description="每次登录是否生成唯一ID")