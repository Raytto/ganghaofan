# Step 2 · 数据模型与表结构（DuckDB）

注：DuckDB 支持 SQL 与 JSON 字段，适合轻量内用。所有金额单位均为分（int）。

## 表与索引

### users
- id INTEGER PRIMARY KEY AUTOINCREMENT
- open_id TEXT UNIQUE NOT NULL
- nickname TEXT
- avatar TEXT
- is_admin BOOLEAN DEFAULT FALSE
- balance_cents INTEGER DEFAULT 0
- created_at TIMESTAMP DEFAULT now()

索引：
- idx_users_open_id (open_id)

### meals
- meal_id INTEGER PRIMARY KEY AUTOINCREMENT
- date DATE NOT NULL
- slot TEXT CHECK(slot IN ('lunch','dinner')) NOT NULL
- title TEXT
- description TEXT
- base_price_cents INTEGER NOT NULL
- options_json JSON -- [{id,name,price_cents,enabled:boolean}]  -- 仅布尔选择，不支持单选项内多份数量
- capacity INTEGER NOT NULL -- 总容量
- per_user_limit INTEGER DEFAULT 1
- status TEXT CHECK(status IN ('published','locked','completed','canceled')) NOT NULL
- created_by INTEGER REFERENCES users(id)
- created_at TIMESTAMP DEFAULT now()
- updated_at TIMESTAMP DEFAULT now()

唯一索引：
- uniq_meal_date_slot (date, slot) -- 每天每餐只有一个发布

### orders
- order_id INTEGER PRIMARY KEY AUTOINCREMENT
- user_id INTEGER REFERENCES users(id)
- meal_id INTEGER REFERENCES meals(meal_id)
- qty INTEGER NOT NULL
- options_json JSON -- [{option_id}]  -- 仅记录选择了哪些选项（布尔）
- amount_cents INTEGER NOT NULL -- 计算后总价（含选项）
- status TEXT CHECK(status IN ('active','canceled')) NOT NULL
- locked_at TIMESTAMP -- 订单锁定时间（随餐次锁单写入）
- created_at TIMESTAMP DEFAULT now()
- updated_at TIMESTAMP DEFAULT now()

索引：
- idx_orders_user (user_id)
- idx_orders_meal (meal_id)

### ledger（台账）
- ledger_id INTEGER PRIMARY KEY AUTOINCREMENT
- user_id INTEGER REFERENCES users(id)
- type TEXT CHECK(type IN ('recharge','debit','refund','adjust')) NOT NULL
- amount_cents INTEGER NOT NULL -- 正为入账，负为出账
- ref_type TEXT CHECK(ref_type IN ('order','meal','manual'))
- ref_id INTEGER
- remark TEXT
- created_at TIMESTAMP DEFAULT now()

索引：
- idx_ledger_user (user_id)

### logs（操作日志）
- log_id INTEGER PRIMARY KEY AUTOINCREMENT
- user_id INTEGER -- 受影响的用户（可为空，如仅管理员动作）
- actor_id INTEGER -- 执行动作的人
- action TEXT -- create_meal / update_meal / lock_meal / complete_meal / cancel_meal / create_order / update_order / cancel_order / recharge / debit / refund
- detail_json JSON
- created_at TIMESTAMP DEFAULT now()

索引：
- idx_logs_user (user_id)
- idx_logs_actor (actor_id)
- idx_logs_action (action)

## 关键约束与校验
- 订单创建/修改：
  - meal.status 必须为 published；
  - qty >= 1 且 <= per_user_limit；（不支持在单个选项内叠加数量，想多加可配置多个类似选项）
  - 所有订单 qty 总和 <= capacity；
  - 选项在 options_json 中存在；
  - amount 由后端计算，前端只传意向。
- 下单扣费：
  - 创建订单成功后，立即写台账 debit（amount_cents 为负数记账或正数配合类型语义，下同）并扣减余额（允许为负）；
  - 取消订单时写 refund 并回滚余额；
  - 修改订单等价于事务内：取消旧单（含退款）+ 新建新单（含扣费）。
- 锁单：
  - meal.status: published → locked；同步写订单 locked_at；锁单后订单不可修改/取消。
- 完成：
  - meal.status: locked → completed；
  - 只做状态流转与日志。
- 取消餐次：
  - meal.status → canceled；
  - 所有关联订单 status → canceled；
  - 如曾扣费则写 refund 台账并回滚余额。
