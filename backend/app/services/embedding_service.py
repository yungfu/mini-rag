import asyncio
import hashlib
from typing import List, Dict, Any
import logging
from langchain_ollama import OllamaEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """嵌入服务"""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.embedding_dim = settings.EMBEDDING_DIM
        self.ollama_base_url = (settings.LLM_BASE_URL or "http://localhost:11434").rstrip("/")
        self.embedding_client = OllamaEmbeddings(
            model=self.model_name,
            base_url=self.ollama_base_url,
        )
        self.cache = {}  # 简单的内存缓存
    
    async def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        # 检查缓存
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self.cache:
            logger.debug(f"命中嵌入缓存: {cache_key[:8]}...")
            return self.cache[cache_key]
        
        try:
            # 仅使用远程API生成嵌入
            embedding = await self._get_remote_embedding(text)
            
            # 缓存结果（限制缓存大小）
            if len(self.cache) < 1000:
                self.cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            raise Exception(f"嵌入生成失败: {str(e)}")
    
    async def _get_remote_embedding(self, text: str) -> List[float]:
        """通过LangChain的Ollama Embeddings获取远程嵌入向量"""
        try:
            embedding = await asyncio.to_thread(self.embedding_client.embed_query, text)

            if not embedding:
                raise Exception("Ollama返回的embedding为空")
            
            # 验证嵌入维度
            if len(embedding) != self.embedding_dim:
                logger.warning(f"嵌入维度不匹配: 期望 {self.embedding_dim}, 实际 {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Ollama嵌入调用失败: {e}")
            raise Exception(f"Ollama嵌入生成失败: {str(e)}")
    
    async def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取嵌入向量"""
        embeddings = []
        
        # 批量处理以提高效率
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = await asyncio.gather(*[
                self.get_embedding(text) for text in batch_texts
            ])
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def similarity_search(self, query_embedding: List[float], 
                              candidate_embeddings: List[List[float]], 
                              top_k: int = 5) -> List[Dict[str, Any]]:
        """相似性搜索"""
        try:
            # 计算余弦相似度
            similarities = []
            for i, candidate in enumerate(candidate_embeddings):
                similarity = self._cosine_similarity(query_embedding, candidate)
                similarities.append({
                    "index": i,
                    "similarity": similarity,
                    "embedding": candidate
                })
            
            # 按相似度排序
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 返回top_k结果
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"相似性搜索失败: {e}")
            raise Exception(f"相似性搜索失败: {str(e)}")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        try:
            # 纯 Python 计算，避免对 numpy 的运行时依赖
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(a * a for a in vec1) ** 0.5
            norm2 = sum(b * b for b in vec2) ** 0.5
            
            # 计算余弦相似度
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"计算余弦相似度失败: {e}")
            return 0.0
    
    async def cleanup_cache(self):
        """清理缓存"""
        self.cache.clear()
        logger.info("嵌入缓存已清理")