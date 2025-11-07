"""地图数据访问层"""
from supabase import Client
from app.models.db_models import TripMap
from app.data.database import get_db
from typing import List, Optional
import uuid
from datetime import datetime


class MapRepository:
    """地图数据仓库"""
    
    def __init__(self, db: Client):
        self.db = db
    
    def save_map(self, trip_id: str, day_number: int, map_url: str) -> TripMap:
        """保存地图图片URL（如果已存在则更新）"""
        # 先检查是否已存在
        existing = self.get_map_by_trip_and_day(trip_id, day_number)
        
        if existing:
            # 更新现有地图
            data = {
                "map_url": map_url,
                "updated_at": datetime.now().isoformat()
            }
            result = self.db.table("trip_maps").update(data).eq("map_id", existing.map_id).execute()
            if result.data:
                return TripMap(**result.data[0])
        else:
            # 创建新地图
            map_id = str(uuid.uuid4())
            data = {
                "map_id": map_id,
                "trip_id": trip_id,
                "day_number": day_number,
                "map_url": map_url,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            result = self.db.table("trip_maps").insert(data).execute()
            if result.data:
                return TripMap(**result.data[0])
        
        raise Exception("保存地图失败")
    
    def get_map_by_trip_and_day(self, trip_id: str, day_number: int) -> Optional[TripMap]:
        """获取指定行程指定天的地图"""
        result = self.db.table("trip_maps").select("*").eq("trip_id", trip_id).eq("day_number", day_number).execute()
        if result.data and len(result.data) > 0:
            return TripMap(**result.data[0])
        return None
    
    def get_maps_by_trip_id(self, trip_id: str) -> List[TripMap]:
        """获取指定行程的所有地图"""
        result = self.db.table("trip_maps").select("*").eq("trip_id", trip_id).order("day_number").execute()
        if result.data:
            return [TripMap(**item) for item in result.data]
        return []


def get_map_repository(db: Client = None) -> MapRepository:
    """获取地图仓库实例"""
    if db is None:
        db = get_db()
    return MapRepository(db)

