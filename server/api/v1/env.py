"""
环境和配置路由模块
重构自原 routers/env.py，提供环境信息查询
"""

from fastapi import APIRouter

# 这个模块主要被auth.py使用，保持简单结构

router = APIRouter()

# 环境相关的路由已经在auth.py中实现
# 这里保留空的路由器以保持兼容性