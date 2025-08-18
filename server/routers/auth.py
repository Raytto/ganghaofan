"""
用户认证路由模块
处理微信小程序的登录认证流程

主要功能：
- 微信code换取token的登录流程
- 用户基本信息的初始化
- JWT token的生成和返回

业务流程：
1. 前端调用wx.login获取微信临时code
2. 后端接收code并验证（当前为开发模拟）
3. 生成JWT token并返回用户信息
4. 前端存储token用于后续API认证

TODO: 集成真实的微信code2session API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..utils.security import create_token

router = APIRouter()


class LoginReq(BaseModel):
    """登录请求体，包含微信登录code"""
    code: str  # 微信wx.login返回的临时code


@router.post("/auth/login")
def login(req: LoginReq):
    """
    微信小程序登录认证
    将微信临时code转换为应用JWT token
    
    Args:
        req: 包含微信code的登录请求
        
    Returns:
        dict: 包含JWT token和用户基本信息的响应
        
    Note:
        当前为开发环境模拟，实际部署时需要：
        1. 调用微信code2session API验证code
        2. 获取真实的openid和session_key
        3. 创建或更新用户记录
        4. 返回用户的实际权限信息
    """
    # TODO: 集成微信code2session API
    # 正式环境需要调用：
    # https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code
    open_id = f"dev_{req.code}"  # 开发环境模拟
    
    token = create_token(open_id)
    
    # 返回最小用户信息，避免敏感数据泄露
    return {
        "token": token,
        "user": {
            "id": None,  # 数据库用户ID，首次登录时为空
            "nickname": None,  # 用户昵称，需要用户授权后获取
            "avatar": None,   # 头像URL，需要用户授权后获取
            "is_admin": False,  # 管理员标识，从数据库查询
        },
    }
