from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
import asyncio
from typing import Generator

from app.config import settings
from app.models import Base

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

    # pgvector 类型必须先注册，ORM 才能创建 vector 列。
    await create_base_extensions()
    
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
                conn.exec_driver_sql("SELECT 1")
                break
        except Exception:
            retry_count += 1
            await asyncio.sleep(2)
    
    if retry_count == max_retries:
        raise Exception("数据库连接超时")

async def create_base_extensions():
    """创建建表前必须存在的PostgreSQL扩展"""
    with engine.connect() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS bm25")
        conn.commit()

async def create_extensions():
    """创建PostgreSQL扩展"""
    with engine.connect() as conn:
        try:
            # 创建向量扩展
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            
            # 创建BM25扩展
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS bm25")
            conn.commit()

            # 兼容旧库：历史版本把向量写入 JSON 字段，新版本统一为 pgvector。
            conn.exec_driver_sql(f"""
                ALTER TABLE chunks
                ALTER COLUMN embedding TYPE vector({settings.EMBEDDING_DIM})
                USING trim(both '"' from embedding::text)::vector
            """)

            conn.exec_driver_sql(f"""
                ALTER TABLE semantic_cache
                ALTER COLUMN query_embedding TYPE vector({settings.EMBEDDING_DIM})
                USING trim(both '"' from query_embedding::text)::vector
            """)
            
            # 创建向量索引
            conn.exec_driver_sql("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
                ON chunks USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = 100)
            """)
            
            # 创建BM25索引
            conn.exec_driver_sql("""
                CREATE INDEX IF NOT EXISTS idx_chunks_content_bm25 
                ON chunks USING bm25 (content_text)
            """)
            
            # 创建缓存索引
            conn.exec_driver_sql("""
                CREATE INDEX IF NOT EXISTS idx_cache_query_embedding 
                ON semantic_cache USING ivfflat (query_embedding vector_cosine_ops) 
                WITH (lists = 50)
            """)

            # 兼容旧库：缓存源引用用于语义缓存命中后返回来源
            conn.exec_driver_sql("""
                ALTER TABLE semantic_cache
                ADD COLUMN IF NOT EXISTS source_chunk_ids JSON
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
