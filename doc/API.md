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