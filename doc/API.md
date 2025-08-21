# 罡好饭 API 接口文档

## 概述

罡好饭是一个基于微信小程序的餐饮订购系统，提供完整的餐次管理、订单处理、用户管理功能，支持**透支功能**，允许用户余额不足时继续订餐。

### 基础信息

- **Base URL**: `http://us.pangruitao.com:8000/api/v1` (公网环境) / `http://127.0.0.1:8000/api/v1` (本地环境)
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
  "details": { ... },
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
| `INSUFFICIENT_BALANCE` | 400 | 余额不足（透支功能启用时为警告） | 充值或使用透支功能继续 |
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

### GET /env/mock
获取Mock环境信息（开发环境）

### POST /env/resolve
解析环境配置

---

## 餐次管理接口

### GET /meals/
获取餐次列表（需要认证）

**查询参数：**
- `status` (string): 餐次状态过滤 (published, locked, completed, canceled)
- `date_from` (string): 开始日期，格式 YYYY-MM-DD  
- `date_to` (string): 结束日期，格式 YYYY-MM-DD
- `limit` (int): 每页数量，默认50
- `offset` (int): 偏移量，默认0

**响应示例：**
```json
{
  "success": true,
  "data": {
    "meals": [
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
    ],
    "total_count": 25,
    "page_info": {
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  }
}
```

### POST /meals/
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

### GET /meals/calendar
获取日历格式的餐次数据

**查询参数：**
- `month` (string): 月份，格式 YYYY-MM

### GET /meals/calendar/batch  
批量获取多月份日历数据

### GET /meals/{meal_id}
获取单个餐次详情

### POST /meals/{meal_id}/lock
锁定餐次（管理员）

**功能说明：** 锁定后用户不能继续下单，但可以修改现有订单

### POST /meals/{meal_id}/unlock
解锁餐次（管理员）

### POST /meals/{meal_id}/cancel
取消餐次（管理员）

**功能说明：** 取消餐次并自动退款所有相关订单，支持透支用户的退款处理

### GET /meals/{meal_id}/export
导出餐次订单Excel（管理员）

**餐次状态流转：**
- `published` → `locked` → `completed`
- `published` → `canceled`
- `locked` → `unlocked` → `published`
- `locked` → `canceled`

---

## 订单管理接口

### POST /orders/orders
创建订单（支持透支）

**请求参数：**
```json
{
  "meal_id": 123,
  "qty": 2,
  "options_json": "{\"chicken_leg\": true}",
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
    "qty": 2,
    "amount_cents": 4600,
    "status": "active",
    "balance_cents": -1400,
    "overdraft_warning": "余额不足，已使用透支功能",
    "created_at": "2024-01-14T16:30:00Z"
  }
}
```

### GET /orders/orders
获取订单列表

### GET /orders/orders/{order_id}
获取单个订单详情

**响应示例：**
```json
{
  "success": true,
  "data": {
    "order_id": 456,
    "meal_id": 123,
    "user_id": 789,
    "qty": 2,
    "amount_cents": 4600,
    "options_json": "{\"chicken_leg\": true}",
    "notes": "不要辣",
    "status": "active",
    "meal_info": {
      "date": "2024-01-15",
      "slot": "lunch",
      "description": "香辣鸡腿饭"
    },
    "user_balance_cents": -1400,
    "can_modify": true,
    "created_at": "2024-01-14T16:30:00Z",
    "updated_at": "2024-01-14T16:30:00Z"
  }
}
```

### PUT /orders/orders/{order_id}
修改订单（支持透支状态下的修改）

**请求参数：**
```json
{
  "qty": 3,
  "options_json": "{\"chicken_leg\": true, \"extra_rice\": true}",
  "notes": "微辣"
}
```

**功能说明：** 通过取消旧订单+创建新订单的原子操作实现，支持透支用户的订单修改

### DELETE /orders/orders/{order_id}
取消订单

**响应示例：**
```json
{
  "success": true,
  "data": {
    "order_id": 456,
    "status": "canceled",
    "refund_amount_cents": 4600,
    "new_balance_cents": 3200,
    "canceled_at": "2024-01-14T17:00:00Z"
  }
}
```

**订单状态流转：**
- `active` ←→ `locked` (管理员可锁定/解锁)
- `active/locked` → `completed` (正常完成)
- `active` → `canceled` (用户取消)
- `active/locked` → `refunded` (餐次取消退款)

---

## 用户管理接口

### GET /users/profile
获取用户资料

### GET /users/me
获取当前用户信息

### PUT /users/me
更新用户信息

### GET /users/me/balance
获取用户余额信息

**响应示例：**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "balance_cents": -1400,
    "overdraft_status": "active",
    "overdraft_limit_cents": -50000,
    "last_updated": "2024-01-14T17:00:00Z"
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

### GET /users/balance/history
获取用户余额变动历史

### POST /users/balance/recharge
用户自助充值

**请求参数：**
```json
{
  "amount_cents": 10000,
  "notes": "支付宝充值"
}
```

### POST /users/self/balance/recharge
用户自助充值（备用端点）

### POST /users/{user_id}/recharge
管理员代充值

---

## 管理员专用接口

### GET /users/admin/users
获取所有用户列表（管理员）

**响应示例：**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": 123,
        "openid": "ox_123...",
        "nickname": "张三",
        "balance_cents": -1400,
        "is_admin": false,
        "overdraft_status": "active",
        "total_orders": 25,
        "total_spent_cents": 51400,
        "created_at": "2024-01-01T00:00:00Z",
        "last_active": "2024-01-14T17:00:00Z"
      }
    ],
    "total_count": 150,
    "statistics": {
      "total_users": 150,
      "active_users": 120,
      "users_in_overdraft": 15,
      "total_overdraft_amount_cents": -45000
    }
  }
}
```

### PUT /users/admin/users/{user_id}/admin
设置/取消管理员权限

### GET /users/admin/stats
获取系统统计数据

**响应示例：**
```json
{
  "success": true,
  "data": {
    "user_stats": {
      "total_users": 150,
      "active_users": 120,
      "admin_users": 5,
      "users_in_overdraft": 15
    },
    "financial_stats": {
      "total_balance_cents": 500000,
      "total_overdraft_cents": -45000,
      "total_transactions_today": 85,
      "total_revenue_today_cents": 12000
    },
    "order_stats": {
      "total_orders": 2500,
      "orders_today": 45,
      "active_orders": 20,
      "completed_orders_today": 25
    },
    "meal_stats": {
      "meals_published": 5,
      "meals_locked": 2,
      "meals_today": 2
    }
  }
}
```

### POST /users/admin/balance/adjust
管理员调整用户余额（透支功能核心API）

**请求参数：**
```json
{
  "user_id": 123,
  "amount_cents": -5000,
  "reason": "订餐透支扣费"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "old_balance_cents": 1000,
    "adjustment_cents": -5000,
    "new_balance_cents": -4000,
    "overdraft_status": "active",
    "ledger_id": 789,
    "reason": "订餐透支扣费"
  }
}
```

### GET /users/admin/balance/transactions
获取所有用户的余额交易记录（管理员）

**查询参数：**
- `user_id` (int): 筛选特定用户
- `type` (string): 交易类型 (debit, credit, adjustment)
- `limit` (int): 每页数量，默认50
- `offset` (int): 偏移量，默认0

**响应示例：**
```json
{
  "success": true,
  "data": {
    "transactions": [
      {
        "ledger_id": 789,
        "user_id": 123,
        "type": "debit",
        "amount_cents": -4600,
        "balance_after_cents": -1400,
        "ref_type": "order",
        "ref_id": 456,
        "remark": "订单消费",
        "created_at": "2024-01-14T16:30:00Z"
      }
    ],
    "total_count": 500,
    "statistics": {
      "total_debits_cents": -250000,
      "total_credits_cents": 300000,
      "net_flow_cents": 50000,
      "overdraft_transactions": 25
    }
  }
}
```

---

## 系统功能接口

### GET /health
健康检查

**响应示例：**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 透支功能专用说明

### 透支机制概述

罡好饭系统支持用户在余额不足的情况下继续订餐，实现了完整的透支功能：

1. **透支限制**：用户可以透支到 -500.00 元（-50000 cents）
2. **透支警告**：系统会在响应中提供透支警告信息
3. **余额计算**：所有余额相关计算都支持负数
4. **透支恢复**：用户可以通过充值恢复正余额

### 透支相关API行为

- **创建订单**：即使余额不足也允许下单，扣费后显示负余额
- **修改订单**：透支状态下可以正常修改订单，金额差额会进一步影响余额
- **取消订单**：退款金额会增加到当前余额（可能仍为负数）
- **充值操作**：充值金额会加到当前余额，帮助用户脱离透支状态
- **管理员操作**：管理员可以为透支用户进行余额调整

### 透支状态监控

- **用户端**：可查看当前余额、透支状态、透支历史
- **管理员端**：可查看所有用户的透支情况、透支统计、透支用户列表

---

## 前端调用示例

### 透支场景下的订单创建

```javascript
// 创建订单（可能触发透支）
const response = await OrderAPI.createOrder({
  meal_id: 123,
  qty: 2,
  options_json: '{"chicken_leg": true}',
  notes: '不要辣'
});

// 检查是否触发透支
if (response.data.balance_cents < 0) {
  wx.showModal({
    title: '透支提醒',
    content: `当前余额：${response.data.balance_cents / 100}元\n${response.data.overdraft_warning || ''}`,
    showCancel: false
  });
}
```

### 余额监控和透支提醒

```javascript
// 获取用户余额状态
const balanceInfo = await UserAPI.getBalance();

// 透支状态处理
if (balanceInfo.data.balance_cents < 0) {
  // 显示透支状态
  const overdraftAmount = Math.abs(balanceInfo.data.balance_cents) / 100;
  console.log(`用户当前透支：${overdraftAmount}元`);
  
  // 可以提示用户充值
  if (overdraftAmount > 30) { // 透支超过30元时提醒
    wx.showModal({
      title: '充值提醒',
      content: `您当前透支${overdraftAmount}元，建议尽快充值`,
      confirmText: '去充值',
      success: (res) => {
        if (res.confirm) {
          // 跳转充值页面
          wx.navigateTo({ url: '/pages/profile/index?tab=recharge' });
        }
      }
    });
  }
}
```

---

## 开发调试

### 请求示例（curl）

```bash
# 登录
curl -X POST "http://us.pangruitao.com:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"code":"test_code","db_key":"test_key"}'

# 获取餐次列表
curl -X GET "http://us.pangruitao.com:8000/api/v1/meals/?date_from=2024-01-15&date_to=2024-01-20" \
  -H "Authorization: Bearer <token>" \
  -H "X-DB-Key: test_value"

# 创建订单（可能透支）
curl -X POST "http://us.pangruitao.com:8000/api/v1/orders/orders" \
  -H "Authorization: Bearer <token>" \
  -H "X-DB-Key: test_value" \
  -H "Content-Type: application/json" \
  -d '{"meal_id":123,"qty":2,"options_json":"{\"chicken_leg\":true}","notes":"不要辣"}'

# 管理员调整余额（透支功能）
curl -X POST "http://us.pangruitao.com:8000/api/v1/users/admin/balance/adjust" \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-DB-Key: test_value" \
  -H "Content-Type: application/json" \
  -d '{"user_id":123,"amount_cents":-5000,"reason":"测试透支功能"}'
```

---

## 更新历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2024-01-15 | 初始版本，包含基础功能 |
| 1.1.0 | 2024-01-20 | 新增订单修改、批量处理功能 |
| 1.2.0 | 2024-01-25 | 新增数据导出、一致性检查功能 |
| 2.0.0 | 2024-08-21 | **重大更新：新增透支功能、完整的余额管理、管理员功能增强** |

---

## 相关文档

- [系统架构设计](./ARCHITECTURE.md)
- [数据库设计](./technical/database-schema.md)
- [部署指南](./DEPLOYMENT.md)
- [故障排查](./guides/troubleshooting.md)
- [透支功能设计文档](./features/overdraft-system.md)