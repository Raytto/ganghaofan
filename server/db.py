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
from pathlib import Path

# 数据文件存储目录，自动创建
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "ganghaofan.duckdb"

# 全局数据库连接实例，延迟初始化
_conn = None

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


def get_conn():
    """
    获取全局数据库连接实例
    使用单例模式确保连接复用，避免频繁创建连接的开销
    
    Returns:
        duckdb.DuckDBPyConnection: DuckDB数据库连接对象
    """
    global _conn
    if _conn is None:
        _conn = duckdb.connect(str(DB_PATH))
    return _conn


def init_db():
    """
    初始化数据库表结构和扩展
    
    执行操作：
    1. 安装并加载JSON扩展以支持JSON列类型
    2. 创建所有必需的表和索引
    
    Note:
        JSON扩展安装失败不会影响基本功能，因为表结构本身会处理JSON字段
        该函数在应用启动时调用，确保数据库就绪
    """
    con = get_conn()
    # 确保JSON扩展可用，用于处理options_json等字段
    try:
        con.execute("INSTALL json")
    except Exception:
        # 扩展可能已安装，忽略错误
        pass
    try:
        con.execute("LOAD json")
    except Exception:
        # 扩展可能已加载，忽略错误
        pass
    con.execute(SCHEMA_SQL)
