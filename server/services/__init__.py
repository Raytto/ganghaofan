"""
Business logic services.
Contains service layer implementations for core business operations.
"""

from .auth_service import AuthService
from .meal_service import MealService
from .order_service import OrderService, order_service
from .user_service import UserService

__all__ = [
    "AuthService",
    "MealService", 
    "OrderService",
    "UserService",
    "order_service"  # 保持向后兼容
]