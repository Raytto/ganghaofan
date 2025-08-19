"""
测试配置文件
提供测试所需的fixtures和配置
"""

import pytest
from fastapi.testclient import TestClient
import tempfile
import os

from ..app import app
from ..core.database import db_manager


@pytest.fixture
def client():
    """创建测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_db():
    """创建临时测试数据库"""
    # 创建临时数据库文件
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.duckdb')
    temp_db_file.close()
    
    # 设置测试数据库路径
    original_connection = db_manager._connection
    db_manager._connection = None
    
    # 重新配置数据库路径（这里需要mock配置）
    yield temp_db_file.name
    
    # 清理
    db_manager._connection = original_connection
    try:
        os.unlink(temp_db_file.name)
    except:
        pass


@pytest.fixture
def auth_headers():
    """创建认证头"""
    # 这里需要创建一个有效的JWT token
    # 暂时返回一个模拟的header
    return {"Authorization": "Bearer test-token"}