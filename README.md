# 罡好饭小程序

一个专为熟人间订餐设计的微信小程序，让健康美味的家常菜触手可及。

## 项目简介

**罡好饭小程序**是一个基于微信小程序的订餐系统，旨在为公司同事提供便捷的家常菜订餐服务。系统由同事G的家人负责制作健康餐食，通过小程序实现菜单发布、在线下单、支付管理等功能，替代了原有的微信群接龙模式。

### 核心特性

- 📅 **月历视图**：直观展示每日午餐和晚餐安排
- 🍽️ **灵活订餐**：支持多种配菜选项和个性化需求
- 👨‍💼 **双重模式**：用户模式和管理员模式无缝切换
- 💰 **账户管理**：支持余额管理和详细消费记录
- 🔒 **状态管控**：订单锁定、完成等多状态管理
- 📱 **深色主题**：现代化UI设计，护眼且美观

## 技术架构

### 前端
- **框架**：微信小程序
- **语言**：TypeScript
- **渲染**：Skyline 渲染引擎
- **样式**：深色主题定制，扁平现代设计
- **布局**：Flexbox 布局，兼容多设备

### 后端
- **框架**：FastAPI (Python 3.11+)
- **数据库**：DuckDB
- **服务器**：Uvicorn
- **认证**：JWT + 微信登录
- **API**：RESTful API 设计

### 核心模块
```
client/                    # 微信小程序前端
├── miniprogram/
│   ├── pages/            # 页面文件
│   │   ├── index/        # 首页日历
│   │   ├── order/        # 订单页面
│   │   ├── admin/        # 管理页面
│   │   └── profile/      # 个人中心
│   ├── components/       # 自定义组件
│   └── utils/           # 工具函数和API封装

server/                   # FastAPI后端服务
├── app.py               # 应用入口
├── routers/             # 路由模块
├── models/              # 数据模型
├── services/            # 业务逻辑
└── data/               # DuckDB数据文件

doc/                     # 项目文档
├── overview.md          # 项目概览
├── color_std.md         # 颜色规范
└── agent_to_do/        # 开发文档
```

## 快速开始

### 环境要求

- **前端开发**：微信开发者工具
- **后端开发**：Python 3.11+, Conda (推荐)
- **数据库**：DuckDB (自动创建)

### 本地开发

#### 1. 后端服务启动（Windows PowerShell）

```powershell
# 克隆项目
git clone <repository-url>
cd ganghaofan

# 创建并激活 Conda 环境（推荐）
conda env create -f server/environment.yml
conda activate ghf-server

# 启动后端服务（确保已激活 ghf-server 环境）
python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

如果不想激活环境，可以使用一次性运行（避免 PATH/激活问题）：
```powershell
conda run -n ghf-server python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

若你看到错误 ModuleNotFoundError: No module named 'jose'，说明当前使用的是 base 环境或错误的 Python。
请激活 ghf-server 后再运行，或直接使用环境内 Python 的绝对路径：
```powershell
& "D:\\ProgramData\\Anaconda3\\envs\\ghf-server\\python.exe" -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

#### 2. 前端开发

1. 打开微信开发者工具
2. 导入项目，选择 `client/miniprogram` 目录
3. 配置后端API地址：`http://127.0.0.1:8000/api/v1`
4. 开始开发调试

#### 3. 验证安装

- 后端健康检查：`GET http://127.0.0.1:8000/api/v1/health`
- 数据库文件：`server/data/ganghaofan.duckdb` (自动创建)

## 部署说明

### 生产环境部署

#### 1. 服务器环境准备

```bash
# 安装Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# 创建项目目录
sudo mkdir -p /opt/ganghaofan
sudo chown $USER:$USER /opt/ganghaofan
```

#### 2. 部署后端服务

```bash
# 上传代码到服务器
cd /opt/ganghaofan
git clone <repository-url> .

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

#### 3. 配置系统服务 (systemd)

创建服务文件 `/etc/systemd/system/ganghaofan.service`：

```ini
[Unit]
Description=GangHaoFan FastAPI Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ganghaofan
Environment=PATH=/opt/ganghaofan/venv/bin
ExecStart=/opt/ganghaofan/venv/bin/python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable ganghaofan
sudo systemctl start ganghaofan
sudo systemctl status ganghaofan
```

#### 4. 配置Nginx反向代理

创建Nginx配置 `/etc/nginx/sites-available/ganghaofan`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 如果需要提供静态文件
    location / {
        root /opt/ganghaofan/static;
        try_files $uri $uri/ =404;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/ganghaofan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. 数据备份策略

创建备份脚本 `/opt/ganghaofan/scripts/backup.py`：

```python
#!/usr/bin/env python3
import os
import shutil
import datetime
from pathlib import Path

def backup_database():
    """每日备份DuckDB数据文件"""
    data_dir = Path("/opt/ganghaofan/server/data")
    backup_dir = Path("/opt/ganghaofan/backups")
    backup_dir.mkdir(exist_ok=True)
    
    # 创建带时间戳的备份
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"ganghaofan_backup_{timestamp}.duckdb"
    
    src = data_dir / "ganghaofan.duckdb"
    dst = backup_dir / backup_name
    
    if src.exists():
        shutil.copy2(src, dst)
        print(f"备份完成: {dst}")
        
        # 清理30天前的备份
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
        for backup_file in backup_dir.glob("ganghaofan_backup_*.duckdb"):
            if backup_file.stat().st_mtime < cutoff.timestamp():
                backup_file.unlink()
                print(f"清理旧备份: {backup_file}")

if __name__ == "__main__":
    backup_database()
```

添加crontab定时任务：
```bash
# 每天凌晨2点执行备份
crontab -e
# 添加：
0 2 * * * /opt/ganghaofan/venv/bin/python /opt/ganghaofan/scripts/backup.py
```

### SSL证书配置 (可选)

使用Let's Encrypt免费SSL证书：

```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo systemctl enable certbot.timer
```

## 功能特性详解

### 用户功能
- **日历浏览**：按月查看可订餐日期和状态
- **在线下单**：选择配菜，实时查看余量
- **订单管理**：修改、取消订单(在锁定前)
- **余额查询**：查看账户余额和消费记录
- **历史记录**：查看所有订餐历史

### 管理员功能
- **餐次发布**：发布每日午餐、晚餐菜单
- **订单管控**：锁定订单、标记完成、批量取消
- **价格管理**：设置基础价格和配菜价格
- **容量控制**：设置每餐供应份数上限
- **财务管理**：查看所有用户订单和收支情况

### 状态管理
- **待发布**：灰色显示，管理员可发布
- **可订餐**：黄色显示，用户可下单
- **已订完**：灰色显示，达到容量上限
- **已锁定**：紫色显示，停止下单和修改
- **已完成**：蓝色显示，餐次结束
- **已取消**：灰色显示，已撤销的餐次

## 常见问题

### 开发问题

**Q: 后端启动失败，提示模块找不到**
```bash
# 确保在仓库根目录运行
cd /path/to/ganghaofan
python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

**Q: 前端无法连接后端**
- 检查后端服务是否正常运行：`http://127.0.0.1:8000/api/v1/health`
- 确认API基础地址配置正确
- 检查网络防火墙设置

**Q: 数据库连接错误**
- DuckDB文件会自动创建在 `server/data/ganghaofan.duckdb`
- 确保目录有写入权限

### 部署问题

**Q: systemd服务启动失败**
```bash
# 查看详细错误信息
sudo journalctl -u ganghaofan -f

# 检查配置文件语法
sudo systemctl daemon-reload
```

**Q: Nginx反向代理不工作**
```bash
# 检查Nginx配置
sudo nginx -t

# 查看错误日志
sudo tail -f /var/log/nginx/error.log
```

## 开发指南

### 添加新页面
1. 在 `app.json.pages` 中注册路由
2. 创建页面目录和文件 (`index.wxml`, `index.ts`, `index.wxss`, `index.json`)
3. 使用 `navigation-bar` 组件保持风格一致

### 添加新API
1. 后端：在相应router中添加路由
2. 前端：在 `utils/api.ts` 中添加封装函数
3. 页面：调用API并处理loading/错误状态

### 样式规范
- 主色调：深色主题 `#1B1B1B`
- 文字颜色：主文字 `#C9D1D9`，次级 `#8B949E`
- 布局：优先使用Flexbox，避免CSS Grid
- 组件：复用 `navigation-bar` 等基础组件

## 贡献指南

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目Issues: [GitHub Issues](../../issues)
- 项目Wiki: [GitHub Wiki](../../wiki)

---

**让我们一起享受健康美味的罡好饭！** 🍽️