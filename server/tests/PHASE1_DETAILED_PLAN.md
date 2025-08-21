# 第一阶段：基础架构搭建 - 详细实施计划

## 阶段目标

建立稳定可靠的测试基础架构，为后续测试用例开发提供强有力的支撑。

## 工作方针

1. **稳定性优先**：确保测试环境稳定可重复
2. **简单易用**：提供简洁的API和工具
3. **模块化设计**：各组件独立，便于维护
4. **详细日志**：提供充分的调试信息

## 详细任务分解

### 任务1：测试环境配置管理 (预计4小时)

#### 1.1 创建测试配置文件
**文件**: `tests/config/test_config.json`
```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8001,
    "startup_timeout": 30
  },
  "database": {
    "path": "data/test_ganghaofan.duckdb",
    "backup_on_failure": true,
    "cleanup_on_success": true
  },
  "auth": {
    "jwt_secret": "test-secret-key-for-e2e-testing",
    "token_expire_hours": 24
  },
  "logging": {
    "level": "INFO",
    "file_pattern": "logs/test_run_{timestamp}.log"
  },
  "timeouts": {
    "api_request": 10,
    "database_operation": 5
  }
}
```

#### 1.2 创建测试用户配置
**文件**: `tests/config/test_users.json`
```json
{
  "admin": {
    "openid": "test_admin_001",
    "nickname": "测试管理员",
    "is_admin": true,
    "initial_balance_cents": 0
  },
  "user_a": {
    "openid": "test_user_001",
    "nickname": "测试用户A",
    "is_admin": false,
    "initial_balance_cents": 0
  },
  "user_b": {
    "openid": "test_user_002", 
    "nickname": "测试用户B",
    "is_admin": false,
    "initial_balance_cents": 0
  },
  "rich_user": {
    "openid": "test_user_003",
    "nickname": "富有用户",
    "is_admin": false,
    "initial_balance_cents": 10000
  }
}
```

#### 1.3 配置管理器实现
**文件**: `tests/utils/config_manager.py`
- 加载和验证测试配置
- 提供配置访问接口
- 支持环境变量覆盖
- 配置变更检测

**核心功能**:
```python
class TestConfigManager:
    def __init__(self):
        self.config = self._load_config()
        self.users = self._load_users()
    
    def get_server_config(self) -> dict
    def get_database_config(self) -> dict
    def get_user_config(self, user_type: str) -> dict
    def get_auth_config(self) -> dict
```

### 任务2：测试数据库管理 (预计6小时)

#### 2.1 数据库管理器核心功能
**文件**: `tests/utils/database_manager.py`

**核心职责**:
- 创建独立的测试数据库
- 初始化数据库schema
- 管理数据库生命周期
- 提供数据清理功能

**关键实现**:
```python
class TestDatabaseManager:
    def __init__(self, config: dict):
        self.config = config
        self.db_path = None
        self.connection = None
    
    def create_test_database(self) -> str:
        """创建测试数据库，返回数据库路径"""
        
    def initialize_schema(self):
        """初始化数据库表结构"""
        
    def cleanup_database(self, success: bool = True):
        """清理数据库（成功时删除，失败时备份）"""
        
    def reset_database(self):
        """重置数据库到初始状态"""
        
    def get_connection(self):
        """获取数据库连接"""
```

#### 2.2 数据库操作辅助工具
**文件**: `tests/utils/db_helper.py`

**功能**:
- 提供常用数据库查询
- 数据验证辅助函数
- 测试数据注入工具

```python
class DatabaseHelper:
    def __init__(self, db_manager: TestDatabaseManager):
        self.db = db_manager
    
    def create_test_user(self, user_config: dict) -> int:
        """创建测试用户，返回用户ID"""
        
    def get_user_balance(self, user_id: int) -> int:
        """获取用户余额"""
        
    def verify_ledger_record(self, user_id: int, amount: int) -> bool:
        """验证账本记录"""
        
    def count_orders_for_meal(self, meal_id: int) -> int:
        """统计餐次的订单数"""
```

### 任务3：认证系统Mock (预计5小时)

#### 3.1 认证辅助工具
**文件**: `tests/utils/auth_helper.py`

**核心功能**:
- 动态设置环境变量模拟不同用户
- 生成真实JWT token
- 管理用户会话状态

```python
class AuthHelper:
    def __init__(self, config: dict, users_config: dict):
        self.config = config
        self.users = users_config
        self.current_user = None
    
    def set_mock_user(self, user_type: str) -> dict:
        """设置当前模拟用户"""
        
    def generate_jwt_token(self, user_type: str) -> str:
        """为指定用户生成JWT token"""
        
    def get_auth_headers(self, user_type: str = None) -> dict:
        """获取认证请求头"""
        
    def switch_user(self, user_type: str):
        """切换当前用户上下文"""
        
    def clear_mock_user(self):
        """清除模拟用户设置"""
```

#### 3.2 环境变量管理
**功能**:
- 自动设置和清理环境变量
- 支持用户快速切换
- 确保环境变量不污染系统

### 任务4：HTTP客户端封装 (预计4小时)

#### 4.1 测试客户端实现
**文件**: `tests/utils/test_client.py`

**核心功能**:
- 封装requests库
- 自动处理认证
- 统一错误处理
- 请求/响应日志记录

```python
class TestAPIClient:
    def __init__(self, base_url: str, auth_helper: AuthHelper):
        self.base_url = base_url
        self.auth = auth_helper
        self.session = requests.Session()
    
    def get(self, endpoint: str, user_type: str = None, **kwargs) -> dict:
        """发送GET请求"""
        
    def post(self, endpoint: str, data: dict = None, user_type: str = None, **kwargs) -> dict:
        """发送POST请求"""
        
    def put(self, endpoint: str, data: dict = None, user_type: str = None, **kwargs) -> dict:
        """发送PUT请求"""
        
    def delete(self, endpoint: str, user_type: str = None, **kwargs) -> dict:
        """发送DELETE请求"""
        
    def health_check(self) -> bool:
        """检查服务器健康状态"""
```

#### 4.2 API响应处理
- 自动解析JSON响应
- 统一错误码处理
- 响应时间记录
- 详细错误信息提取

### 任务5：测试服务器管理 (预计3小时)

#### 5.1 服务器启动脚本
**文件**: `tests/scripts/setup_test_env.sh`

**功能**:
```bash
#!/bin/bash

# 检查依赖
check_dependencies() {
    # 检查Python、conda、必要包
}

# 设置环境变量
setup_environment() {
    export TESTING=true
    export TEST_DB_PATH="data/test_ganghaofan.duckdb"
    export TEST_SERVER_PORT=8001
    # ... 其他环境变量
}

# 启动测试服务器
start_test_server() {
    # 使用conda环境启动服务器
    conda run -n ghf-server python -m uvicorn server.app:app \
        --reload --host 127.0.0.1 --port 8001 &
    
    # 等待服务器启动
    wait_for_server
}

# 验证服务器状态
verify_server() {
    # 健康检查
    curl -s http://127.0.0.1:8001/health
}

main() {
    check_dependencies
    setup_environment
    start_test_server
    verify_server
}
```

#### 5.2 服务器管理工具
**文件**: `tests/utils/server_manager.py`

```python
class TestServerManager:
    def __init__(self, config: dict):
        self.config = config
        self.process = None
    
    def start_server(self) -> bool:
        """启动测试服务器"""
        
    def stop_server(self):
        """停止测试服务器"""
        
    def is_server_running(self) -> bool:
        """检查服务器是否运行"""
        
    def wait_for_server(self, timeout: int = 30) -> bool:
        """等待服务器启动完成"""
```

### 任务6：基础测试框架 (预计2小时)

#### 6.1 测试基类
**文件**: `tests/e2e/base_test.py`

```python
class BaseE2ETest:
    @classmethod
    def setup_class(cls):
        """测试类级别的设置"""
        cls.config = TestConfigManager()
        cls.db_manager = TestDatabaseManager(cls.config.get_database_config())
        cls.auth_helper = AuthHelper(cls.config.get_auth_config(), cls.config.users)
        cls.server_manager = TestServerManager(cls.config.get_server_config())
        cls.client = TestAPIClient(cls._get_base_url(), cls.auth_helper)
    
    @classmethod
    def teardown_class(cls):
        """测试类级别的清理"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.db_manager.reset_database()
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.auth_helper.clear_mock_user()
```

#### 6.2 基础测试实现
**文件**: `tests/e2e/test_basic_health.py`

- 服务器健康检查测试
- 基础认证流程测试
- 数据库连接测试
- 环境配置验证测试

## 验收标准

### 功能验收
- [ ] 测试配置能正确加载和验证
- [ ] 测试数据库能自动创建和初始化
- [ ] Mock认证系统能正常切换用户
- [ ] HTTP客户端能完成基本API调用
- [ ] 测试服务器能稳定启动和停止

### 性能验收
- [ ] 测试环境启动时间 < 30秒
- [ ] 数据库初始化时间 < 5秒
- [ ] 基础API调用响应时间 < 1秒

### 稳定性验收
- [ ] 连续启动/停止10次无失败
- [ ] 多个测试用例切换无冲突
- [ ] 异常情况下能正确清理资源

### 可用性验收
- [ ] 提供清晰的错误信息
- [ ] 日志记录详细且有用
- [ ] 配置简单易懂

## 时间规划

| 任务 | 预计时间 | 依赖关系 | 负责人 |
|------|----------|----------|--------|
| 配置管理 | 4小时 | - | Claude |
| 数据库管理 | 6小时 | 配置管理 | Claude |
| 认证Mock | 5小时 | 配置管理 | Claude |
| HTTP客户端 | 4小时 | 认证Mock | Claude |
| 服务器管理 | 3小时 | - | Claude |
| 基础测试 | 2小时 | 所有其他任务 | Claude |

**总计**: 24小时 (预留8小时缓冲) = 2个工作日

## 风险预案

### 高风险项
1. **服务器端口冲突**: 提供端口动态分配功能
2. **数据库文件权限**: 确保测试用户有读写权限
3. **环境变量冲突**: 使用前缀隔离测试环境变量

### 中风险项
1. **依赖包版本冲突**: 固定测试依赖版本
2. **Mock认证失效**: 提供多种认证配置方式
3. **测试数据残留**: 强制清理机制

### 应急措施
- 准备回退到手动测试
- 提供详细的故障排查文档
- 建立测试环境快速重建流程

## 下一步行动

1. **立即开始**: 按任务顺序逐一实现
2. **每日检查**: 跟踪任务完成进度
3. **及时调整**: 根据实际情况调整计划
4. **文档同步**: 重要决策及时更新文档

完成第一阶段后，立即进入第二阶段的核心测试用例开发。