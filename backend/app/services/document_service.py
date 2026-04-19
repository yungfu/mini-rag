import os
import uuid
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
import aiofiles
from fastapi import HTTPException, UploadFile
import asyncio

from app.database import get_async_db, SessionLocal
from app.models import Document, DocumentChunk, ProcessingLog
from app.config import settings
from app.services.embedding_service import EmbeddingService

class DocumentService:
    """文档服务"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.supported_formats = settings.SUPPORTED_FORMATS
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.upload_dir = settings.UPLOAD_DIR
        
        # 确保上传目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def upload_document(self, file: UploadFile, document_type: str = "md") -> Dict[str, Any]:
        """上传文档"""
        if document_type not in self.supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文档类型: {document_type}. 支持的类型: {', '.join(self.supported_formats)}"
            )
        
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大，最大支持 {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # 生成唯一文档ID
        doc_id = str(uuid.uuid4())
        file_path = os.path.join(self.upload_dir, f"{doc_id}.{document_type}")
        
        # 记录处理日志
        await self._log_processing(doc_id, "upload", "pending", "开始上传文档")
        
        try:
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # 创建文档记录
            db = SessionLocal()
            try:
                document = Document(
                    doc_id=doc_id,
                    filename=file.filename,
                    file_type=document_type,
                    file_size=len(content),
                    status="processing"
                )
                db.add(document)
                db.commit()
                db.refresh(document)
                
                # 开始异步处理文档
                asyncio.create_task(self._process_document(doc_id, file_path, document_type))
                
                await self._log_processing(doc_id, "upload", "completed", "文档上传成功")
                
                return {
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "file_type": document_type,
                    "status": "processing",
                    "message": "文档上传成功，正在处理中"
                }
                
            finally:
                db.close()
                
        except Exception as e:
            await self._log_processing(doc_id, "upload", "failed", f"文档上传失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")
    
    async def _process_document(self, doc_id: str, file_path: str, file_type: str):
        """异步处理文档"""
        await self._log_processing(doc_id, "process", "pending", "开始处理文档")
        
        try:
            # 解析文档内容
            content = await self._parse_document(file_path, file_type)
            
            # 生成切片
            chunks = await self._create_chunks(content, doc_id)
            
            # 生成向量和存储
            await self._store_chunks(chunks)
            
            # 更新文档状态
            await self._update_document_status(doc_id, "ready")
            
            await self._log_processing(doc_id, "process", "completed", "文档处理成功")
            
        except Exception as e:
            await self._update_document_status(doc_id, "failed")
            await self._log_processing(doc_id, "process", "failed", f"文档处理失败: {str(e)}")
    
    async def _parse_document(self, file_path: str, file_type: str) -> str:
        """解析文档内容"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            if file_type == "md":
                # Markdown处理：保留标题结构，去除markdown语法
                import re
                content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
            elif file_type == "html":
                # HTML处理：提取文本内容
                import re
                content = re.sub(r'<[^>]+>', '', content)  # 移除HTML标签
                content = re.sub(r'\s+', ' ', content)  # 合并空白字符
                content = content.strip()
            
            return content
            
        except Exception as e:
            raise Exception(f"文档解析失败: {str(e)}")
    
    async def _create_chunks(self, content: str, doc_id: str) -> List[Dict[str, Any]]:
        """创建文档切片"""
        chunks = []
        
        # 简单的按字符数分割
        text_length = len(content)
        chunk_count = (text_length // self.chunk_size) + 1
        
        for i in range(chunk_count):
            start = i * self.chunk_size
            end = min((i + 1) * self.chunk_size + self.chunk_overlap, text_length)
            
            # 小切片：用于BM25检索
            small_chunk = content[start:end]
            
            # 大切块：用于生成答案（包含更多上下文）
            large_start = max(0, i * self.chunk_size - self.chunk_overlap)
            large_end = min((i + 1) * self.chunk_size + self.chunk_overlap, text_length)
            large_chunk = content[large_start:large_end]
            
            chunks.append({
                "doc_id": doc_id,
                "content_text": small_chunk,
                "content_large": large_chunk,
                "metadata": {
                    "chunk_index": i,
                    "total_chunks": chunk_count,
                    "small_chunk_start": start,
                    "small_chunk_end": end,
                    "large_chunk_start": large_start,
                    "large_chunk_end": large_end
                }
            })
        
        return chunks
    
    async def _store_chunks(self, chunks: List[Dict[str, Any]]):
        """存储文档切片"""
        # 生成所有向量的批处理
        embeddings = []
        for chunk in chunks:
            embedding = await self.embedding_service.get_embedding(chunk["content_text"])
            embeddings.append(embedding)
            chunk["embedding"] = embedding
        
        # 批量存储到数据库
        db = SessionLocal()
        try:
            for chunk in chunks:
                document_chunk = DocumentChunk(
                    doc_id=chunk["doc_id"],
                    content_text=chunk["content_text"],
                    content_large=chunk["content_large"],
                    embedding=json.dumps(chunk["embedding"]),
                    metadata=json.dumps(chunk["metadata"]),
                    chunk_index=chunk["metadata"]["chunk_index"]
                )
                db.add(document_chunk)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise Exception(f"存储切片失败: {str(e)}")
        finally:
            db.close()
    
    async def _update_document_status(self, doc_id: str, status: str):
        """更新文档状态"""
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.doc_id == doc_id).first()
            if document:
                document.status = status
                document.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            db.rollback()
            raise Exception(f"更新文档状态失败: {str(e)}")
        finally:
            db.close()
    
    async def _log_processing(self, doc_id: str, operation: str, status: str, message: str):
        """记录处理日志"""
        db = SessionLocal()
        try:
            log = ProcessingLog(
                doc_id=doc_id,
                operation=operation,
                status=status,
                message=message
            )
            db.add(log)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"记录处理日志失败: {str(e)}")
        finally:
            db.close()
    
    async def get_documents(self) -> List[Dict[str, Any]]:
        """获取文档列表"""
        db = SessionLocal()
        try:
            documents = db.query(Document).filter(Document.status != "deleted").all()
            return [doc.to_dict() for doc in documents]
        finally:
            db.close()
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档"""
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.doc_id == doc_id).first()
            return document.to_dict() if document else None
        finally:
            db.close()
    
    async def delete_document(self, doc_id: str):
        """删除文档"""
        db = SessionLocal()
        try:
            # 标记文档为删除状态
            document = db.query(Document).filter(Document.doc_id == doc_id).first()
            if document:
                document.status = "deleted"
                document.updated_at = datetime.utcnow()
                db.commit()
                
                # 可以在这里添加物理删除文件的逻辑
                # file_path = os.path.join(self.upload_dir, f"{doc_id}.{document.file_type}")
                # if os.path.exists(file_path):
                #     os.remove(file_path)
            else:
                raise HTTPException(status_code=404, detail="文档不存在")
                
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")
        finally:
            db.close()
    
    async def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """获取文档的所有切片"""
        db = SessionLocal()
        try:
            chunks = db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc_id).all()
            return [chunk.to_dict() for chunk in chunks]
        finally:
            db.close()