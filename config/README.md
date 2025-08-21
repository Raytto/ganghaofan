# 环境配置管理

本目录包含项目的环境配置管理系统，支持在本地开发和远程服务器环境之间快速切换。

## 文件说明

- `environment.json` - 环境配置文件，定义了本地和远程环境的API地址和数据库路径
- `../scripts/switch-env.py` - 环境切换脚本
- `../scripts/start-local.bat` - 启动本地开发环境的批处理文件
- `../scripts/start-remote.bat` - 切换到远程环境的批处理文件

## 使用方法

### 方式一：使用批处理文件（推荐）

1. **启动本地开发环境**：
   ```bash
   双击运行 scripts/start-local.bat
   ```
   这会自动：
   - 切换到本地环境配置
   - 启动本地开发服务器

2. **切换到远程环境**：
   ```bash
   双击运行 scripts/start-remote.bat
   ```
   这会将前端配置切换到远程服务器

### 方式二：使用命令行

1. **查看当前环境**：
   ```bash
   python scripts/switch-env.py
   ```

2. **切换到本地环境**：
   ```bash
   python scripts/switch-env.py local
   ```

3. **切换到远程环境**：
   ```bash
   python scripts/switch-env.py remote
   ```

4. **手动启动本地服务器**：
   ```bash
   cd server
   conda activate ghf-server
   python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

## 环境配置

### 本地环境 (local)
- API地址: `http://127.0.0.1:8000/api/v1`
- 数据库: `./server/data/ganghaofan.duckdb`

### 远程环境 (remote)
- API地址: `http://us.pangruitao.com:8000/api/v1`
- 数据库: `/home/pp/mp/ganghaofan/server/data/ganghaofan.duckdb`

## 自定义环境

可以在 `environment.json` 中添加新的环境配置：

```json
{
  "environments": {
    "staging": {
      "name": "测试环境",
      "backend": {
        "host": "staging.example.com",
        "port": 8000,
        "protocol": "https"
      },
      "database": {
        "path": "/path/to/staging/db"
      }
    }
  }
}
```

然后使用 `python scripts/switch-env.py staging` 切换到新环境。

## 原理说明

环境切换脚本会自动更新以下文件中的配置：

1. `client/miniprogram/core/constants/api.ts` - 前端API常量配置
2. `client/miniprogram/utils/api.ts` - 前端API工具配置  
3. `server/config/settings.py` - 后端配置文件

这样确保前后端都使用正确的环境配置。