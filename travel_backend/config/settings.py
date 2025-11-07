from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """应用配置类，从 .env 文件加载配置"""
    
    # LLM 配置（千问/通义千问）
    qianwen_api_key: str
    qianwen_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 科大讯飞 API 配置（标准版）
    xunfei_app_id: str = ""
    xunfei_api_key: str = ""
    xunfei_api_secret: str = ""
    
    # 科大讯飞大模型 API 配置
    xunfei_llm_app_id: str = ""
    xunfei_llm_access_key_id: str = ""
    xunfei_llm_access_key_secret: str = ""
    
    # 地图 API 配置
    map_api_type: Literal["amap", "baidu"] = "amap"
    amap_api_key: str = ""
    baidu_api_key: str = ""
    
    # Supabase 配置
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""
    
    # JWT 配置
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis 配置（可选）
    redis_url: str = "redis://localhost:6379/0"
    
    # 应用配置
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()


