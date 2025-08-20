# 罡好饭后端Makefile
# 提供便捷的开发和测试命令

.PHONY: help setup test test-unit test-api test-coverage clean dev lint format

# 默认目标
help:
	@echo "罡好饭后端开发命令"
	@echo ""
	@echo "开发命令:"
	@echo "  setup      设置开发环境"
	@echo "  dev        启动开发服务器"
	@echo "  test       运行所有测试"
	@echo "  test-unit  运行单元测试"
	@echo "  test-api   运行API测试"
	@echo "  test-cov   运行测试并生成覆盖率报告"
	@echo "  clean      清理临时文件"
	@echo "  lint       代码风格检查"
	@echo "  format     格式化代码"

# 设置开发环境
setup:
	@echo "设置罡好饭后端开发环境..."
	@if [ ! -d "../.conda/envs/ghf-server" ]; then \
		conda env create -f environment.yml; \
	fi
	@conda run -n ghf-server pip install pytest pytest-cov pytest-mock pytest-asyncio httpx
	@echo "开发环境设置完成"

# 启动开发服务器
dev:
	@echo "启动开发服务器..."
	@conda run -n ghf-server python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

# 运行所有测试
test:
	@echo "运行所有测试..."
	@./run_tests.sh

# 运行单元测试
test-unit:
	@echo "运行单元测试..."
	@./run_tests.sh unit

# 运行API测试
test-api:
	@echo "运行API测试..."
	@./run_tests.sh api

# 运行测试并生成覆盖率报告
test-cov:
	@echo "运行测试并生成覆盖率报告..."
	@./run_tests.sh coverage

# 清理临时文件
clean:
	@echo "清理临时文件..."
	@./run_tests.sh clean
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage
	@echo "清理完成"

# 代码风格检查
lint:
	@echo "进行代码风格检查..."
	@conda run -n ghf-server python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@conda run -n ghf-server python -m flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# 格式化代码
format:
	@echo "格式化代码..."
	@conda run -n ghf-server python -m black . --line-length 127
	@conda run -n ghf-server python -m isort . --profile black

# 快速健康检查
health:
	@echo "检查服务健康状态..."
	@curl -s http://127.0.0.1:8000/health || echo "服务未运行"

# 数据库初始化（开发用）
db-init:
	@echo "初始化开发数据库..."
	@conda run -n ghf-server python -c "from core.database import db_manager; db_manager.init_database(); print('数据库初始化完成')"

# 安装开发依赖
install-dev:
	@echo "安装开发依赖..."
	@conda run -n ghf-server pip install black flake8 isort pytest-xdist