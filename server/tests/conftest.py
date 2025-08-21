"""
测试配置文件
提供测试所需的fixtures和配置
"""

import pytest
import tempfile
import os
import json
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from core.database import DatabaseManager
from config.settings import settings

class TestSettings:
    """测试环境配置"""
    debug: bool = True
    database_url: str = "duckdb:///:memory:"  # 内存数据库
    jwt_secret_key: str = "test-secret-key"
    api_title: str = "罡好饭 API (Test)"
    api_version: str = "1.0.0-test"
    api_prefix: str = "/api/v1"

@pytest.fixture
def test_settings():
    """测试配置"""
    return TestSettings()

@pytest.fixture
def test_db(test_settings):
    """测试数据库"""
    db_manager = DatabaseManager()
    db_manager.db_path = ":memory:"
    
    # 初始化测试数据库
    with db_manager.connection as conn:
        # 创建表结构
        conn.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            openid VARCHAR(100) UNIQUE NOT NULL,
            nickname VARCHAR(100),
            avatar_url TEXT,
            balance_cents INTEGER DEFAULT 0,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.execute("""
        CREATE TABLE meals (
            meal_id INTEGER PRIMARY KEY,
            date DATE NOT NULL,
            slot VARCHAR(20) NOT NULL,
            description TEXT NOT NULL,
            base_price_cents INTEGER NOT NULL,
            capacity INTEGER NOT NULL,
            options TEXT,
            status VARCHAR(20) DEFAULT 'published',
            creator_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, slot)
        )
        """)
        
        conn.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            meal_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            options_json TEXT,
            amount_cents INTEGER NOT NULL,
            notes TEXT,
            status VARCHAR(20) DEFAULT 'active',
            locked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.execute("""
        CREATE TABLE ledger (
            ledger_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type VARCHAR(20) NOT NULL,
            amount_cents INTEGER NOT NULL,
            ref_type VARCHAR(20),
            ref_id INTEGER,
            remark TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.execute("""
        CREATE TABLE logs (
            log_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            actor_id INTEGER,
            action VARCHAR(50) NOT NULL,
            detail_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    
    yield db_manager
    
    # 清理
    db_manager._connection = None

@pytest.fixture
def app_instance(test_settings, test_db):
    """测试应用"""
    # 临时替换全局设置
    import config.settings as settings_module
    original_settings = settings_module.settings
    settings_module.settings = test_settings
    
    # 临时替换数据库管理器
    import core.database as db_module
    original_db_manager = db_module.db_manager
    db_module.db_manager = test_db
    
    app = create_app()
    
    yield app
    
    # 恢复原始配置
    settings_module.settings = original_settings
    db_module.db_manager = original_db_manager

@pytest.fixture
def client(app_instance):
    """测试客户端"""
    return TestClient(app_instance)

@pytest.fixture
def sample_user(test_db):
    """示例用户"""
    with test_db.connection as conn:
        conn.execute("""
        INSERT INTO users (openid, nickname, balance_cents, is_admin)
        VALUES ('test_openid_123', '测试用户', 10000, FALSE)
        """)
        user_id = conn.lastrowid
    
    return {
        "user_id": user_id,
        "openid": "test_openid_123",
        "nickname": "测试用户",
        "balance_cents": 10000,
        "is_admin": False
    }

@pytest.fixture
def admin_user(test_db):
    """管理员用户"""
    with test_db.connection as conn:
        conn.execute("""
        INSERT INTO users (openid, nickname, balance_cents, is_admin)
        VALUES ('admin_openid_456', '管理员', 50000, TRUE)
        """)
        user_id = conn.lastrowid
    
    return {
        "user_id": user_id,
        "openid": "admin_openid_456", 
        "nickname": "管理员",
        "balance_cents": 50000,
        "is_admin": True
    }

@pytest.fixture
def sample_meal(test_db, admin_user):
    """示例餐次"""
    with test_db.connection as conn:
        options = json.dumps([
            {"id": "chicken_leg", "name": "加鸡腿", "price_cents": 300},
            {"id": "extra_rice", "name": "加饭", "price_cents": 100}
        ])
        
        conn.execute("""
        INSERT INTO meals (date, slot, description, base_price_cents, capacity, options, creator_id)
        VALUES ('2024-01-15', 'lunch', '香辣鸡腿饭', 2000, 50, ?, ?)
        """, [options, admin_user["user_id"]])
        meal_id = conn.lastrowid
    
    return {
        "meal_id": meal_id,
        "date": "2024-01-15",
        "slot": "lunch",
        "description": "香辣鸡腿饭",
        "base_price_cents": 2000,
        "capacity": 50,
        "status": "published"
    }

@pytest.fixture
def auth_headers(sample_user):
    """认证请求头"""
    # 这里应该生成真实的JWT token，简化为mock
    return {
        "Authorization": "Bearer test_token",
        "X-DB-Key": "test_key"
    }

@pytest.fixture
def admin_headers(admin_user):
    """管理员认证请求头"""
    return {
        "Authorization": "Bearer admin_token",
        "X-DB-Key": "test_key"
    }