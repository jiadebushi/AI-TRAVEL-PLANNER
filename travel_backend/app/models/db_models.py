"""数据库 ORM 模型定义"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class User(BaseModel):
    """用户模型"""
    user_id: str
    email: str
    hashed_password: Optional[str] = None  # 存储时不返回
    preferences: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TripHeader(BaseModel):
    """行程概要"""
    trip_id: str
    user_id: str
    trip_name: str
    destination: str
    start_date: str  # ISO format
    end_date: str  # ISO format
    status: str = "draft"  # draft, generated, active, completed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TripDetail(BaseModel):
    """详细行程（每日）"""
    detail_id: str
    trip_id: str
    day_number: int
    theme: str
    hotel_recommendation: Optional[Dict[str, Any]] = None
    activities: List[Dict[str, Any]]  # JSON 格式存储活动列表
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Budget(BaseModel):
    """预算估算"""
    budget_id: str
    trip_id: str
    user_budget: float  # 用户准备的预算
    estimated_total: float  # LLM估算的总预算
    categories: List[Dict[str, Any]]  # JSON 格式存储类别细分
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Expense(BaseModel):
    """实际开销"""
    expense_id: str
    trip_id: str
    category: str
    amount: float
    currency: str = "CNY"
    description: str
    timestamp: datetime
    created_at: Optional[datetime] = None


class TripMap(BaseModel):
    """行程地图"""
    map_id: str
    trip_id: str
    day_number: int
    map_url: str  # 高德静态地图API返回的图片URL
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


