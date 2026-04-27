-- MiniRAG 数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS bm25;

-- backend 启动后才会建表；这里仅在表已存在时补索引和默认配置。
DO $$
BEGIN
    IF to_regclass('public.chunks') IS NOT NULL THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_chunks_content_bm25 ON chunks USING bm25 (content_text)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_chunks_content_search ON chunks USING gin (to_tsvector(''chinese'', content_text))';
    END IF;

    IF to_regclass('public.semantic_cache') IS NOT NULL THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_cache_query_embedding ON semantic_cache USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 50)';
    END IF;

    IF to_regclass('public.system_config') IS NOT NULL THEN
        INSERT INTO system_config (key, value, description) VALUES
        ('chunk_size', '512', '文档切片大小'),
        ('chunk_overlap', '50', '文档切片重叠大小'),
        ('parent_chunk_size', '2048', '父块大小'),
        ('parent_chunk_overlap', '0', '父块重叠大小'),
        ('top_k', '5', '检索返回结果数量'),
        ('similarity_threshold', '0.7', '相似度阈值'),
        ('cache_similarity_threshold', '0.85', '缓存相似度阈值'),
        ('cache_ttl_days', '7', '缓存有效期（天）'),
        ('enable_semantic_cache', 'true', '是否启用语义缓存'),
        ('rerank_enabled', 'false', '是否启用重排序')
        ON CONFLICT (key) DO NOTHING;
    END IF;
END $$;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'MiniRAG 数据库初始化完成';
END $$;
