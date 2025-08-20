"""
罡好饭小程序后端服务 - 主应用入口
提供餐次订餐系统的完整后端API服务

主要功能模块：
- 微信小程序用户认证
- 餐次发布和管理
- 用户订单处理
- 余额和账单管理
- 操作日志记录

技术栈：FastAPI + DuckDB + JWT认证
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

# 导入新的模块结构
from .core.database import db_manager
from .core.exceptions import BaseApplicationError
from .core.error_handler import (
    application_error_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from .config.settings import settings
from .api import api_router

# 向后兼容：保持原有的导入路径可用
from .db import use_db_key
from fastapi import Depends


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    try:
        db_manager.init_database()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        # 不要让应用启动失败，允许在运行时重试
    
    yield
    
    # 关闭时的清理工作可以在这里添加


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="罡好饭餐饮订购系统API",
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 在生产环境中应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册异常处理器
    app.add_exception_handler(BaseApplicationError, application_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # 注册路由
    app.include_router(api_router, prefix=settings.api_prefix)
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        try:
            db_manager.get_connection()
            return {
                "status": "healthy",
                "version": settings.api_version,
                "database": "connected"
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "version": settings.api_version,
                "database": f"error: {str(e)}"
            }
    
    @app.get("/")
    async def root():
        return {
            "name": settings.api_title,
            "version": settings.api_version,
            "description": "罡好饭餐饮订购系统API"
        }
    
    return app

# 应用实例
app = create_app()
