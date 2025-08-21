"""
测试HTTP客户端
封装requests库，提供统一的API调用接口
"""

import requests
import json
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
import time

from .auth_helper import AuthHelper
from .config_manager import get_config_manager


class TestAPIClient:
    """测试API客户端"""
    
    def __init__(self, base_url: str = None, auth_helper: AuthHelper = None):
        """初始化API客户端"""
        config_mgr = get_config_manager()
        
        self.base_url = base_url or config_mgr.get_base_url()
        self.auth = auth_helper or AuthHelper()
        self.timeouts = config_mgr.get_timeouts()
        
        # 创建session
        self.session = requests.Session()
        
        # 设置默认超时
        self.session.timeout = self.timeouts.get("api_request", 10)
        
        # 请求计数和时间统计
        self.request_count = 0
        self.total_time = 0.0
    
    def _make_request(self, method: str, endpoint: str, user_type: str = None,
                     data: Dict = None, json_data: Dict = None,
                     params: Dict = None, headers: Dict = None,
                     **kwargs) -> Dict[str, Any]:
        """发送HTTP请求的内部方法"""
        
        # 构造完整URL
        if endpoint.startswith('http'):
            url = endpoint
        else:
            # 确保endpoint以/开头
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
            url = urljoin(self.base_url, endpoint)
        
        # 准备请求头
        request_headers = {}
        
        # 添加认证头
        if user_type:
            auth_headers = self.auth.get_auth_headers(user_type)
            request_headers.update(auth_headers)
        elif self.auth.get_current_user_type():
            auth_headers = self.auth.get_auth_headers()
            request_headers.update(auth_headers)
        
        # 添加自定义头
        if headers:
            request_headers.update(headers)
        
        # 设置默认Content-Type
        if not request_headers.get('Content-Type'):
            request_headers['Content-Type'] = 'application/json'
        
        # 准备请求体
        request_data = None
        if json_data:
            request_data = json.dumps(json_data) if json_data else None
        elif data:
            request_data = data
        
        # 记录请求开始时间
        start_time = time.time()
        
        try:
            # 发送请求
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                data=request_data,
                params=params,
                **kwargs
            )
            
            # 记录请求时间
            elapsed = time.time() - start_time
            self.request_count += 1
            self.total_time += elapsed
            
            # 解析响应
            return self._parse_response(response, method, url, elapsed)
            
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            raise RuntimeError(f"Request failed: {method} {url} - {e} (took {elapsed:.2f}s)")
    
    def _parse_response(self, response: requests.Response, method: str, 
                       url: str, elapsed: float) -> Dict[str, Any]:
        """解析HTTP响应"""
        
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "elapsed": elapsed,
            "method": method,
            "url": url,
            "success": response.ok
        }
        
        # 解析响应体
        try:
            if response.content:
                result["data"] = response.json()
            else:
                result["data"] = None
        except json.JSONDecodeError:
            result["data"] = response.text
            result["warning"] = "Response is not valid JSON"
        
        # 处理错误响应
        if not response.ok:
            error_msg = f"{method} {url} failed with status {response.status_code}"
            
            if isinstance(result["data"], dict):
                error_detail = result["data"].get("detail", "Unknown error")
                error_msg += f": {error_detail}"
            elif result["data"]:
                error_msg += f": {result['data'][:200]}"
            
            result["error"] = error_msg
        
        return result
    
    def get(self, endpoint: str, user_type: str = None, params: Dict = None, 
            **kwargs) -> Dict[str, Any]:
        """发送GET请求"""
        return self._make_request("GET", endpoint, user_type, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Dict = None, user_type: str = None,
             **kwargs) -> Dict[str, Any]:
        """发送POST请求"""
        return self._make_request("POST", endpoint, user_type, json_data=data, **kwargs)
    
    def put(self, endpoint: str, data: Dict = None, user_type: str = None,
            **kwargs) -> Dict[str, Any]:
        """发送PUT请求"""
        return self._make_request("PUT", endpoint, user_type, json_data=data, **kwargs)
    
    def delete(self, endpoint: str, user_type: str = None, **kwargs) -> Dict[str, Any]:
        """发送DELETE请求"""
        return self._make_request("DELETE", endpoint, user_type, **kwargs)
    
    def patch(self, endpoint: str, data: Dict = None, user_type: str = None,
              **kwargs) -> Dict[str, Any]:
        """发送PATCH请求"""
        return self._make_request("PATCH", endpoint, user_type, json_data=data, **kwargs)
    
    def health_check(self) -> bool:
        """检查服务器健康状态"""
        try:
            response = self.get("/health")
            
            if response["success"] and isinstance(response["data"], dict):
                health_data = response["data"]
                return (health_data.get("status") == "healthy" and 
                       health_data.get("database") == "connected")
            
            return False
            
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def wait_for_server(self, timeout: int = 30, interval: float = 1.0) -> bool:
        """等待服务器启动完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.health_check():
                    print(f"✓ Server is ready (took {time.time() - start_time:.1f}s)")
                    return True
            except Exception:
                pass
            
            time.sleep(interval)
        
        print(f"✗ Server not ready after {timeout}s")
        return False
    
    def login(self, user_type: str, code: str = "test_code") -> Dict[str, Any]:
        """模拟用户登录"""
        # 设置Mock用户
        login_data = self.auth.create_login_request(user_type, code)
        
        # 发送登录请求
        response = self.post("/api/v1/auth/login", login_data)
        
        return response
    
    def get_user_info(self, user_type: str = None) -> Dict[str, Any]:
        """获取用户信息"""
        return self.get("/api/v1/users/me", user_type)
    
    def get_user_profile(self, user_type: str = None) -> Dict[str, Any]:
        """获取用户资料"""
        return self.get("/api/v1/users/me", user_type)
    
    def create_meal(self, meal_data: Dict[str, Any], user_type: str = "admin") -> Dict[str, Any]:
        """创建餐次"""
        return self.post("/api/v1/meals", meal_data, user_type)
    
    def get_meals(self, user_type: str = None, **params) -> Dict[str, Any]:
        """获取餐次列表"""
        return self.get("/api/v1/meals", user_type, params=params)
    
    def get_meal(self, meal_id: int, user_type: str = None) -> Dict[str, Any]:
        """获取单个餐次信息"""
        return self.get(f"/api/v1/meals/{meal_id}", user_type)
    
    def create_order(self, order_data: Dict[str, Any], user_type: str = None) -> Dict[str, Any]:
        """创建订单"""
        return self.post("/api/v1/orders/orders", order_data, user_type)
    
    def get_orders(self, user_type: str = None, **params) -> Dict[str, Any]:
        """获取订单列表"""
        return self.get("/api/v1/orders", user_type, params=params)
    
    def update_order(self, order_id: int, order_data: Dict[str, Any], 
                    user_type: str = None) -> Dict[str, Any]:
        """更新订单"""
        return self.put(f"/api/v1/orders/{order_id}", order_data, user_type)
    
    def recharge_balance(self, user_id: int, amount_cents: int, 
                        user_type: str = "admin") -> Dict[str, Any]:
        """给用户充值"""
        recharge_data = {
            "user_id": user_id,
            "amount_cents": amount_cents,
            "remark": "Test recharge"
        }
        return self.post("/api/v1/users/recharge", recharge_data, user_type)
    
    def get_balance(self, user_type: str = None) -> Dict[str, Any]:
        """获取用户余额"""
        return self.get("/api/v1/users/balance", user_type)
    
    def get_user_balance(self, user_type: str = None) -> Dict[str, Any]:
        """获取用户余额"""
        return self.get("/api/v1/users/me/balance", user_type)
    
    def lock_meal(self, meal_id: int, user_type: str = "admin") -> Dict[str, Any]:
        """锁定餐次"""
        return self.post(f"/api/v1/meals/{meal_id}/lock", {}, user_type)
    
    def unlock_meal(self, meal_id: int, user_type: str = "admin") -> Dict[str, Any]:
        """解锁餐次"""
        return self.post(f"/api/v1/meals/{meal_id}/unlock", {}, user_type)
    
    def cancel_meal(self, meal_id: int, user_type: str = "admin") -> Dict[str, Any]:
        """取消餐次"""
        return self.post(f"/api/v1/meals/{meal_id}/cancel", {}, user_type)
    
    # === 订单管理API ===    
    def get_order(self, order_id: int, user_type: str) -> Dict[str, Any]:
        """获取单个订单详情"""
        return self.get(f"/api/v1/orders/orders/{order_id}", user_type)
    
    def update_order(self, order_id: int, order_data: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """更新订单"""
        return self.put(f"/api/v1/orders/orders/{order_id}", order_data, user_type)
    
    def cancel_order(self, order_id: int, user_type: str) -> Dict[str, Any]:
        """取消订单"""
        return self.delete(f"/api/v1/orders/orders/{order_id}", user_type)
    
    def get_user_orders(self, user_type: str) -> Dict[str, Any]:
        """获取用户订单列表"""
        return self.get("/api/v1/orders/orders", user_type)
    
    # === 余额管理API ===    
    def get_user_balance_by_id(self, user_id: int, user_type: str) -> Dict[str, Any]:
        """根据用户ID获取余额（管理员功能）"""
        return self.get(f"/api/v1/users/{user_id}/balance", user_type)
    
    def recharge_balance(self, recharge_data: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """用户余额充值"""
        return self.post("/api/v1/user/recharge", recharge_data, user_type)
    
    def get_balance_history(self, user_type: str) -> Dict[str, Any]:
        """获取用户余额变动记录"""
        return self.get("/api/v1/user/balance/history", user_type)
    
    def admin_adjust_balance(self, adjust_data: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """管理员调整用户余额"""
        return self.post("/api/v1/admin/balance/adjust", adjust_data, user_type)
    
    def admin_recharge_user(self, recharge_data: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """管理员给用户充值"""
        return self.post("/api/v1/admin/users/recharge", recharge_data, user_type)
    
    # === 用户管理API ===
    
    def get_all_users(self, user_type: str) -> Dict[str, Any]:
        """获取所有用户列表（管理员功能）"""
        return self.get("/api/v1/admin/users", user_type)
    
    def get_system_stats(self, user_type: str) -> Dict[str, Any]:
        """获取系统统计信息（管理员功能）"""
        return self.get("/api/v1/admin/stats", user_type)
    
    # === HTTP方法扩展 ===
    def put(self, endpoint: str, data: Dict = None, user_type: str = None,
            **kwargs) -> Dict[str, Any]:
        """发送PUT请求"""
        return self._make_request("PUT", endpoint, user_type, json_data=data, **kwargs)
    
    def delete(self, endpoint: str, user_type: str = None, **kwargs) -> Dict[str, Any]:
        """发送DELETE请求"""
        return self._make_request("DELETE", endpoint, user_type, **kwargs)
    
    def assert_success(self, response: Dict[str, Any], message: str = ""):
        """断言请求成功"""
        if not response["success"]:
            error = response.get("error", "Unknown error")
            raise AssertionError(f"Request failed{': ' + message if message else ''}: {error}")
    
    def assert_status_code(self, response: Dict[str, Any], expected_code: int):
        """断言状态码"""
        actual_code = response["status_code"]
        if actual_code != expected_code:
            raise AssertionError(f"Expected status code {expected_code}, got {actual_code}")
    
    def assert_response_data(self, response: Dict[str, Any], expected_keys: list):
        """断言响应数据包含指定字段"""
        self.assert_success(response)
        
        data = response["data"]
        if not isinstance(data, dict):
            raise AssertionError(f"Expected dict response data, got {type(data)}")
        
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            raise AssertionError(f"Missing expected keys in response: {missing_keys}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        avg_time = self.total_time / self.request_count if self.request_count > 0 else 0
        
        return {
            "total_requests": self.request_count,
            "total_time": round(self.total_time, 2),
            "average_time": round(avg_time, 3),
            "base_url": self.base_url
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.request_count = 0
        self.total_time = 0.0


if __name__ == "__main__":
    # 测试HTTP客户端（需要服务器运行）
    try:
        print("Testing API client...")
        
        client = TestAPIClient()
        print(f"Client base URL: {client.base_url}")
        
        # 测试健康检查（如果服务器在运行）
        print("Attempting health check...")
        if client.health_check():
            print("✓ Health check passed")
            
            # 测试用户切换和认证
            with client.auth as auth:
                auth.set_mock_user("admin")
                response = client.get_user_info("admin")
                
                if response["success"]:
                    print("✓ User info request successful")
                else:
                    print(f"User info request failed: {response.get('error')}")
            
        else:
            print("Server not available for testing")
        
        # 显示统计
        stats = client.get_stats()
        print(f"✓ Client stats: {stats}")
        
        print("✓ API client test completed")
        
    except Exception as e:
        print(f"✗ API client test failed: {e}")