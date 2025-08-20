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
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
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
        title="罡好饭 API",
        description="""
        ## 罡好饭餐饮订购系统API

        这是一个完整的餐饮订购系统API，支持：
        
        ### 核心功能
        - 🔐 **用户认证**: 微信小程序登录
        - 🍽️ **餐次管理**: 发布、锁定、完成餐次
        - 📝 **订单处理**: 下单、修改、取消订单
        - 💰 **余额管理**: 充值、扣费、退款
        - 📊 **统计导出**: 订单统计、数据导出
        
        ### 业务规则
        - 每个用户每个餐次只能有一个订单
        - 订单在餐次锁定前可以修改
        - 余额不足时无法下单
        - 管理员可以管理餐次和查看所有订单
        
        ### 认证方式
        - 使用JWT Bearer Token认证
        - 需要在请求头中包含数据库访问密钥
        
        ```
        Authorization: Bearer <token>
        X-DB-Key: <db_key>
        ```
        """,
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
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
    
    # 自定义OpenAPI配置
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="罡好饭 API",
            version=settings.api_version,
            description=app.description,
            routes=app.routes,
        )
        
        # 添加认证配置
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "DBKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-DB-Key"
            }
        }
        
        # 全局安全要求
        openapi_schema["security"] = [
            {"BearerAuth": []},
            {"DBKeyAuth": []}
        ]
        
        # 添加错误响应模板
        openapi_schema["components"]["responses"] = {
            "ValidationError": {
                "description": "数据验证错误",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "AuthenticationError": {
                "description": "认证失败",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            },
            "BusinessRuleError": {
                "description": "业务规则错误",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                    }
                }
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi

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
