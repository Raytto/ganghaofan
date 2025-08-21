#!/bin/bash

# 罡好饭测试环境设置脚本
# 检查依赖、设置环境变量、启动测试服务器

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查是否在正确的目录
check_directory() {
    if [ ! -f "tests/config/test_config.json" ] || [ ! -d "tests/utils" ]; then
        log_error "请在server目录下执行此脚本"
        exit 1
    fi
    log_success "目录检查通过"
}


# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查conda
    if ! command -v conda &> /dev/null; then
        log_error "Conda未安装或未添加到PATH"
        exit 1
    fi
    log_success "Conda可用"
    
    # 检查ghf-server环境
    if ! conda env list | grep -q "ghf-server"; then
        log_warning "ghf-server环境不存在，尝试创建..."
        if [ -f "environment.yml" ]; then
            conda env create -f environment.yml
            log_success "Conda环境创建成功"
        else
            log_error "environment.yml文件不存在，无法创建环境"
            exit 1
        fi
    else
        log_success "ghf-server环境已存在"
    fi
    
    # 检查Python包
    log_info "检查Python包..."
    conda run -n ghf-server python -c "import requests, pytest, duckdb, fastapi" 2>/dev/null || {
        log_warning "缺少必要的Python包，尝试安装..."
        conda run -n ghf-server pip install requests pytest duckdb fastapi uvicorn python-jwt
        log_success "Python包安装完成"
    }
}

# 设置环境变量
setup_environment() {
    log_info "设置测试环境变量..."
    
    export TESTING=true
    export TEST_DB_PATH="data/test_ganghaofan.duckdb"
    export TEST_SERVER_PORT=8001
    export TEST_SERVER_HOST=127.0.0.1
    export JWT_SECRET_KEY="test-secret-key-for-e2e-testing"
    
    # 设置passphrase
    export GHF_PASSPHRASE_MAP='{"test_key": "test_value"}'
    
    # 设置Mock认证
    export GHF_MOCK_AUTH='{"mock_enabled": true, "open_id": "test_user", "nickname": "测试用户", "unique_per_login": true}'
    
    log_success "环境变量设置完成"
}

# 清理旧的测试数据
cleanup_old_data() {
    log_info "清理旧的测试数据..."
    
    # 删除测试数据库
    if [ -f "data/test_ganghaofan.duckdb" ]; then
        rm -f data/test_ganghaofan.duckdb
        log_success "删除旧的测试数据库"
    fi
    
    # 清理测试日志
    if [ -d "tests/logs" ]; then
        find tests/logs -name "test_run_*.log" -mtime +7 -delete 2>/dev/null || true
        log_success "清理旧的测试日志"
    fi
}

# 检查端口是否被占用
check_port() {
    local port=${TEST_SERVER_PORT:-8001}
    
    log_info "检查端口 $port 占用情况..."
    
    # 优先使用lsof，备用ss
    if command -v lsof &> /dev/null; then
        if lsof -ti:$port > /dev/null 2>&1; then
            log_warning "端口 $port 被占用"
            
            # 获取占用端口的进程PID
            local pids=$(lsof -ti:$port)
            
            for pid in $pids; do
                if [ -n "$pid" ] && [ "$pid" != "0" ]; then
                    log_info "尝试终止进程 PID: $pid"
                    
                    # 尝试优雅终止
                    if kill -TERM "$pid" 2>/dev/null; then
                        log_info "发送TERM信号到进程 $pid"
                        sleep 2
                        
                        # 检查进程是否还存在
                        if kill -0 "$pid" 2>/dev/null; then
                            log_warning "进程仍在运行，强制终止"
                            kill -KILL "$pid" 2>/dev/null || true
                            sleep 1
                        fi
                    fi
                fi
            done
            
            # 再次检查端口
            if lsof -ti:$port > /dev/null 2>&1; then
                log_error "端口 $port 仍被占用，无法继续"
                return 1
            else
                log_success "端口 $port 已释放"
            fi
        else
            log_success "端口 $port 可用"
        fi
    elif command -v ss &> /dev/null; then
        # 使用ss命令的版本
        if ss -tlnp | grep -q ":$port "; then
            log_warning "端口 $port 被占用"
            
            # 获取占用端口的进程PID
            local pid=$(ss -tlnp | grep ":$port " | sed 's/.*pid=\([0-9]*\).*/\1/' | head -1)
            
            if [ -n "$pid" ] && [ "$pid" != "0" ]; then
                log_info "尝试终止进程 PID: $pid"
                
                # 尝试优雅终止
                if kill -TERM "$pid" 2>/dev/null; then
                    log_info "发送TERM信号到进程 $pid"
                    sleep 2
                    
                    # 检查进程是否还存在
                    if kill -0 "$pid" 2>/dev/null; then
                        log_warning "进程仍在运行，强制终止"
                        kill -KILL "$pid" 2>/dev/null || true
                        sleep 1
                    fi
                fi
                
                # 再次检查端口
                if ss -tlnp | grep -q ":$port "; then
                    log_error "端口 $port 仍被占用，无法继续"
                    return 1
                else
                    log_success "端口 $port 已释放"
                fi
            else
                log_warning "无法获取占用端口 $port 的进程ID"
                return 1
            fi
        else
            log_success "端口 $port 可用"
        fi
    else
        log_warning "无法检查端口占用情况 (lsof和ss都不可用)"
        return 0
    fi
    
    return 0
}

# 启动测试服务器
start_test_server() {
    local port=${TEST_SERVER_PORT:-8001}
    local host=${TEST_SERVER_HOST:-127.0.0.1}
    
    log_info "启动测试服务器 $host:$port ..."
    
    # 检查端口
    check_port
    
    # 获取当前绝对路径
    local current_dir=$(pwd)
    
    # 启动服务器（后台运行，设置正确的工作目录）
    (TESTING=true \
        TEST_DB_PATH="$current_dir/data/test_ganghaofan.duckdb" \
        TEST_SERVER_PORT=8001 \
        TEST_SERVER_HOST=127.0.0.1 \
        JWT_SECRET_KEY="test-secret-key-for-e2e-testing" \
        GHF_PASSPHRASE_MAP='{"test_key": "test_value"}' \
        GHF_MOCK_AUTH='{"mock_enabled": true, "open_id": "test_user", "nickname": "测试用户", "unique_per_login": true}' \
        PYTHONPATH="$current_dir" \
        /home/pp/miniconda3/envs/ghf-server/bin/python -c "
import os
os.chdir('$current_dir')
import uvicorn
uvicorn.run('app:app', host='$host', port=$port, log_level='info')
" > tests/logs/server.log 2>&1) &
    
    local server_pid=$!
    echo $server_pid > tests/logs/server.pid
    
    # 等待服务器启动
    wait_for_server $host $port
    
    return 0
}

# 等待服务器启动
wait_for_server() {
    local host=$1
    local port=$2
    local timeout=30
    local count=0
    
    log_info "等待服务器启动 (超时: ${timeout}s)..."
    
    while [ $count -lt $timeout ]; do
        if curl -s http://$host:$port/health > /dev/null 2>&1; then
            log_success "测试服务器已启动"
            return 0
        fi
        
        sleep 1
        count=$((count + 1))
        
        # 每5秒显示一次进度
        if [ $((count % 5)) -eq 0 ]; then
            log_info "等待中... (${count}s/${timeout}s)"
        fi
    done
    
    log_error "服务器启动超时"
    return 1
}

# 验证服务器状态
verify_server() {
    local host=${TEST_SERVER_HOST:-127.0.0.1}
    local port=${TEST_SERVER_PORT:-8001}
    
    log_info "验证服务器状态..."
    
    # 健康检查
    local health_response
    health_response=$(curl -s http://$host:$port/health 2>/dev/null || echo "ERROR")
    
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        log_success "健康检查通过"
    else
        log_error "健康检查失败: $health_response"
        return 1
    fi
    
    # API检查
    local api_response
    api_response=$(curl -s -H "X-DB-Key: test_value" http://$host:$port/api/v1/meals 2>/dev/null || echo "ERROR")
    
    if [ "$api_response" != "ERROR" ]; then
        log_success "API接口可访问"
    else
        log_warning "API接口可能有问题"
    fi
    
    return 0
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start       启动测试环境（默认）"
    echo "  stop        停止测试服务器"
    echo "  restart     重启测试服务器"
    echo "  status      显示测试环境状态"
    echo "  clean       清理测试环境"
    echo "  help        显示此帮助信息"
    echo ""
    echo "环境变量:"
    echo "  TEST_SERVER_PORT    测试服务器端口 (默认: 8001)"
    echo "  TEST_SERVER_HOST    测试服务器主机 (默认: 127.0.0.1)"
}

# 停止测试服务器
stop_test_server() {
    log_info "停止测试服务器..."
    
    local pid_file="tests/logs/server.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            sleep 2
            
            # 强制终止
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid"
            fi
            
            log_success "测试服务器已停止 (PID: $pid)"
        fi
        rm -f "$pid_file"
    fi
    
    # 额外检查端口
    local port=${TEST_SERVER_PORT:-8001}
    if command -v lsof &> /dev/null && lsof -ti:$port > /dev/null 2>&1; then
        lsof -ti:$port | xargs -r kill -9
        log_success "清理端口 $port"
    fi
}

# 显示状态
show_status() {
    local host=${TEST_SERVER_HOST:-127.0.0.1}
    local port=${TEST_SERVER_PORT:-8001}
    
    echo "=== 测试环境状态 ==="
    echo "服务器地址: http://$host:$port"
    
    if curl -s http://$host:$port/health > /dev/null 2>&1; then
        echo "服务器状态: 运行中 ✓"
        
        local health=$(curl -s http://$host:$port/health 2>/dev/null)
        echo "健康检查: $health"
    else
        echo "服务器状态: 未运行 ✗"
    fi
    
    if [ -f "tests/logs/server.pid" ]; then
        local pid=$(cat "tests/logs/server.pid")
        if kill -0 "$pid" 2>/dev/null; then
            echo "服务器PID: $pid (运行中)"
        else
            echo "服务器PID: $pid (已停止)"
        fi
    fi
    
    echo "数据库路径: data/test_ganghaofan.duckdb"
    if [ -f "data/test_ganghaofan.duckdb" ]; then
        echo "测试数据库: 存在"
    else
        echo "测试数据库: 不存在"
    fi
}

# 清理环境
clean_environment() {
    log_info "清理测试环境..."
    
    # 停止服务器
    stop_test_server
    
    # 清理数据库
    rm -f data/test_ganghaofan.duckdb*
    
    # 清理日志
    rm -f tests/logs/server.log tests/logs/server.pid
    
    log_success "测试环境清理完成"
}

# 确保日志目录存在
mkdir -p tests/logs

# 主函数
main() {
    case "${1:-start}" in
        "start")
            check_directory
            check_dependencies
            setup_environment
            cleanup_old_data
            start_test_server
            verify_server
            log_success "测试环境已就绪！"
            log_info "服务器地址: http://${TEST_SERVER_HOST:-127.0.0.1}:${TEST_SERVER_PORT:-8001}"
            ;;
        "stop")
            stop_test_server
            ;;
        "restart")
            stop_test_server
            sleep 2
            setup_environment
            start_test_server
            verify_server
            log_success "测试服务器已重启！"
            ;;
        "status")
            show_status
            ;;
        "clean")
            clean_environment
            ;;
        "help")
            show_usage
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
}

# 信号处理
trap 'log_warning "收到中断信号，正在清理..."; stop_test_server; exit 1' INT TERM

# 执行主函数
main "$@"