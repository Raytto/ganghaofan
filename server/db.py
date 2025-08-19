"""
数据库连接和表结构管理模块（单库版本）
负责 DuckDB 数据库的初始化、连接管理和表结构定义。

简化说明：
- 统一使用一个数据库文件，路径从 server/config/db.json 读取（键：db_path），
    若未配置则回退到 server/data/ganghaofan.duckdb。
- 保留 JSON 扩展与建表逻辑。
- 不再根据口令切换数据库；改为在路由依赖中校验口令是否有效。

数据库表说明：
- users: 用户基本信息和余额
- meals: 餐次基本信息和配置
- orders: 用户订单记录
- ledger: 余额变动明细账
- logs: 系统操作日志
"""

import duckdb
from pathlib import Path
import json
from fastapi import HTTPException, Header
from typing import Optional
from .config import get_passphrase_map

# 数据文件存储目录，默认位置
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 全局单一连接
_conn_single: duckdb.DuckDBPyConnection | None = None

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


def _load_db_config_path() -> Path:
    """从 server/config/db.json 读取 db_path，若不存在则使用默认路径。"""
    cfg_file = Path(__file__).parent / "config" / "db.json"
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("db_path"):
                p = Path(str(data["db_path"]))
                # 若为相对路径，则相对于 server/ 目录
                if not p.is_absolute():
                    p = (Path(__file__).parent / p).resolve()
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
        except Exception:
            pass
    # 默认路径
    return (DATA_DIR / "ganghaofan.duckdb").resolve()


def get_conn():
    """获取（并按需创建）全局唯一的 DuckDB 连接。"""
    global _conn_single
    if _conn_single is not None:
        return _conn_single
    db_path = _load_db_config_path()
    con = duckdb.connect(str(db_path))
    try:
        con.execute("INSTALL json")
    except Exception:
        pass
    try:
        con.execute("LOAD json")
    except Exception:
        pass
    con.execute(SCHEMA_SQL)
    _conn_single = con
    return _conn_single


def init_db():
    """初始化单一库表结构和扩展。"""
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
    """兼容入口：现在仅初始化单一库。"""
    init_db()


# FastAPI 依赖：校验来自 /env/resolve 的 key（不再切库，仅校验权限）
async def use_db_key(x_db_key: Optional[str] = Header(default=None)):
    mapping = get_passphrase_map() or {}
    valid_keys = {str(v).strip() for v in mapping.values() if str(v).strip()}
    # 允许在未配置口令时（空配置）直接通过；否则必须提供有效 key
    if valid_keys:
        if not x_db_key or str(x_db_key).strip() not in valid_keys:
            raise HTTPException(status_code=403, detail="passphrase required")
    return x_db_key or ""
