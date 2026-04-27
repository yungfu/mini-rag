# MiniRAG Justfile
set shell := ["bash", "-cu"]

default: help

help:
    @echo "MiniRAG 开发工具"
    @echo ""
    @echo "可用命令:"
    @echo "  just install-dev      - 安装开发环境依赖"
    @echo "  just install-backend  - 安装后端依赖(uv)"
    @echo "  just install-front    - 安装前端依赖"
    @echo "  just run-dev          - 开发模式启动所有服务"
    @echo "  just run-prod         - 生产模式启动所有服务"
    @echo "  just test             - 运行后端测试"
    @echo "  just test-backend     - 运行后端测试"
    @echo "  just build            - 构建Docker镜像"
    @echo "  just clean            - 清理构建文件和依赖"
    @echo "  just logs             - 查看服务日志"
    @echo "  just stop             - 停止所有服务"

install-dev: install-backend install-front
    @echo "开发环境依赖安装完成"

install-backend:
    @echo "安装后端Python依赖(uv)..."
    cd backend && uv sync --dev

install-front:
    @echo "安装前端Node.js依赖..."
    cd frontend && npm install

run-dev:
    @echo "启动开发环境..."
    @if ! docker info >/dev/null 2>&1; then \
        echo "错误: Docker daemon 未运行。请先启动 Docker Desktop，或执行 'sudo service docker start'。"; \
        exit 1; \
    fi
    docker compose up db -d
    @echo "数据库启动完成，等待10秒..."
    sleep 10
    @echo "启动后端服务..."
    cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    @echo "启动前端服务..."
    cd frontend && npm run dev &
    @echo "开发环境启动完成"
    @echo "前端: http://localhost:3000"
    @echo "后端: http://localhost:8000"

run-prod:
    @echo "启动生产环境..."
    docker compose up -d
    @echo "生产环境启动完成"
    @echo "前端: http://localhost:3000"
    @echo "后端: http://localhost:8000"

test:
    @echo "运行后端测试..."
    cd backend && uv run pytest

test-backend:
    @echo "运行后端测试..."
    cd backend && uv run pytest

build:
    @echo "构建Docker镜像..."
    docker compose build

clean:
    @echo "清理构建文件..."
    docker compose down -v --remove-orphans
    rm -rf backend/.venv
    rm -rf backend/__pycache__/
    rm -rf backend/*.pyc
    rm -rf frontend/node_modules/
    rm -rf frontend/dist/
    rm -rf frontend/build/
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    @echo "清理完成"

logs:
    @echo "查看服务日志 (按Ctrl+C退出)"
    docker compose logs -f

stop:
    @echo "停止所有服务..."
    docker compose down
    pkill -f "uvicorn main:app" || true
    pkill -f "npm run dev" || true
    @echo "服务已停止"

reset-db:
    @echo "重置数据库..."
    docker compose down -v
    docker compose up -d db
    @echo "数据库已重置"

format:
    @echo "格式化代码..."
    cd backend && uv run isort .
    cd backend && uv run black .
    cd frontend && npm run lint

lint:
    @echo "检查代码质量..."
    cd backend && uv run flake8 .
    cd backend && uv run mypy .
    cd frontend && npm run lint

security:
    @echo "运行安全检查..."
    cd backend && uv run bandit -r .
