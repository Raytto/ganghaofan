"""
JWT认证和安全工具模块
处理微信小程序的用户身份认证和API授权

主要功能：
- JWT token的生成和验证
- HTTP请求的Bearer token解析
- 用户身份的统一认证依赖

安全考虑：
- 使用HS256算法签名JWT token
- 统一的token格式验证和错误处理
- 支持微信openid作为用户唯一标识
"""
from fastapi import Depends, HTTPException, Header
from jose import jwt

# JWT配置常量
SECRET = "dev-secret-key-change-me"  # 生产环境应使用环境变量
ALGO = "HS256"


def create_token(open_id: str) -> str:
    """
    为用户创建JWT访问令牌
    
    Args:
        open_id: 微信用户的openid，作为用户唯一标识
        
    Returns:
        str: 签名后的JWT token字符串
        
    Note:
        token中只包含openid，避免敏感信息泄露
        使用统一的密钥和算法确保token安全性
    """
    return jwt.encode({"open_id": open_id}, SECRET, algorithm=ALGO)


async def get_open_id(authorization: str | None = Header(default=None)) -> str:
    """
    从HTTP请求头中提取并验证用户身份
    用作FastAPI依赖注入，自动处理所有需要认证的API端点
    
    Args:
        authorization: HTTP Authorization header，格式为 "Bearer <token>"
        
    Returns:
        str: 验证成功的用户openid
        
    Raises:
        HTTPException: 
            401 - token缺失、格式错误或验证失败
            
    Note:
        作为FastAPI的Depends使用，提供统一的认证机制
        token解析失败时抛出401，由前端自动重试登录
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
        
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload.get("open_id")
    except Exception:
        # JWT解析失败，可能是token过期、篡改或密钥不匹配
        raise HTTPException(401, "invalid token")
