"""
数据库连接和管理模块
重构自原 db.py，提供更清晰的数据库操作接口
"""

import duckdb
from pathlib import Path
import json
from typing import Optional, Generator
from contextlib import contextmanager
import threading
try:
    from .exceptions import DatabaseError
    from ..config.settings import settings
except ImportError:
    # Fallback for test environment
    from core.exceptions import DatabaseError
    from config.settings import settings

# 数据文件存储目录
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 全局单一连接
_conn_single: Optional[duckdb.DuckDBPyConnection] = None

# 完整的表结构定义
SCHEMA_SQL = r"""
CREATE SEQUENCE IF NOT EXISTS users_id_seq;
CREATE TABLE IF NOT EXISTS users (
  id INTEGER DEFAULT nextval('users_id_seq') PRIMARY KEY,
  open_id TEXT UNIQUE NOT NULL,
  nickname TEXT,
  avatar TEXT,
  is_admin BOOLEAN DEFAULT FALSE,
  balance_cents INTEGER DEFAULT 0,
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
  options_json JSON,
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
  options_json JSON,
  amount_cents INTEGER NOT NULL,
  status TEXT CHECK(status IN ('active','canceled')) NOT NULL,
  locked_at TIMESTAMP,
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
  ref_type TEXT CHECK(ref_type IN ('order','meal','manual')),
  ref_id INTEGER,
  remark TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_user ON ledger(user_id);

CREATE SEQUENCE IF NOT EXISTS logs_id_seq;
CREATE TABLE IF NOT EXISTS logs (
  log_id INTEGER DEFAULT nextval('logs_id_seq') PRIMARY KEY,
  user_id INTEGER,
  actor_id INTEGER,
  action TEXT,
  detail_json JSON,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_actor ON logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action);
"""


class DatabaseManager:
    """数据库管理器，封装所有数据库操作"""
    
    def __init__(self):
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._lock = threading.RLock()
        self.db_path = self._get_db_path_from_settings()
    
    def _get_db_path_from_settings(self) -> str:
        """从设置中获取数据库路径"""
        db_url = settings.database_url
        if db_url.startswith("duckdb://"):
            return db_url.replace("duckdb://", "")
        return db_url
    
    def _load_db_config_path(self) -> Path:
        """从配置文件读取数据库路径"""
        cfg_file = Path(__file__).parent.parent / "config" / "db.json"
        if cfg_file.exists():
            try:
                data = json.loads(cfg_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("db_path"):
                    p = Path(str(data["db_path"]))
                    if not p.is_absolute():
                        p = (Path(__file__).parent.parent / p).resolve()
                    p.parent.mkdir(parents=True, exist_ok=True)
                    return p
            except Exception as e:
                raise DatabaseError(f"Failed to load database config: {e}")
        
        # 默认路径
        return (DATA_DIR / "ganghaofan.duckdb").resolve()
    
    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """获取数据库连接"""
        if self._connection is None:
            self._connection = duckdb.connect(self.db_path)
            self._init_schema()
        return self._connection
    
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """获取数据库连接 - 保持向后兼容"""
        return self.connection
    
    def _init_schema(self):
        """初始化数据库表结构"""
        try:
            # 安装和加载JSON扩展
            try:
                self._connection.execute("INSTALL json")
                self._connection.execute("LOAD json")
            except Exception:
                pass  # JSON扩展可能已经安装
            
            # 创建表结构
            self._connection.execute(SCHEMA_SQL)
            
        except Exception as e:
            raise DatabaseError(f"Failed to initialize schema: {e}")
    
    @contextmanager
    def transaction(self, isolation_level: str = "SERIALIZABLE") -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        数据库事务上下文管理器（简化版并发控制）
        
        Args:
            isolation_level: 事务隔离级别，支持 READ_COMMITTED, SERIALIZABLE
        """
        with self._lock:
            conn = self.connection
            try:
                # DuckDB doesn't support SET TRANSACTION ISOLATION LEVEL syntax
                # Just begin the transaction
                conn.execute("BEGIN")
                yield conn
                conn.execute("COMMIT")
            except Exception as e:
                try:
                    conn.execute("ROLLBACK")
                except:
                    pass  # 忽略回滚错误
                
                # 简化并发冲突处理：不自动重试，直接返回错误
                if "conflict" in str(e).lower() or "serialization" in str(e).lower():
                    from .exceptions import ConcurrencyError
                    raise ConcurrencyError(f"系统繁忙，请稍后重试")
                raise DatabaseError(f"数据库操作失败: {str(e)}")
    
    def init_database(self):
        """初始化数据库"""
        con = self.get_connection()
        try:
            con.execute("INSTALL json")
            con.execute("LOAD json")
        except Exception:
            pass
        con.execute(SCHEMA_SQL)
    
    def execute_query(self, query: str, params: list = None) -> list:
        """执行查询并返回结果"""
        try:
            con = self.get_connection()
            if params:
                return con.execute(query, params).fetchall()
            return con.execute(query).fetchall()
        except Exception as e:
            raise DatabaseError(f"Query execution failed: {e}")
    
    def execute_one(self, query: str, params: list = None) -> Optional[tuple]:
        """执行查询并返回单条结果"""
        try:
            con = self.get_connection()
            if params:
                return con.execute(query, params).fetchone()
            return con.execute(query).fetchone()
        except Exception as e:
            raise DatabaseError(f"Query execution failed: {e}")
    
    def begin_transaction(self):
        """开始事务"""
        con = self.get_connection()
        con.execute("BEGIN")
    
    def commit_transaction(self):
        """提交事务"""
        con = self.get_connection()
        con.execute("COMMIT")
    
    def rollback_transaction(self):
        """回滚事务"""
        con = self.get_connection()
        con.execute("ROLLBACK")


# 全局数据库管理器实例
db_manager = DatabaseManager()


def get_conn():
    """保持向后兼容的连接获取函数"""
    return db_manager.get_connection()


def init_db():
    """保持向后兼容的初始化函数"""
    db_manager.init_database()


def init_all_dbs():
    """保持向后兼容的批量初始化函数"""
    init_db()