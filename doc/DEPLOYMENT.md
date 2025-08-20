# 罡好饭系统部署指南

## 部署概述

本文档提供罡好饭餐饮订购系统的完整部署指南，包括开发环境、测试环境和生产环境的部署流程。

### 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   微信小程序     │────│   FastAPI后端   │────│   DuckDB数据库   │
│   (前端界面)     │    │   (API服务)     │    │   (数据存储)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 环境要求

### 系统要求
- **操作系统**: Linux (推荐 Ubuntu 20.04+) / macOS / Windows WSL2
- **Python**: 3.11+
- **Node.js**: 16+ (前端开发)
- **内存**: 2GB+ (开发) / 4GB+ (生产)
- **存储**: 10GB+ 可用空间

### 软件依赖
- **Conda**: 环境管理
- **Git**: 代码版本控制
- **Nginx**: 反向代理 (生产环境)
- **Supervisor**: 进程管理 (生产环境)

---

## 开发环境部署

### 1. 代码获取

```bash
# 克隆代码库
git clone <repository-url> ganghaofan
cd ganghaofan

# 切换到开发分支
git checkout main
```

### 2. 后端环境设置

```bash
# 进入后端目录
cd server

# 创建并激活Conda环境
conda env create -f environment.yml
conda activate ghf-server

# 验证环境
python --version  # 应该显示 3.11+
pip list | grep fastapi
```

### 3. 配置文件设置

```bash
# 创建配置目录
mkdir -p config

# 创建数据库配置
cat > config/db.json << 'EOF'
{
    "db_path": "data/ganghaofan.duckdb"
}
EOF

# 创建访问密钥配置 (开发环境可为空)
cat > config/passphrases.json << 'EOF'
{
    "dev_key": "development"
}
EOF

# 创建Mock配置 (可选)
cat > config/dev_mock.json << 'EOF'
{
    "enabled": true,
    "openid": "mock_dev_user",
    "nickname": "开发测试用户",
    "unique_per_login": false
}
EOF
```

### 4. 启动后端服务

```bash
# 方式1: 直接启动
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

# 方式2: 使用Makefile
make dev

# 方式3: 一次性运行
conda run -n ghf-server python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

### 5. 前端环境设置

```bash
# 进入前端目录
cd ../client

# 安装依赖
npm install

# 使用微信开发者工具
# 1. 打开微信开发者工具
# 2. 导入项目：选择 client/miniprogram 目录
# 3. 配置 AppID 和服务器域名
```

### 6. 验证部署

```bash
# 后端健康检查
curl http://127.0.0.1:8000/health

# 预期响应
{
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected"
}

# API文档访问
# http://127.0.0.1:8000/docs
```

---

## 测试环境部署

### 1. 运行测试套件

```bash
cd server

# 运行所有测试
./run_tests.sh

# 运行特定测试
./run_tests.sh unit        # 单元测试
./run_tests.sh api         # API测试
./run_tests.sh coverage    # 带覆盖率的测试

# 使用Makefile
make test
make test-cov
```

### 2. 测试环境配置

测试会自动使用内存数据库，不需要额外配置。测试完成后会自动清理。

---

## 生产环境部署

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础软件
sudo apt install -y git nginx supervisor curl

# 安装Conda (如果未安装)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
```

### 2. 部署脚本

```bash
# 创建部署脚本
cat > deploy.sh << 'EOF'
#!/bin/bash
set -e

# 配置变量
DEPLOY_USER="www-data"
APP_NAME="ganghaofan"
APP_PATH="/opt/ganghaofan"
CONDA_ENV="ghf-server"

# 创建应用目录
sudo mkdir -p $APP_PATH
sudo chown $DEPLOY_USER:$DEPLOY_USER $APP_PATH

# 克隆代码
sudo -u $DEPLOY_USER git clone <repository-url> $APP_PATH

# 进入应用目录
cd $APP_PATH/server

# 创建Conda环境
sudo -u $DEPLOY_USER conda env create -f environment.yml

# 创建生产配置
sudo -u $DEPLOY_USER mkdir -p config
sudo -u $DEPLOY_USER cat > config/db.json << 'DBEOF'
{
    "db_path": "/opt/ganghaofan/data/ganghaofan.duckdb"
}
DBEOF

# 创建数据目录
sudo -u $DEPLOY_USER mkdir -p ../data

echo "代码部署完成"
EOF

chmod +x deploy.sh
```

### 3. 生产配置

#### Nginx配置

```nginx
# /etc/nginx/sites-available/ganghaofan
server {
    listen 80;
    server_name your-domain.com;  # 替换为实际域名

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    # API文档 (可选，生产环境可关闭)
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }

    # 静态文件 (如果有)
    location /static/ {
        alias /opt/ganghaofan/static/;
        expires 30d;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/ganghaofan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### Supervisor配置

```ini
# /etc/supervisor/conf.d/ganghaofan.conf
[program:ganghaofan]
directory=/opt/ganghaofan/server
command=/home/www-data/miniconda3/envs/ghf-server/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 2
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/ganghaofan.log
environment=
    JWT_SECRET_KEY="your-production-secret-key-here",
    ENVIRONMENT="production"

[program:ganghaofan-worker]
directory=/opt/ganghaofan/server
command=/home/www-data/miniconda3/envs/ghf-server/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8001 --workers 1
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/ganghaofan-worker.log
environment=
    JWT_SECRET_KEY="your-production-secret-key-here",
    ENVIRONMENT="production"
```

```bash
# 重新加载配置
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ganghaofan:*
```

### 4. 环境变量配置

```bash
# 创建环境配置文件
cat > /opt/ganghaofan/server/.env << 'EOF'
# 生产环境配置
ENVIRONMENT=production
DEBUG=false

# JWT配置 - 必须设置强密钥
JWT_SECRET_KEY=your-very-secure-secret-key-change-this-in-production

# API配置
API_TITLE=罡好饭 API
API_VERSION=1.0.0

# 数据库配置
DATABASE_URL=duckdb:///opt/ganghaofan/data/ganghaofan.duckdb

# 日志配置
LOG_LEVEL=INFO
EOF

# 设置适当权限
sudo chown www-data:www-data /opt/ganghaofan/server/.env
sudo chmod 600 /opt/ganghaofan/server/.env
```

### 5. SSL证书配置 (推荐)

```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 数据库管理

### 初始化

```bash
# 开发环境
cd server
python -c "from core.database import db_manager; db_manager.init_database()"

# 生产环境
cd /opt/ganghaofan/server
sudo -u www-data /home/www-data/miniconda3/envs/ghf-server/bin/python -c "from core.database import db_manager; db_manager.init_database()"
```

### 备份与恢复

```bash
# 备份脚本
#!/bin/bash
BACKUP_DIR="/opt/backups/ganghaofan"
DB_PATH="/opt/ganghaofan/data/ganghaofan.duckdb"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_PATH "${BACKUP_DIR}/ganghaofan_${DATE}.duckdb"

# 保留最近30天的备份
find $BACKUP_DIR -name "ganghaofan_*.duckdb" -mtime +30 -delete

echo "备份完成: ganghaofan_${DATE}.duckdb"
```

### 数据迁移

```bash
# 从开发环境迁移到生产环境
scp server/data/ganghaofan.duckdb user@production-server:/opt/ganghaofan/data/

# 恢复备份
cp /opt/backups/ganghaofan/ganghaofan_20240115_120000.duckdb /opt/ganghaofan/data/ganghaofan.duckdb
sudo chown www-data:www-data /opt/ganghaofan/data/ganghaofan.duckdb
```

---

## 监控与日志

### 系统监控

```bash
# 检查服务状态
sudo supervisorctl status ganghaofan:*

# 查看日志
sudo tail -f /var/log/supervisor/ganghaofan.log

# 系统资源监控
htop
df -h  # 磁盘空间
free -h  # 内存使用
```

### 应用监控

```bash
# API健康检查脚本
#!/bin/bash
curl -f http://127.0.0.1:8000/health > /dev/null
if [ $? -eq 0 ]; then
    echo "$(date): API healthy"
else
    echo "$(date): API down, restarting..."
    sudo supervisorctl restart ganghaofan:*
fi
```

### 日志轮转

```bash
# /etc/logrotate.d/ganghaofan
/var/log/supervisor/ganghaofan*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

---

## 安全配置

### 1. 防火墙配置

```bash
# UFW配置
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw deny 8000  # 阻止直接访问应用端口
```

### 2. JWT密钥管理

- 生产环境必须设置强JWT密钥
- 定期轮换密钥
- 使用环境变量存储敏感信息

### 3. 数据库访问控制

- 限制数据库文件权限
- 定期备份数据
- 监控异常访问

---

## 故障排查

### 常见问题

1. **服务无法启动**
   ```bash
   # 检查Conda环境
   conda env list
   
   # 检查Python路径
   which python
   
   # 检查端口占用
   netstat -tlnp | grep :8000
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库文件权限
   ls -la /opt/ganghaofan/data/
   
   # 检查配置文件
   cat config/db.json
   ```

3. **API访问错误**
   ```bash
   # 检查Nginx配置
   sudo nginx -t
   
   # 检查代理设置
   curl -I http://127.0.0.1:8000/health
   ```

### 日志分析

```bash
# 应用日志
sudo tail -f /var/log/supervisor/ganghaofan.log

# Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 系统日志
sudo journalctl -u nginx -f
```

---

## 性能优化

### 1. 应用层优化

- 使用多个worker进程
- 启用异步处理
- 合理设置连接池

### 2. 数据库优化

- 定期运行`VACUUM`清理数据库
- 监控数据库大小
- 优化查询性能

### 3. 缓存策略

- API响应缓存
- 静态资源缓存
- CDN配置 (如需要)

---

## 版本更新

### 1. 代码更新流程

```bash
# 1. 备份当前版本
sudo -u www-data cp -r /opt/ganghaofan /opt/backups/ganghaofan_$(date +%Y%m%d)

# 2. 拉取新代码
cd /opt/ganghaofan
sudo -u www-data git fetch
sudo -u www-data git checkout <new-version-tag>

# 3. 更新依赖
cd server
sudo -u www-data conda env update -f environment.yml

# 4. 数据库迁移 (如有)
sudo -u www-data /home/www-data/miniconda3/envs/ghf-server/bin/python migrate.py

# 5. 重启服务
sudo supervisorctl restart ganghaofan:*

# 6. 验证更新
curl http://127.0.0.1:8000/health
```

### 2. 回滚流程

```bash
# 1. 停止服务
sudo supervisorctl stop ganghaofan:*

# 2. 恢复代码
sudo rm -rf /opt/ganghaofan
sudo mv /opt/backups/ganghaofan_$(date +%Y%m%d) /opt/ganghaofan

# 3. 恢复数据库 (如需要)
sudo cp /opt/backups/ganghaofan/ganghaofan_backup.duckdb /opt/ganghaofan/data/ganghaofan.duckdb

# 4. 重启服务
sudo supervisorctl start ganghaofan:*
```

---

## 联系支持

如在部署过程中遇到问题，请查看：

- [技术文档](./README.md)
- [API文档](./API.md)
- [故障排查指南](./guides/troubleshooting.md)
- 项目Issue页面

---

**注意**: 本文档假设您具备基本的Linux系统管理知识。生产环境部署建议由有经验的运维人员执行。