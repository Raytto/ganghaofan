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
from contextlib import asynccontextmanager

# 导入新的模块结构
from .core.database import db_manager
from .core.exceptions import BaseApplicationError
from .api.v1 import auth, users, meals, orders, logs, env

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


app = FastAPI(
    title="GangHaoFan API",
    version="2.0.0",
    description="罡好饭餐饮订购系统API",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BaseApplicationError)
async def application_error_handler(request, exc: BaseApplicationError):
    """统一处理应用异常"""
    return HTTPException(
        status_code=400,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


# 注册API路由模块
app.include_router(auth.router, prefix="/api/v1", tags=["认证"])
app.include_router(
    users.router, 
    prefix="/api/v1", 
    tags=["用户"], 
    dependencies=[Depends(use_db_key)]
)
app.include_router(
    meals.router, 
    prefix="/api/v1", 
    tags=["餐次"], 
    dependencies=[Depends(use_db_key)]
)
app.include_router(
    orders.router, 
    prefix="/api/v1", 
    tags=["订单"], 
    dependencies=[Depends(use_db_key)]
)
app.include_router(
    logs.router, 
    prefix="/api/v1", 
    tags=["日志"], 
    dependencies=[Depends(use_db_key)]
)
app.include_router(env.router, prefix="/api/v1", tags=["环境"])


@app.get("/api/v1/health", tags=["系统"])
def health():
    """健康检查接口"""
    try:
        # 测试数据库连接
        db_manager.get_connection()
        return {
            "status": "healthy",
            "version": "2.0.0",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "version": "2.0.0",
            "database": f"error: {str(e)}"
        }


@app.get("/", tags=["系统"])
def root():
    """根路径"""
    return {
        "name": "GangHaoFan API",
        "version": "2.0.0",
        "description": "罡好饭餐饮订购系统API"
    }
