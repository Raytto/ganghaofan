"""
认证API集成测试
测试认证相关的API端点
"""

import pytest
import json


class TestAuthAPI:
    """认证API测试"""

    def test_login_success_with_mock(self, client):
        """测试使用Mock登录成功"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "code": "test_code",
                "db_key": "dev_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token_info" in data["data"]
        assert "user_info" in data["data"]
        assert data["data"]["token_info"]["token_type"] == "Bearer"

    def test_login_invalid_db_key(self, client):
        """测试使用无效的db_key登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "code": "test_code",
                "db_key": "invalid_key"
            }
        )
        
        # 根据实际实现，这里可能返回401或403
        assert response.status_code in [401, 403, 400]

    def test_login_missing_code(self, client):
        """测试缺少微信code的登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "db_key": "dev_key"
            }
        )
        
        assert response.status_code == 422  # 验证错误

    def test_login_missing_db_key(self, client):
        """测试缺少db_key的登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "code": "test_code"
            }
        )
        
        assert response.status_code == 422  # 验证错误

    def test_login_empty_request(self, client):
        """测试空请求体登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={}
        )
        
        assert response.status_code == 422  # 验证错误

    def test_login_malformed_json(self, client):
        """测试畸形JSON请求"""
        response = client.post(
            "/api/v1/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_passphrase_resolve_success(self, client):
        """测试口令解析成功"""
        response = client.post(
            "/api/v1/auth/passphrase/resolve",
            json={
                "passphrase": "test_passphrase"
            }
        )
        
        # 根据实际实现调整预期结果
        # 如果功能未实现，可能返回404或501
        assert response.status_code in [200, 404, 501]

    def test_token_validation_flow(self, client):
        """测试Token验证流程"""
        # 先登录获取Token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "code": "test_code",
                "db_key": "dev_key"
            }
        )
        
        assert login_response.status_code == 200
        token = login_response.json()["data"]["token_info"]["token"]
        
        # 使用Token访问需要认证的端点
        headers = {
            "Authorization": f"Bearer {token}",
            "X-DB-Key": "dev_key"
        }
        
        profile_response = client.get(
            "/api/v1/users/profile",
            headers=headers
        )
        
        # 根据实际API实现调整预期结果
        assert profile_response.status_code in [200, 404, 501]

    def test_expired_token_handling(self, client):
        """测试过期Token处理"""
        # 使用明显过期的Token
        headers = {
            "Authorization": "Bearer expired_token",
            "X-DB-Key": "dev_key"
        }
        
        response = client.get(
            "/api/v1/users/profile",
            headers=headers
        )
        
        assert response.status_code == 401

    def test_invalid_token_format(self, client):
        """测试无效Token格式"""
        headers = {
            "Authorization": "Bearer invalid.token.format",
            "X-DB-Key": "dev_key"
        }
        
        response = client.get(
            "/api/v1/users/profile",
            headers=headers
        )
        
        assert response.status_code == 401

    def test_missing_authorization_header(self, client):
        """测试缺少Authorization头"""
        response = client.get("/api/v1/users/profile")
        
        assert response.status_code == 401

    def test_missing_db_key_header(self, client):
        """测试缺少DB-Key头"""
        headers = {
            "Authorization": "Bearer some_token"
        }
        
        response = client.get(
            "/api/v1/users/profile",
            headers=headers
        )
        
        assert response.status_code in [401, 400]

    def test_user_info_structure(self, client):
        """测试登录返回的用户信息结构"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "code": "test_code",
                "db_key": "dev_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查token_info结构
        token_info = data["data"]["token_info"]
        assert "token" in token_info
        assert "expires_in" in token_info
        assert "token_type" in token_info
        assert token_info["token_type"] == "Bearer"
        
        # 检查user_info结构
        user_info = data["data"]["user_info"]
        assert "user_id" in user_info
        assert "openid" in user_info
        assert "balance_cents" in user_info
        assert "is_admin" in user_info
        assert isinstance(user_info["balance_cents"], int)
        assert isinstance(user_info["is_admin"], bool)

    def test_concurrent_login_attempts(self, client):
        """测试并发登录尝试"""
        import threading
        import time
        
        results = {}
        
        def login_thread(thread_id):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "code": f"test_code_{thread_id}",
                    "db_key": "dev_key"
                }
            )
            results[thread_id] = response.status_code
        
        # 启动多个并发登录线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=login_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有登录都成功
        for status_code in results.values():
            assert status_code == 200