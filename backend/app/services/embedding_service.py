import json
import asyncio
from typing import List, Optional, Dict, Any
from litellm import embedding as litellm_embedding
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """嵌入服务"""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.provider = settings.LLM_PROVIDER
        self.embedding_dim = settings.EMBEDDING_DIM
        self.cache = {}  # 简单的内存缓存
        
        # 初始化本地模型（如果使用）
        if self.provider == "local":
            try:
                self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embedding_dim = 384  # all-MiniLM-L6-v2的维度
                logger.info(f"本地嵌入模型加载成功: {self.model_name}")
            except Exception as e:
                logger.error(f"本地模型加载失败: {e}")
                self.local_model = None
        else:
            self.local_model = None
    
    async def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        # 检查缓存
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self.cache:
            logger.debug(f"命中嵌入缓存: {cache_key[:8]}...")
            return self.cache[cache_key]
        
        try:
            if self.provider == "local" and self.local_model:
                # 使用本地模型
                embedding = await self._get_local_embedding(text)
            else:
                # 使用远程API
                embedding = await self._get_remote_embedding(text)
            
            # 缓存结果（限制缓存大小）
            if len(self.cache) < 1000:
                self.cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            raise Exception(f"嵌入生成失败: {str(e)}")
    
    async def _get_remote_embedding(self, text: str) -> List[float]:
        """获取远程嵌入向量"""
        try:
            response = litellm_embedding(
                model=self.model_name,
                input=[text],
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                timeout=30
            )
            
            embedding = response['data'][0]['embedding']
            
            # 验证嵌入维度
            if len(embedding) != self.embedding_dim:
                logger.warning(f"嵌入维度不匹配: 期望 {self.embedding_dim}, 实际 {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"远程嵌入调用失败: {e}")
            raise Exception(f"远程嵌入生成失败: {str(e)}")
    
    async def _get_local_embedding(self, text: str) -> List[float]:
        """获取本地嵌入向量"""
        if not self.local_model:
            raise Exception("本地嵌入模型未加载")
        
        try:
            # 使用sentence-transformers
            embedding = self.local_model.encode(text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"本地嵌入生成失败: {e}")
            raise Exception(f"本地嵌入生成失败: {str(e)}")
    
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
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            # 计算点积
            dot_product = np.dot(vec1, vec2)
            
            # 计算模长
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
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