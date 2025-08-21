#!/bin/bash

# 罡好饭后端测试执行脚本
# 一键执行完整的测试套件，包括环境准备、测试执行、结果报告

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
    if [ ! -f "pytest.ini" ] || [ ! -d "tests" ]; then
        log_error "请在server目录下执行此脚本"
        exit 1
    fi
}

# 检查Conda环境
check_conda_environment() {
    log_info "检查Conda环境..."
    
    if ! command -v conda &> /dev/null; then
        log_error "Conda未安装或未添加到PATH"
        exit 1
    fi
    
    # 检查ghf-server环境是否存在
    if ! conda env list | grep -q "ghf-server"; then
        log_warning "ghf-server环境不存在，尝试创建..."
        if [ -f "../environment.yml" ]; then
            conda env create -f ../environment.yml
            log_success "Conda环境创建成功"
        else
            log_error "environment.yml文件不存在，无法创建环境"
            exit 1
        fi
    else
        log_success "ghf-server环境已存在"
    fi
}

# 激活环境并安装测试依赖
setup_test_environment() {
    log_info "设置测试环境..."
    
    # 激活环境
    eval "$(conda shell.bash hook)"
    conda activate ghf-server
    
    # 安装测试依赖
    log_info "安装测试依赖..."
    pip install pytest pytest-cov pytest-mock pytest-asyncio httpx
    
    log_success "测试环境设置完成"
}

# 运行不同类型的测试
run_unit_tests() {
    log_info "运行单元测试..."
    
    if [ -f "tests/test_order_service.py" ]; then
        # 设置PYTHONPATH让Python能正确导入模块
        export PYTHONPATH="${PWD}:${PYTHONPATH}"
        python -m pytest tests/test_order_service.py -v --tb=short
        log_success "单元测试完成"
    else
        log_warning "单元测试文件不存在，跳过"
    fi
}

run_api_tests() {
    log_info "运行API集成测试..."
    
    # 设置测试环境变量
    export TESTING=true
    export JWT_SECRET_KEY="test-secret-key-for-testing"
    
    # 设置PYTHONPATH让Python能正确导入模块
    export PYTHONPATH="${PWD}:${PYTHONPATH}"
    
    # 运行API测试
    python -m pytest tests/test_api_*.py -v --tb=short
    log_success "API测试完成"
}

run_all_tests_with_coverage() {
    log_info "运行完整测试套件（包含覆盖率）..."
    
    # 设置环境变量
    export TESTING=true
    export JWT_SECRET_KEY="test-secret-key-for-testing"
    
    # 设置PYTHONPATH让Python能正确导入模块
    export PYTHONPATH="${PWD}:${PYTHONPATH}"
    
    # 运行所有测试并生成覆盖率报告
    python -m pytest tests/ \
        --cov=. \
        --cov-report=html \
        --cov-report=term \
        --cov-fail-under=60 \
        -v
    
    log_success "完整测试套件执行完成"
    
    if [ -d "htmlcov" ]; then
        log_info "覆盖率报告已生成到 htmlcov/ 目录"
    fi
}

# 清理测试环境
cleanup_test_environment() {
    log_info "清理测试环境..."
    
    # 删除测试生成的文件
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # 清理覆盖率文件
    if [ -f ".coverage" ]; then
        rm .coverage
    fi
    
    log_success "测试环境清理完成"
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  unit        只运行单元测试"
    echo "  api         只运行API测试"
    echo "  coverage    运行完整测试套件并生成覆盖率报告"
    echo "  clean       清理测试环境"
    echo "  help        显示此帮助信息"
    echo ""
    echo "默认（无参数）: 运行所有测试"
}

# 主函数
main() {
    log_info "开始执行罡好饭后端测试..."
    
    case "${1:-all}" in
        "unit")
            check_directory
            check_conda_environment
            setup_test_environment
            run_unit_tests
            ;;
        "api")
            check_directory
            check_conda_environment
            setup_test_environment
            run_api_tests
            ;;
        "coverage")
            check_directory
            check_conda_environment
            setup_test_environment
            run_all_tests_with_coverage
            ;;
        "clean")
            cleanup_test_environment
            ;;
        "help")
            show_usage
            exit 0
            ;;
        "all"|"")
            check_directory
            check_conda_environment
            setup_test_environment
            run_unit_tests
            run_api_tests
            cleanup_test_environment
            ;;
        *)
            log_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
    
    log_success "测试执行完成！"
}

# 执行主函数
main "$@"