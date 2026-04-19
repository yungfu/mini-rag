-- MiniRAG 数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS bm25;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
ON chunks USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunks_content_bm25 
ON chunks USING bm25 (content_text);

CREATE INDEX IF NOT EXISTS idx_cache_query_embedding 
ON semantic_cache USING ivfflat (query_embedding vector_cosine_ops) 
WITH (lists = 50);

-- 创建全文搜索索引
CREATE INDEX IF NOT EXISTS idx_chunks_content_search 
ON chunks USING gin (to_tsvector('chinese', content_text));

-- 插入默认配置
INSERT INTO system_config (key, value, description) VALUES 
('chunk_size', '512', '文档切片大小'),
('chunk_overlap', '50', '文档切片重叠大小'),
('top_k', '5', '检索返回结果数量'),
('similarity_threshold', '0.7', '相似度阈值'),
('cache_similarity_threshold', '0.85', '缓存相似度阈值'),
('cache_ttl_days', '7', '缓存有效期（天）'),
('enable_semantic_cache', 'true', '是否启用语义缓存'),
('rerank_enabled', 'false', '是否启用重排序')
ON CONFLICT (key) DO NOTHING;

-- 设置优化参数
SET shared_preload_libraries = 'vector,bm25';
SET pg_bm25.enable_preload = true;
SET vectorizer = 'pgvector';

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'MiniRAG 数据库初始化完成';
END $$;