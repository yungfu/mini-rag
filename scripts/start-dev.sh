#!/bin/bash

# MiniRAG 开发环境启动脚本

set -e

echo "=== MiniRAG 开发环境启动脚本 ==="

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

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 加载环境变量
load_environment() {
    print_info "加载环境变量..."
    
    if [ -f "backend/.env" ]; then
        source backend/.env
        print_success "环境变量加载完成"
    else
        print_warning "环境变量文件不存在，将使用默认配置"
        cp backend/.env.example backend/.env
        print_info "已创建环境变量文件，请编辑 backend/.env 配置API密钥"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p backend/uploads
    mkdir -p backend/logs
    mkdir -p frontend/public
    
    print_success "目录创建完成"
}

# 启动数据库
start_database() {
    print_info "启动数据库..."
    
    docker-compose up -d db
    
    print_info "等待数据库启动..."
    sleep 30
    
    # 检查数据库是否就绪
    if docker-compose exec -T db pg_isready -U postgres; then
        print_success "数据库启动成功"
    else
        print_error "数据库启动失败"
        exit 1
    fi
}

# 启动后端服务
start_backend() {
    print_info "启动后端服务..."
    
    cd backend
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_info "创建Python虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install -r requirements.txt
    
    # 启动后端服务
    uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    cd ..
    
    print_success "后端服务已启动 (PID: $BACKEND_PID)"
}

# 启动前端服务
start_frontend() {
    print_info "启动前端服务..."
    
    cd frontend
    
    # 检查是否已安装依赖
    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install
    fi
    
    # 启动前端服务
    npm run dev &
    FRONTEND_PID=$!
    
    cd ..
    
    print_success "前端服务已启动 (PID: $FRONTEND_PID)"
}

# 等待服务启动
wait_for_services() {
    print_info "等待服务启动..."
    
    # 等待后端服务
    while ! curl -s http://localhost:8000/health > /dev/null; do
        sleep 2
        print_info "等待后端服务..."
    done
    
    # 等待前端服务
    while ! curl -s http://localhost:3000 > /dev/null; do
        sleep 2
        print_info "等待前端服务..."
    done
    
    print_success "所有服务启动完成"
}

# 显示服务信息
show_service_info() {
    print_info "服务信息："
    echo ""
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│                    MiniRAG 服务状态                       │"
    echo "├─────────────────────────────────────────────────────────────┤"
    echo "│ 前端地址: http://localhost:3000                          │"
    echo "│ 后端API: http://localhost:8000                           │"
    echo "│ API文档: http://localhost:8000/docs                      │"
    echo "│ 数据库: localhost:5432                                  │"
    echo "├─────────────────────────────────────────────────────────────┤"
    echo "│                                                           │"
    echo "│  使用 Ctrl+C 停止所有服务                                │"
    echo "│  使用 ./scripts/stop-dev.sh 停止服务                   │"
    echo "│                                                           │"
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""
}

# 清理函数
cleanup() {
    print_warning "收到中断信号，正在清理..."
    
    # 停止后端服务
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # 停止前端服务
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # 停止Docker容器
    docker-compose down
    
    print_success "清理完成"
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 主流程
main() {
    check_dependencies
    load_environment
    create_directories
    start_database
    start_backend
    start_frontend
    wait_for_services
    show_service_info
    
    print_success "MiniRAG 开发环境启动完成！"
    
    # 保持脚本运行
    while true; do
        sleep 1
    done
}

# 运行主函数
main "$@"