# 使用官方Node.js 18镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制package.json和package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 安装serve用于生产环境部署
RUN npm install -g serve

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["serve", "-s", "dist", "-l", "3000"]