"""LLM 输出数据结构（严格对应 LLM 的 JSON 输出）"""
from pydantic import BaseModel
from typing import List, Optional


class TransportSegment(BaseModel):
    """交通方式段"""
    mode: Optional[str] = None  # 交通方式: "地铁", "步行", "打车", "公交"
    recommendation: Optional[str] = None  # LLM推荐理由
    next_poi_id: Optional[str] = None  # 下一个POI的ID


class Activity(BaseModel):
    """活动项"""
    poi_id: Optional[str] = None
    poi_name: Optional[str] = None
    activity_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    estimated_time_slot: Optional[str] = None  # e.g., "9:30 - 12:30"
    estimated_duration_minutes: Optional[int] = 0  # 来自地图 API 3.3
    notes: Optional[str] = ""
    transport_to_next: Optional[TransportSegment] = None


class DailyPlan(BaseModel):
    """每日行程计划"""
    day: int
    theme: str
    hotel_recommendation: Optional[dict] = None
    activities: List[Activity]


class ItineraryResponse(BaseModel):
    """完整的行程响应（LLM生成的）"""
    trip_name: str
    daily_plans: List[DailyPlan]


class BudgetCategory(BaseModel):
    """预算类别"""
    name: str  # "住宿", "餐饮", "交通", "门票", "购物", "其他"
    estimated_cny: float


class TripBudget(BaseModel):
    """行程预算"""
    trip_id: str
    estimated_total_cny: float
    categories: List[BudgetCategory]


class UserIntent(BaseModel):
    """用户意图解析结果"""
    destination: str
    start_date: str  # ISO format string
    end_date: str  # ISO format string
    budget_cny: float
    people: str
    preferences: str


