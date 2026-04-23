# 使用官方Python 3.11镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装uv
COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /usr/local/bin/uv

# 复制依赖文件
COPY pyproject.toml ./

# 安装Python依赖(不含开发依赖)
RUN uv sync --no-dev

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p uploads

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
