"""
自定义异常类
提供更精确的错误处理和异常信息
"""

from typing import Any, Dict, Optional


class BaseApplicationError(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(BaseApplicationError):
    """数据库相关异常"""
    pass


class AuthenticationError(BaseApplicationError):
    """认证相关异常"""
    pass


class AuthorizationError(BaseApplicationError):
    """授权相关异常"""
    pass


class ValidationError(BaseApplicationError):
    """数据验证异常"""
    pass


class BusinessLogicError(BaseApplicationError):
    """业务逻辑异常"""
    pass


class MealNotFoundError(BusinessLogicError):
    """餐次不存在异常"""
    pass


class OrderNotFoundError(BusinessLogicError):
    """订单不存在异常"""
    pass


class InsufficientBalanceError(BusinessLogicError):
    """余额不足异常"""
    pass


class CapacityExceededError(BusinessLogicError):
    """容量超限异常"""
    pass


class DuplicateOrderError(BusinessLogicError):
    """重复订单异常"""
    pass


class MealStatusError(BusinessLogicError):
    """餐次状态错误异常"""
    pass


class ConcurrencyError(BaseApplicationError):
    """并发控制错误"""
    pass


class PermissionDeniedError(BaseApplicationError):
    """权限拒绝错误"""
    pass


class BusinessRuleError(BaseApplicationError):
    """业务规则错误"""
    pass


class MealCapacityExceededError(BusinessRuleError):
    """餐次容量超限错误"""
    pass