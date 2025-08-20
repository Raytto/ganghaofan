# Phase 3: 文档和测试详细执行方案

## 概述
Phase 3 专注于完善文档体系和建立测试体系，确保代码质量和系统可维护性。目标是建立AI友好的文档结构和全面的测试覆盖。

## 执行时间线: 第5周

---

## Week 5: 完善文档和测试

### Day 1-2: API文档完善

#### 目标
建立完整的API文档体系，包括OpenAPI规范文档、接口示例和错误码文档。

#### 具体操作

##### 1. 生成OpenAPI文档

**新建文件: `server/schemas/__init__.py`**
```python
from .auth import *
from .meal import *
from .order import *
from .user import *
from .common import *

__all__ = [
    # Auth schemas
    "LoginRequest", "LoginResponse", "TokenInfo",
    
    # Meal schemas  
    "MealResponse", "MealListResponse", "MealCreateRequest", "MealUpdateRequest",
    
    # Order schemas
    "OrderResponse", "OrderListResponse", "OrderCreateRequest", "OrderUpdateRequest", 
    "OrderModifyRequest", "OrderBatchRequest",
    
    # User schemas
    "UserProfileResponse", "UserOrderHistoryResponse", "UserBalanceHistoryResponse",
    
    # Common schemas
    "ApiResponse", "PaginationInfo", "ErrorResponse"
]
```

**新建文件: `server/schemas/common.py`**
```python
from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """通用API响应格式"""
    success: bool = Field(description="请求是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    error_code: Optional[str] = Field(None, description="错误码")
    timestamp: Optional[str] = Field(None, description="响应时间戳")

class ErrorResponse(BaseModel):
    """错误响应格式"""
    success: bool = Field(False, description="请求失败")
    message: str = Field(description="错误消息")
    error_code: str = Field(description="错误码")
    timestamp: str = Field(description="错误时间戳")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "余额不足",
                "error_code": "INSUFFICIENT_BALANCE",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }

class PaginationInfo(BaseModel):
    """分页信息"""
    limit: int = Field(description="每页数量")
    offset: int = Field(description="偏移量")
    total_count: int = Field(description="总记录数")
    has_more: bool = Field(description="是否有更多数据")

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    items: List[T] = Field(description="数据列表")
    pagination: PaginationInfo = Field(description="分页信息")
```

**修改文件: `server/schemas/auth.py`**
```python
from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    """登录请求"""
    code: str = Field(description="微信登录凭证", example="061234567890123456789")
    db_key: str = Field(description="数据库访问密钥", example="dev_key")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "061234567890123456789",
                "db_key": "dev_key"
            }
        }

class TokenInfo(BaseModel):
    """Token信息"""
    token: str = Field(description="访问令牌")
    expires_in: int = Field(description="过期时间(秒)")
    token_type: str = Field(default="Bearer", description="令牌类型")

class UserInfo(BaseModel):
    """用户信息"""
    user_id: int = Field(description="用户ID")
    openid: str = Field(description="微信OpenID")
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    balance_cents: int = Field(description="余额(分)")
    is_admin: bool = Field(description="是否为管理员")

class LoginResponse(BaseModel):
    """登录响应"""
    token_info: TokenInfo = Field(description="令牌信息")
    user_info: UserInfo = Field(description="用户信息")
    
    class Config:
        schema_extra = {
            "example": {
                "token_info": {
                    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "expires_in": 604800,
                    "token_type": "Bearer"
                },
                "user_info": {
                    "user_id": 123,
                    "openid": "ox_12345678901234567890",
                    "nickname": "张三",
                    "avatar_url": "https://...",
                    "balance_cents": 5000,
                    "is_admin": false
                }
            }
        }
```

**修改文件: `server/app.py`** (添加OpenAPI配置)
```python
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from .config.settings import settings

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
        debug=settings.debug
    )
    
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
    
    # 其他配置...
    return app
```

##### 2. 创建API文档汇总

**新建文件: `doc/API.md`**
```markdown
# 罡好饭 API 接口文档

## 概述

罡好饭是一个基于微信小程序的餐饮订购系统，提供完整的餐次管理、订单处理、用户管理功能。

### 基础信息

- **Base URL**: `http://127.0.0.1:8000/api/v1` (开发环境)
- **认证方式**: JWT Bearer Token + DB Key
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证说明

所有API请求都需要包含以下请求头：

```http
Authorization: Bearer <JWT_TOKEN>
X-DB-Key: <DATABASE_KEY>
```

### 通用响应格式

#### 成功响应
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 错误响应
```json
{
  "success": false,
  "message": "错误描述",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 常见错误码

| 错误码 | HTTP状态码 | 说明 | 解决方案 |
|--------|------------|------|----------|
| `INVALID_TOKEN` | 401 | JWT Token无效或过期 | 重新登录获取Token |
| `PERMISSION_DENIED` | 403 | 权限不足 | 检查用户权限级别 |
| `VALIDATION_ERROR` | 422 | 请求数据格式错误 | 检查请求参数格式 |
| `BUSINESS_RULE_ERROR` | 400 | 业务规则违反 | 根据错误消息调整业务逻辑 |
| `INSUFFICIENT_BALANCE` | 400 | 余额不足 | 充值或减少订单金额 |
| `CAPACITY_EXCEEDED` | 400 | 餐次容量不足 | 选择其他餐次或减少数量 |
| `ORDER_LOCKED` | 400 | 订单已锁定 | 等待管理员解锁或选择其他餐次 |
| `INVALID_STATUS_TRANSITION` | 400 | 状态流转不合法 | 检查当前状态和目标状态 |
| `CONCURRENCY_ERROR` | 409 | 并发冲突 | 稍后重试 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 | 联系技术支持 |

---

## 认证相关接口

### POST /auth/login
微信小程序登录

**请求参数：**
```json
{
  "code": "061234567890123456789",
  "db_key": "dev_key"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "token_info": {
      "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "expires_in": 604800,
      "token_type": "Bearer"
    },
    "user_info": {
      "user_id": 123,
      "openid": "ox_12345678901234567890",
      "nickname": "张三",
      "avatar_url": "https://...",
      "balance_cents": 5000,
      "is_admin": false
    }
  }
}
```

---

## 餐次管理接口

### GET /meals
获取餐次列表

**查询参数：**
- `start_date` (string): 开始日期，格式 YYYY-MM-DD
- `end_date` (string): 结束日期，格式 YYYY-MM-DD

**响应示例：**
```json
{
  "success": true,
  "data": [
    {
      "meal_id": 123,
      "date": "2024-01-15",
      "slot": "lunch",
      "description": "香辣鸡腿饭",
      "base_price_cents": 2000,
      "capacity": 50,
      "status": "published",
      "options": [
        {
          "id": "chicken_leg",
          "name": "加鸡腿",
          "price_cents": 300
        }
      ],
      "ordered_count": 15,
      "available_capacity": 35,
      "created_at": "2024-01-14T15:00:00Z"
    }
  ]
}
```

### POST /meals
创建餐次（管理员）

**请求参数：**
```json
{
  "date": "2024-01-15",
  "slot": "lunch",
  "description": "香辣鸡腿饭",
  "base_price_cents": 2000,
  "capacity": 50,
  "options": [
    {
      "id": "chicken_leg",
      "name": "加鸡腿", 
      "price_cents": 300
    }
  ]
}
```

### PUT /meals/{meal_id}/status
更新餐次状态（管理员）

**请求参数：**
```json
{
  "status": "locked",
  "reason": "准备开始制作"
}
```

**餐次状态流转：**
- `published` → `locked` → `completed`
- `published` → `canceled`
- `locked` → `canceled`

**订单状态流转：**
- `active` ←→ `locked` (管理员可锁定/解锁)
- `active/locked` → `completed` (正常完成)
- `active` → `canceled` (用户取消)
- `active/locked` → `refunded` (餐次取消退款)

---

## 订单管理接口

### POST /orders
创建订单

**请求参数：**
```json
{
  "meal_id": 123,
  "quantity": 2,
  "selected_options": [
    {
      "id": "chicken_leg",
      "name": "加鸡腿",
      "price_cents": 300
    }
  ],
  "notes": "不要辣"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "order_id": 456,
    "meal_id": 123,
    "user_id": 789,
    "quantity": 2,
    "selected_options": [...],
    "total_price_cents": 4600,
    "status": "active",
    "can_modify": true,
    "created_at": "2024-01-14T16:30:00Z"
  }
}
```

### PUT /orders/{order_id}/modify
修改订单（原子性操作）

**请求参数：**
```json
{
  "new_quantity": 3,
  "new_selected_options": [
    {
      "id": "chicken_leg",
      "name": "加鸡腿",
      "price_cents": 300
    }
  ],
  "new_notes": "微辣"
}
```

### DELETE /orders/{order_id}
取消订单

**响应示例：**
```json
{
  "success": true,
  "data": {
    "order_id": 456,
    "status": "canceled",
    "refund_amount_cents": 4600,
    "canceled_at": "2024-01-14T17:00:00Z"
  }
}
```

---

## 用户管理接口

### GET /users/profile
获取用户资料摘要

**响应示例：**
```json
{
  "success": true,
  "data": {
    "user_info": {
      "user_id": 123,
      "nickname": "张三",
      "balance_cents": 5000,
      "is_admin": false,
      "created_at": "2024-01-01T00:00:00Z"
    },
    "recent_activity": {
      "recent_orders": 5,
      "recent_spent_cents": 10000,
      "recent_meal_days": 3
    },
    "lifetime_stats": {
      "total_orders": 25,
      "total_spent_cents": 50000
    }
  }
}
```

### GET /users/orders/history
获取用户订单历史

**查询参数：**
- `start_date` (string): 开始日期
- `end_date` (string): 结束日期
- `status` (string): 订单状态过滤
- `limit` (int): 每页数量，默认50
- `offset` (int): 偏移量，默认0

**响应示例：**
```json
{
  "success": true,
  "data": {
    "orders": [
      {
        "order_id": 456,
        "meal_date": "2024-01-15",
        "meal_slot": "lunch",
        "meal_description": "香辣鸡腿饭",
        "quantity": 2,
        "total_price_cents": 4600,
        "status": "active",
        "order_time": "2024-01-14T16:30:00Z"
      }
    ],
    "total_count": 25,
    "page_info": {
      "limit": 50,
      "offset": 0,
      "has_more": false
    },
    "statistics": {
      "general": {
        "total_orders": 25,
        "total_spent_cents": 50000,
        "total_meals": 30,
        "total_days": 15
      }
    }
  }
}
```

### GET /users/balance/history
获取用户余额变动历史

**查询参数：**
- `limit` (int): 每页数量，默认50
- `offset` (int): 偏移量，默认0

**响应示例：**
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "ledger_id": 123,
        "user_id": 456,
        "amount_cents": -2000,
        "description": "订单消费",
        "related_order_id": 789,
        "balance_after_cents": 8000,
        "created_at": "2024-01-14T16:30:00Z"
      }
    ],
    "total_count": 15,
    "page_info": {
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

### POST /users/balance/recharge
管理员充值用户余额

**请求参数：**
```json
{
  "user_id": 123,
  "amount_cents": 10000
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "old_balance_cents": 5000,
    "new_balance_cents": 15000,
    "recharge_amount_cents": 10000
  }
}
```

---

## 管理员专用接口

### GET /meals/{meal_id}/orders
获取餐次订单列表（管理员）

### GET /meals/{meal_id}/export
导出餐次订单Excel（管理员）

### POST /orders/batch
批量处理订单（管理员）

**请求参数：**
```json
{
  "order_ids": [456, 457, 458],
  "action": "complete",
  "reason": "餐次制作完成"
}
```

**支持的操作：**
- `complete`: 完成订单
- `cancel`: 取消订单
- `refund`: 退款订单

### POST /orders/lock-by-meal
锁定餐次的所有订单（管理员）

**请求参数：**
```json
{
  "meal_id": 123
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "meal_id": 123,
    "locked_orders": 15,
    "status": "locked"
  }
}
```

### POST /orders/unlock-by-meal
解锁餐次的所有订单（管理员）

**请求参数：**
```json
{
  "meal_id": 123
}
```

### POST /orders/complete-by-meal
完成餐次的所有订单（管理员）

**请求参数：**
```json
{
  "meal_id": 123
}
```

### POST /orders/refund-by-meal
退款餐次的所有订单（管理员）

**请求参数：**
```json
{
  "meal_id": 123,
  "reason": "餐次取消，全额退款"
}
```

---

## 实时监控接口

### GET /health
健康检查

**响应示例：**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /system/consistency
数据一致性检查（管理员）

**响应示例：**
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T10:30:00Z",
    "checks": {
      "balance": {
        "status": "pass",
        "inconsistent_count": 0
      },
      "capacity": {
        "status": "fail", 
        "over_capacity_count": 1,
        "details": [...]
      }
    }
  }
}
```

---

## 开发调试

### 请求示例（curl）

```bash
# 登录
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"code":"test_code","db_key":"dev_key"}'

# 获取餐次列表
curl -X GET "http://127.0.0.1:8000/api/v1/meals?start_date=2024-01-15&end_date=2024-01-20" \
  -H "Authorization: Bearer <token>" \
  -H "X-DB-Key: dev_key"

# 创建订单
curl -X POST "http://127.0.0.1:8000/api/v1/orders" \
  -H "Authorization: Bearer <token>" \
  -H "X-DB-Key: dev_key" \
  -H "Content-Type: application/json" \
  -d '{"meal_id":123,"quantity":2,"selected_options":[]}'
```

### 前端调用示例（JavaScript）

```javascript
// 使用封装的API客户端
import { MealAPI, OrderAPI } from './core/api';

// 获取餐次列表
const meals = await MealAPI.getMealsByDateRange('2024-01-15', '2024-01-20');

// 创建订单
const order = await OrderAPI.createOrder({
  meal_id: 123,
  quantity: 2,
  selected_options: []
});
```

---

## 更新历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2024-01-15 | 初始版本，包含基础功能 |
| 1.1.0 | 2024-01-20 | 新增订单修改、批量处理功能 |
| 1.2.0 | 2024-01-25 | 新增数据导出、一致性检查功能 |

---

## 相关文档

- [系统架构设计](./ARCHITECTURE.md)
- [数据库设计](./technical/database-schema.md)
- [部署指南](./DEPLOYMENT.md)
- [故障排查](./guides/troubleshooting.md)
```

### Day 3-4: 测试覆盖

#### 目标
建立全面的测试体系，包括单元测试、集成测试和端到端测试。

#### 具体操作

##### 1. 后端测试框架搭建

**新建文件: `server/tests/conftest.py`**
```python
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from ..app import create_app
from ..core.database import DatabaseManager
from ..config.settings import Settings

class TestSettings(Settings):
    """测试环境配置"""
    debug: bool = True
    database_url: str = "duckdb:///:memory:"  # 内存数据库
    jwt_secret_key: str = "test-secret-key"

@pytest.fixture
def test_settings():
    """测试配置"""
    return TestSettings()

@pytest.fixture
def test_db(test_settings):
    """测试数据库"""
    db_manager = DatabaseManager()
    db_manager.db_path = ":memory:"
    
    # 初始化测试数据库
    with db_manager.connection as conn:
        # 创建表结构
        conn.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            openid VARCHAR(100) UNIQUE NOT NULL,
            nickname VARCHAR(100),
            avatar_url TEXT,
            balance_cents INTEGER DEFAULT 0,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.execute("""
        CREATE TABLE meals (
            meal_id INTEGER PRIMARY KEY,
            date DATE NOT NULL,
            slot VARCHAR(20) NOT NULL,
            description TEXT NOT NULL,
            base_price_cents INTEGER NOT NULL,
            capacity INTEGER NOT NULL,
            options TEXT,
            status VARCHAR(20) DEFAULT 'published',
            creator_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, slot)
        )
        """)
        
        conn.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            meal_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            selected_options TEXT,
            total_price_cents INTEGER NOT NULL,
            notes TEXT,
            status VARCHAR(20) DEFAULT 'active',
            can_modify BOOLEAN DEFAULT TRUE,
            modify_deadline TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)
        
        conn.execute("""
        CREATE TABLE ledger (
            ledger_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            description TEXT,
            related_order_id INTEGER,
            balance_after_cents INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.execute("""
        CREATE TABLE logs (
            log_id INTEGER PRIMARY KEY,
            operation_type VARCHAR(50),
            user_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    
    yield db_manager
    
    # 清理
    db_manager._connection = None

@pytest.fixture
def app(test_settings, test_db):
    """测试应用"""
    # 临时替换全局设置
    import server.config.settings as settings_module
    original_settings = settings_module.settings
    settings_module.settings = test_settings
    
    # 临时替换数据库管理器
    import server.core.database as db_module
    original_db_manager = db_module.db_manager
    db_module.db_manager = test_db
    
    app = create_app()
    
    yield app
    
    # 恢复原始配置
    settings_module.settings = original_settings
    db_module.db_manager = original_db_manager

@pytest.fixture
def client(app):
    """测试客户端"""
    return TestClient(app)

@pytest.fixture
def sample_user(test_db):
    """示例用户"""
    with test_db.connection as conn:
        conn.execute("""
        INSERT INTO users (openid, nickname, balance_cents, is_admin)
        VALUES ('test_openid_123', '测试用户', 10000, FALSE)
        """)
        user_id = conn.lastrowid
    
    return {
        "user_id": user_id,
        "openid": "test_openid_123",
        "nickname": "测试用户",
        "balance_cents": 10000,
        "is_admin": False
    }

@pytest.fixture
def admin_user(test_db):
    """管理员用户"""
    with test_db.connection as conn:
        conn.execute("""
        INSERT INTO users (openid, nickname, balance_cents, is_admin)
        VALUES ('admin_openid_456', '管理员', 50000, TRUE)
        """)
        user_id = conn.lastrowid
    
    return {
        "user_id": user_id,
        "openid": "admin_openid_456", 
        "nickname": "管理员",
        "balance_cents": 50000,
        "is_admin": True
    }

@pytest.fixture
def sample_meal(test_db, admin_user):
    """示例餐次"""
    import json
    
    with test_db.connection as conn:
        options = json.dumps([
            {"id": "chicken_leg", "name": "加鸡腿", "price_cents": 300},
            {"id": "extra_rice", "name": "加饭", "price_cents": 100}
        ])
        
        conn.execute("""
        INSERT INTO meals (date, slot, description, base_price_cents, capacity, options, creator_id)
        VALUES ('2024-01-15', 'lunch', '香辣鸡腿饭', 2000, 50, ?, ?)
        """, [options, admin_user["user_id"]])
        meal_id = conn.lastrowid
    
    return {
        "meal_id": meal_id,
        "date": "2024-01-15",
        "slot": "lunch",
        "description": "香辣鸡腿饭",
        "base_price_cents": 2000,
        "capacity": 50,
        "status": "published"
    }

@pytest.fixture
def auth_headers(sample_user):
    """认证请求头"""
    # 这里应该生成真实的JWT token，简化为mock
    return {
        "Authorization": "Bearer test_token",
        "X-DB-Key": "test_key"
    }

@pytest.fixture
def admin_headers(admin_user):
    """管理员认证请求头"""
    return {
        "Authorization": "Bearer admin_token",
        "X-DB-Key": "test_key"
    }
```

##### 2. 服务层单元测试

**新建文件: `server/tests/test_order_service.py`**
```python
import pytest
from datetime import datetime, date, timedelta
from ..services.order_service import OrderService
from ..models.order import OrderCreate, OrderModify
from ..core.exceptions import *

class TestOrderService:
    """订单服务测试"""
    
    def test_create_order_success(self, test_db, sample_user, sample_meal):
        """测试成功创建订单"""
        order_service = OrderService()
        
        order_data = OrderCreate(
            meal_id=sample_meal["meal_id"],
            quantity=2,
            selected_options=[
                {"id": "chicken_leg", "name": "加鸡腿", "price_cents": 300}
            ],
            total_price_cents=4600  # (2000 + 300) * 2
        )
        
        order = order_service.create_order(order_data, sample_user["user_id"])
        
        assert order.order_id is not None
        assert order.meal_id == sample_meal["meal_id"]
        assert order.user_id == sample_user["user_id"]
        assert order.quantity == 2
        assert order.total_price_cents == 4600
        assert order.status == "active"
    
    def test_create_order_insufficient_balance(self, test_db, sample_meal):
        """测试余额不足时创建订单失败"""
        # 创建余额不足的用户
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO users (openid, nickname, balance_cents)
            VALUES ('poor_user', '穷用户', 1000)
            """)
            poor_user_id = conn.lastrowid
        
        order_service = OrderService()
        
        order_data = OrderCreate(
            meal_id=sample_meal["meal_id"],
            quantity=2,
            selected_options=[],
            total_price_cents=4000
        )
        
        with pytest.raises(InsufficientBalanceError):
            order_service.create_order(order_data, poor_user_id)
    
    def test_create_order_capacity_exceeded(self, test_db, sample_user):
        """测试容量超限时创建订单失败"""
        # 创建容量很小的餐次
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO meals (date, slot, description, base_price_cents, capacity, creator_id)
            VALUES ('2024-01-16', 'dinner', '小容量餐次', 2000, 1, 1)
            """)
            small_meal_id = conn.lastrowid
            
            # 创建一个已存在的订单占用容量
            conn.execute("""
            INSERT INTO orders (user_id, meal_id, quantity, total_price_cents, status)
            VALUES (999, ?, 1, 2000, 'active')
            """, [small_meal_id])
        
        order_service = OrderService()
        
        order_data = OrderCreate(
            meal_id=small_meal_id,
            quantity=1,
            selected_options=[],
            total_price_cents=2000
        )
        
        with pytest.raises(MealCapacityExceededError):
            order_service.create_order(order_data, sample_user["user_id"])
    
    def test_modify_order_success(self, test_db, sample_user, sample_meal):
        """测试成功修改订单"""
        order_service = OrderService()
        
        # 先创建订单
        order_data = OrderCreate(
            meal_id=sample_meal["meal_id"],
            quantity=1,
            selected_options=[],
            total_price_cents=2000
        )
        order = order_service.create_order(order_data, sample_user["user_id"])
        
        # 修改订单
        modify_data = OrderModify(
            new_quantity=2,
            new_selected_options=[
                {"id": "chicken_leg", "name": "加鸡腿", "price_cents": 300}
            ]
        )
        
        modified_order = order_service.modify_order_atomic(
            order.order_id, modify_data, sample_user["user_id"]
        )
        
        assert modified_order.quantity == 2
        assert len(modified_order.selected_options) == 1
        assert modified_order.total_price_cents == 4600  # (2000 + 300) * 2
    
    def test_modify_order_unauthorized(self, test_db, sample_user, admin_user, sample_meal):
        """测试无权限修改他人订单"""
        order_service = OrderService()
        
        # 用户A创建订单
        order_data = OrderCreate(
            meal_id=sample_meal["meal_id"],
            quantity=1,
            selected_options=[],
            total_price_cents=2000
        )
        order = order_service.create_order(order_data, sample_user["user_id"])
        
        # 用户B尝试修改
        modify_data = OrderModify(
            new_quantity=2,
            new_selected_options=[]
        )
        
        with pytest.raises(PermissionDeniedError):
            order_service.modify_order_atomic(
                order.order_id, modify_data, admin_user["user_id"]
            )
    
    def test_concurrent_order_creation(self, test_db, sample_meal):
        """测试并发创建订单的处理"""
        import threading
        import time
        
        # 创建容量为1的餐次
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO meals (date, slot, description, base_price_cents, capacity, creator_id)
            VALUES ('2024-01-17', 'lunch', '并发测试餐次', 2000, 1, 1)
            """)
            concurrent_meal_id = conn.lastrowid
            
            # 创建两个有余额的用户
            conn.execute("""
            INSERT INTO users (openid, nickname, balance_cents)
            VALUES ('user1', 'User1', 10000), ('user2', 'User2', 10000)
            """)
            user1_id = conn.execute("SELECT user_id FROM users WHERE openid = 'user1'").fetchone()['user_id']
            user2_id = conn.execute("SELECT user_id FROM users WHERE openid = 'user2'").fetchone()['user_id']
        
        order_service = OrderService()
        results = {}
        
        def create_order_thread(user_id, thread_name):
            try:
                order_data = OrderCreate(
                    meal_id=concurrent_meal_id,
                    quantity=1,
                    selected_options=[],
                    total_price_cents=2000
                )
                order = order_service.create_order_with_retry(order_data, user_id)
                results[thread_name] = {"success": True, "order": order}
            except Exception as e:
                results[thread_name] = {"success": False, "error": str(e)}
        
        # 启动两个并发线程
        thread1 = threading.Thread(target=create_order_thread, args=(user1_id, "thread1"))
        thread2 = threading.Thread(target=create_order_thread, args=(user2_id, "thread2"))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # 验证结果：只有一个成功，一个失败
        success_count = sum(1 for result in results.values() if result["success"])
        assert success_count == 1, f"Expected 1 success, got {success_count}. Results: {results}"
    
    def test_order_status_transitions(self, test_db, sample_user, sample_meal, admin_user):
        """测试订单状态流转"""
        order_service = OrderService()
        
        # 创建订单
        order_data = OrderCreate(
            meal_id=sample_meal["meal_id"],
            quantity=1,
            selected_options=[],
            total_price_cents=2000
        )
        order = order_service.create_order(order_data, sample_user["user_id"])
        assert order.status == "active"
        
        # 测试锁定订单
        result = order_service.lock_orders_by_meal(
            sample_meal["meal_id"], 
            admin_user["openid"]
        )
        assert result["locked_orders"] == 1
        
        # 验证订单状态已变为locked
        with test_db.connection as conn:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order.order_id]
            ).fetchone()["status"]
            assert order_status == "locked"
        
        # 测试解锁订单
        result = order_service.unlock_orders_by_meal(
            sample_meal["meal_id"], 
            admin_user["openid"]
        )
        assert result["unlocked_orders"] == 1
        
        # 验证订单状态已变回active
        with test_db.connection as conn:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order.order_id]
            ).fetchone()["status"]
            assert order_status == "active"
    
    def test_order_refund_by_meal(self, test_db, sample_user, sample_meal, admin_user):
        """测试餐次取消时的订单退款"""
        order_service = OrderService()
        
        # 创建订单
        order_data = OrderCreate(
            meal_id=sample_meal["meal_id"],
            quantity=1,
            selected_options=[],
            total_price_cents=2000
        )
        order = order_service.create_order(order_data, sample_user["user_id"])
        
        # 记录用户当前余额
        with test_db.connection as conn:
            old_balance = conn.execute(
                "SELECT balance_cents FROM users WHERE user_id = ?", 
                [sample_user["user_id"]]
            ).fetchone()["balance_cents"]
        
        # 餐次取消，退款所有订单
        result = order_service.refund_orders_by_meal(
            sample_meal["meal_id"], 
            admin_user["openid"], 
            "测试餐次取消"
        )
        
        assert result["refunded_orders"] == 1
        assert result["total_refund_amount_cents"] == 2000
        
        # 验证订单状态为refunded
        with test_db.connection as conn:
            order_status = conn.execute(
                "SELECT status FROM orders WHERE order_id = ?", 
                [order.order_id]
            ).fetchone()["status"]
            assert order_status == "refunded"
            
            # 验证余额已恢复
            new_balance = conn.execute(
                "SELECT balance_cents FROM users WHERE user_id = ?", 
                [sample_user["user_id"]]
            ).fetchone()["balance_cents"]
            assert new_balance == old_balance + 2000
```

##### 3. API集成测试

**新建文件: `server/tests/test_api_orders.py`**
```python
import pytest
import json
from fastapi.testclient import TestClient

class TestOrdersAPI:
    """订单API集成测试"""
    
    def test_create_order_api(self, client, auth_headers, sample_meal):
        """测试创建订单API"""
        order_data = {
            "meal_id": sample_meal["meal_id"],
            "quantity": 2,
            "selected_options": [
                {"id": "chicken_leg", "name": "加鸡腿", "price_cents": 300}
            ],
            "notes": "不要辣"
        }
        
        response = client.post(
            "/api/v1/orders",
            json=order_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["meal_id"] == sample_meal["meal_id"]
        assert data["data"]["quantity"] == 2
        assert data["data"]["status"] == "active"
    
    def test_create_order_validation_error(self, client, auth_headers):
        """测试创建订单时的验证错误"""
        # 缺少必需字段
        order_data = {
            "quantity": 2
            # 缺少 meal_id
        }
        
        response = client.post(
            "/api/v1/orders",
            json=order_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "validation" in data["message"].lower()
    
    def test_get_user_orders(self, client, auth_headers, sample_user, sample_meal, test_db):
        """测试获取用户订单列表"""
        # 先创建一些订单
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO orders (user_id, meal_id, quantity, total_price_cents, status, created_at)
            VALUES 
                (?, ?, 1, 2000, 'active', '2024-01-15 12:00:00'),
                (?, ?, 2, 4000, 'completed', '2024-01-14 12:00:00')
            """, [
                sample_user["user_id"], sample_meal["meal_id"],
                sample_user["user_id"], sample_meal["meal_id"]
            ])
        
        response = client.get(
            "/api/v1/users/orders/history",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["orders"]) == 2
        assert data["data"]["total_count"] == 2
    
    def test_modify_order_api(self, client, auth_headers, sample_user, sample_meal, test_db):
        """测试修改订单API"""
        # 先创建订单
        with test_db.connection as conn:
            conn.execute("""
            INSERT INTO orders (user_id, meal_id, quantity, total_price_cents, status, can_modify)
            VALUES (?, ?, 1, 2000, 'active', TRUE)
            """, [sample_user["user_id"], sample_meal["meal_id"]])
            order_id = conn.lastrowid
        
        modify_data = {
            "new_quantity": 2,
            "new_selected_options": [
                {"id": "chicken_leg", "name": "加鸡腿", "price_cents": 300}
            ],
            "new_notes": "加辣"
        }
        
        response = client.put(
            f"/api/v1/orders/{order_id}/modify",
            json=modify_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["quantity"] == 2
    
    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/orders")
        assert response.status_code == 401
    
    def test_admin_batch_operations(self, client, admin_headers, sample_meal, test_db):
        """测试管理员批量操作"""
        # 创建一些订单
        order_ids = []
        with test_db.connection as conn:
            for i in range(3):
                conn.execute("""
                INSERT INTO orders (user_id, meal_id, quantity, total_price_cents, status)
                VALUES (?, ?, 1, 2000, 'active')
                """, [100 + i, sample_meal["meal_id"]])
                order_ids.append(conn.lastrowid)
        
        batch_data = {
            "order_ids": order_ids,
            "action": "complete",
            "reason": "测试批量完成"
        }
        
        response = client.post(
            "/api/v1/orders/batch",
            json=batch_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success_count"] == 3
        assert data["data"]["failed_count"] == 0
```

##### 4. 前端测试示例

**新建文件: `client/miniprogram/tests/api.test.js`**
```javascript
/**
 * API测试示例
 * 注意：微信小程序的测试需要特殊的测试框架，这里提供思路
 */

// 使用Jest或类似框架进行API模块测试
describe('API Client', () => {
  beforeEach(() => {
    // Mock wx.request
    global.wx = {
      request: jest.fn(),
      showLoading: jest.fn(),
      hideLoading: jest.fn(),
      showToast: jest.fn()
    };
  });

  describe('MealAPI', () => {
    test('should fetch meals by date range', async () => {
      // Mock成功响应
      wx.request.mockImplementation(({ success }) => {
        success({
          statusCode: 200,
          data: {
            success: true,
            data: [
              {
                meal_id: 123,
                date: '2024-01-15',
                slot: 'lunch',
                description: '香辣鸡腿饭'
              }
            ]
          }
        });
      });

      const { MealAPI } = require('../core/api/meal');
      const result = await MealAPI.getMealsByDateRange('2024-01-15', '2024-01-20');

      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(1);
      expect(result.data[0].meal_id).toBe(123);
    });

    test('should handle network error', async () => {
      // Mock网络错误
      wx.request.mockImplementation(({ fail }) => {
        fail({ errMsg: 'request:fail timeout' });
      });

      const { MealAPI } = require('../core/api/meal');
      const result = await MealAPI.getMealsByDateRange('2024-01-15', '2024-01-20');

      expect(result.success).toBe(false);
      expect(result.error_code).toBe('NETWORK_ERROR');
    });
  });

  describe('OrderAPI', () => {
    test('should create order successfully', async () => {
      wx.request.mockImplementation(({ success }) => {
        success({
          statusCode: 200,
          data: {
            success: true,
            data: {
              order_id: 456,
              meal_id: 123,
              quantity: 2,
              status: 'active'
            }
          }
        });
      });

      const { OrderAPI } = require('../core/api/order');
      const orderData = {
        meal_id: 123,
        quantity: 2,
        selected_options: []
      };
      
      const result = await OrderAPI.createOrder(orderData);

      expect(result.success).toBe(true);
      expect(result.data.order_id).toBe(456);
      expect(wx.showLoading).toHaveBeenCalled();
    });

    test('should handle business rule error', async () => {
      wx.request.mockImplementation(({ success }) => {
        success({
          statusCode: 400,
          data: {
            success: false,
            message: '余额不足',
            error_code: 'INSUFFICIENT_BALANCE'
          }
        });
      });

      const { OrderAPI } = require('../core/api/order');
      const result = await OrderAPI.createOrder({
        meal_id: 123,
        quantity: 2
      });

      expect(result.success).toBe(false);
      expect(result.error_code).toBe('INSUFFICIENT_BALANCE');
    });
  });

  describe('Retry Mechanism', () => {
    test('should retry on network error', async () => {
      let callCount = 0;
      wx.request.mockImplementation(({ success, fail }) => {
        callCount++;
        if (callCount < 3) {
          fail({ errMsg: 'request:fail timeout' });
        } else {
          success({
            statusCode: 200,
            data: { success: true, data: 'success' }
          });
        }
      });

      const { apiClient } = require('../core/api/base');
      const result = await apiClient.get('/test');

      expect(callCount).toBe(3); // 2次重试 + 1次成功
      expect(result.success).toBe(true);
    });
  });
});

// 状态管理测试
describe('State Management', () => {
  beforeEach(() => {
    // Mock wx存储API
    global.wx = {
      getStorageSync: jest.fn(),
      setStorageSync: jest.fn(),
      removeStorageSync: jest.fn()
    };
  });

  describe('StateManager', () => {
    test('should manage state correctly', () => {
      const { stateManager } = require('../core/store');
      
      // 设置状态
      stateManager.setState('user.balance', 1000);
      expect(stateManager.getState('user.balance')).toBe(1000);
      
      // 批量更新
      stateManager.batchUpdate([
        { path: 'user.balance', value: 2000 },
        { path: 'user.isAdmin', value: true }
      ]);
      
      expect(stateManager.getState('user.balance')).toBe(2000);
      expect(stateManager.getState('user.isAdmin')).toBe(true);
    });

    test('should handle state subscription', () => {
      const { stateManager } = require('../core/store');
      const callback = jest.fn();
      
      // 订阅状态变化
      const unsubscribe = stateManager.subscribe('user.balance', callback);
      
      // 状态变化应该触发回调
      stateManager.setState('user.balance', 1500);
      expect(callback).toHaveBeenCalledWith(1500);
      
      // 取消订阅
      unsubscribe();
      stateManager.setState('user.balance', 2000);
      expect(callback).toHaveBeenCalledTimes(1); // 不应该再次被调用
    });

    test('should persist important state', () => {
      const { stateManager } = require('../core/store');
      
      // 设置需要持久化的状态
      stateManager.setState('app.darkMode', true);
      stateManager.setState('user.openId', 'test_openid');
      
      // 应该调用wx.setStorageSync
      expect(wx.setStorageSync).toHaveBeenCalledWith('dark_mode', true);
      expect(wx.setStorageSync).toHaveBeenCalledWith('user_openid', 'test_openid');
    });
  });

  describe('Actions', () => {
    test('should update user login state', () => {
      const { actions, stateManager } = require('../core/store');
      
      actions.user.setLoginState('test_openid', true, 5000);
      
      expect(stateManager.getState('user.isLoggedIn')).toBe(true);
      expect(stateManager.getState('user.openId')).toBe('test_openid');
      expect(stateManager.getState('user.isAdmin')).toBe(true);
      expect(stateManager.getState('user.balance')).toBe(5000);
    });

    test('should toggle dark mode', () => {
      const { actions, stateManager } = require('../core/store');
      
      stateManager.setState('app.darkMode', false);
      actions.app.toggleDarkMode();
      
      expect(stateManager.getState('app.darkMode')).toBe(true);
    });
  });
});

// 权限系统测试
describe('Permission System', () => {
  beforeEach(() => {
    const { stateManager } = require('../core/store');
    // 重置状态
    stateManager.setState('user.isAdmin', false);
    stateManager.setState('app.adminViewEnabled', false);
  });

  describe('PermissionManager', () => {
    test('should check basic permissions', () => {
      const { PermissionManager } = require('../core/utils/permissions');
      
      // 基础权限应该总是允许
      expect(PermissionManager.hasPermission('VIEW_PROFILE')).toBe(true);
      expect(PermissionManager.hasPermission('MANAGE_ORDERS')).toBe(true);
    });

    test('should check admin permissions', () => {
      const { PermissionManager, stateManager } = require('../core/utils/permissions');
      
      // 非管理员不应该有管理员权限
      expect(PermissionManager.hasPermission('ADMIN_MANAGE_MEALS')).toBe(false);
      
      // 设置为管理员并启用管理视图
      stateManager.setState('user.isAdmin', true);
      stateManager.setState('app.adminViewEnabled', true);
      
      // 现在应该有管理员权限
      expect(PermissionManager.hasPermission('ADMIN_MANAGE_MEALS')).toBe(true);
      expect(PermissionManager.hasAdminAccess()).toBe(true);
    });

    test('should guard permissions correctly', () => {
      const { PermissionManager } = require('../core/utils/permissions');
      
      // Mock wx.showToast
      global.wx.showToast = jest.fn();
      
      // 无权限时应该显示错误
      const result = PermissionManager.guardPermission('ADMIN_MANAGE_MEALS');
      expect(result).toBe(false);
      expect(wx.showToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: '您没有权限执行此操作' })
      );
    });
  });
});

// 订单状态工具测试
describe('Order Status Helper', () => {
  describe('OrderStatusHelper', () => {
    test('should validate status transitions', () => {
      const { OrderStatusHelper, OrderStatus } = require('../core/utils/orderStatus');
      
      // 有效的状态流转
      expect(OrderStatusHelper.canTransition(OrderStatus.ACTIVE, OrderStatus.LOCKED)).toBe(true);
      expect(OrderStatusHelper.canTransition(OrderStatus.LOCKED, OrderStatus.ACTIVE)).toBe(true);
      expect(OrderStatusHelper.canTransition(OrderStatus.ACTIVE, OrderStatus.CANCELED)).toBe(true);
      
      // 无效的状态流转
      expect(OrderStatusHelper.canTransition(OrderStatus.COMPLETED, OrderStatus.ACTIVE)).toBe(false);
      expect(OrderStatusHelper.canTransition(OrderStatus.CANCELED, OrderStatus.LOCKED)).toBe(false);
    });

    test('should get correct status text', () => {
      const { OrderStatusHelper, OrderStatus } = require('../core/utils/orderStatus');
      
      expect(OrderStatusHelper.getOrderStatusText(OrderStatus.ACTIVE, 2)).toBe('已订餐 (2份)');
      expect(OrderStatusHelper.getOrderStatusText(OrderStatus.LOCKED, 1)).toBe('已锁定 (1份)');
      expect(OrderStatusHelper.getOrderStatusText(OrderStatus.CANCELED)).toBe('已取消');
    });

    test('should determine order modifiability', () => {
      const { OrderStatusHelper, OrderStatus, MealStatus } = require('../core/utils/orderStatus');
      
      // 活跃订单且餐次已发布时可修改
      expect(OrderStatusHelper.isOrderModifiable(OrderStatus.ACTIVE, MealStatus.PUBLISHED)).toBe(true);
      
      // 锁定订单不可修改
      expect(OrderStatusHelper.isOrderModifiable(OrderStatus.LOCKED, MealStatus.PUBLISHED)).toBe(false);
      
      // 餐次锁定时不可修改
      expect(OrderStatusHelper.isOrderModifiable(OrderStatus.ACTIVE, MealStatus.LOCKED)).toBe(false);
    });
  });
});
```

### Day 5: 部署文档

#### 目标
完善部署流程文档和监控运维手册。

#### 具体操作

##### 1. 创建部署指南

**新建文件: `doc/DEPLOYMENT.md`**
```markdown
# 罡好饭系统部署指南

## 概述

本文档详细说明如何在不同环境中部署罡好饭餐饮订购系统。

## 环境要求

### 服务器要求
- **操作系统**: Linux (Ubuntu 20.04+ 推荐) 或 macOS
- **内存**: 最低 2GB，推荐 4GB+
- **存储**: 最低 20GB 可用空间
- **网络**: 稳定的互联网连接

### 软件依赖
- **Python**: 3.11+
- **Node.js**: 16.0+（仅开发环境）
- **Git**: 版本控制
- **Nginx**: 反向代理（生产环境）
- **Supervisor**: 进程管理（生产环境）

---

## 开发环境部署

### 1. 代码获取
```bash
# 克隆代码仓库
git clone <repository-url> ganghaofan
cd ganghaofan

# 检查项目结构
ls -la
```

### 2. 后端环境配置
```bash
# 创建Conda环境
conda env create -f server/environment.yml

# 激活环境
conda activate ghf-server

# 验证安装
python --version
python -c "import fastapi; print('FastAPI installed')"
```

### 3. 数据库初始化
```bash
# 创建数据目录
mkdir -p server/data

# 创建配置文件
cp server/config/db.json.example server/config/db.json
cp server/config/passphrases.json.example server/config/passphrases.json

# 初始化数据库（首次启动时自动创建）
python -c "from server.db import init_database; init_database()"
```

### 4. 启动开发服务器
```bash
# 方式1：直接启动
python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000

# 方式2：使用Conda环境运行
conda run -n ghf-server python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000

# 验证服务
curl http://127.0.0.1:8000/api/v1/health
```

### 5. 前端开发环境
```bash
# 进入前端目录
cd client

# 安装依赖
npm install

# 配置API地址（在微信开发者工具中）
# 1. 导入 client/miniprogram 目录
# 2. 配置服务器域名：http://127.0.0.1:8000
# 3. 启用开发者模式
```

---

## 生产环境部署

### 1. 服务器准备
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础软件
sudo apt install -y python3.11 python3.11-venv python3-pip
sudo apt install -y nginx supervisor git

# 创建应用用户
sudo useradd -m -s /bin/bash ghfuser
sudo usermod -aG sudo ghfuser

# 切换到应用用户
sudo su - ghfuser
```

### 2. 应用部署
```bash
# 克隆代码
git clone <repository-url> /home/ghfuser/ganghaofan
cd /home/ghfuser/ganghaofan

# 创建Python虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r server/requirements.txt

# 创建生产配置
cp server/config/production.env.example server/config/production.env
# 编辑配置文件，设置生产环境参数

# 创建数据目录
mkdir -p server/data
chmod 750 server/data

# 初始化数据库
python -c "from server.db import init_database; init_database()"
```

### 3. Nginx配置
```bash
# 创建Nginx配置文件
sudo tee /etc/nginx/sites-available/ganghaofan << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 替换为实际域名
    
    # 日志配置
    access_log /var/log/nginx/ganghaofan_access.log;
    error_log /var/log/nginx/ganghaofan_error.log;
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
    
    # 静态文件（如果有）
    location /static/ {
        alias /home/ghfuser/ganghaofan/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # 安全配置
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 文件上传大小限制
    client_max_body_size 10M;
}
EOF

# 启用站点
sudo ln -s /etc/nginx/sites-available/ganghaofan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Supervisor配置
```bash
# 创建Supervisor配置文件
sudo tee /etc/supervisor/conf.d/ganghaofan.conf << 'EOF'
[program:ganghaofan]
command=/home/ghfuser/ganghaofan/venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 --workers 4
directory=/home/ghfuser/ganghaofan
user=ghfuser
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/ganghaofan.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PYTHONPATH="/home/ghfuser/ganghaofan"

[group:ganghaofan-group]
programs=ganghaofan
EOF

# 更新Supervisor配置
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ganghaofan

# 检查状态
sudo supervisorctl status ganghaofan
```

### 5. SSL证书配置（可选）
```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 申请SSL证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run

# 设置自动续期
sudo crontab -e
# 添加：0 2 * * * certbot renew --quiet
```

---

## 环境配置

### 1. 环境变量配置

**生产环境配置文件 (`server/config/production.env`)**:
```env
# 数据库配置
DATABASE_URL=duckdb:///home/ghfuser/ganghaofan/server/data/ganghaofan.duckdb

# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=168

# 微信小程序配置
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret

# API配置
API_TITLE=罡好饭 API
API_VERSION=1.0.0
API_PREFIX=/api/v1

# 安全配置
DEBUG=false
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/ganghaofan/app.log
```

### 2. 数据库配置

**数据库配置文件 (`server/config/db.json`)**:
```json
{
  "path": "/home/ghfuser/ganghaofan/server/data/ganghaofan.duckdb",
  "backup_path": "/home/ghfuser/ganghaofan/backups/",
  "auto_backup": true,
  "backup_interval_hours": 24
}
```

### 3. 访问控制配置

**口令配置文件 (`server/config/passphrases.json`)**:
```json
{
  "production_key": "your-production-database-key",
  "staging_key": "your-staging-database-key"
}
```

---

## 监控与日志

### 1. 应用日志
```bash
# 查看应用日志
sudo tail -f /var/log/supervisor/ganghaofan.log

# 查看Nginx日志
sudo tail -f /var/log/nginx/ganghaofan_access.log
sudo tail -f /var/log/nginx/ganghaofan_error.log

# 查看系统日志
sudo journalctl -u nginx -f
sudo journalctl -u supervisor -f
```

### 2. 性能监控
```bash
# 安装监控工具
sudo apt install -y htop iotop nethogs

# 监控系统资源
htop
iotop -o
nethogs

# 数据库文件大小监控
du -h /home/ghfuser/ganghaofan/server/data/ganghaofan.duckdb
```

### 3. 健康检查脚本

**创建健康检查脚本 (`scripts/health_check.sh`)**:
```bash
#!/bin/bash

# 健康检查脚本
API_URL="http://127.0.0.1:8000/api/v1/health"
LOG_FILE="/var/log/ganghaofan/health_check.log"

# 检查API健康状态
response=$(curl -s -w "%{http_code}" -o /dev/null $API_URL)

if [ $response -eq 200 ]; then
    echo "$(date): API健康检查通过" >> $LOG_FILE
    exit 0
else
    echo "$(date): API健康检查失败，HTTP状态码: $response" >> $LOG_FILE
    
    # 尝试重启服务
    sudo supervisorctl restart ganghaofan
    
    # 发送告警（如果配置了）
    # 这里可以添加邮件或短信告警逻辑
    
    exit 1
fi
```

```bash
# 设置执行权限
chmod +x scripts/health_check.sh

# 添加到定时任务
sudo crontab -e
# 添加：*/5 * * * * /home/ghfuser/ganghaofan/scripts/health_check.sh
```

---

## 备份与恢复

### 1. 自动备份脚本

**创建备份脚本 (`scripts/backup.sh`)**:
```bash
#!/bin/bash

# 备份脚本
BACKUP_DIR="/home/ghfuser/ganghaofan/backups"
DB_FILE="/home/ghfuser/ganghaofan/server/data/ganghaofan.duckdb"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ganghaofan_backup_$DATE.duckdb"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 复制数据库文件
cp $DB_FILE $BACKUP_FILE

# 压缩备份文件
gzip $BACKUP_FILE

# 删除30天前的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "$(date): 备份完成: $BACKUP_FILE.gz"
```

### 2. 数据恢复
```bash
# 停止服务
sudo supervisorctl stop ganghaofan

# 恢复数据库
gunzip -c /path/to/backup.duckdb.gz > /home/ghfuser/ganghaofan/server/data/ganghaofan.duckdb

# 重启服务
sudo supervisorctl start ganghaofan
```

---

## 更新部署

### 1. 应用更新流程
```bash
# 1. 备份当前版本
cd /home/ghfuser/ganghaofan
git tag backup-$(date +%Y%m%d_%H%M%S)

# 2. 备份数据库
./scripts/backup.sh

# 3. 拉取最新代码
git pull origin main

# 4. 更新依赖
source venv/bin/activate
pip install -r server/requirements.txt

# 5. 运行数据库迁移（如果有）
python scripts/migrate.py

# 6. 重启服务
sudo supervisorctl restart ganghaofan

# 7. 验证部署
curl http://127.0.0.1:8000/api/v1/health
```

### 2. 回滚流程
```bash
# 1. 停止服务
sudo supervisorctl stop ganghaofan

# 2. 回滚代码
git reset --hard backup-YYYYMMDD_HHMMSS

# 3. 恢复数据库（如果需要）
# 参考数据恢复步骤

# 4. 重启服务
sudo supervisorctl start ganghaofan
```

---

## 故障排查

### 常见问题

#### 1. 服务启动失败
```bash
# 检查日志
sudo supervisorctl tail ganghaofan stderr

# 检查配置
python -c "from server.config.settings import settings; print(settings)"

# 检查端口占用
sudo netstat -tlnp | grep :8000
```

#### 2. 数据库连接问题
```bash
# 检查数据库文件权限
ls -la /home/ghfuser/ganghaofan/server/data/

# 检查数据库连接
python -c "from server.core.database import db_manager; print(db_manager.connection)"
```

#### 3. 性能问题
```bash
# 检查系统资源
top
df -h
free -h

# 检查数据库大小
du -h /home/ghfuser/ganghaofan/server/data/ganghaofan.duckdb

# 分析慢查询
# 在应用日志中查找耗时较长的操作
```

### 性能优化建议

1. **数据库优化**
   - 定期清理过期日志
   - 添加适当的索引
   - 监控数据库文件大小

2. **应用优化**
   - 启用适当数量的Worker进程
   - 配置连接池
   - 实现查询缓存

3. **系统优化**
   - 配置文件描述符限制
   - 优化内核参数
   - 使用SSD存储

---

## 安全配置

### 1. 防火墙配置
```bash
# 安装ufw
sudo apt install -y ufw

# 配置防火墙规则
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable
```

### 2. 系统安全加固
```bash
# 禁用root SSH登录
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# 配置fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. 应用安全
- 定期更新依赖包
- 使用强密码和密钥
- 启用HTTPS
- 实施访问控制
- 定期安全审计

---

## 微信小程序发布

### 1. 配置服务器域名
在微信公众平台配置以下域名：
- request合法域名：`https://your-domain.com`
- uploadFile合法域名：`https://your-domain.com`
- downloadFile合法域名：`https://your-domain.com`

### 2. 代码审核发布
1. 使用微信开发者工具上传代码
2. 在微信公众平台提交审核
3. 审核通过后发布上线

---

## 联系与支持

如在部署过程中遇到问题，请：

1. 查看相关日志文件
2. 参考故障排查章节
3. 联系技术支持团队

---

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2024-01-15 | 初始部署文档 |
| 1.1 | 2024-01-20 | 添加SSL配置和监控 |
| 1.2 | 2024-01-25 | 完善故障排查和安全配置 |
```

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "phase1_plan", "status": "completed", "content": "Create Phase 1 detailed execution plan (\u57fa\u7840\u91cd\u6784)"}, {"id": "phase2_plan", "status": "completed", "content": "Create Phase 2 detailed execution plan (\u529f\u80fd\u5b8c\u5584)"}, {"id": "phase3_plan", "status": "completed", "content": "Create Phase 3 detailed execution plan (\u6587\u6863\u548c\u6d4b\u8bd5)"}]