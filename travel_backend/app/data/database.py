"""数据库连接配置"""
from supabase import create_client, Client
from config import settings
from typing import Optional


class Database:
    """数据库单例类"""
    _instance: Optional['Database'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
    
    @property
    def client(self) -> Client:
        """获取 Supabase 客户端"""
        return self._client
    
    @property
    def service_client(self) -> Client:
        """获取 Supabase 服务端客户端（使用 service_key）"""
        return create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )


# 全局数据库实例
db = Database()


def get_db() -> Client:
    """依赖注入：获取数据库客户端"""
    return db.client


