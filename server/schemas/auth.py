"""
认证相关的请求/响应模式
"""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(..., description="微信登录code")


class LoginResponse(BaseModel):
    """登录响应"""
    token: str = Field(..., description="JWT访问token")
    user_id: int = Field(..., description="用户ID")
    is_admin: bool = Field(False, description="是否为管理员")


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