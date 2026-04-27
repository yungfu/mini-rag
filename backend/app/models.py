from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
import json

from app.config import settings

Base = declarative_base()

class Document(Base):
    """文档表"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, unique=True, index=True, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # md, txt, html
    file_size = Column(Integer)
    status = Column(String, default="processing")  # processing, ready, deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联切片
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class DocumentChunk(Base):
    """文档切片表"""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, ForeignKey("documents.doc_id"), nullable=False)
    content_text = Column(Text, nullable=False)  # 小切片内容，用于BM25
    content_large = Column(Text, nullable=False)  # 大切块内容，用于生成
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)  # 小块向量数据
    metadata = Column(JSON, nullable=True)  # 扩展元数据
    chunk_index = Column(Integer, nullable=False)  # 切片序号
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联文档
    document = relationship("Document", back_populates="chunks")
    
    def to_dict(self):
        embedding = self.embedding.tolist() if hasattr(self.embedding, "tolist") else self.embedding
        metadata = self.metadata
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "content_text": self.content_text,
            "content_large": self.content_large,
            "embedding": embedding,
            "metadata": metadata,
            "chunk_index": self.chunk_index,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SemanticCache(Base):
    """语义缓存表"""
    __tablename__ = "semantic_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)
    cached_answer = Column(Text, nullable=False)
    similarity_score = Column(Float, nullable=False)
    source_chunk_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    def to_dict(self):
        query_embedding = self.query_embedding.tolist() if hasattr(self.query_embedding, "tolist") else self.query_embedding
        source_chunk_ids = self.source_chunk_ids
        if isinstance(source_chunk_ids, str):
            try:
                source_chunk_ids = json.loads(source_chunk_ids)
            except json.JSONDecodeError:
                source_chunk_ids = []
        return {
            "id": self.id,
            "query_text": self.query_text,
            "query_embedding": query_embedding,
            "cached_answer": self.cached_answer,
            "similarity_score": self.similarity_score,
            "source_chunk_ids": source_chunk_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

class ProcessingLog(Base):
    """处理日志表"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, nullable=False)
    operation = Column(String, nullable=False)  # upload, process, delete
    status = Column(String, nullable=False)  # pending, processing, completed, failed
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "operation": self.operation,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

# Pydantic模型用于API
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DocumentResponse(BaseModel):
    id: int
    doc_id: str
    filename: str
    file_type: str
    file_size: Optional[int]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]

class DocumentChunkResponse(BaseModel):
    id: int
    doc_id: str
    content_text: str
    content_large: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]]
    chunk_index: int
    created_at: Optional[str]

class SemanticCacheResponse(BaseModel):
    id: int
    query_text: str
    cached_answer: str
    similarity_score: float
    created_at: Optional[str]
    expires_at: Optional[str]

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    use_cache: bool = True
    use_rerank: bool = False

class ChatResponse(BaseModel):
    answer: str
    sources: List[DocumentChunkResponse]
    cache_hit: bool
    processing_time: float
    rerank_used: bool = False

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    status: str
    message: str
