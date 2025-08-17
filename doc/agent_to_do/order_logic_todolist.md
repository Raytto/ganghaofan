# 订单与餐次交互改造 · Todo

优先级：P0> P1> P2。

## P0（本次改造必做）
- 首页餐次单元三行展示（午/晚；本餐状态；我的状态）。
  - 数据结构：为每个 slot 增加 `myOrdered:boolean`、`left:number`、`status:'none'|'published'|'locked'|'completed'`；
  - 颜色与文字映射：按 overview 颜色规则渲染。
- 打开/关闭弹窗前的最新数据拉取（用户与管理模式通用）。
  - 新增 API：`GET /meals/{meal_id}` 返回：`{ id,date,slot,description,base_price_cents,options:[{id,name,price_cents}],capacity,ordered_qty,status, my_order?:{id, options:[], remark?:string} }`。
  - 前端：`openOrderDialog(meal_id)` 与 `openPublishDialog` 打开前先刷新详情；关闭时也刷新并重绘周视图。
- 点餐弹窗（用户）：
  - 未订：显示选项按钮、备注输入、下单按钮；
  - 已订：显示当前选择（可改）、备注输入、确定修改、撤单；
  - 订完/锁定/完成：只读（按钮锁定）并显示对应提示文案。
- 管理弹窗：
  - 已发布（可订/订完）：修改/撤单/锁定；含红字风险提示逻辑；
  - 已锁定：修改/撤单/取消锁定；
  - 已完成：只读查看。
- 并发与提示：
  - 下单提交若遇到状态变化（锁定等）提示“订单状态已改变，请刷新”，并关闭弹窗。
- 后端事务：
  - create/update/cancel order；admin cancel+repost 流程；均在事务内更新订单、余额、餐次已订数量。

## P1（可选增强）
- 首页本餐状态短语本地化与国际化占位；
- 选项价格统一格式化（+N元/-N元）；
- 用户已订高亮处理（slot 三行里第三行加图标）。

## P2（后续）
- 订单历史页；
- 用消息订阅/推送优化数据一致性；
- 管理批量操作（批量锁定/完成）。
