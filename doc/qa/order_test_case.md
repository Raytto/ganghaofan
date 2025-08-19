# 订单/餐次 · 测试用例（Server）

本用例集覆盖“下单/修改/撤单/锁定/解锁/完成/撤单重发”等核心路径，含并发与边界。用于回归与联调验证。

## 0. 范围与前置
- 架构：单 DuckDB；业务路由需 JWT 与 `X-DB-Key`（白名单校验）。
- 约束：每用户每餐最多 1 单；金额单位为分（cents）。
- 事务：订单变更 + 余额变更需原子提交。
- 角色：普通用户（U1/U2）；管理员（Admin）。
- 关键接口（摘要）：
  - 用户：`POST /orders`（创建或替换本餐订单）；`DELETE /orders?meal_id=...`（取消本餐订单）或 `DELETE /orders/{order_id}`；`GET /users/me/balance`。
  - 管理：`POST /meals`，`PUT /meals/{id}`，`POST /meals/{id}/repost`，`POST /meals/{id}/lock`，`POST /meals/{id}/unlock`，`POST /meals/{id}/complete`，`POST /meals/{id}/cancel`。
  - 日历：`GET /calendar`/`/calendar/batch`；详情：`GET /meals/{id}`。
  - 鉴权：`POST /auth/login`；口令：`POST /env/resolve`。

说明：部分实现允许使用 `PATCH /orders/{order_id}` 修改订单；若服务端接受“`POST /orders` 覆盖现有订单”的简化路径，以下用例优先采用后者。

## 1. 数据准备（通用）
- 创建用户：U1、U2，初始余额均为 10000（1 元 = 100 分）。
- 创建餐次 M1：
  - `date=今天`，`slot=lunch`，`base_price_cents=2000`，`capacity=5`，`per_user_limit=1`；
  - `options=[{id:"A",name:"鸡腿",price_cents:300},{id:"B",name:"米饭加量",price_cents:100},{id:"C",name:"素减脂",price_cents:-100}]`。
- 若无特殊说明，用例均以此为初始状态；每个用例优先独立执行（或重置状态）。

## 2. 下单（Create）
- ORD-001 成功下单（无选项）
  - 前置：M1 可订（status=published，left=5）；U1 余额=10000。
  - 步骤：U1 `POST /orders {meal_id:M1, qty:1, options:[]}`。
  - 期望：
    - 响应 200（或 201）；返回订单明细；
    - U1 余额=10000-2000=8000；M1 ordered_qty=1，left=4；
    - 日志两条：order_create（actor=U1，balance_before/after），user_balance_change。

- ORD-002 成功下单（含正价选项）
  - 步骤：U1 `POST /orders {meal_id:M1, options:["A","B"]}`。
  - 期望：扣款=2000+300+100=2400；余额减少 2400；日志包含 options 明细。

- ORD-003 成功下单（含负价选项）
  - 步骤：U1 `POST /orders {meal_id:M1, options:["C"]}`。
  - 期望：扣款=2000-100=1900；允许负价选项但总价≥0；余额减少 1900。

- ORD-004 重复下单同餐（幂等限制）
  - 前置：U1 已在 M1 有订单。
  - 步骤：U1 再次 `POST /orders {meal_id:M1, options:[]}`。
  - 期望（二选一，取决于实现）：
    - A) 直接替换：旧单作废，按新价差额增减余额；ordered_qty 仍为 1；日志 order_update；
    - B) 返回 409/400 表示已存在（若不支持覆盖）。

- ORD-005 余额不足
  - 前置：U1 余额=100（小于应付 2000）。
  - 步骤：U1 `POST /orders {meal_id:M1}`。
  - 期望：失败 400/402；余额不变；无订单创建；日志记录失败原因（可选）。

- ORD-006 库存边界（最后一份）
  - 前置：M1 left=1。
  - 步骤：U1 下单；
  - 期望：成功；left=0；其它用户下单同餐返回 409/400“售罄”。

- ORD-007 非法选项 ID
  - 步骤：U1 `POST /orders {meal_id:M1, options:["X"]}`。
  - 期望：失败 400；余额/库存不变；错误信息指示非法选项。

## 3. 修改订单（Update/Replace）
- ORD-101 仅改选项（加价）
  - 前置：U1 已下单 M1（无选项，实付 2000）。
  - 步骤：U1 `POST /orders {meal_id:M1, options:["A"]}` 替换。
  - 期望：差额 = +300；余额再扣 300；ordered_qty 仍为 1；日志 order_update（含 before/after 金额、options）。

- ORD-102 仅改选项（降价）
  - 前置：U1 已下单 M1（含 A，实付 2300）。
  - 步骤：改为 `options:["C"]`。
  - 期望：差额 = 1900-2300 = -400；余额返还 400；日志记录 balance_before/after。

- ORD-103 修改时库存不应变化
  - 前置：U1 已下单；M1 left=0。
  - 步骤：U1 修改自身订单选项。
  - 期望：允许修改；left 仍为 0；无越界。

## 4. 撤单（Cancel）
- ORD-201 用户撤单成功
  - 前置：U1 已在 M1 下单（实付 X）。
  - 步骤：`DELETE /orders?meal_id=M1`（或 `DELETE /orders/{order_id}`）。
  - 期望：余额返还 X；M1 left += 1；日志 order_cancel（actor=U1）+ balance 变更。

- ORD-202 未下单撤单
  - 步骤：U1 撤单 M1。
  - 期望：幂等处理；200/204；余额/库存不变。

## 5. 并发与竞态
- ORD-301 最后一份并发抢单（U1 vs U2）
  - 前置：M1 left=1。
  - 步骤：U1 与 U2 同时 `POST /orders`。
  - 期望：恰有一人成功；另一人失败 409/400；无双扣/超卖；日志仅一条成功创建。

- ORD-302 下单与锁定竞态
  - 前置：M1 可订。
  - 步骤：U1 下单同时 Admin `POST /meals/{id}/lock`。
  - 期望：要么下单先提交成功（随后锁定生效），要么下单失败“已锁定”；不应部分扣款。

- ORD-303 修改/撤单与完成竞态
  - 前置：M1 可订；U1 已下单。
  - 步骤：Admin `POST /meals/{id}/complete` 与 U1 修改/撤单同时。
  - 期望：已完成后用户操作应失败 409/400；余额/订单一致。

- ORD-304 危险修改重发与用户并发
  - 前置：M1 已有多名用户订单。
  - 步骤：Admin `POST /meals/{id}/repost` 与若干用户修改/撤单同时。
  - 期望：服务端以事务顺序保证一致：重发成功则原订单全部取消并退款；用户并发请求要么基于新态，要么失败并返回提示。

## 6. 管理操作与影响
- ORD-401 发布餐次
  - 步骤：Admin `POST /meals` 创建。
  - 期望：状态=published；可订；日志 meal_publish（actor=Admin）。

- ORD-402 直接修改（非危险）
  - 前置：有已订但修改项不触达“危险”集合（如仅描述、容量上调、仅新增选项）。
  - 步骤：`PUT /meals/{id}`。
  - 期望：保留现有订单；不触发批量退款；日志 meal_update。

- ORD-403 危险修改重发
  - 条件：改价；容量下调至 < 已订；删除已存在选项。
  - 步骤：`POST /meals/{id}/repost`。
  - 期望：
    - 所有活跃订单取消并退款；ordered_qty 归零；状态保持 published；
    - 日志：meal_repost（actor=Admin）+ 每个用户一条 order_cancel（actor=Admin，balance_before/after 准确）。

- ORD-404 锁定/解锁
  - 步骤：`POST /meals/{id}/lock` → `POST /meals/{id}/unlock`。
  - 期望：锁定后用户不能新下单或修改；已订可查看；解锁后恢复 published；日志 meal_lock / meal_unlock。

- ORD-405 完成
  - 步骤：`POST /meals/{id}/complete`。
  - 期望：状态=completed；用户所有操作只读；日志 meal_complete。

- ORD-406 取消餐次
  - 步骤：`POST /meals/{id}/cancel`。
  - 期望：
    - 所有活跃订单取消并退款；状态=canceled；
    - 日志：meal_cancel（actor=Admin）+ 每位用户一条 order_cancel（actor=Admin）。

- ORD-407 权限校验
  - 步骤：非管理员调用任一管理路由。
  - 期望：403 Forbidden；无数据变更；日志可选记录拒绝。

## 7. 余额与日志一致性
- ORD-501 余额精度
  - 步骤：多次下单/修改/退款组合，含正负价选项。
  - 期望：余额为整数分；无浮点误差；每次日志 balance_before/after 连贯。

- ORD-502 日志分页与筛选
  - 步骤：连续产生 50+ 日志；`GET /logs/my` 分页拉取。
  - 期望：分页正确；时间倒序；详情包含 actor_id、detail_json（含 options、amount_deltas）。

## 8. 异常与校验
- ORD-601 未登录/Token 失效
  - 步骤：无 Authorization 访问受限接口。
  - 期望：401；无副作用。

- ORD-602 缺少/非法 DB Key
  - 步骤：无 `X-DB-Key` 或不在白名单访问业务路由。
  - 期望：403；无副作用。

- ORD-603 非法参数
  - 步骤：负数量、超长描述、重复 option id、未知 slot、非法日期格式。
  - 期望：400；错误消息明确；无副作用。

- ORD-604 跨餐次/跨用户越权
  - 步骤：U1 删除/修改 U2 的订单；修改与路径 `meal_id` 不一致。
  - 期望：403/404；无副作用。

## 9. 查询与一致性
- ORD-701 详情一致
  - 步骤：`GET /meals/{id}` 与日历数据对比。
  - 期望：ordered_qty、capacity、status 一致；选项结构一致（数组）。

- ORD-702 用户余额接口
  - 步骤：多次操作后 `GET /users/me/balance`。
  - 期望：与日志推导余额一致。

## 10. 故障注入（可选）
- 在支付扣款与订单落库之间制造异常。
- 期望：整体回滚；无“扣款成功但无订单”或“有订单但未扣款”。

---
执行这些用例时，建议：
- 为每个用例提供独立的“准备/步骤/期望/清理”记录；
- 并发用例使用脚本或多终端并行触发并采集响应时间与顺序；
- 所有金额校验以“分”为单位。
