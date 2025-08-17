# Step 6 · 关键业务流程详解（基于已确认规则）

本文将下单、改单、取消、锁单、完成、取消餐次等流程拆解为可实现的原子步骤，明确事务边界与校验点，便于编码与测试。

## 公共约束与定义
- 金额单位为分（int），后端计算总价；
- 选项为布尔勾选集合（不可对单个选项设置数量）；
- 余额允许为负；
- 餐次状态：published → locked → completed/canceled；
- 订单状态：active → canceled（锁单后不可变更）。

## F1：创建订单（下单即扣费）
前置：
- meal.status == published；
- qty ∈ [1, per_user_limit]；
- 选项均在 meal.options_json 中；
- 现有订单总份数 + qty ≤ capacity。

流程（单事务）：
1) 读取 meal 与当日订单聚合校验容量；
2) 计算 amount = base_price_cents * qty + sum(option.price_cents for option in options)；
3) 插入 orders(active)；
4) 写 ledger(type=debit, amount_cents=amount, ref_type='order', ref_id=order_id)；
5) 更新 users.balance_cents -= amount；
6) 写 logs(create_order, debit)；
7) 返回订单、最新余额、餐次剩余容量。

异常与回滚：
- 任一步失败回滚事务，返回 CONFLICT/INVALID_INPUT 等。

## F2：修改订单（等价于取消旧单+新建新单）
前置：
- 旧订单 status == active 且 meal.status == published；
- 锁单后禁止修改。

流程（单事务）：
1) 取消旧单（见 F3），完成退款与日志；
2) 按新参数执行创建订单（见 F1）；
3) 返回新订单结果。

## F3：取消订单（原路退款）
前置：
- 订单 active 且 meal.status == published；

流程（单事务）：
1) 更新订单 status → canceled；
2) 写 ledger(type=refund, amount_cents=原订单 amount)；
3) 更新 users.balance_cents += 原订单 amount；
4) 写 logs(cancel_order, refund)；
5) 返回最新余额与餐次剩余容量。

锁单后：
- 禁止取消，返回 FORBIDDEN。

## F4：锁单（管理员）
前置：
- meal.status == published。

流程（单事务）：
1) 更新 meal.status → locked；
2) 批量更新该 meal 的所有 active 订单 locked_at=now()；
3) 写 logs(lock_meal)。

说明：
- 因为采用“下单即扣费”，锁单不再产生扣费动作。

## F5：标记完成（管理员）
前置：
- meal.status == locked。

流程：
1) 更新 meal.status → completed；
2) 写 logs(complete_meal)。

## F6：取消餐次（管理员，批量退款）
前置：
- meal.status in {published, locked}（均可取消，统一退款）。

流程（单事务，或分批循环事务处理以避免大事务超时）：
1) 更新 meal.status → canceled；
2) 查询所有 active 订单，逐个：
   - 更新 order.status → canceled；
   - 写 ledger(refund, amount=该订单 amount)；
   - 更新用户余额 += amount；
3) 写 logs(cancel_meal)。

注意：
- 如订单很多，建议分页处理并记录进度；但需保证每个订单的退款与状态在同一事务内。

## F7：充值（管理员）
流程（单事务）：
1) 写 ledger(type=recharge, amount_cents>0, ref_type='manual')；
2) 更新 users.balance_cents += amount；
3) 写 logs(recharge)。

## 并发与一致性建议
- 对单个 meal 的写操作（订单创建/修改/取消、锁单、取消餐次）采用“按餐次加行级锁/互斥执行”的服务层串行化策略；
- 计算剩余容量使用聚合 + 校验，失败返回 CONFLICT；
- 所有含余额与台账的流程必须使用数据库事务封装。

## 前端交互提示要点
- 下单成功即扣费；
- 修改会先退旧单再扣新单；
- 锁单后不可修改或取消；
- 取消餐次将自动退款到余额；
- 余额可为负，将在个人中心提示尽快充值。
