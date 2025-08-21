#!/bin/bash

# 罡好饭测试环境清理脚本
# 停止测试服务器、清理测试数据和日志

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 停止测试服务器
stop_server() {
    log_info "停止测试服务器..."
    
    local pid_file="tests/logs/server.pid"
    local stopped=false
    
    # 通过PID文件停止
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 2
            
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            log_success "服务器进程已停止 (PID: $pid)"
            stopped=true
        fi
        rm -f "$pid_file"
    fi
    
    # 通过端口停止
    local ports=(8001 8000)  # 常用测试端口
    for port in "${ports[@]}"; do
        if command -v lsof &> /dev/null; then
            if lsof -ti:$port > /dev/null 2>&1; then
                log_warning "清理端口 $port 上的进程..."
                lsof -ti:$port | xargs -r kill -9 2>/dev/null || true
                stopped=true
            fi
        fi
    done
    
    if [ "$stopped" = true ]; then
        log_success "测试服务器已停止"
    else
        log_info "没有发现运行中的测试服务器"
    fi
}

# 清理测试数据库
cleanup_database() {
    log_info "清理测试数据库..."
    
    local db_files=(
        "data/test_ganghaofan.duckdb"
        "data/test_ganghaofan_*.duckdb"
    )
    
    local cleaned=false
    for pattern in "${db_files[@]}"; do
        for file in $pattern; do
            if [ -f "$file" ]; then
                rm -f "$file"
                log_success "删除数据库文件: $file"
                cleaned=true
            fi
        done
    done
    
    if [ "$cleaned" = false ]; then
        log_info "没有发现测试数据库文件"
    fi
}

# 清理测试日志
cleanup_logs() {
    log_info "清理测试日志..."
    
    if [ -d "tests/logs" ]; then
        # 清理服务器日志
        rm -f tests/logs/server.log
        rm -f tests/logs/server.pid
        
        # 清理旧的测试运行日志 (保留最近3天)
        find tests/logs -name "test_run_*.log" -mtime +3 -delete 2>/dev/null || true
        
        log_success "测试日志已清理"
    else
        log_info "没有发现测试日志目录"
    fi
}

# 清理临时文件
cleanup_temp_files() {
    log_info "清理临时文件..."
    
    # 清理Python缓存
    find tests -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find tests -name "*.pyc" -delete 2>/dev/null || true
    
    # 清理pytest缓存
    rm -rf tests/.pytest_cache 2>/dev/null || true
    
    # 清理覆盖率文件
    rm -f tests/.coverage 2>/dev/null || true
    rm -rf tests/htmlcov 2>/dev/null || true
    
    log_success "临时文件已清理"
}

# 重置环境变量
reset_environment() {
    log_info "重置环境变量..."
    
    # 清理测试相关的环境变量
    unset TESTING
    unset TEST_DB_PATH
    unset TEST_SERVER_PORT
    unset TEST_SERVER_HOST
    unset GHF_MOCK_AUTH
    unset GHF_PASSPHRASE_MAP
    
    log_success "环境变量已重置"
}

# 验证清理结果
verify_cleanup() {
    log_info "验证清理结果..."
    
    local issues=0
    
    # 检查服务器是否还在运行
    if curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
        log_warning "端口8001上仍有服务在运行"
        issues=$((issues + 1))
    fi
    
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        log_warning "端口8000上仍有服务在运行"
        issues=$((issues + 1))
    fi
    
    # 检查数据库文件
    if ls data/test_ganghaofan*.duckdb 1> /dev/null 2>&1; then
        log_warning "仍有测试数据库文件存在"
        issues=$((issues + 1))
    fi
    
    if [ $issues -eq 0 ]; then
        log_success "清理验证通过"
        return 0
    else
        log_warning "发现 $issues 个清理问题"
        return 1
    fi
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  all         完整清理（默认）"
    echo "  server      仅停止服务器"
    echo "  database    仅清理数据库"
    echo "  logs        仅清理日志"
    echo "  temp        仅清理临时文件"
    echo "  verify      验证清理状态"
    echo "  help        显示此帮助信息"
}

# 主函数
main() {
    local action="${1:-all}"
    
    case "$action" in
        "all")
            log_info "开始完整清理测试环境..."
            stop_server
            cleanup_database  
            cleanup_logs
            cleanup_temp_files
            reset_environment
            verify_cleanup
            log_success "测试环境清理完成！"
            ;;
        "server")
            stop_server
            ;;
        "database")
            cleanup_database
            ;;
        "logs")
            cleanup_logs
            ;;
        "temp")
            cleanup_temp_files
            ;;
        "verify")
            verify_cleanup
            ;;
        "help")
            show_usage
            exit 0
            ;;
        *)
            log_error "未知选项: $action"
            show_usage
            exit 1
            ;;
    esac
}

# 信号处理
trap 'log_warning "收到中断信号"; exit 1' INT TERM

# 执行主函数
main "$@"