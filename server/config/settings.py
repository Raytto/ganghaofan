from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # 数据库配置
    database_url: str = "duckdb://./server/data/ganghaofan.duckdb"
    
    # JWT配置
    jwt_secret_key: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24 * 7  # 7天
    
    # 微信小程序配置
    wechat_app_id: Optional[str] = None
    wechat_app_secret: Optional[str] = None
    
    # API配置
    api_title: str = "罡好饭 API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # 开发模式
    debug: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 全局设置实例
settings = Settings()