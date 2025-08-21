"""
测试数据库管理器
负责创建、初始化和管理测试专用数据库
"""

import duckdb
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

from .config_manager import get_config_manager


class TestDatabaseManager:
    """测试数据库管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化数据库管理器"""
        if config is None:
            config = get_config_manager().get_database_config()
        
        self.config = config
        self.db_path: Optional[Path] = None
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
        self.backup_path: Optional[Path] = None
    
    def create_test_database(self) -> str:
        """创建测试数据库，返回数据库路径"""
        try:
            # 确定数据库路径
            self.db_path = Path(self.config["path"])
            
            # 确保父目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果数据库已存在，先备份
            if self.db_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.backup_path = self.db_path.parent / f"{self.db_path.stem}_backup_{timestamp}.duckdb"
                shutil.copy2(self.db_path, self.backup_path)
                print(f"Existing database backed up to: {self.backup_path}")
                
                # 删除原数据库
                self.db_path.unlink()
            
            print(f"Creating test database at: {self.db_path}")
            return str(self.db_path)
            
        except Exception as e:
            raise RuntimeError(f"Failed to create test database: {e}")
    
    def initialize_schema(self):
        """初始化数据库表结构"""
        if not self.db_path:
            raise RuntimeError("Database not created yet. Call create_test_database() first.")
        
        try:
            # 建立连接
            self.connection = duckdb.connect(str(self.db_path))
            
            # 安装和加载JSON扩展
            try:
                self.connection.execute("INSTALL json")
                self.connection.execute("LOAD json")
            except Exception as e:
                print(f"Warning: JSON extension setup failed: {e}")
            
            # 执行schema初始化
            schema_sql = self._get_schema_sql()
            self.connection.execute(schema_sql)
            
            print("✓ Database schema initialized successfully")
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize database schema: {e}")
    
    def _get_schema_sql(self) -> str:
        """获取数据库schema SQL"""
        return """
        -- 创建序列
        CREATE SEQUENCE IF NOT EXISTS users_id_seq;
        CREATE SEQUENCE IF NOT EXISTS meals_id_seq;
        CREATE SEQUENCE IF NOT EXISTS orders_id_seq;
        CREATE SEQUENCE IF NOT EXISTS ledger_id_seq;
        CREATE SEQUENCE IF NOT EXISTS logs_id_seq;
        
        -- 用户表
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
        
        -- 餐次表
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
        
        -- 订单表
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
        
        -- 账本表
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
        
        -- 日志表
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
    
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """获取数据库连接"""
        if not self.connection:
            if not self.db_path or not self.db_path.exists():
                raise RuntimeError("Database not initialized. Call create_test_database() and initialize_schema() first.")
            
            self.connection = duckdb.connect(str(self.db_path))
            
            # 确保JSON扩展已加载
            try:
                self.connection.execute("LOAD json")
            except Exception:
                pass
        
        return self.connection
    
    def reset_database(self):
        """重置数据库到初始状态（清空所有数据）"""
        if not self.connection:
            return
        
        try:
            # 清空所有表的数据
            tables = ['logs', 'ledger', 'orders', 'meals', 'users']
            for table in tables:
                self.connection.execute(f"DELETE FROM {table}")
            
            # 重置序列
            sequences = ['users_id_seq', 'meals_id_seq', 'orders_id_seq', 'ledger_id_seq', 'logs_id_seq']
            for seq in sequences:
                self.connection.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
            
            print("✓ Database reset to initial state")
            
        except Exception as e:
            print(f"Warning: Database reset failed: {e}")
    
    def cleanup_database(self, success: bool = True):
        """清理数据库"""
        try:
            # 关闭连接
            if self.connection:
                self.connection.close()
                self.connection = None
            
            if not self.db_path or not self.db_path.exists():
                return
            
            if success and self.config.get("cleanup_on_success", True):
                # 测试成功，删除数据库
                self.db_path.unlink()
                print("✓ Test database cleaned up (success)")
                
                # 删除备份文件
                if self.backup_path and self.backup_path.exists():
                    self.backup_path.unlink()
                    print("✓ Backup database cleaned up")
                    
            elif not success and self.config.get("backup_on_failure", True):
                # 测试失败，保留数据库供调试
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                failure_path = self.db_path.parent / f"{self.db_path.stem}_failure_{timestamp}.duckdb"
                shutil.copy2(self.db_path, failure_path)
                print(f"✓ Test database preserved for debugging: {failure_path}")
                
                # 删除原数据库
                self.db_path.unlink()
            else:
                # 删除数据库
                self.db_path.unlink()
                print("✓ Test database removed")
                
        except Exception as e:
            print(f"Warning: Database cleanup failed: {e}")
    
    def verify_schema(self) -> bool:
        """验证数据库schema是否正确"""
        if not self.connection:
            return False
        
        try:
            # 检查必需的表是否存在
            required_tables = ['users', 'meals', 'orders', 'ledger', 'logs']
            
            for table in required_tables:
                result = self.connection.execute(
                    f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'"
                ).fetchone()
                
                if not result or result[0] == 0:
                    print(f"✗ Required table missing: {table}")
                    return False
            
            print("✓ Database schema verification passed")
            return True
            
        except Exception as e:
            print(f"✗ Schema verification failed: {e}")
            return False
    
    def get_table_count(self, table_name: str) -> int:
        """获取指定表的记录数"""
        if not self.connection:
            return 0
        
        try:
            result = self.connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except Exception:
            return 0
    
    def execute_query(self, sql: str, params: list = None) -> list:
        """执行查询并返回结果"""
        if not self.connection:
            raise RuntimeError("Database connection not available")
        
        try:
            if params:
                result = self.connection.execute(sql, params)
            else:
                result = self.connection.execute(sql)
            
            return result.fetchall()
            
        except Exception as e:
            raise RuntimeError(f"Query execution failed: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        success = exc_type is None
        self.cleanup_database(success)


if __name__ == "__main__":
    # 测试数据库管理器
    try:
        print("Testing database manager...")
        
        with TestDatabaseManager() as db_mgr:
            # 创建数据库
            db_path = db_mgr.create_test_database()
            print(f"Database created: {db_path}")
            
            # 初始化schema
            db_mgr.initialize_schema()
            
            # 验证schema
            if db_mgr.verify_schema():
                print("✓ Database manager test passed")
            else:
                print("✗ Database manager test failed")
                
    except Exception as e:
        print(f"✗ Database manager test failed: {e}")