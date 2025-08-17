# Step 1 · 架构与技术选型

## 目标
- 面向“熟人小群体”的内用点餐，优先简单可靠与易维护。
- 本地开发便捷，生产部署在个人云服务器。

## 技术栈
- 前端：微信小程序（TS + Skyline），自定义组件，现代扁平风格。
- 后端：Python FastAPI
- 数据库：DuckDB（嵌入式，单文件存储），通过 SQLite 风格 API 访问（duckdb Python）。
- 认证：微信登录（wx.login → code → 服务端换取 openId），服务端维护管理员白名单。
- 部署：后端使用 uvicorn/systemd 运行；定时任务使用 Windows/Linux cron/Task Scheduler；备份到对象存储/本地目录。

## 系统组件
- 小程序前端：
  - 日历视图（按月，午/晚两栏）。
  - 订单下单/修改/取消页。
  - 管理发布/编辑/锁单/完成页。
  - 个人中心与日志分页。
- 服务端 API：
  - Auth：code2session、用户信息上报。
  - 菜单/餐次：发布、编辑、取消、锁单、完成、查询。
  - 订单：创建（下单即扣费）、修改（等价于取消+新建）、取消（原路退款）、查询。
  - 余额：查询、充值、扣费、退款（内部）。
  - 日志：分页查询个人与全量（管理员）。
- 数据存储：DuckDB 单文件 + 每日备份。

## 域模型（概要）
- User(id, open_id, nickname, avatar, is_admin, balance_cents, created_at)
- Meal(meal_id, date, slot[lunch|dinner], title, desc, base_price_cents, options_json, capacity, per_user_limit, status[published|locked|completed|canceled], created_by, updated_at)
- Order(order_id, user_id, meal_id, qty, options_json, amount_cents, status[active|canceled], locked_at, created_at, updated_at)
- Ledger(ledger_id, user_id, type[recharge|debit|refund|adjust], amount_cents, ref_type[order|meal|manual], ref_id, created_at, remark)
- Log(log_id, user_id, action, detail_json, created_at, actor_id)

## 状态流转
- Meal：未发布 → 已发布 → 已锁单 → 已完成/已取消
- Order：active → canceled（锁单后不可变更）；“修改订单”在实现上表现为：旧单 canceled + 新单 active（原子事务）。

## 非功能
- 可恢复：通过日志与台账可追溯。
- 性能：日历分页（月）；查询按 date range。
- 安全：仅内部使用，管理员白名单；参数校验；限速可选。

## 约束共识（来自 Step 0）
- 下单即扣费、取消原路退款、修改=取消+新建；允许负余额（提示尽快充值）；每日备份保留30天。
