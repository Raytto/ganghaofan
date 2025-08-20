#!/bin/bash

# 罡好饭系统自动化部署脚本
# 支持开发环境、测试环境和生产环境的一键部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 默认配置
DEFAULT_ENV="development"
DEFAULT_PORT=8000
DEFAULT_HOST="127.0.0.1"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 显示banner
show_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════╗"
    echo "║          罡好饭系统部署工具          ║"
    echo "║     Gang Hao Fan Deployment Tool    ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [环境] [选项]"
    echo ""
    echo "环境:"
    echo "  dev         开发环境部署"
    echo "  test        测试环境部署"
    echo "  prod        生产环境部署"
    echo ""
    echo "选项:"
    echo "  --port PORT     指定端口 (默认: 8000)"
    echo "  --host HOST     指定主机 (默认: 127.0.0.1)"
    echo "  --no-deps       跳过依赖安装"
    echo "  --no-db         跳过数据库初始化"
    echo "  --backup        部署前创建备份"
    echo "  --help          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 dev                    # 开发环境部署"
    echo "  $0 prod --port 8080       # 生产环境部署到8080端口"
    echo "  $0 test --backup          # 测试环境部署并创建备份"
}

# 检查系统环境
check_system_requirements() {
    log_step "检查系统环境..."
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]] && [[ "$OSTYPE" != "darwin"* ]]; then
        log_warning "检测到非Linux/macOS系统，可能需要额外配置"
    fi
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装，请先安装Python 3.11+"
        exit 1
    fi
    
    # 检查Conda
    if ! command -v conda &> /dev/null; then
        log_error "Conda 未安装，请先安装Miniconda或Anaconda"
        exit 1
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        log_error "Git 未安装，请先安装Git"
        exit 1
    fi
    
    log_success "系统环境检查通过"
}

# 检查项目结构
check_project_structure() {
    log_step "检查项目结构..."
    
    if [ ! -f "server/app.py" ] || [ ! -f "server/environment.yml" ]; then
        log_error "项目结构不正确，请在项目根目录运行此脚本"
        exit 1
    fi
    
    log_success "项目结构检查通过"
}

# 创建或更新Conda环境
setup_conda_environment() {
    log_step "设置Conda环境..."
    
    if [ "$SKIP_DEPS" = true ]; then
        log_info "跳过依赖安装"
        return
    fi
    
    cd server
    
    # 检查环境是否存在
    if conda env list | grep -q "ghf-server"; then
        log_info "更新现有Conda环境..."
        conda env update -f environment.yml
    else
        log_info "创建新Conda环境..."
        conda env create -f environment.yml
    fi
    
    # 安装额外的开发/测试依赖
    if [ "$ENVIRONMENT" = "development" ] || [ "$ENVIRONMENT" = "test" ]; then
        log_info "安装开发和测试依赖..."
        conda run -n ghf-server pip install pytest pytest-cov pytest-mock pytest-asyncio httpx black flake8 isort
    fi
    
    cd ..
    log_success "Conda环境设置完成"
}

# 创建配置文件
create_configuration_files() {
    log_step "创建配置文件..."
    
    cd server
    mkdir -p config data
    
    # 数据库配置
    if [ ! -f "config/db.json" ]; then
        log_info "创建数据库配置文件..."
        cat > config/db.json << 'EOF'
{
    "db_path": "data/ganghaofan.duckdb"
}
EOF
    fi
    
    # 访问密钥配置
    if [ ! -f "config/passphrases.json" ]; then
        log_info "创建访问密钥配置文件..."
        if [ "$ENVIRONMENT" = "production" ]; then
            # 生产环境需要实际配置
            cat > config/passphrases.json << 'EOF'
{
    "prod_key": "请在生产环境中设置实际的访问密钥"
}
EOF
            log_warning "请手动配置 config/passphrases.json 中的生产环境访问密钥"
        else
            # 开发/测试环境可以使用默认配置
            cat > config/passphrases.json << 'EOF'
{
    "dev_key": "development",
    "test_key": "testing"
}
EOF
        fi
    fi
    
    # Mock配置 (仅开发环境)
    if [ "$ENVIRONMENT" = "development" ] && [ ! -f "config/dev_mock.json" ]; then
        log_info "创建Mock配置文件..."
        cat > config/dev_mock.json << 'EOF'
{
    "enabled": true,
    "openid": "mock_dev_user",
    "nickname": "开发测试用户",
    "unique_per_login": false
}
EOF
    fi
    
    # 环境变量文件
    if [ ! -f ".env" ]; then
        log_info "创建环境变量文件..."
        case "$ENVIRONMENT" in
            "production")
                cat > .env << 'EOF'
# 生产环境配置
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=your-production-secret-key-change-this
API_TITLE=罡好饭 API
API_VERSION=1.0.0
LOG_LEVEL=INFO
EOF
                log_warning "请设置安全的 JWT_SECRET_KEY 在生产环境中"
                ;;
            "test")
                cat > .env << 'EOF'
# 测试环境配置
ENVIRONMENT=test
DEBUG=true
JWT_SECRET_KEY=test-secret-key-for-testing
API_TITLE=罡好饭 API (Test)
API_VERSION=1.0.0-test
LOG_LEVEL=DEBUG
EOF
                ;;
            *)
                cat > .env << 'EOF'
# 开发环境配置
ENVIRONMENT=development
DEBUG=true
JWT_SECRET_KEY=dev-secret-key
API_TITLE=罡好饭 API (Dev)
API_VERSION=1.0.0-dev
LOG_LEVEL=DEBUG
EOF
                ;;
        esac
    fi
    
    cd ..
    log_success "配置文件创建完成"
}

# 初始化数据库
initialize_database() {
    log_step "初始化数据库..."
    
    if [ "$SKIP_DB" = true ]; then
        log_info "跳过数据库初始化"
        return
    fi
    
    cd server
    
    log_info "运行数据库初始化脚本..."
    conda run -n ghf-server python -c "
from core.database import db_manager
try:
    db_manager.init_database()
    print('数据库初始化成功')
except Exception as e:
    print(f'数据库初始化失败: {e}')
    exit(1)
"
    
    cd ..
    log_success "数据库初始化完成"
}

# 运行测试
run_tests() {
    log_step "运行测试套件..."
    
    cd server
    
    # 检查测试脚本是否存在
    if [ -f "run_tests.sh" ]; then
        log_info "运行单元测试..."
        chmod +x run_tests.sh
        ./run_tests.sh unit
        
        log_info "运行API测试..."
        ./run_tests.sh api
    else
        log_warning "测试脚本不存在，跳过测试"
    fi
    
    cd ..
    log_success "测试完成"
}

# 创建备份
create_backup() {
    if [ "$CREATE_BACKUP" != true ]; then
        return
    fi
    
    log_step "创建备份..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份数据库
    if [ -f "server/data/ganghaofan.duckdb" ]; then
        cp server/data/ganghaofan.duckdb "$BACKUP_DIR/"
        log_info "数据库已备份到 $BACKUP_DIR/"
    fi
    
    # 备份配置文件
    if [ -d "server/config" ]; then
        cp -r server/config "$BACKUP_DIR/"
        log_info "配置文件已备份到 $BACKUP_DIR/"
    fi
    
    log_success "备份完成"
}

# 启动服务
start_service() {
    log_step "启动服务..."
    
    cd server
    
    case "$ENVIRONMENT" in
        "production")
            log_info "生产环境启动 (推荐使用 supervisor 管理)"
            log_info "启动命令: conda run -n ghf-server python -m uvicorn app:app --host $HOST --port $PORT --workers 2"
            
            if command -v supervisor &> /dev/null; then
                log_info "检测到 supervisor，建议使用 supervisor 管理服务"
            else
                log_warning "生产环境建议安装 supervisor 进行进程管理"
                log_info "后台启动服务..."
                nohup conda run -n ghf-server python -m uvicorn app:app --host "$HOST" --port "$PORT" --workers 2 > ../logs/app.log 2>&1 &
                echo $! > ../logs/app.pid
                log_info "服务已后台启动，PID文件: logs/app.pid"
            fi
            ;;
        "test")
            log_info "测试环境启动 (单进程模式)"
            conda run -n ghf-server python -m uvicorn app:app --host "$HOST" --port "$PORT" &
            TEST_PID=$!
            log_info "测试服务已启动，PID: $TEST_PID"
            
            # 等待服务启动并进行健康检查
            sleep 5
            if curl -f "http://$HOST:$PORT/health" &> /dev/null; then
                log_success "测试服务健康检查通过"
                kill $TEST_PID
            else
                log_error "测试服务健康检查失败"
                kill $TEST_PID 2>/dev/null || true
                exit 1
            fi
            ;;
        *)
            log_info "开发环境启动 (热重载模式)"
            log_info "服务将在前台运行，使用 Ctrl+C 停止"
            exec conda run -n ghf-server python -m uvicorn app:app --reload --host "$HOST" --port "$PORT"
            ;;
    esac
    
    cd ..
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo ""
    echo "部署信息:"
    echo "  环境: $ENVIRONMENT"
    echo "  主机: $HOST"
    echo "  端口: $PORT"
    echo "  项目目录: $(pwd)"
    echo ""
    echo "访问地址:"
    echo "  API文档: http://$HOST:$PORT/docs"
    echo "  健康检查: http://$HOST:$PORT/health"
    echo ""
    
    if [ "$ENVIRONMENT" = "development" ]; then
        echo "开发环境说明:"
        echo "  - 服务支持热重载"
        echo "  - 启用了Mock登录"
        echo "  - 数据库位置: server/data/ganghaofan.duckdb"
    elif [ "$ENVIRONMENT" = "production" ]; then
        echo "生产环境注意事项:"
        echo "  - 请设置强密码的JWT_SECRET_KEY"
        echo "  - 建议配置Nginx反向代理"
        echo "  - 建议使用Supervisor进程管理"
        echo "  - 定期备份数据库文件"
    fi
    
    echo ""
    echo "常用命令:"
    echo "  健康检查: curl http://$HOST:$PORT/health"
    echo "  查看日志: tail -f server/logs/app.log"
    echo "  运行测试: cd server && ./run_tests.sh"
}

# 主函数
main() {
    show_banner
    
    # 参数解析
    ENVIRONMENT="${1:-$DEFAULT_ENV}"
    shift || true
    
    HOST="$DEFAULT_HOST"
    PORT="$DEFAULT_PORT"
    SKIP_DEPS=false
    SKIP_DB=false
    CREATE_BACKUP=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                PORT="$2"
                shift 2
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            --no-deps)
                SKIP_DEPS=true
                shift
                ;;
            --no-db)
                SKIP_DB=true
                shift
                ;;
            --backup)
                CREATE_BACKUP=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 验证环境参数
    case "$ENVIRONMENT" in
        "dev"|"development")
            ENVIRONMENT="development"
            ;;
        "test"|"testing")
            ENVIRONMENT="test"
            ;;
        "prod"|"production")
            ENVIRONMENT="production"
            ;;
        *)
            log_error "无效环境: $ENVIRONMENT"
            show_usage
            exit 1
            ;;
    esac
    
    log_info "开始部署罡好饭系统到 $ENVIRONMENT 环境..."
    
    # 执行部署步骤
    check_system_requirements
    check_project_structure
    create_backup
    setup_conda_environment
    create_configuration_files
    initialize_database
    
    # 测试环境运行测试
    if [ "$ENVIRONMENT" = "test" ]; then
        run_tests
    fi
    
    start_service
    show_deployment_info
}

# 清理函数 (Ctrl+C时调用)
cleanup() {
    log_info "正在清理..."
    
    # 停止后台进程
    if [ -f "logs/app.pid" ]; then
        PID=$(cat logs/app.pid)
        if kill -0 "$PID" 2>/dev/null; then
            log_info "停止服务进程 $PID"
            kill "$PID"
        fi
        rm -f logs/app.pid
    fi
    
    exit 0
}

# 注册清理函数
trap cleanup SIGINT SIGTERM

# 创建日志目录
mkdir -p logs

# 执行主函数
main "$@"