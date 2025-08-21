"""
API routes and endpoints.
"""

from fastapi import APIRouter
from .v1 import auth, meals, orders, users

api_router = APIRouter()

# 包含所有v1路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(meals.router, prefix="/meals", tags=["餐次"])
# Calendar API路由 - 为了向后兼容前端，单独暴露calendar端点
api_router.include_router(meals.router, prefix="", tags=["日历"])  # 无前缀以支持 /calendar 路径
api_router.include_router(orders.router, prefix="/orders", tags=["订单"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])