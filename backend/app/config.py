from decouple import config
from pydantic import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    APP_NAME: str = "MiniRAG"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = config("DEBUG", default=False, cast=bool)
    
    # 数据库配置
    DB_HOST: str = config("DB_HOST", default="localhost")
    DB_PORT: int = config("DB_PORT", default=5432, cast=int)
    DB_NAME: str = config("DB_NAME", default="rag_db")
    DB_USER: str = config("DB_USER", default="postgres")
    DB_PASSWORD: str = config("DB_PASSWORD", default="postgres")
    
    @property
    def DATABASE_URL(self) -> str:
        """数据库连接URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # LLM配置
    LLM_PROVIDER: str = config("LLM_PROVIDER", default="openai")
    LLM_API_KEY: str = config("LLM_API_KEY", default="")
    LLM_MODEL: str = config("LLM_MODEL", default="gpt-3.5-turbo")
    LLM_BASE_URL: Optional[str] = config("LLM_BASE_URL", default=None)
    
    # Embedding配置
    EMBEDDING_MODEL: str = config("EMBEDDING_MODEL", default="text-embedding-ada-002")
    EMBEDDING_DIM: int = config("EMBEDDING_DIM", default=1536, cast=int)
    
    # Rerank配置
    RERANK_MODEL: str = config("RERANK_MODEL", default="")
    RERANK_ENABLED: bool = config("RERANK_ENABLED", default=False, cast=bool)
    
    # 检索配置
    TOP_K: int = config("TOP_K", default=5, cast=int)
    SIMILARITY_THRESHOLD: float = config("SIMILARITY_THRESHOLD", default=0.7, cast=float)
    
    # 缓存配置
    ENABLE_SEMANTIC_CACHE: bool = config("ENABLE_SEMANTIC_CACHE", default=True, cast=bool)
    CACHE_SIMILARITY_THRESHOLD: float = config("CACHE_SIMILARITY_THRESHOLD", default=0.85, cast=float)
    CACHE_TTL_DAYS: int = config("CACHE_TTL_DAYS", default=7, cast=int)
    
    # 文档处理配置
    CHUNK_SIZE: int = config("CHUNK_SIZE", default=512, cast=int)
    CHUNK_OVERLAP: int = config("CHUNK_OVERLAP", default=50, cast=int)
    SUPPORTED_FORMATS: List[str] = config("SUPPORTED_FORMATS", default=["md", "txt", "html"], cast=lambda x: x.split(","))
    
    # Redis配置（可选）
    REDIS_HOST: str = config("REDIS_HOST", default="localhost")
    REDIS_PORT: int = config("REDIS_PORT", default=6379, cast=int)
    REDIS_PASSWORD: Optional[str] = config("REDIS_PASSWORD", default=None)
    REDIS_DB: int = config("REDIS_DB", default=0, cast=int)
    
    # 文件上传配置
    UPLOAD_DIR: str = config("UPLOAD_DIR", default="/app/uploads")
    MAX_FILE_SIZE: int = config("MAX_FILE_SIZE", default=10 * 1024 * 1024, cast=int)  # 10MB
    
    # 日志配置
    LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
    LOG_FORMAT: str = config("LOG_FORMAT", default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 创建全局配置实例
settings = Settings()

# 验证配置
def validate_settings():
    """验证配置"""
    errors = []
    
    if not settings.LLM_API_KEY:
        errors.append("LLM_API_KEY is required")
    
    if settings.TOP_K <= 0:
        errors.append("TOP_K must be greater than 0")
    
    if not 0 < settings.SIMILARITY_THRESHOLD <= 1:
        errors.append("SIMILARITY_THRESHOLD must be between 0 and 1")
    
    if not 0 < settings.CACHE_SIMILARITY_THRESHOLD <= 1:
        errors.append("CACHE_SIMILARITY_THRESHOLD must be between 0 and 1")
    
    if settings.CHUNK_SIZE <= 0:
        errors.append("CHUNK_SIZE must be greater than 0")
    
    if settings.CHUNK_OVERLAP < 0:
        errors.append("CHUNK_OVERLAP must be non-negative")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

# 验证配置
try:
    validate_settings()
except ValueError as e:
    print(f"Configuration error: {e}")
    raise