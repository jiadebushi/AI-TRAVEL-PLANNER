"""行程数据访问层"""
from supabase import Client
from app.models.db_models import TripHeader, TripDetail
from app.data.database import get_db
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime


class TripRepository:
    """行程数据仓库"""
    
    def __init__(self, db: Client):
        self.db = db
    
    def create_trip_header(self, user_id: str, trip_name: str, destination: str,
                          start_date: str, end_date: str, status: str = "draft") -> TripHeader:
        """创建行程头"""
        # Supabase使用UUID，但在Python中可以用字符串形式
        trip_id = str(uuid.uuid4())
        
        data = {
            "trip_id": trip_id,
            "user_id": user_id,
            "trip_name": trip_name,
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = self.db.table("trip_headers").insert(data).execute()
        if result.data:
            return TripHeader(**result.data[0])
        raise Exception("创建行程失败")
    
    def save_trip_details(self, trip_id: str, daily_plans: List[Dict[str, Any]]) -> List[TripDetail]:
        """保存行程详情"""
        details = []
        for plan in daily_plans:
            detail_id = str(uuid.uuid4())
            data = {
                "detail_id": detail_id,
                "trip_id": trip_id,
                "day_number": plan["day"],
                "theme": plan["theme"],
                "hotel_recommendation": plan.get("hotel_recommendation"),
                "activities": plan.get("activities", []),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            result = self.db.table("trip_details").insert(data).execute()
            if result.data:
                details.append(TripDetail(**result.data[0]))
        return details
    
    def get_trip_by_id(self, trip_id: str) -> Optional[TripHeader]:
        """获取行程头"""
        result = self.db.table("trip_headers").select("*").eq("trip_id", trip_id).execute()
        if result.data and len(result.data) > 0:
            return TripHeader(**result.data[0])
        return None
    
    def get_trip_details_by_trip_id(self, trip_id: str) -> List[TripDetail]:
        """获取行程详情列表"""
        result = self.db.table("trip_details").select("*").eq("trip_id", trip_id).order("day_number").execute()
        if result.data:
            return [TripDetail(**item) for item in result.data]
        return []
    
    def get_trip_detail_by_day(self, trip_id: str, day_number: int) -> Optional[TripDetail]:
        """获取指定行程指定天的详情"""
        result = self.db.table("trip_details").select("*").eq("trip_id", trip_id).eq("day_number", day_number).execute()
        if result.data and len(result.data) > 0:
            return TripDetail(**result.data[0])
        return None
    
    def get_trips_by_user_id(self, user_id: str) -> List[TripHeader]:
        """获取用户的所有行程"""
        result = self.db.table("trip_headers").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        if result.data:
            return [TripHeader(**item) for item in result.data]
        return []
    
    def update_trip_header(self, trip_id: str, **kwargs) -> bool:
        """更新行程头"""
        kwargs["updated_at"] = datetime.now().isoformat()
        result = self.db.table("trip_headers").update(kwargs).eq("trip_id", trip_id).execute()
        return result.data is not None and len(result.data) > 0
    
    def delete_trip(self, trip_id: str) -> bool:
        """删除行程（级联删除详情）"""
        # 先删除详情
        self.db.table("trip_details").delete().eq("trip_id", trip_id).execute()
        # 再删除头
        result = self.db.table("trip_headers").delete().eq("trip_id", trip_id).execute()
        return result.data is not None


def get_trip_repository(db: Client = None) -> TripRepository:
    """获取行程仓库实例"""
    if db is None:
        db = get_db()
    return TripRepository(db)

