#!/bin/bash

# MiniRAG 开发环境停止脚本

set -e

echo "=== MiniRAG 开发环境停止脚本 ==="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 停止后端服务
stop_backend() {
    print_info "停止后端服务..."
    
    # 查找并停止后端进程
    BACKEND_PIDS=$(ps aux | grep "uvicorn main:app" | grep -v grep | awk '{print $2}' || true)
    
    if [ ! -z "$BACKEND_PIDS" ]; then
        echo "找到后端进程: $BACKEND_PIDS"
        echo $BACKEND_PIDS | xargs kill -9 2>/dev/null || true
        print_success "后端服务已停止"
    else
        print_warning "未找到运行中的后端服务"
    fi
}

# 停止前端服务
stop_frontend() {
    print_info "停止前端服务..."
    
    # 查找并停止前端进程
    FRONTEND_PIDS=$(ps aux | grep "npm run dev" | grep -v grep | awk '{print $2}' || true)
    
    if [ ! -z "$FRONTEND_PIDS" ]; then
        echo "找到前端进程: $FRONTEND_PIDS"
        echo $FRONTEND_PIDS | xargs kill -9 2>/dev/null || true
        print_success "前端服务已停止"
    else
        print_warning "未找到运行中的前端服务"
    fi
}

# 停止Docker容器
stop_docker() {
    print_info "停止Docker容器..."
    
    if docker-compose ps -q | grep -q .; then
        docker-compose down
        print_success "Docker容器已停止"
    else
        print_warning "没有运行中的Docker容器"
    fi
}

# 清理临时文件
cleanup_temp_files() {
    print_info "清理临时文件..."
    
    # 清理Python缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # 清理Node.js缓存
    find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".cache" -exec rm -rf {} + 2>/dev/null || true
    
    print_success "临时文件清理完成"
}

# 显示停止结果
show_stop_result() {
    print_info "停止结果："
    echo ""
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│                    MiniRAG 服务停止状态                     │"
    echo "├─────────────────────────────────────────────────────────────┤"
    echo "│ 后端服务: 已停止                                          │"
    echo "│ 前端服务: 已停止                                          │"
    echo "│ Docker容器: 已停止                                        │"
    echo "│ 临时文件: 已清理                                          │"
    echo "├─────────────────────────────────────────────────────────────┤"
    echo "│                                                           │"
    echo "│ 使用 ./scripts/start-dev.sh 重新启动服务                   │"
    echo "│                                                           │"
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""
}

# 主流程
main() {
    stop_backend
    stop_frontend
    stop_docker
    cleanup_temp_files
    show_stop_result
    
    print_success "MiniRAG 开发环境已完全停止！"
}

# 运行主函数
main "$@"