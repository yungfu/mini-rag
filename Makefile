# MiniRAG Makefile

.PHONY: help install-dev install-backend install-front run-dev run-prod test clean build

# 默认目标
help:
	@echo "MiniRAG 开发工具"
	@echo ""
	@echo "可用目标:"
	@echo "  install-dev    - 安装开发环境依赖"
	@echo "  install-backend - 安装后端依赖"
	@echo "  install-front  - 安装前端依赖"
	@echo "  run-dev        - 开发模式启动所有服务"
	@echo "  run-prod       - 生产模式启动所有服务"
	@echo "  test           - 运行测试"
	@echo "  test-backend   - 运行后端测试"
	@echo "  build          - 构建Docker镜像"
	@echo "  clean          - 清理构建文件和依赖"
	@echo "  logs           - 查看服务日志"
	@echo "  stop           - 停止所有服务"

# 安装开发环境
install-dev: install-backend install-front
	@echo "开发环境依赖安装完成"

# 安装后端依赖
install-backend:
	@echo "安装后端Python依赖..."
	cd backend && pip install -r requirements.txt
	cd backend && pip install pytest pytest-asyncio

# 安装前端依赖
install-front:
	@echo "安装前端Node.js依赖..."
	cd frontend && npm install

# 开发模式启动
run-dev:
	@echo "启动开发环境..."
	docker-compose up -d db
	@echo "数据库启动完成，等待30秒..."
	sleep 30
	@echo "启动后端服务..."
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "启动前端服务..."
	cd frontend && npm run dev &
	@echo "开发环境启动完成"
	@echo "前端: http://localhost:3000"
	@echo "后端: http://localhost:8000"

# 生产模式启动
run-prod:
	@echo "启动生产环境..."
	docker-compose up -d
	@echo "生产环境启动完成"
	@echo "前端: http://localhost:3000"
	@echo "后端: http://localhost:8000"

# 运行测试
test:
	@echo "运行所有测试..."
	pytest tests/
	@echo "前端测试: cd frontend && npm test"

# 运行后端测试
test-backend:
	@echo "运行后端测试..."
	cd backend && pytest

# 构建Docker镜像
build:
	@echo "构建Docker镜像..."
	docker-compose build

# 清理
clean:
	@echo "清理构建文件..."
	docker-compose down -v --remove-orphans
	rm -rf backend/__pycache__/
	rm -rf backend/*.pyc
	rm -rf frontend/node_modules/
	rm -rf frontend/dist/
	rm -rf frontend/build/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "清理完成"

# 查看日志
logs:
	@echo "查看服务日志 (按Ctrl+C退出)"
	docker-compose logs -f

# 停止服务
stop:
	@echo "停止所有服务..."
	docker-compose down
	pkill -f "uvicorn main:app"
	pkill -f "npm run dev"
	@echo "服务已停止"

# 数据库重置
reset-db:
	@echo "重置数据库..."
	docker-compose down -v
	docker-compose up -d db
	@echo "数据库已重置"

# 代码格式化
format:
	@echo "格式化代码..."
	cd backend && isort .
	cd backend && black .
	cd frontend && npm run lint

# 代码检查
lint:
	@echo "检查代码质量..."
	cd backend && flake8 .
	cd backend && mypy .
	cd frontend && npm run lint

# 安全检查
security:
	@echo "运行安全检查..."
	cd backend && bandit -r .
	cd backend && safety check