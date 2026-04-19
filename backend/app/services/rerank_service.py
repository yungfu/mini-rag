import json
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from litellm import rerank as litellm_rerank
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class RerankService:
    """重排序服务"""
    
    def __init__(self):
        self.model_name = settings.RERANK_MODEL
        self.provider = settings.LLM_PROVIDER
        self.enabled = settings.RERANK_ENABLED
    
    async def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        """对文档进行重排序"""
        if not self.enabled or not self.model_name:
            logger.warning("Rerank功能未启用或未配置模型，跳过重排序")
            return documents
        
        try:
            # 准备重排序数据
            doc_texts = [doc["content_large"] for doc in documents]
            doc_ids = [doc["id"] for doc in documents]
            
            # 调用重排序模型
            reranked_results = await self._call_rerank_api(query, doc_texts)
            
            # 合并结果
            reranked_documents = []
            for result in reranked_results:
                doc_index = result["index"]
                if doc_index < len(documents):
                    doc = documents[doc_index].copy()
                    doc["rerank_score"] = result["relevance_score"]
                    doc["rerank_rank"] = result["rank"]
                    reranked_documents.append(doc)
            
            # 按重排序分数重新排序
            reranked_documents.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            # 限制返回数量
            if top_k:
                reranked_documents = reranked_documents[:top_k]
            
            return reranked_documents
            
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            # 返回原始文档
            return documents
    
    async def _call_rerank_api(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """调用重排序API"""
        try:
            if self.provider == "local":
                return await self._local_rerank(query, documents)
            else:
                return await self._remote_rerank(query, documents)
                
        except Exception as e:
            logger.error(f"重排序API调用失败: {e}")
            raise Exception(f"重排序失败: {str(e)}")
    
    async def _remote_rerank(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """远程重排序"""
        try:
            response = litellm_rerank(
                model=self.model_name,
                query=query,
                documents=documents,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                top_n=len(documents),
                timeout=30
            )
            
            # 处理响应
            reranked_results = []
            for i, result in enumerate(response.data):
                reranked_results.append({
                    "index": result["index"],
                    "relevance_score": result["relevance_score"],
                    "rank": i + 1
                })
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"远程重排序调用失败: {e}")
            raise Exception(f"远程重排序失败: {str(e)}")
    
    async def _local_rerank(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """本地重排序"""
        try:
            from sentence_transformers import CrossEncoder
            
            # 使用本地交叉编码器进行重排序
            model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            # 准备数据对
            pairs = [[query, doc] for doc in documents]
            
            # 预测相关性分数
            scores = model.predict(pairs)
            
            # 创建结果
            reranked_results = []
            for i, score in enumerate(scores):
                reranked_results.append({
                    "index": i,
                    "relevance_score": float(score),
                    "rank": i + 1
                })
            
            # 按分数排序
            reranked_results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"本地重排序失败: {e}")
            raise Exception(f"本地重排序失败: {str(e)}")
    
    async def rerank_cross_encoder(self, query: str, documents: List[Dict[str, Any]], 
                                  model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> List[Dict[str, Any]]:
        """使用交叉编码器进行重排序"""
        try:
            from sentence_transformers import CrossEncoder
            
            model = CrossEncoder(model_name)
            
            # 准备数据对
            pairs = [[query, doc["content_large"]] for doc in documents]
            
            # 预测相关性分数
            scores = model.predict(pairs)
            
            # 合并结果
            reranked_documents = []
            for i, (score, doc) in enumerate(zip(scores, documents)):
                doc_copy = doc.copy()
                doc_copy["rerank_score"] = float(score)
                doc_copy["rerank_rank"] = i + 1
                reranked_documents.append(doc_copy)
            
            # 按分数排序
            reranked_documents.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            return reranked_documents
            
        except Exception as e:
            logger.error(f"交叉编码器重排序失败: {e}")
            return documents
    
    async def rerank_pointwise(self, query: str, documents: List[Dict[str, Any]], 
                               model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> List[Dict[str, Any]]:
        """使用点式编码器进行重排序"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer(model_name)
            
            # 获取查询和文档的向量
            query_embedding = model.encode(query)
            doc_embeddings = model.encode([doc["content_large"] for doc in documents])
            
            # 计算相似度
            similarities = []
            for i, doc_embedding in enumerate(doc_embeddings):
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities.append({
                    "index": i,
                    "relevance_score": similarity,
                    "rank": i + 1
                })
            
            # 按相似度排序
            similarities.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # 合并结果
            reranked_documents = []
            for similarity in similarities:
                doc_index = similarity["index"]
                doc_copy = documents[doc_index].copy()
                doc_copy["rerank_score"] = similarity["relevance_score"]
                doc_copy["rerank_rank"] = similarity["rank"]
                reranked_documents.append(doc_copy)
            
            return reranked_documents
            
        except Exception as e:
            logger.error(f"点式编码器重排序失败: {e}")
            return documents
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)