# Phase 1: 基础重构详细执行方案

## 概述
Phase 1 专注于代码架构的基础重构，包括后端模块化重组和前端组件优化。目标是建立清晰的模块边界和标准化的代码结构。

## 执行时间线: 第1-2周

---

## Week 1: 后端重构

### Day 1-2: 重构目录结构和模块划分

#### 目标
将现有单体代码重构为模块化架构，建立清晰的层次结构。

#### 具体操作

##### 1. 创建新的目录结构
```bash
# 在 server/ 目录下创建新的模块目录
mkdir -p server/config/environments
mkdir -p server/core
mkdir -p server/models
mkdir -p server/services
mkdir -p server/api/v1
mkdir -p server/schemas
mkdir -p server/utils
mkdir -p server/tests
mkdir -p server/migrations/versions
```

##### 2. 创建配置管理模块

**新建文件: `server/config/__init__.py`**
```python
# 空文件，标记为Python包
```

**新建文件: `server/config/settings.py`**
```python
from pydantic import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # 数据库配置
    database_url: str = "duckdb:///data/ganghaofan.duckdb"
    
    # JWT配置
    jwt_secret_key: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24 * 7  # 7天
    
    # 微信小程序配置
    wechat_app_id: Optional[str] = None
    wechat_app_secret: Optional[str] = None
    
    # API配置
    api_title: str = "罡好饭 API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # 开发模式
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 全局设置实例
settings = Settings()
```

**新建文件: `server/config/environments/development.py`**
```python
from ..settings import Settings

class DevelopmentSettings(Settings):
    debug: bool = True
    database_url: str = "duckdb:///data/ganghaofan_dev.duckdb"
```

**新建文件: `server/config/environments/production.py`**
```python
from ..settings import Settings

class ProductionSettings(Settings):
    debug: bool = False
    # 生产环境特定配置
```

##### 3. 重构核心模块

**修改文件: `server/core/database.py`** (基于现有 `server/db.py`)
```python
# 将现有 db.py 的内容迁移到这里
# 添加连接池管理和事务处理优化
import duckdb
from contextlib import contextmanager
from typing import Generator
from ..config.settings import settings

class DatabaseManager:
    def __init__(self):
        self.db_path = settings.database_url.replace("duckdb://", "")
        self._connection = None
    
    @property
    def connection(self):
        if self._connection is None:
            self._connection = duckdb.connect(self.db_path)
            self._init_schema()
        return self._connection
    
    def _init_schema(self):
        # 迁移现有的数据库初始化逻辑
        pass
    
    @contextmanager
    def transaction(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        conn = self.connection
        try:
            conn.begin()
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

# 全局数据库实例
db_manager = DatabaseManager()
```

**新建文件: `server/core/exceptions.py`** (基于现有 `server/core/exceptions.py`)
```python
# 保持现有的异常类，添加新的业务异常
class BaseApplicationError(Exception):
    """应用基础异常"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class ValidationError(BaseApplicationError):
    """数据验证错误"""
    pass

class BusinessRuleError(BaseApplicationError):
    """业务规则错误"""
    pass

class ConcurrencyError(BaseApplicationError):
    """并发控制错误"""
    pass

class InsufficientBalanceError(BusinessRuleError):
    """余额不足错误"""
    pass

class MealCapacityExceededError(BusinessRuleError):
    """餐次容量超限错误"""
    pass
```

**修改文件: `server/core/security.py`** (基于现有 `server/utils/security.py`)
```python
# 将现有的JWT和安全相关代码迁移到这里
# 添加更完善的权限验证逻辑
```

##### 4. 创建数据模型层

**新建文件: `server/models/__init__.py`**
```python
from .base import BaseModel
from .user import User, UserCreate, UserUpdate
from .meal import Meal, MealCreate, MealUpdate
from .order import Order, OrderCreate, OrderUpdate

__all__ = [
    "BaseModel",
    "User", "UserCreate", "UserUpdate",
    "Meal", "MealCreate", "MealUpdate", 
    "Order", "OrderCreate", "OrderUpdate"
]
```

**新建文件: `server/models/base.py`**
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel, Field

class BaseModel(PydanticBaseModel):
    """基础模型"""
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TimestampMixin:
    """时间戳混入"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
```

**新建文件: `server/models/user.py`**
```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from .base import BaseModel as AppBaseModel, TimestampMixin

class UserBase(BaseModel):
    openid: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: bool = False

class UserCreate(UserBase):
    """用户创建模型"""
    pass

class UserUpdate(BaseModel):
    """用户更新模型"""
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

class User(UserBase, TimestampMixin):
    """完整用户模型"""
    user_id: int
    balance_cents: int = 0
    
    class Config:
        from_attributes = True
```

**新建文件: `server/models/meal.py`**
```python
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from .base import BaseModel as AppBaseModel, TimestampMixin

class MealOption(BaseModel):
    """餐次选项模型"""
    id: str
    name: str
    price_cents: int

class MealBase(BaseModel):
    date: date
    slot: str  # 'lunch' or 'dinner'
    description: str
    base_price_cents: int
    capacity: int
    options: List[MealOption] = []
    
    @validator('slot')
    def validate_slot(cls, v):
        if v not in ['lunch', 'dinner']:
            raise ValueError('slot must be lunch or dinner')
        return v

class MealCreate(MealBase):
    """餐次创建模型"""
    pass

class MealUpdate(BaseModel):
    """餐次更新模型"""
    description: Optional[str] = None
    base_price_cents: Optional[int] = None
    capacity: Optional[int] = None
    options: Optional[List[MealOption]] = None
    status: Optional[str] = None

class Meal(MealBase, TimestampMixin):
    """完整餐次模型"""
    meal_id: int
    status: str = 'published'
    creator_id: int
    
    class Config:
        from_attributes = True
```

**新建文件: `server/models/order.py`**
```python
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .base import BaseModel as AppBaseModel, TimestampMixin

class OrderOption(BaseModel):
    """订单选项模型"""
    id: str
    name: str
    price_cents: int

class OrderBase(BaseModel):
    meal_id: int
    quantity: int = 1
    selected_options: List[OrderOption] = []
    total_price_cents: int

class OrderCreate(OrderBase):
    """订单创建模型"""
    pass

class OrderUpdate(BaseModel):
    """订单更新模型"""
    quantity: Optional[int] = None
    selected_options: Optional[List[OrderOption]] = None

class Order(OrderBase, TimestampMixin):
    """完整订单模型"""
    order_id: int
    user_id: int
    status: str = 'active'
    
    class Config:
        from_attributes = True
```

##### 5. 重构路由模块

**修改文件: `server/api/__init__.py`**
```python
from fastapi import APIRouter
from .v1 import auth, meals, orders, users

api_router = APIRouter()

# 包含所有v1路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(meals.router, prefix="/meals", tags=["餐次"])
api_router.include_router(orders.router, prefix="/orders", tags=["订单"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
```

**修改文件: `server/api/v1/auth.py`** (基于现有 `server/routers/auth.py`)
```python
# 保持现有的认证路由逻辑
# 添加对新服务层的调用
from fastapi import APIRouter, Depends, HTTPException
from ...services.auth_service import AuthService
from ...schemas.auth import LoginRequest, LoginResponse

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, auth_service: AuthService = Depends()):
    """微信登录"""
    return await auth_service.login(request.code, request.db_key)

# 其他认证相关路由...
```

### Day 3-4: 服务层抽象

#### 目标
将业务逻辑从路由层抽离到服务层，实现更好的代码组织和可测试性。

#### 具体操作

##### 1. 创建认证服务

**新建文件: `server/services/__init__.py`**
```python
from .auth_service import AuthService
from .meal_service import MealService
from .order_service import OrderService
from .user_service import UserService

__all__ = [
    "AuthService",
    "MealService", 
    "OrderService",
    "UserService"
]
```

**新建文件: `server/services/auth_service.py`**
```python
from datetime import datetime, timedelta
from typing import Optional
import jwt
import requests
from ..core.database import db_manager
from ..core.exceptions import AuthenticationError, ValidationError
from ..models.user import User, UserCreate
from ..config.settings import settings

class AuthService:
    """认证服务"""
    
    def __init__(self):
        self.db = db_manager
    
    async def login(self, code: str, db_key: str) -> dict:
        """微信登录"""
        try:
            # 验证数据库访问权限
            self._validate_db_access(db_key)
            
            # 获取微信用户信息
            openid = await self._get_openid_from_code(code)
            
            # 获取或创建用户
            user = self._get_or_create_user(openid)
            
            # 生成JWT token
            token = self._generate_token(user.user_id)
            
            return {
                "token": token,
                "user": user,
                "is_admin": user.is_admin
            }
        except Exception as e:
            raise AuthenticationError(f"登录失败: {str(e)}")
    
    def _validate_db_access(self, db_key: str):
        """验证数据库访问权限"""
        # 基于现有的口令验证逻辑
        pass
    
    async def _get_openid_from_code(self, code: str) -> str:
        """从微信code获取openid"""
        # 基于现有的微信API调用逻辑
        pass
    
    def _get_or_create_user(self, openid: str) -> User:
        """获取或创建用户"""
        with self.db.transaction() as conn:
            # 基于现有的用户查询和创建逻辑
            pass
    
    def _generate_token(self, user_id: int) -> str:
        """生成JWT token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    def verify_token(self, token: str) -> Optional[int]:
        """验证token并返回用户ID"""
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token已过期")
        except jwt.InvalidTokenError:
            raise AuthenticationError("无效的token")
```

##### 2. 创建餐次服务

**新建文件: `server/services/meal_service.py`** (基于现有 `server/routers/meals.py`)
```python
from datetime import date
from typing import List, Optional
from ..core.database import db_manager
from ..core.exceptions import ValidationError, BusinessRuleError, PermissionDeniedError
from ..models.meal import Meal, MealCreate, MealUpdate

class MealService:
    """餐次服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def create_meal(self, meal_data: MealCreate, creator_id: int) -> Meal:
        """创建餐次"""
        with self.db.transaction() as conn:
            # 验证创建者权限
            if not self._is_admin(creator_id):
                raise PermissionDeniedError("需要管理员权限")
            
            # 验证日期时段唯一性
            if self._meal_exists(meal_data.date, meal_data.slot):
                raise BusinessRuleError("该日期时段已存在餐次")
            
            # 创建餐次
            meal_id = self._insert_meal(conn, meal_data, creator_id)
            
            # 记录日志
            self._log_meal_operation(conn, meal_id, "create", creator_id)
            
            return self.get_meal(meal_id)
    
    def update_meal_status(self, meal_id: int, status: str, operator_id: int) -> Meal:
        """更新餐次状态"""
        with self.db.transaction() as conn:
            # 验证权限
            if not self._is_admin(operator_id):
                raise PermissionDeniedError("需要管理员权限")
            
            # 验证状态转换
            current_meal = self.get_meal(meal_id)
            self._validate_status_transition(current_meal.status, status)
            
            # 更新状态
            self._update_meal_status(conn, meal_id, status)
            
            # 记录日志
            self._log_meal_operation(conn, meal_id, f"status_change_{status}", operator_id)
            
            return self.get_meal(meal_id)
    
    def get_meals_by_date_range(self, start_date: date, end_date: date) -> List[Meal]:
        """按日期范围获取餐次"""
        # 基于现有的查询逻辑
        pass
    
    def get_meal(self, meal_id: int) -> Optional[Meal]:
        """获取单个餐次"""
        # 基于现有的查询逻辑
        pass
    
    def _is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        pass
    
    def _meal_exists(self, date: date, slot: str) -> bool:
        """检查餐次是否已存在"""
        pass
    
    def _validate_status_transition(self, current_status: str, new_status: str):
        """验证状态转换是否合法"""
        valid_transitions = {
            'published': ['locked', 'canceled'],
            'locked': ['completed', 'canceled'],
            'completed': [],
            'canceled': []
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise BusinessRuleError(f"无法从 {current_status} 转换到 {new_status}")
    
    def _insert_meal(self, conn, meal_data: MealCreate, creator_id: int) -> int:
        """插入餐次数据"""
        pass
    
    def _update_meal_status(self, conn, meal_id: int, status: str):
        """更新餐次状态"""
        pass
    
    def _log_meal_operation(self, conn, meal_id: int, operation: str, operator_id: int):
        """记录操作日志"""
        pass
```

##### 3. 重构订单服务

**修改文件: `server/services/order_service.py`** (基于现有 `server/services/order_service.py`)
```python
# 保持现有的订单服务逻辑
# 添加更完善的异常处理和日志记录
# 优化事务处理和并发控制

from typing import List, Optional
from ..core.database import db_manager
from ..core.exceptions import (
    ValidationError, BusinessRuleError, 
    InsufficientBalanceError, MealCapacityExceededError
)
from ..models.order import Order, OrderCreate, OrderUpdate
from ..models.meal import Meal

class OrderService:
    """订单服务 - 增强版"""
    
    def __init__(self):
        self.db = db_manager
    
    def create_order(self, order_data: OrderCreate, user_id: int) -> Order:
        """创建订单 - 增强版本"""
        with self.db.transaction() as conn:
            # 基于现有逻辑，添加更完善的验证和异常处理
            meal = self._get_meal_with_lock(conn, order_data.meal_id)
            
            # 验证餐次状态
            if meal.status != 'published':
                raise BusinessRuleError("餐次不可订购")
            
            # 验证容量限制
            if self._check_capacity_exceeded(conn, order_data.meal_id, order_data.quantity):
                raise MealCapacityExceededError("餐次容量不足")
            
            # 验证用户是否已有订单
            if self._user_has_order_for_meal(conn, user_id, order_data.meal_id):
                raise BusinessRuleError("用户已有该餐次的订单")
            
            # 计算总价
            total_price = self._calculate_total_price(meal, order_data)
            
            # 验证余额
            if not self._check_sufficient_balance(conn, user_id, total_price):
                raise InsufficientBalanceError("余额不足")
            
            # 创建订单
            order_id = self._insert_order(conn, order_data, user_id, total_price)
            
            # 扣除余额
            self._deduct_balance(conn, user_id, total_price, order_id)
            
            # 记录日志
            self._log_order_operation(conn, order_id, "create", user_id)
            
            return self.get_order(order_id)
    
    def modify_order(self, order_id: int, order_data: OrderUpdate, user_id: int) -> Order:
        """修改订单"""
        with self.db.transaction() as conn:
            # 基于现有逻辑，实现原子性的取消+创建操作
            pass
    
    # 其他现有方法保持不变，添加更好的异常处理
```

##### 4. 创建用户服务

**新建文件: `server/services/user_service.py`**
```python
from typing import List, Optional
from ..core.database import db_manager
from ..core.exceptions import ValidationError, BusinessRuleError
from ..models.user import User, UserUpdate

class UserService:
    """用户服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def get_user_profile(self, user_id: int) -> Optional[User]:
        """获取用户资料"""
        pass
    
    def update_user_profile(self, user_id: int, user_data: UserUpdate) -> User:
        """更新用户资料"""
        pass
    
    def get_user_balance(self, user_id: int) -> int:
        """获取用户余额"""
        pass
    
    def get_user_order_history(self, user_id: int, limit: int = 50, offset: int = 0) -> List[dict]:
        """获取用户订单历史"""
        # 新功能：过滤用户相关的订单历史
        pass
    
    def recharge_balance(self, user_id: int, amount_cents: int, operator_id: int) -> dict:
        """充值余额（管理员操作）"""
        pass
```

### Day 5: 异常处理和日志优化

#### 目标
建立统一的异常处理机制和完善的日志记录系统。

#### 具体操作

##### 1. 优化错误处理器

**修改文件: `server/core/error_handler.py`** (基于现有文件)
```python
# 扩展现有的错误处理器
# 添加更详细的错误分类和处理逻辑
# 增加错误码映射和国际化支持

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from .exceptions import *
import logging

logger = logging.getLogger(__name__)

class ErrorCode:
    """错误码常量"""
    # 认证相关 (1000-1999)
    INVALID_TOKEN = "1001"
    TOKEN_EXPIRED = "1002"
    PERMISSION_DENIED = "1003"
    
    # 业务逻辑相关 (2000-2999)
    VALIDATION_ERROR = "2001"
    BUSINESS_RULE_ERROR = "2002"
    INSUFFICIENT_BALANCE = "2003"
    CAPACITY_EXCEEDED = "2004"
    
    # 系统相关 (5000-5999)
    INTERNAL_ERROR = "5001"
    DATABASE_ERROR = "5002"

async def business_exception_handler(request: Request, exc: BaseApplicationError):
    """业务异常处理器"""
    logger.warning(f"Business error: {exc.message}", extra={
        "error_code": exc.error_code,
        "path": request.url.path,
        "method": request.method
    })
    
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """验证异常处理器"""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": ErrorCode.VALIDATION_ERROR,
            "message": exc.message,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# 其他异常处理器...
```

##### 2. 更新应用入口

**修改文件: `server/app.py`**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import api_router
from .config.settings import settings
from .core.error_handler import (
    business_exception_handler,
    validation_exception_handler,
    BaseApplicationError,
    ValidationError
)

def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        debug=settings.debug
    )
    
    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册异常处理器
    app.add_exception_handler(BaseApplicationError, business_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # 注册路由
    app.include_router(api_router, prefix=settings.api_prefix)
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.api_version}
    
    return app

# 应用实例
app = create_app()
```

---

## Week 2: 前端重构

### Day 1-2: 组件模块化

#### 目标
重构现有组件，提升复用性和可维护性。

#### 具体操作

##### 1. 创建基础组件库

**新建目录结构:**
```bash
mkdir -p client/miniprogram/components/base/button
mkdir -p client/miniprogram/components/base/input
mkdir -p client/miniprogram/components/base/dialog
mkdir -p client/miniprogram/components/base/loading
mkdir -p client/miniprogram/components/base/toast
```

**新建文件: `client/miniprogram/components/base/button/button.ts`**
```typescript
/**
 * 基础按钮组件
 * 
 * @description 标准化的按钮组件，支持多种样式和状态
 * @version 2.0.0
 */
Component({
  properties: {
    /** 按钮类型 */
    type: {
      type: String,
      value: 'primary' // primary, secondary, danger, ghost
    },
    /** 按钮大小 */
    size: {
      type: String,
      value: 'medium' // small, medium, large
    },
    /** 是否禁用 */
    disabled: {
      type: Boolean,
      value: false
    },
    /** 是否加载中 */
    loading: {
      type: Boolean,
      value: false
    },
    /** 按钮文本 */
    text: {
      type: String,
      value: ''
    },
    /** 是否为块级按钮 */
    block: {
      type: Boolean,
      value: false
    }
  },

  methods: {
    onTap() {
      if (this.data.disabled || this.data.loading) {
        return;
      }
      this.triggerEvent('tap');
    }
  }
});
```

**新建文件: `client/miniprogram/components/base/button/button.wxml`**
```xml
<button 
  class="base-button base-button--{{type}} base-button--{{size}} {{block ? 'base-button--block' : ''}} {{disabled ? 'base-button--disabled' : ''}}"
  disabled="{{disabled || loading}}"
  bindtap="onTap"
>
  <loading wx:if="{{loading}}" class="base-button__loading" />
  <text class="base-button__text">{{text}}</text>
</button>
```

**新建文件: `client/miniprogram/components/base/button/button.wxss`**
```css
.base-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8rpx;
  font-size: 32rpx;
  font-weight: 500;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.base-button--primary {
  background: var(--color-primary);
  color: #fff;
}

.base-button--secondary {
  background: var(--color-secondary);
  color: var(--color-text-primary);
}

.base-button--danger {
  background: var(--color-error);
  color: #fff;
}

.base-button--ghost {
  background: transparent;
  border: 2rpx solid var(--color-primary);
  color: var(--color-primary);
}

.base-button--small {
  height: 60rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
}

.base-button--medium {
  height: 80rpx;
  padding: 0 32rpx;
  font-size: 32rpx;
}

.base-button--large {
  height: 100rpx;
  padding: 0 40rpx;
  font-size: 36rpx;
}

.base-button--block {
  width: 100%;
}

.base-button--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.base-button__loading {
  margin-right: 16rpx;
}
```

##### 2. 重构业务组件

**修改文件: `client/miniprogram/components/slot-card/slot-card.ts`**
```typescript
/**
 * 时间段卡片组件 - 重构版
 * 
 * @description 显示餐次信息和订餐状态的卡片组件
 * @version 2.0.0
 */
import { formatCurrency, formatDate } from '../../core/utils/format';
import { MealSlot } from '../../types/business';

Component({
  properties: {
    /** 餐次数据 */
    meal: {
      type: Object,
      value: null
    },
    /** 是否显示管理员操作 */
    showAdminActions: {
      type: Boolean,
      value: false
    },
    /** 当前用户的订单 */
    userOrder: {
      type: Object,
      value: null
    }
  },

  data: {
    statusText: '',
    statusColor: '',
    canOrder: false,
    canModify: false
  },

  observers: {
    'meal, userOrder': function(meal: MealSlot, userOrder: any) {
      if (meal) {
        this.updateStatus(meal, userOrder);
      }
    }
  },

  methods: {
    updateStatus(meal: MealSlot, userOrder: any) {
      const now = new Date();
      const mealDate = new Date(meal.date);
      
      let statusText = '';
      let statusColor = '';
      let canOrder = false;
      let canModify = false;

      if (meal.status === 'published') {
        if (userOrder) {
          statusText = `已订餐 (${userOrder.quantity}份)`;
          statusColor = 'success';
          canModify = true;
        } else {
          statusText = '可订餐';
          statusColor = 'primary';
          canOrder = true;
        }
      } else if (meal.status === 'locked') {
        statusText = '已锁定';
        statusColor = 'warning';
      } else if (meal.status === 'completed') {
        statusText = '已完成';
        statusColor = 'info';
      } else if (meal.status === 'canceled') {
        statusText = '已取消';
        statusColor = 'error';
      }

      this.setData({
        statusText,
        statusColor,
        canOrder,
        canModify
      });
    },

    onTapCard() {
      if (this.data.canOrder) {
        this.triggerEvent('order', { meal: this.data.meal });
      } else if (this.data.canModify) {
        this.triggerEvent('modify', { 
          meal: this.data.meal,
          order: this.data.userOrder 
        });
      }
    },

    onTapAdminAction(e: any) {
      const action = e.currentTarget.dataset.action;
      this.triggerEvent('adminAction', {
        action,
        meal: this.data.meal
      });
    }
  }
});
```

### Day 3-4: API层优化

#### 目标
重构API调用层，实现统一的错误处理和请求缓存。

#### 具体操作

##### 1. 重构基础API类

**修改文件: `client/miniprogram/core/api/base.ts`**
```typescript
/**
 * API基础类 - 重构版
 * 
 * @description 统一的API请求封装，包含错误处理、重试机制和缓存
 * @version 2.0.0
 */
import { getStorageSync } from '../../utils/storage';
import { showToast, showModal } from '../../utils/ui';

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error_code?: string;
  timestamp?: string;
}

export interface RequestConfig {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  data?: any;
  header?: Record<string, string>;
  timeout?: number;
  cache?: boolean;
  cacheDuration?: number;
  retry?: boolean;
  retryCount?: number;
  showLoading?: boolean;
  loadingText?: string;
}

class ApiClient {
  private baseURL: string;
  private cache: Map<string, { data: any; expires: number }> = new Map();
  private defaultTimeout = 10000;
  private defaultRetryCount = 3;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  /**
   * 通用请求方法
   */
  async request<T = any>(config: RequestConfig): Promise<ApiResponse<T>> {
    const {
      url,
      method = 'GET',
      data,
      header = {},
      timeout = this.defaultTimeout,
      cache = false,
      cacheDuration = 5 * 60 * 1000, // 5分钟
      retry = true,
      retryCount = this.defaultRetryCount,
      showLoading = false,
      loadingText = '请求中...'
    } = config;

    const fullUrl = `${this.baseURL}${url}`;
    const cacheKey = this.getCacheKey(fullUrl, method, data);

    // 检查缓存
    if (cache && method === 'GET') {
      const cached = this.getFromCache(cacheKey);
      if (cached) {
        return cached;
      }
    }

    // 显示加载提示
    if (showLoading) {
      wx.showLoading({ title: loadingText, mask: true });
    }

    try {
      const response = await this.makeRequest({
        url: fullUrl,
        method,
        data,
        header: this.buildHeaders(header),
        timeout
      });

      const result = this.processResponse<T>(response);

      // 缓存GET请求结果
      if (cache && method === 'GET' && result.success) {
        this.setToCache(cacheKey, result, cacheDuration);
      }

      return result;

    } catch (error) {
      // 重试机制
      if (retry && retryCount > 0) {
        await this.delay(1000); // 等待1秒后重试
        return this.request({
          ...config,
          retryCount: retryCount - 1,
          showLoading: false // 重试时不显示loading
        });
      }

      return this.handleError(error);
    } finally {
      if (showLoading) {
        wx.hideLoading();
      }
    }
  }

  /**
   * GET请求
   */
  async get<T = any>(url: string, params?: any, config?: Partial<RequestConfig>): Promise<ApiResponse<T>> {
    const queryString = params ? this.buildQueryString(params) : '';
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    
    return this.request<T>({
      url: fullUrl,
      method: 'GET',
      cache: true,
      ...config
    });
  }

  /**
   * POST请求
   */
  async post<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<ApiResponse<T>> {
    return this.request<T>({
      url,
      method: 'POST',
      data,
      showLoading: true,
      ...config
    });
  }

  /**
   * PUT请求
   */
  async put<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<ApiResponse<T>> {
    return this.request<T>({
      url,
      method: 'PUT',
      data,
      showLoading: true,
      ...config
    });
  }

  /**
   * DELETE请求
   */
  async delete<T = any>(url: string, config?: Partial<RequestConfig>): Promise<ApiResponse<T>> {
    return this.request<T>({
      url,
      method: 'DELETE',
      showLoading: true,
      ...config
    });
  }

  private async makeRequest(options: any): Promise<any> {
    return new Promise((resolve, reject) => {
      wx.request({
        ...options,
        success: resolve,
        fail: reject
      });
    });
  }

  private buildHeaders(customHeaders: Record<string, string>): Record<string, string> {
    const token = getStorageSync('token');
    const dbKey = getStorageSync('dbKey');

    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (dbKey) {
      headers['X-DB-Key'] = dbKey;
    }

    return headers;
  }

  private processResponse<T>(response: any): ApiResponse<T> {
    const { statusCode, data } = response;

    if (statusCode >= 200 && statusCode < 300) {
      return data || { success: true };
    }

    // 处理HTTP错误状态码
    if (statusCode === 401) {
      this.handleUnauthorized();
    }

    return {
      success: false,
      message: data?.message || `请求失败 (${statusCode})`,
      error_code: data?.error_code
    };
  }

  private handleError(error: any): ApiResponse {
    console.error('API请求错误:', error);
    
    let message = '网络请求失败';
    
    if (error.errMsg) {
      if (error.errMsg.includes('timeout')) {
        message = '请求超时，请检查网络连接';
      } else if (error.errMsg.includes('fail')) {
        message = '网络连接失败';
      }
    }

    // 显示错误提示
    showToast(message, 'error');

    return {
      success: false,
      message,
      error_code: 'NETWORK_ERROR'
    };
  }

  private handleUnauthorized() {
    // 清除本地认证信息
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    
    // 跳转到登录页面
    wx.reLaunch({
      url: '/pages/index/index'
    });
  }

  private getCacheKey(url: string, method: string, data?: any): string {
    const dataString = data ? JSON.stringify(data) : '';
    return `${method}_${url}_${dataString}`;
  }

  private getFromCache(key: string): any {
    const cached = this.cache.get(key);
    if (cached && cached.expires > Date.now()) {
      return cached.data;
    }
    this.cache.delete(key);
    return null;
  }

  private setToCache(key: string, data: any, duration: number) {
    this.cache.set(key, {
      data,
      expires: Date.now() + duration
    });
  }

  private buildQueryString(params: Record<string, any>): string {
    return Object.entries(params)
      .filter(([_, value]) => value !== undefined && value !== null)
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&');
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 清除缓存
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * 清除特定URL的缓存
   */
  clearCacheByUrl(url: string) {
    const keysToDelete = Array.from(this.cache.keys()).filter(key => key.includes(url));
    keysToDelete.forEach(key => this.cache.delete(key));
  }
}

// 导出默认实例
export const apiClient = new ApiClient('http://127.0.0.1:8000/api/v1');
```

##### 2. 重构具体API模块

**修改文件: `client/miniprogram/core/api/meal.ts`**
```typescript
/**
 * 餐次相关API - 重构版
 */
import { apiClient } from './base';
import { Meal, MealCreate } from '../../types/business';

export class MealAPI {
  /**
   * 获取日期范围内的餐次
   */
  static async getMealsByDateRange(startDate: string, endDate: string) {
    return apiClient.get<Meal[]>('/meals', {
      start_date: startDate,
      end_date: endDate
    }, {
      cache: true,
      cacheDuration: 2 * 60 * 1000 // 2分钟缓存
    });
  }

  /**
   * 获取单个餐次详情
   */
  static async getMealDetail(mealId: number) {
    return apiClient.get<Meal>(`/meals/${mealId}`, undefined, {
      cache: true,
      cacheDuration: 1 * 60 * 1000 // 1分钟缓存
    });
  }

  /**
   * 创建餐次（管理员）
   */
  static async createMeal(mealData: MealCreate) {
    const result = await apiClient.post<Meal>('/meals', mealData);
    
    // 清除相关缓存
    if (result.success) {
      apiClient.clearCacheByUrl('/meals');
    }
    
    return result;
  }

  /**
   * 更新餐次状态（管理员）
   */
  static async updateMealStatus(mealId: number, status: string) {
    const result = await apiClient.put<Meal>(`/meals/${mealId}/status`, { status });
    
    // 清除相关缓存
    if (result.success) {
      apiClient.clearCacheByUrl('/meals');
    }
    
    return result;
  }

  /**
   * 获取餐次订单列表（管理员）
   */
  static async getMealOrders(mealId: number) {
    return apiClient.get(`/meals/${mealId}/orders`, undefined, {
      cache: true,
      cacheDuration: 30 * 1000 // 30秒缓存
    });
  }
}
```

### Day 5: 状态管理优化

#### 目标
实现统一的状态管理，优化用户认证和主题切换逻辑。

#### 具体操作

##### 1. 创建状态管理器

**新建文件: `client/miniprogram/core/store/index.ts`**
```typescript
/**
 * 简单状态管理器
 * 
 * @description 基于观察者模式的轻量级状态管理
 * @version 2.0.0
 */
export interface StoreState {
  // 用户相关状态
  user: {
    isLoggedIn: boolean;
    userInfo: any;
    isAdmin: boolean;
    balance: number;
  };
  
  // 主题相关状态  
  theme: {
    isDark: boolean;
    primaryColor: string;
  };
  
  // 应用相关状态
  app: {
    loading: boolean;
    networkStatus: 'online' | 'offline';
    dbKey: string;
  };
}

type Listener<T = any> = (newState: T, oldState: T) => void;
type StateSelector<T = any> = (state: StoreState) => T;

class Store {
  private state: StoreState = {
    user: {
      isLoggedIn: false,
      userInfo: null,
      isAdmin: false,
      balance: 0
    },
    theme: {
      isDark: true, // 默认深色主题
      primaryColor: '#007AFF'
    },
    app: {
      loading: false,
      networkStatus: 'online',
      dbKey: ''
    }
  };

  private listeners: Map<string, Listener[]> = new Map();

  /**
   * 获取状态
   */
  getState(): StoreState;
  getState<T>(selector: StateSelector<T>): T;
  getState<T>(selector?: StateSelector<T>): StoreState | T {
    if (selector) {
      return selector(this.state);
    }
    return this.state;
  }

  /**
   * 更新状态
   */
  setState<K extends keyof StoreState>(
    module: K, 
    updates: Partial<StoreState[K]>
  ): void {
    const oldModuleState = { ...this.state[module] };
    const newModuleState = { ...oldModuleState, ...updates };
    
    this.state[module] = newModuleState;
    
    // 通知监听器
    this.notifyListeners(module, newModuleState, oldModuleState);
  }

  /**
   * 订阅状态变化
   */
  subscribe<K extends keyof StoreState>(
    module: K,
    listener: Listener<StoreState[K]>
  ): () => void {
    const key = String(module);
    
    if (!this.listeners.has(key)) {
      this.listeners.set(key, []);
    }
    
    this.listeners.get(key)!.push(listener);
    
    // 返回取消订阅函数
    return () => {
      const listeners = this.listeners.get(key);
      if (listeners) {
        const index = listeners.indexOf(listener);
        if (index > -1) {
          listeners.splice(index, 1);
        }
      }
    };
  }

  /**
   * 批量更新状态
   */
  batchUpdate(updates: {
    [K in keyof StoreState]?: Partial<StoreState[K]>
  }): void {
    Object.entries(updates).forEach(([module, moduleUpdates]) => {
      if (moduleUpdates) {
        this.setState(module as keyof StoreState, moduleUpdates);
      }
    });
  }

  private notifyListeners<K extends keyof StoreState>(
    module: K,
    newState: StoreState[K],
    oldState: StoreState[K]
  ): void {
    const listeners = this.listeners.get(String(module));
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(newState, oldState);
        } catch (error) {
          console.error('状态监听器执行错误:', error);
        }
      });
    }
  }

  /**
   * 清除所有状态
   */
  clear(): void {
    this.state = {
      user: {
        isLoggedIn: false,
        userInfo: null,
        isAdmin: false,
        balance: 0
      },
      theme: {
        isDark: true,
        primaryColor: '#007AFF'
      },
      app: {
        loading: false,
        networkStatus: 'online',
        dbKey: ''
      }
    };
    
    this.listeners.clear();
  }
}

// 全局状态实例
export const store = new Store();
```

##### 2. 创建认证状态管理

**新建文件: `client/miniprogram/core/store/auth.ts`**
```typescript
/**
 * 认证状态管理
 */
import { store } from './index';
import { getStorageSync, setStorageSync, removeStorageSync } from '../../utils/storage';

export class AuthStore {
  /**
   * 初始化认证状态
   */
  static init() {
    const token = getStorageSync('token');
    const userInfo = getStorageSync('userInfo');
    const isAdmin = getStorageSync('isAdmin') || false;
    const dbKey = getStorageSync('dbKey') || '';
    
    if (token && userInfo) {
      store.setState('user', {
        isLoggedIn: true,
        userInfo,
        isAdmin
      });
    }
    
    store.setState('app', { dbKey });
  }

  /**
   * 设置登录状态
   */
  static setLoginState(token: string, userInfo: any, isAdmin: boolean = false) {
    // 保存到本地存储
    setStorageSync('token', token);
    setStorageSync('userInfo', userInfo);
    setStorageSync('isAdmin', isAdmin);
    
    // 更新状态
    store.setState('user', {
      isLoggedIn: true,
      userInfo,
      isAdmin,
      balance: userInfo.balance_cents || 0
    });
  }

  /**
   * 设置数据库密钥
   */
  static setDbKey(dbKey: string) {
    setStorageSync('dbKey', dbKey);
    store.setState('app', { dbKey });
  }

  /**
   * 更新用户余额
   */
  static updateBalance(balance: number) {
    const userInfo = store.getState(state => state.user.userInfo);
    const updatedUserInfo = { ...userInfo, balance_cents: balance };
    
    setStorageSync('userInfo', updatedUserInfo);
    store.setState('user', {
      userInfo: updatedUserInfo,
      balance
    });
  }

  /**
   * 清除登录状态
   */
  static clearLoginState() {
    // 清除本地存储
    removeStorageSync('token');
    removeStorageSync('userInfo');
    removeStorageSync('isAdmin');
    
    // 清除状态
    store.setState('user', {
      isLoggedIn: false,
      userInfo: null,
      isAdmin: false,
      balance: 0
    });
  }

  /**
   * 检查是否已登录
   */
  static isLoggedIn(): boolean {
    return store.getState(state => state.user.isLoggedIn);
  }

  /**
   * 检查是否为管理员
   */
  static isAdmin(): boolean {
    return store.getState(state => state.user.isAdmin);
  }

  /**
   * 获取当前用户信息
   */
  static getCurrentUser() {
    return store.getState(state => state.user.userInfo);
  }
}
```

##### 3. 创建主题状态管理

**新建文件: `client/miniprogram/core/store/theme.ts`**
```typescript
/**
 * 主题状态管理
 */
import { store } from './index';
import { getStorageSync, setStorageSync } from '../../utils/storage';

export class ThemeStore {
  /**
   * 初始化主题状态
   */
  static init() {
    const isDark = getStorageSync('theme.isDark');
    const primaryColor = getStorageSync('theme.primaryColor') || '#007AFF';
    
    store.setState('theme', {
      isDark: isDark !== null ? isDark : true, // 默认深色主题
      primaryColor
    });
    
    this.applyTheme();
  }

  /**
   * 切换主题模式
   */
  static toggleTheme() {
    const currentTheme = store.getState(state => state.theme);
    const newIsDark = !currentTheme.isDark;
    
    this.setTheme(newIsDark, currentTheme.primaryColor);
  }

  /**
   * 设置主题
   */
  static setTheme(isDark: boolean, primaryColor?: string) {
    const currentTheme = store.getState(state => state.theme);
    const newTheme = {
      isDark,
      primaryColor: primaryColor || currentTheme.primaryColor
    };
    
    // 保存到本地存储
    setStorageSync('theme.isDark', isDark);
    if (primaryColor) {
      setStorageSync('theme.primaryColor', primaryColor);
    }
    
    // 更新状态
    store.setState('theme', newTheme);
    
    // 应用主题
    this.applyTheme();
  }

  /**
   * 应用主题到页面
   */
  static applyTheme() {
    const theme = store.getState(state => state.theme);
    
    // 设置CSS变量
    const systemInfo = wx.getSystemInfoSync();
    if (systemInfo.platform !== 'devtools') {
      wx.setNavigationBarColor({
        frontColor: theme.isDark ? '#ffffff' : '#000000',
        backgroundColor: theme.isDark ? '#1f1f1f' : '#ffffff'
      });
    }
    
    // 通知页面更新主题
    const pages = getCurrentPages();
    pages.forEach(page => {
      if (page.onThemeChange && typeof page.onThemeChange === 'function') {
        page.onThemeChange(theme);
      }
    });
  }

  /**
   * 获取当前主题
   */
  static getCurrentTheme() {
    return store.getState(state => state.theme);
  }

  /**
   * 订阅主题变化
   */
  static subscribeThemeChange(callback: (theme: any) => void) {
    return store.subscribe('theme', callback);
  }
}
```

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "phase1_plan", "status": "completed", "content": "Create Phase 1 detailed execution plan (\u57fa\u7840\u91cd\u6784)"}, {"id": "phase2_plan", "status": "in_progress", "content": "Create Phase 2 detailed execution plan (\u529f\u80fd\u5b8c\u5584)"}, {"id": "phase3_plan", "status": "pending", "content": "Create Phase 3 detailed execution plan (\u6587\u6863\u548c\u6d4b\u8bd5)"}]