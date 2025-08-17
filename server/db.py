import os
import duckdb
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "ganghaofan.duckdb"

_conn = None

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


def get_conn():
    global _conn
    if _conn is None:
        _conn = duckdb.connect(str(DB_PATH))
    return _conn


def init_db():
    con = get_conn()
    # Ensure JSON extension is available (for JSON column type)
    try:
        con.execute("INSTALL json")
    except Exception:
        pass
    try:
        con.execute("LOAD json")
    except Exception:
        pass
    con.execute(SCHEMA_SQL)
