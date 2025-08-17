# Step 3 · 后端 API 设计（FastAPI）

注：实际路径可统一加上前缀 /api/v1。

## Auth
- POST /auth/login
  - 输入：{ code }
  - 输出：{ token, user: { id, nickname, avatar, is_admin } }
- GET /me
  - 头：Authorization: Bearer <token>
  - 输出：当前用户信息与余额

## 用户
- GET /users/me/balance
- POST /users/:id/recharge（管理员）
  - 输入：{ amount_cents, remark }

## 日历/餐次
- GET /calendar?month=YYYY-MM
  - 输出：该月所有 meal 及聚合状态（每餐：已发布/未发布、剩余容量、是否达上限）
- POST /meals（管理员）
  - 输入：{ date, slot, title, description, base_price_cents, options:[{id,name,price_cents,max_qty_per_order?}], capacity, per_user_limit }
- PATCH /meals/:meal_id（管理员）
  - 可更新上述字段
- POST /meals/:meal_id/lock（管理员）
- POST /meals/:meal_id/complete（管理员）
- POST /meals/:meal_id/cancel（管理员）

## 订单
- GET /meals/:meal_id/orders (管理员查看明细)
- GET /orders/my?meal_id=xxx
- POST /orders
  - 输入：{ meal_id, qty, options:[option_id] }  -- 选项为布尔勾选集合
  - 语义：创建订单成功即扣费（写台账 debit，余额可为负），返回最新余额与订单详情
- PATCH /orders/:order_id
  - 输入：{ qty, options:[option_id] }
  - 语义：等价于取消旧单并新建新单（在一个事务内完成，包含退款与扣费），返回新订单
- DELETE /orders/:order_id
  - 语义：取消订单并原路退款（写台账 refund），锁单后禁止

## 日志
- GET /logs/my?cursor=...&limit=10
 token 简化使用服务端签发的 JWT（内网用途），有效期 7 天，支持续期。
 事务保证：订单创建/修改/取消涉及 台账与余额 的多表写入，必须使用事务确保一致性。

## 扩展接口（后续）
- 是否需要导出报表接口（CSV），如 /reports/ledger?month=YYYY-MM
  - code 示例：INVALID_INPUT / NOT_FOUND / FORBIDDEN / CONFLICT / BALANCE_NOT_ENOUGH（如采用即刻扣费策略）

## 安全
- 所有修改类接口需校验 is_admin 或用户自身权限。
- token 简化使用服务端签发的 JWT（内网用途），有效期 7 天，支持续期。

## 开放问题
- 是否需要导出报表接口（CSV），如 /reports/ledger?month=...
