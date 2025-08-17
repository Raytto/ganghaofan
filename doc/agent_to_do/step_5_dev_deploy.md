# Step 5 · 开发、测试与部署

## 开发环境
- 前端：微信开发者工具 + TS + Skyline；
- 后端：Python 3.11+，FastAPI，uvicorn，duckdb；
- 本地同时运行前后端，前端通过环境变量配置后端基地址（如 http://127.0.0.1:8000）。

## 目录建议
- server/
  - app.py（FastAPI 入口）
  - db.py（DuckDB 连接、初始化）
  - models/、routers/、services/
  - scripts/backup.py（备份）
- client/（已存在）
- doc/

## 任务拆解（落地）
1) 初始化后端 FastAPI 工程与 DuckDB 表结构迁移脚本；
2) 实现 Auth（登录换取 openId 的模拟/对接）与管理员白名单；
3) 实现 Meal 发布/查询/锁单/完成/取消；
4) 实现 Order 创建/修改/取消，含容量与上限校验与金额计算；下单即扣费、取消即退款、修改=取消+新建（单事务）；
5) 实现 Ledger 台账与余额增减（允许余额为负）；
6) 实现 Logs 操作记录；
7) 前端搭建：日历骨架 + 顶部区 + 模式切换；
8) 前端下单页与发布页；
9) 日志与个人中心；
10) 本地 E2E 自测；
11) 部署脚本与文档：
    - 服务器：Python 环境、systemd 服务、Nginx 反向代理；
    - DuckDB 数据目录、备份计划（每日）。

## 部署（生产）
- 使用 uvicorn + systemd 常驻：
  - WorkingDirectory=/opt/ganghaofan/server
  - ExecStart=/usr/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
- Nginx 反代到 /api/
- DuckDB 数据文件与日志目录每日打包备份（保留30天）。

## 测试
- 单元：服务层的金额计算、容量与状态校验；
- 集成：下单（扣费）→ 修改（退款+再扣）→ 取消（退款）→ 锁单 → 完成 → 取消餐次（批量退款）（异常路径验证）；
- 前端：月历渲染、状态图标、下单表单校验。

## 风险与缓解
- DuckDB 单文件损坏风险：每日备份 + 写操作日志；
- 小程序登录不可用：允许本地模拟 openId；
- 支付对接复杂：初期不接入，内账处理。
