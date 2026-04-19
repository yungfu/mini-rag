import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_

from app.database import get_async_db, SessionLocal
from app.models import DocumentChunk, SemanticCache
from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.rerank_service import RerankService

logger = logging.getLogger(__name__)

class RAGService:
    """RAG服务"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.rerank_service = RerankService()
        self.semantic_cache_enabled = settings.ENABLE_SEMANTIC_CACHE
        self.cache_similarity_threshold = settings.CACHE_SIMILARITY_THRESHOLD
        self.cache_ttl_days = settings.CACHE_TTL_DAYS
        self.top_k = settings.TOP_K
        self.similarity_threshold = settings.SIMILARITY_THRESHOLD
    
    async def generate_response(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """生成回答（非流式）"""
        start_time = time.time()
        
        try:
            # 尝试从缓存获取
            cached_result = await self._get_cached_response(query)
            if cached_result:
                return {
                    "answer": cached_result["cached_answer"],
                    "sources": cached_result["sources"],
                    "cache_hit": True,
                    "processing_time": time.time() - start_time,
                    "rerank_used": cached_result.get("rerank_used", False)
                }
            
            # 执行RAG检索
            result = await self._execute_rag(query, top_k)
            
            # 缓存结果
            if self.semantic_cache_enabled:
                await self._cache_response(query, result)
            
            return {
                "answer": result["answer"],
                "sources": result["sources"],
                "cache_hit": False,
                "processing_time": time.time() - start_time,
                "rerank_used": result.get("rerank_used", False)
            }
            
        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            raise Exception(f"RAG生成失败: {str(e)}")
    
    async def generate_response_stream(self, query: str, top_k: int = 5):
        """生成回答（流式）"""
        start_time = time.time()
        cache_hit = False
        rerank_used = False
        
        try:
            # 尝试从缓存获取
            cached_result = await self._get_cached_response(query)
            if cached_result:
                cache_hit = True
                rerank_used = cached_result.get("rerank_used", False)
                
                # 流式输出缓存答案
                for chunk in self._stream_text(cached_result["cached_answer"]):
                    yield {
                        "type": "answer",
                        "content": chunk,
                        "cache_hit": cache_hit,
                        "processing_time": time.time() - start_time,
                        "rerank_used": rerank_used
                    }
                
                # 发送源信息
                yield {
                    "type": "sources",
                    "sources": cached_result["sources"],
                    "cache_hit": cache_hit,
                    "processing_time": time.time() - start_time,
                    "rerank_used": rerank_used
                }
                
                return
            
            # 执行RAG检索
            result = await self._execute_rag(query, top_k)
            rerank_used = result.get("rerank_used", False)
            
            # 缓存结果
            if self.semantic_cache_enabled:
                await self._cache_response(query, result)
            
            # 流式输出生成的答案
            for chunk in self._stream_text(result["answer"]):
                yield {
                    "type": "answer",
                    "content": chunk,
                    "cache_hit": cache_hit,
                    "processing_time": time.time() - start_time,
                    "rerank_used": rerank_used
                }
            
            # 发送源信息
            yield {
                "type": "sources",
                "sources": result["sources"],
                "cache_hit": cache_hit,
                "processing_time": time.time() - start_time,
                "rerank_used": rerank_used
            }
            
        except Exception as e:
            logger.error(f"流式生成回答失败: {e}")
            yield {
                "type": "error",
                "content": f"生成回答失败: {str(e)}",
                "cache_hit": cache_hit,
                "processing_time": time.time() - start_time,
                "rerank_used": rerank_used
            }
    
    async def _execute_rag(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """执行RAG检索"""
        try:
            # 1. 获取查询向量
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # 2. 双路召回
            vector_results = await self._vector_search(query_embedding, top_k * 2)
            bm25_results = await self._bm25_search(query, top_k * 2)
            
            # 3. 结果融合
            fused_results = await self._fuse_results(vector_results, bm25_results, top_k)
            
            # 4. 重新排序（如果启用）
            if settings.RERANK_ENABLED and settings.RERANK_MODEL:
                fused_results = await self.rerank_service.rerank(query, fused_results)
                rerank_used = True
            else:
                rerank_used = False
            
            # 5. 生成最终答案
            answer = await self._generate_answer(query, fused_results)
            
            return {
                "answer": answer,
                "sources": fused_results,
                "rerank_used": rerank_used
            }
            
        except Exception as e:
            logger.error(f"RAG执行失败: {e}")
            raise Exception(f"RAG执行失败: {str(e)}")
    
    async def _vector_search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """向量搜索"""
        db = SessionLocal()
        try:
            # 构建SQL查询
            query = text("""
                SELECT 
                    id, doc_id, content_text, content_large, embedding, metadata, chunk_index,
                    1 - (embedding <=> :query_embedding) as similarity_score
                FROM chunks 
                WHERE 1 - (embedding <=> :query_embedding) >= :similarity_threshold
                ORDER BY similarity_score DESC 
                LIMIT :top_k
            """)
            
            result = db.execute(query, {
                "query_embedding": json.dumps(query_embedding),
                "similarity_threshold": self.similarity_threshold,
                "top_k": top_k
            })
            
            chunks = []
            for row in result:
                chunks.append({
                    "id": row.id,
                    "doc_id": row.doc_id,
                    "content_text": row.content_text,
                    "content_large": row.content_large,
                    "embedding": json.loads(row.embedding),
                    "metadata": json.loads(row.metadata) if row.metadata else {},
                    "chunk_index": row.chunk_index,
                    "similarity_score": float(row.similarity_score)
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            raise Exception(f"向量搜索失败: {str(e)}")
        finally:
            db.close()
    
    async def _bm25_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """BM25搜索"""
        db = SessionLocal()
        try:
            # 使用PostgreSQL的bm25扩展进行全文搜索
            query = text("""
                SELECT 
                    id, doc_id, content_text, content_large, embedding, metadata, chunk_index,
                    ts_rank_cd(to_tsvector('chinese', content_text), to_tsquery('chinese', :query)) as rank_score
                FROM chunks 
                WHERE to_tsvector('chinese', content_text) @@ to_tsquery('chinese', :query)
                ORDER BY rank_score DESC 
                LIMIT :top_k
            """)
            
            result = db.execute(query, {
                "query": query,
                "top_k": top_k
            })
            
            chunks = []
            for row in result:
                chunks.append({
                    "id": row.id,
                    "doc_id": row.doc_id,
                    "content_text": row.content_text,
                    "content_large": row.content_large,
                    "embedding": json.loads(row.embedding) if row.embedding else [],
                    "metadata": json.loads(row.metadata) if row.metadata else {},
                    "chunk_index": row.chunk_index,
                    "bm25_score": float(row.rank_score)
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"BM25搜索失败: {e}")
            raise Exception(f"BM25搜索失败: {str(e)}")
        finally:
            db.close()
    
    async def _fuse_results(self, vector_results: List[Dict[str, Any]], 
                           bm25_results: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """融合搜索结果（RRF算法）"""
        try:
            # 创建文档ID到结果的映射
            doc_to_chunks = {}
            
            # 合并向量搜索结果
            for i, chunk in enumerate(vector_results):
                doc_id = chunk["doc_id"]
                if doc_id not in doc_to_chunks:
                    doc_to_chunks[doc_id] = []
                
                chunk["vector_rank"] = i + 1
                chunk["vector_score"] = 1 / (chunk["vector_rank"] + 60)
                doc_to_chunks[doc_id].append(chunk)
            
            # 合并BM25搜索结果
            for i, chunk in enumerate(bm25_results):
                doc_id = chunk["doc_id"]
                if doc_id not in doc_to_chunks:
                    doc_to_chunks[doc_id] = []
                
                chunk["bm25_rank"] = i + 1
                chunk["bm25_score"] = 1 / (chunk["bm25_rank"] + 60)
                doc_to_chunks[doc_id].append(chunk)
            
            # 计算每个切片的综合得分
            fused_chunks = []
            for doc_id, chunks in doc_to_chunks.items():
                for chunk in chunks:
                    # RRF融合公式
                    if "vector_score" in chunk and "bm25_score" in chunk:
                        chunk["fused_score"] = chunk["vector_score"] + chunk["bm25_score"]
                    elif "vector_score" in chunk:
                        chunk["fused_score"] = chunk["vector_score"]
                    elif "bm25_score" in chunk:
                        chunk["fused_score"] = chunk["bm25_score"]
                    else:
                        chunk["fused_score"] = 0
                    
                    fused_chunks.append(chunk)
            
            # 按综合得分排序
            fused_chunks.sort(key=lambda x: x["fused_score"], reverse=True)
            
            # 返回前top_k个结果
            return fused_chunks[:top_k]
            
        except Exception as e:
            logger.error(f"结果融合失败: {e}")
            raise Exception(f"结果融合失败: {str(e)}")
    
    async def _generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """生成最终答案"""
        try:
            # 构建上下文
            context = "\n\n".join([chunk["content_large"] for chunk in context_chunks])
            
            # 构建提示词
            prompt = f"""基于以下上下文回答用户问题。请确保回答准确、相关且有帮助。

上下文：
{context}

问题：{query}

回答："""
            
            # 调用LLM生成答案
            from litellm import completion
            
            response = completion(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                temperature=0.7,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            return answer.strip()
            
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return "抱歉，我无法生成回答。请稍后再试。"
    
    async def _get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """获取缓存的回答"""
        if not self.semantic_cache_enabled:
            return None
        
        try:
            # 获取查询向量
            query_embedding = await self.embedding_service.get_embedding(query)
            
            db = SessionLocal()
            try:
                # 查找最相似的缓存
                query = text("""
                    SELECT id, query_text, cached_answer, query_embedding, similarity_score
                    FROM semantic_cache 
                    WHERE expires_at > NOW()
                    ORDER BY query_embedding <=> :query_embedding ASC
                    LIMIT 1
                """)
                
                result = db.execute(query, {
                    "query_embedding": json.dumps(query_embedding)
                })
                
                row = result.fetchone()
                if row and row.similarity_score >= self.cache_similarity_threshold:
                    # 查找相关源文档
                    source_chunks = await self._get_source_chunks_for_cache(row.id)
                    
                    return {
                        "cached_answer": row.cached_answer,
                        "sources": source_chunks,
                        "rerank_used": False
                    }
                
                return None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取缓存回答失败: {e}")
            return None
    
    async def _cache_response(self, query: str, result: Dict[str, Any]):
        """缓存回答"""
        try:
            # 获取查询向量
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # 计算过期时间
            expires_at = datetime.utcnow() + timedelta(days=self.cache_ttl_days)
            
            db = SessionLocal()
            try:
                # 创建缓存记录
                cache_record = SemanticCache(
                    query_text=query,
                    query_embedding=json.dumps(query_embedding),
                    cached_answer=result["answer"],
                    similarity_score=1.0,  # 新缓存的相似度设为1.0
                    expires_at=expires_at
                )
                
                db.add(cache_record)
                db.commit()
                
                # 关联源文档（可选）
                # await self._link_sources_to_cache(cache_record.id, result["sources"])
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"缓存回答失败: {e}")
    
    def _stream_text(self, text: str, chunk_size: int = 50):
        """流式输出文本"""
        words = text.split()
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            if len(current_chunk) >= chunk_size:
                yield " ".join(current_chunk)
                current_chunk = []
        
        if current_chunk:
            yield " ".join(current_chunk)
    
    async def _get_source_chunks_for_cache(self, cache_id: int) -> List[Dict[str, Any]]:
        """获取缓存相关的源文档切片"""
        # 这里可以实现从缓存中关联源文档的逻辑
        # 目前返回空列表
        return []