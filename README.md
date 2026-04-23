# MiniRAG - 基于PostgreSQL的混合检索RAG系统

## 项目概述

MiniRAG 是一个基于PostgreSQL的全容器化RAG（Retrieval-Augmented Generation）系统，实现了向量检索、关键词检索、业务数据存储和语义缓存的一体化解决方案。

## 核心特性

- 🚀 **混合检索策略**：结合向量检索(BM25)和关键词检索，使用RRF算法进行结果融合
- 📄 **多格式文档支持**：支持Markdown、文本、HTML三种格式的文档处理
- 🔍 **智能缓存机制**：基于向量相似度的语义缓存，显著提升响应速度
- 🐳 **容器化部署**：使用Docker Compose实现一键部署，环境隔离
- ⚙️ **配置化管理**：支持多种LLM提供商和灵活的参数配置
- 🔧 **模块化架构**：易于扩展和维护的代码结构

## 技术架构

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend      │    │   Database      │
│   (React +      │    │   (FastAPI)    │    │   (PostgreSQL   │
│    Vite)        │◄──►│                 │◄──►│   + Extensions) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                    ┌─────────────────┐
                    │   External      │
                    │   Services     │
                    │   (LLM APIs)  │
                    └─────────────────┘
```

### 核心组件

- **表现层**：React + Vite + TailwindCSS + react-markdown
- **应用层**：Python FastAPI框架，异步处理I/O密集型任务
- **数据层**：PostgreSQL 15+ + pgvector + pg_bm25

## 快速开始

### 前置要求

- Docker 和 Docker Compose
- Node.js 18+ (前端开发)
- Python 3.11+ (后端开发)

### 环境配置

1. 克隆项目：
```bash
git clone <repository-url>
cd mini-rag
```

2. 配置环境变量：
```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env` 文件，配置LLM API密钥等参数：
```bash
# LLM配置
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key-here
LLM_MODEL=gpt-3.5-turbo

# 其他配置...
```

### 启动服务

使用Docker Compose启动所有服务：
```bash
docker compose up -d
```

服务启动后：
- 前端服务：http://localhost:3000
- 后端API：http://localhost:8000
- 数据库：localhost:5432

### 开发模式

如果需要开发模式（带热重载，推荐使用 just + uv）：

1. 启动数据库：
```bash
docker compose up -d db
```

2. 启动后端（开发模式）：
```bash
cd backend
uv sync --dev
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. 启动前端（开发模式）：
```bash
cd frontend
npm install
npm run dev
```

## 使用指南

### 上传文档

1. 访问前端界面
2. 点击"文档管理"标签
3. 拖拽或点击上传支持格式的文档文件
4. 等待文档处理完成（状态显示为"就绪"）

### 智能问答

1. 切换到"智能问答"标签
2. 输入您的问题
3. 系统将基于上传的文档内容生成回答
4. 可以查看参考来源文档切片

### API文档

访问 http://localhost:8000/docs 查看 FastAPI 自动生成的API文档。

## 配置说明

### 环境变量

#### 数据库配置
- `DB_HOST`: 数据库主机地址
- `DB_PORT`: 数据库端口
- `DB_NAME`: 数据库名称
- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码

#### LLM配置
- `LLM_PROVIDER`: LLM提供商 (openai/azure/qwen等)
- `LLM_API_KEY`: API密钥
- `LLM_MODEL`: 生成模型名称
- `LLM_BASE_URL`: 自定义API基础URL

#### Embedding配置
- `EMBEDDING_MODEL`: Embedding模型名称
- `EMBEDDING_DIM`: 向量维度

#### Rerank配置
- `RERANK_MODEL`: 重排序模型名称
- `RERANK_ENABLED`: 是否启用重排序

#### 检索配置
- `TOP_K`: 检索返回结果数量
- `SIMILARITY_THRESHOLD`: 相似度阈值

#### 缓存配置
- `ENABLE_SEMANTIC_CACHE`: 是否启用语义缓存
- `CACHE_SIMILARITY_THRESHOLD`: 缓存相似度阈值
- `CACHE_TTL_DAYS`: 缓存有效期（天）

### 文档处理配置

- `CHUNK_SIZE`: 文档切片大小 (默认512)
- `CHUNK_OVERLAP`: 文档切片重叠大小 (默认50)
- `SUPPORTED_FORMATS`: 支持的文档格式 (md,txt,html)

## 数据库设计

### 核心表结构

#### documents表（文档元数据）
- `id`: 主键
- `doc_id`: 文档唯一标识
- `filename`: 文件名
- `file_type`: 文件类型（md/txt/html）
- `status`: 状态（processing/ready/deleted）
- `created_at`: 创建时间
- `updated_at`: 更新时间

#### chunks表（切片数据）
- `id`: 主键
- `doc_id`: 外键关联文档
- `content_text`: 小切片内容（用于BM25）
- `content_large`: 大切块内容（用于生成）
- `embedding`: 向量数据（pgvector类型）
- `metadata`: 扩展元数据（jsonb类型）

#### semantic_cache表（语义缓存）
- `id`: 主键
- `query_text`: 原始问题文本
- `query_embedding`: 问题向量
- `cached_answer`: 缓存答案
- `similarity_score`: 相似度得分
- `created_at`: 创建时间
- `expires_at`: 过期时间

## 部署指南

### 生产环境部署

1. 修改环境变量配置
2. 构建镜像：
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

3. 启动服务：
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 监控和运维

- 查看日志：`docker compose logs -f [service]`
- 健康检查：访问 `/health` 端点
- 数据备份：定期备份pg_data目录

## 扩展开发

### 添加新的文档格式

1. 在 `app/services/document_service.py` 中添加解析逻辑
2. 更新配置文件中的支持格式列表

### 添加新的检索算法

1. 在 `app/services/rag_service.py` 中添加新的检索方法
2. 更新结果融合逻辑

### 添加新的LLM提供商

1. 在 `app/config.py` 中添加配置选项
2. 在相关服务中实现调用逻辑

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否启动
   - 验证连接参数配置

2. **文档处理失败**
   - 检查文件格式是否支持
   - 查看后端日志获取详细错误信息

3. **LLM调用失败**
   - 验证API密钥配置
   - 检查网络连接和API服务状态

### 日志查看

```bash
# 查看后端日志
docker compose logs -f backend

# 查看前端日志
docker compose logs -f frontend

# 查看数据库日志
docker compose logs -f db
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件至 [your-email@example.com]

---

**MiniRAG** - 让AI问答更加智能和高效！
## 开发命令（Just）

项目已从 Makefile 迁移到 justfile：

```bash
# 查看可用命令
just

# 安装依赖（后端使用 uv）
just install-dev

# 启动开发环境
just run-dev

# 后端测试
just test-backend
```
