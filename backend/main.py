from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from typing import List, Optional
import asyncio
import logging
from datetime import datetime
import json

from app.database import get_db, init_db
from app.models import Document, DocumentChunk, SemanticCache
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.config import settings

app = FastAPI(
    title="MiniRAG API",
    description="基于PostgreSQL的混合检索RAG系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    logger.info("启动MiniRAG应用...")
    await init_db()

@app.get("/")
async def root():
    """根路径"""
    return {"message": "MiniRAG API服务正在运行", "version": "1.0.0"}

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("md")
):
    """上传文档"""
    try:
        document_service = DocumentService()
        result = await document_service.upload_document(file, document_type)
        return result
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def get_documents():
    """获取文档列表"""
    try:
        document_service = DocumentService()
        documents = await document_service.get_documents()
        return {"documents": documents}
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    try:
        document_service = DocumentService()
        await document_service.delete_document(doc_id)
        return {"message": "文档删除成功"}
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_stream(query: str, top_k: int = 5):
    """流式聊天接口"""
    try:
        rag_service = RAGService()
        
        async def generate_response():
            async for chunk in rag_service.generate_response_stream(query, top_k):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"聊天生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(query: str, top_k: int = 5):
    """普通聊天接口"""
    try:
        rag_service = RAGService()
        result = await rag_service.generate_response(query, top_k)
        return result
    except Exception as e:
        logger.error(f"聊天生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
