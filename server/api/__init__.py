"""
API routes and endpoints.
"""

from fastapi import APIRouter
from .v1 import auth, meals, orders, users

api_router = APIRouter()

# 包含所有v1路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(meals.router, prefix="/meals", tags=["餐次"])
api_router.include_router(orders.router, prefix="/orders", tags=["订单"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])