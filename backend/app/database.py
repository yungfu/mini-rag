from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
import asyncio
from typing import Generator
import os

from app.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """初始化数据库"""
    # 等待数据库连接就绪
    await wait_for_db()
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 创建扩展索引
    await create_extensions()

async def wait_for_db():
    """等待数据库连接就绪"""
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
                break
        except Exception:
            retry_count += 1
            await asyncio.sleep(2)
    
    if retry_count == max_retries:
        raise Exception("数据库连接超时")

async def create_extensions():
    """创建PostgreSQL扩展"""
    with engine.connect() as conn:
        try:
            # 创建向量扩展
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            
            # 创建BM25扩展
            conn.execute("CREATE EXTENSION IF NOT EXISTS bm25")
            conn.commit()
            
            # 创建向量索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
                ON chunks USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """)
            
            # 创建BM25索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_content_bm25 
                ON chunks USING bm25 (content_text)
            """)
            
            # 创建缓存索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_query_embedding 
                ON semantic_cache USING ivfflat (query_embedding vector_cosine_ops) 
                WITH (lists = 50)
            """)
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"创建扩展失败: {e}")

# 异步上下文管理器
@asynccontextmanager
async def get_async_db():
    """异步获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()