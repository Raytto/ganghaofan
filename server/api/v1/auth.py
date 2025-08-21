"""
用户认证路由模块
处理微信小程序的登录认证流程
重构自原 routers/auth.py，使用新的架构和错误处理
"""

from fastapi import APIRouter, HTTPException

from ...schemas.auth import (
    LoginRequest, 
    LoginResponse, 
    PassphraseResolveRequest, 
    PassphraseResolveResponse,
    MockConfigResponse
)
from ...core.security import security_manager
from ...core.exceptions import AuthenticationError
from ...config import get_mock_settings, get_passphrase_map

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """
    微信小程序登录认证
    将微信临时code转换为应用JWT token
    
    Args:
        req: 包含微信code的登录请求
        
    Returns:
        LoginResponse: 包含JWT token和用户基本信息的响应
        
    Note:
        当前为开发环境模拟，实际部署时需要：
        1. 调用微信code2session API验证code
        2. 获取真实的openid和session_key
        3. 创建或更新用户记录
    """
    try:
        # TODO: 集成微信code2session API
        # 正式环境需要调用微信API验证code
        
        # 处理Mock配置
        mock = get_mock_settings()
        if mock.get("mock_enabled") and mock.get("open_id"):
            # 支持按登录生成唯一 open_id，便于区分"新用户"
            if bool(mock.get("unique_per_login")) and req.code:
                open_id = f"{str(mock.get('open_id'))}_{req.code}"
            else:
                open_id = str(mock.get("open_id"))
        else:
            open_id = f"dev_{req.code}"  # 开发环境模拟
        
        # 生成JWT token
        token = security_manager.create_jwt_token(open_id)
        
        return LoginResponse(
            token=token,
            user_id=0,  # 将在用户信息查询时获取真实ID
            is_admin=False  # 将在用户信息查询时获取真实权限
        )
        
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/env/resolve", response_model=PassphraseResolveResponse)
def resolve_passphrase(req: PassphraseResolveRequest):
    """
    解析访问口令为数据库密钥
    
    Args:
        req: 包含口令的请求
        
    Returns:
        PassphraseResolveResponse: 包含数据库密钥的响应
        
    Raises:
        HTTPException: 口令无效时返回400
    """
    try:
        passphrase_map = get_passphrase_map()
        
        # 查找口令对应的密钥
        key = passphrase_map.get(req.passphrase)
        if key is None:
            raise HTTPException(status_code=400, detail="口令无效")
        
        return PassphraseResolveResponse(key=key)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"口令解析失败: {str(e)}")


@router.get("/env/mock", response_model=MockConfigResponse)
def get_mock_config():
    """
    获取Mock配置信息
    用于前端判断是否处于开发模式
    
    Returns:
        MockConfigResponse: Mock配置信息
    """
    mock = get_mock_settings()
    return MockConfigResponse(
        mock_enabled=mock.get("mock_enabled", False),
        open_id=mock.get("open_id", ""),
        nickname=mock.get("nickname", ""),
        unique_per_login=mock.get("unique_per_login", False)
    )