#!/bin/bash

# 罡好饭E2E测试执行脚本
# 启动测试环境、运行E2E测试、生成报告、清理环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

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

log_test() {
    echo -e "${PURPLE}[TEST]${NC} $1"
}

# 全局变量
SERVER_STARTED=false
TEST_RESULTS=()
FAILED_TESTS=()
TOTAL_TESTS=0
PASSED_TESTS=0

# 检查目录
check_directory() {
    if [ ! -f "tests/config/test_config.json" ] || [ ! -d "tests/e2e" ]; then
        log_error "请在server目录下执行此脚本"
        exit 1
    fi
    log_success "目录检查通过"
}

# 启动测试环境
start_test_environment() {
    log_info "启动测试环境..."
    
    # 使用环境设置脚本启动
    if ./tests/scripts/setup_test_env.sh start; then
        SERVER_STARTED=true
        log_success "测试环境启动成功"
        sleep 2  # 等待服务器完全就绪
    else
        log_error "测试环境启动失败"
        exit 1
    fi
}

# 停止测试环境
stop_test_environment() {
    if [ "$SERVER_STARTED" = true ]; then
        log_info "停止测试环境..."
        ./tests/scripts/cleanup_test_env.sh all
        SERVER_STARTED=false
    fi
}

# 验证测试环境
verify_test_environment() {
    log_info "验证测试环境..."
    
    # 健康检查
    if curl -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
        log_success "服务器健康检查通过"
    else
        log_error "服务器健康检查失败"
        return 1
    fi
    
    # 基础API检查
    if curl -s -H "X-DB-Key: test_value" http://127.0.0.1:8001/api/v1/meals > /dev/null 2>&1; then
        log_success "API接口可访问"
    else
        log_warning "API接口可能有问题"
    fi
    
    return 0
}

# 运行单个测试
run_single_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .py)
    
    log_test "运行测试: $test_name"
    
    local start_time=$(date +%s)
    local output_file="tests/logs/${test_name}_$(date +%Y%m%d_%H%M%S).log"
    
    # 运行测试
    if conda run -n ghf-server python -m pytest "$test_file" -v \
        --tb=short --no-header -q > "$output_file" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_success "✓ $test_name 通过 (${duration}s)"
        TEST_RESULTS+=("PASS: $test_name (${duration}s)")
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_error "✗ $test_name 失败 (${duration}s)"
        TEST_RESULTS+=("FAIL: $test_name (${duration}s)")
        FAILED_TESTS+=("$test_name")
        
        # 显示失败详情
        log_warning "失败详情 (最后10行):"
        tail -10 "$output_file" | sed 's/^/    /'
        
        return 1
    fi
}

# 运行所有E2E测试
run_e2e_tests() {
    log_info "开始运行E2E测试..."
    
    # 确保日志目录存在
    mkdir -p tests/logs
    
    # 获取所有测试文件
    local test_files=(
        "tests/e2e/test_basic_health.py"
        "tests/e2e/test_meal_crud.py"
        "tests/e2e/test_order_flow.py"
        "tests/e2e/test_balance.py"
        "tests/e2e/test_permissions.py"
        "tests/e2e/test_admin_apis.py"
        "tests/e2e/test_enhanced_features.py"
        "tests/e2e/test_complex_business_flow.py"
    )
    
    # 检查测试文件是否存在
    for test_file in "${test_files[@]}"; do
        if [ ! -f "$test_file" ]; then
            log_warning "测试文件不存在: $test_file"
        else
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
        fi
    done
    
    if [ $TOTAL_TESTS -eq 0 ]; then
        log_error "没有找到可执行的测试文件"
        return 1
    fi
    
    log_info "找到 $TOTAL_TESTS 个测试文件"
    echo ""
    
    # 运行测试
    for test_file in "${test_files[@]}"; do
        if [ -f "$test_file" ]; then
            run_single_test "$test_file"
            echo ""
        fi
    done
    
    return 0
}

# 生成测试报告
generate_test_report() {
    log_info "生成测试报告..."
    
    local report_file="tests/logs/e2e_test_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# E2E测试报告

**执行时间**: $(date)
**测试环境**: 端到端测试环境 (端口8001)

## 测试统计

- **总测试数**: $TOTAL_TESTS
- **通过测试**: $PASSED_TESTS  
- **失败测试**: $((TOTAL_TESTS - PASSED_TESTS))
- **通过率**: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)%

## 测试结果详情

EOF

    # 添加测试结果
    for result in "${TEST_RESULTS[@]}"; do
        if [[ $result == PASS* ]]; then
            echo "✅ $result" >> "$report_file"
        else
            echo "❌ $result" >> "$report_file"
        fi
    done
    
    # 添加失败测试详情
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        cat >> "$report_file" << EOF

## 失败测试分析

EOF
        for failed_test in "${FAILED_TESTS[@]}"; do
            echo "### $failed_test" >> "$report_file"
            echo "" >> "$report_file"
            echo "详细日志请查看: \`tests/logs/${failed_test}_*.log\`" >> "$report_file"
            echo "" >> "$report_file"
        done
    fi
    
    cat >> "$report_file" << EOF

## 环境信息

- **服务器地址**: http://127.0.0.1:8001
- **数据库**: SQLite (测试专用)
- **认证模式**: Mock认证
- **日志目录**: tests/logs/

## 建议

EOF

    if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
        echo "🎉 所有测试通过！系统功能正常。" >> "$report_file"
    else
        echo "⚠️  有测试失败，请检查失败测试的日志文件进行调试。" >> "$report_file"
    fi
    
    log_success "测试报告已生成: $report_file"
}

# 显示测试摘要
show_test_summary() {
    echo ""
    echo "============================================"
    echo "           E2E测试执行摘要"
    echo "============================================"
    echo ""
    echo "执行时间: $(date)"
    echo "总测试数: $TOTAL_TESTS"
    echo "通过测试: $PASSED_TESTS"
    echo "失败测试: $((TOTAL_TESTS - PASSED_TESTS))"
    
    if [ $TOTAL_TESTS -gt 0 ]; then
        local pass_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)
        echo "通过率: ${pass_rate}%"
    fi
    
    echo ""
    
    if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
        log_success "🎉 所有测试通过！"
    else
        log_warning "⚠️  有 $((TOTAL_TESTS - PASSED_TESTS)) 个测试失败"
        echo ""
        echo "失败的测试:"
        for failed_test in "${FAILED_TESTS[@]}"; do
            echo "  - $failed_test"
        done
    fi
    
    echo ""
    echo "============================================"
}

# 显示使用说明
show_usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  all         运行完整E2E测试（默认）"
    echo "  health      仅运行健康检查测试"
    echo "  meal        仅运行餐次管理测试"
    echo "  order       仅运行订单流程测试"
    echo "  balance     仅运行余额管理测试"
    echo "  permissions 仅运行权限控制测试"
    echo "  admin       仅运行管理员API测试"
    echo "  enhanced    仅运行增强功能测试"
    echo "  complex     仅运行复杂业务流程测试（包含透支测试）"
    echo "  clean       清理测试环境"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 all      # 运行所有E2E测试"
    echo "  $0 meal     # 仅测试餐次管理功能"
    echo "  $0 clean    # 清理测试环境"
}

# 运行特定测试组
run_specific_test() {
    local test_type=$1
    
    case "$test_type" in
        "health")
            if [ -f "tests/e2e/test_basic_health.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_basic_health.py"
            fi
            ;;
        "meal")
            if [ -f "tests/e2e/test_meal_crud.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_meal_crud.py"
            fi
            ;;
        "order")
            if [ -f "tests/e2e/test_order_flow.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_order_flow.py"
            fi
            ;;
        "balance")
            if [ -f "tests/e2e/test_balance.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_balance.py"
            fi
            ;;
        "permissions")
            if [ -f "tests/e2e/test_permissions.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_permissions.py"
            fi
            ;;
        "admin")
            if [ -f "tests/e2e/test_admin_apis.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_admin_apis.py"
            fi
            ;;
        "enhanced")
            if [ -f "tests/e2e/test_enhanced_features.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_enhanced_features.py"
            fi
            ;;
        "complex")
            if [ -f "tests/e2e/test_complex_business_flow.py" ]; then
                TOTAL_TESTS=1
                run_single_test "tests/e2e/test_complex_business_flow.py"
            fi
            ;;
        *)
            log_error "未知的测试类型: $test_type"
            show_usage
            exit 1
            ;;
    esac
}

# 信号处理
cleanup_on_exit() {
    log_warning "收到中断信号，正在清理..."
    stop_test_environment
    exit 1
}

trap cleanup_on_exit INT TERM

# 主函数
main() {
    local action="${1:-all}"
    
    case "$action" in
        "clean")
            stop_test_environment
            log_success "测试环境已清理"
            exit 0
            ;;
        "help")
            show_usage
            exit 0
            ;;
        "all")
            echo ""
            echo "🚀 启动罡好饭E2E测试套件"
            echo ""
            
            check_directory
            start_test_environment
            
            if verify_test_environment; then
                run_e2e_tests
                generate_test_report
            else
                log_error "测试环境验证失败"
            fi
            
            show_test_summary
            stop_test_environment
            
            # 根据测试结果设置退出码
            if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
                exit 0
            else
                exit 1
            fi
            ;;
        "health"|"meal"|"order"|"balance"|"permissions"|"admin"|"enhanced"|"complex")
            echo ""
            echo "🧪 运行特定测试: $action"
            echo ""
            
            check_directory
            start_test_environment
            
            if verify_test_environment; then
                run_specific_test "$action"
            else
                log_error "测试环境验证失败"
            fi
            
            show_test_summary
            stop_test_environment
            
            if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
                exit 0
            else
                exit 1
            fi
            ;;
        *)
            log_error "未知选项: $action"
            show_usage
            exit 1
            ;;
    esac
}

# 检查必要工具
if ! command -v bc &> /dev/null; then
    log_warning "bc计算器未安装，将跳过通过率计算"
fi

# 执行主函数
main "$@"