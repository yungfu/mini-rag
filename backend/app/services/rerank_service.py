import asyncio
from typing import List, Dict, Any
import re
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class RerankService:
    """重排序服务"""
    
    def __init__(self):
        self.model_name = settings.RERANK_MODEL
        self.enabled = settings.RERANK_ENABLED
        self.base_url = settings.LLM_BASE_URL or "http://localhost:11434"
    
    async def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        """对文档进行重排序"""
        if not self.enabled or not self.model_name:
            logger.warning("Rerank功能未启用或未配置模型，跳过重排序")
            return documents
        
        try:
            # 准备重排序数据
            doc_texts = [doc["content_large"] for doc in documents]
            
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
            return await self._remote_rerank(query, documents)
                
        except Exception as e:
            logger.error(f"重排序API调用失败: {e}")
            raise Exception(f"重排序失败: {str(e)}")
    
    async def _remote_rerank(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """使用LangChain + Ollama进行远程重排序"""
        try:
            llm = ChatOllama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=0,
            )

            async def score_one(index: int, document: str) -> Dict[str, Any]:
                prompt = (
                    "请根据查询与文档内容的相关性，仅返回一个0到1之间的小数。"
                    "只返回数字，不要返回其他文字。\n\n"
                    f"查询：{query}\n\n"
                    f"文档：{document[:2000]}"
                )
                response = await asyncio.to_thread(
                    llm.invoke,
                    [HumanMessage(content=prompt)],
                )
                content = response.content
                text_content = content if isinstance(content, str) else " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
                matched = re.search(r"-?\d+(?:\.\d+)?", text_content)
                score = float(matched.group(0)) if matched else 0.0
                score = max(0.0, min(1.0, score))
                return {"index": index, "relevance_score": score}

            scored_results = await asyncio.gather(*[
                score_one(i, doc) for i, doc in enumerate(documents)
            ])

            scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)

            reranked_results = []
            for i, result in enumerate(scored_results):
                reranked_results.append({
                    "index": result["index"],
                    "relevance_score": result["relevance_score"],
                    "rank": i + 1
                })
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"远程重排序调用失败: {e}")
            raise Exception(f"远程重排序失败: {str(e)}")
