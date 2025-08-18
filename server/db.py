"""
数据库连接和表结构管理模块
负责DuckDB数据库的初始化、连接管理和表结构定义

主要功能：
- 提供全局数据库连接实例
- 定义完整的表结构和索引
- 支持JSON扩展以处理动态选项数据

数据库表说明：
- users: 用户基本信息和余额
- meals: 餐次基本信息和配置
- orders: 用户订单记录
- ledger: 余额变动明细账
- logs: 系统操作日志
"""

import os
import duckdb
from contextvars import ContextVar
from pathlib import Path
from .config import get_passphrase_map

# 数据文件存储目录，自动创建
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "ganghaofan.duckdb"

# 每个请求的数据库键（来自口令映射），默认空串表示默认库
_current_db_key: ContextVar[str] = ContextVar("current_db_key", default="")

# 连接池：不同 key 使用不同的连接
_conns: dict[str, duckdb.DuckDBPyConnection] = {}

# 全局数据库连接实例，延迟初始化
_conn = None  # 保留但不再使用（兼容旧代码）

# 完整的表结构和索引定义
# 使用序列生成自增主键，支持并发插入
SCHEMA_SQL = r"""
CREATE SEQUENCE IF NOT EXISTS users_id_seq;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER DEFAULT nextval('users_id_seq') PRIMARY KEY,
  open_id TEXT UNIQUE NOT NULL,
  nickname TEXT,
  avatar TEXT,
  is_admin BOOLEAN DEFAULT FALSE,
  balance_cents INTEGER DEFAULT 0,  -- 使用分为单位避免浮点精度问题
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_open_id ON users(open_id);

CREATE SEQUENCE IF NOT EXISTS meals_id_seq;
CREATE TABLE IF NOT EXISTS meals (
  meal_id INTEGER DEFAULT nextval('meals_id_seq') PRIMARY KEY,
  date DATE NOT NULL,
  slot TEXT CHECK(slot IN ('lunch','dinner')) NOT NULL,
  title TEXT,
  description TEXT,
  base_price_cents INTEGER NOT NULL,
  options_json JSON,  -- 存储可选配菜的动态结构
  capacity INTEGER NOT NULL,
  per_user_limit INTEGER DEFAULT 1,
  status TEXT CHECK(status IN ('published','locked','completed','canceled')) NOT NULL,
  created_by INTEGER,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_meal_date_slot ON meals(date, slot);

CREATE SEQUENCE IF NOT EXISTS orders_id_seq;
CREATE TABLE IF NOT EXISTS orders (
  order_id INTEGER DEFAULT nextval('orders_id_seq') PRIMARY KEY,
  user_id INTEGER,
  meal_id INTEGER,
  qty INTEGER NOT NULL,
  options_json JSON,  -- 用户选择的配菜选项
  amount_cents INTEGER NOT NULL,  -- 订单总金额（基础价格+配菜价格）
  status TEXT CHECK(status IN ('active','canceled')) NOT NULL,
  locked_at TIMESTAMP,  -- 餐次锁定时间，用于防止锁定后修改订单
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_meal ON orders(meal_id);

CREATE SEQUENCE IF NOT EXISTS ledger_id_seq;
CREATE TABLE IF NOT EXISTS ledger (
  ledger_id INTEGER DEFAULT nextval('ledger_id_seq') PRIMARY KEY,
  user_id INTEGER,
  type TEXT CHECK(type IN ('recharge','debit','refund','adjust')) NOT NULL,
  amount_cents INTEGER NOT NULL,
  ref_type TEXT CHECK(ref_type IN ('order','meal','manual')),  -- 关联对象类型
  ref_id INTEGER,  -- 关联对象ID
  remark TEXT,  -- 操作备注说明
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_user ON ledger(user_id);

CREATE SEQUENCE IF NOT EXISTS logs_id_seq;
CREATE TABLE IF NOT EXISTS logs (
  log_id INTEGER DEFAULT nextval('logs_id_seq') PRIMARY KEY,
  user_id INTEGER,  -- 操作涉及的用户
  actor_id INTEGER,  -- 实际执行操作的用户（如管理员）
  action TEXT,  -- 操作类型标识
  detail_json JSON,  -- 操作详情的结构化数据
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_actor ON logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action);
"""


def set_request_db_key(key: str | None) -> None:
    """在当前请求上下文设置数据库 key。"""
    _current_db_key.set((key or "").strip())


def _get_path_for_key(key: str) -> Path:
    if not key:
        return DB_PATH
    return DATA_DIR / f"ganghaofan_{key}.duckdb"


def get_conn():
    """
    获取（并按需创建）当前请求对应 key 的 DuckDB 连接。
    """
    # 基于当前请求的 db key 选择连接
    key = _current_db_key.get()
    if key in _conns:
        return _conns[key]

    path = _get_path_for_key(key)
    con = duckdb.connect(str(path))
    # 确保扩展与表结构
    try:
        con.execute("INSTALL json")
    except Exception:
        pass
    try:
        con.execute("LOAD json")
    except Exception:
        pass
    con.execute(SCHEMA_SQL)
    _conns[key] = con
    return con


def init_db():
    """
    初始化数据库表结构和扩展（默认库）。
    """
    # 初始化默认库结构
    set_request_db_key("")
    con = get_conn()
    # 再次确保 JSON 扩展就绪
    try:
        con.execute("INSTALL json")
    except Exception:
        pass
    try:
        con.execute("LOAD json")
    except Exception:
        pass
    con.execute(SCHEMA_SQL)


def init_all_dbs():
    """
    启动时预初始化所有配置的数据库：
    - 默认库（空key）
    - 配置文件/环境变量映射到的所有 key 的库
    若文件不存在会自动创建；若未建表会自动执行SCHEMA。
    """
    # 1) 默认库
    init_db()
    # 2) 通过配置获取所有 key（passphrase -> key 的值集合）
    try:
        mapping = get_passphrase_map() or {}
        keys = sorted({str(v).strip() for v in mapping.values() if str(v).strip()})
        for k in keys:
            try:
                set_request_db_key(k)
                con = get_conn()  # get_conn 会确保 JSON 扩展和 SCHEMA
                # 再执行一次 SCHEMA 以防版本更新（幂等）
                con.execute(SCHEMA_SQL)
            except Exception:
                # 单库失败不阻塞其他库初始化
                continue
    finally:
        # 恢复到默认 key，避免影响后续请求上下文
        set_request_db_key("")


# FastAPI 依赖：从请求头读取 X-DB-Key 并设置当前请求的数据库
try:
    from fastapi import Header
    from typing import Optional

    async def use_db_key(x_db_key: Optional[str] = Header(default=None)):
        set_request_db_key(x_db_key)
        return x_db_key or ""

except Exception:
    # 非运行期导入 fastapi 失败时忽略（便于类型检查）
    pass
