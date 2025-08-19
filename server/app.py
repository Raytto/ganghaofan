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

from fastapi import FastAPI
from .routers import auth, users, meals, orders, logs, env
from .db import init_db, init_all_dbs, use_db_key
from fastapi import Depends

app = FastAPI(title="GangHaoFan API", version="0.1.0")


@app.on_event("startup")
def _on_startup():
    """应用启动时初始化数据库表结构"""
    # 初始化默认库和所有配置映射的库
    try:
        init_all_dbs()
    except Exception:
        # 回退至少初始化默认库，避免启动失败
        init_db()


# 注册路由模块，统一使用 /api/v1 前缀
# 登录不强制口令
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1", dependencies=[Depends(use_db_key)])
app.include_router(meals.router, prefix="/api/v1", dependencies=[Depends(use_db_key)])
app.include_router(orders.router, prefix="/api/v1", dependencies=[Depends(use_db_key)])
app.include_router(logs.router, prefix="/api/v1", dependencies=[Depends(use_db_key)])
app.include_router(env.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    """健康检查接口，用于验证服务可用性"""
    return {"ok": True}
