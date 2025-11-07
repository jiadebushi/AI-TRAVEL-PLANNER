"""行程规划主服务"""
from app.services.ai_service import ai_service
from app.services.map_service import map_service
from app.services.voice_service import voice_service
from app.data.trip_repository import get_trip_repository, TripRepository
from app.data.expense_repository import get_expense_repository, ExpenseRepository
from app.data.map_repository import get_map_repository, MapRepository
from app.models.llm_models import ItineraryResponse
from app.models.api_models import TripInput
from typing import Dict, Any, List
import json


class TripService:
    """行程规划服务"""
    
    def __init__(self):
        self.ai_service = ai_service
        self.map_service = map_service
        self.voice_service = voice_service
    
    async def process_voice_input(self, user_id: str, audio_file_path: str) -> str:
        """
        处理语音输入的主流程
        1. 语音转文本（科大讯飞）
        2. LLM意图解析
        3. 调用生成完整行程
        
        Returns:
            trip_id: 创建的行程ID
        """
        # 1. 语音转文本
        text = await self.voice_service.transcribe_audio_file(audio_file_path)
        
        # 2. LLM意图解析
        user_intent = await self.ai_service.parse_user_intent(text)
        
        # 3. 转换为TripInput格式并生成行程
        trip_input = TripInput(
            destination=user_intent.destination,
            start_date=user_intent.start_date,
            end_date=user_intent.end_date,
            budget_cny=user_intent.budget_cny,
            people=user_intent.people,
            preferences=user_intent.preferences
        )
        
        # 4. 生成完整行程
        trip_id = await self.generate_full_itinerary(user_id, trip_input)
        return trip_id
    
    async def generate_full_itinerary(self, user_id: str, trip_input: TripInput) -> str:
        """
        生成完整行程的主流程（3.1-3.4）
        1. 地图API（POI检索）
        2. LLM（行程决策）
        3. 地图API（耗时预估）
        4. 存储TripHeader和TripDetail
        5. 估算预算
        
        Returns:
            trip_id: 创建的行程ID
        """
        trip_repo = get_trip_repository()
        expense_repo = get_expense_repository()
        
        # 1. POI检索
        # 基础关键词 + 通过LLM从用户偏好中提取的关键词
        keywords = ["景点", "餐厅", "连锁酒店"]
        if trip_input.preferences:
            try:
                extracted = await self.ai_service.extract_poi_keywords(trip_input.preferences)
                if extracted:
                    keywords.extend(extracted)
            except Exception:
                pass
        # 去重，保持顺序
        seen_keys = set()
        deduped = []
        for k in keywords:
            if k and k not in seen_keys:
                seen_keys.add(k)
                deduped.append(k)
        keywords = deduped
        
        poi_list = await self.map_service.search_poi(
            destination=trip_input.destination,
            preference=trip_input.preferences or "",
            keywords=keywords
        )
        
        # 2. LLM决策行程和交通方式
        user_data = {
            "destination": trip_input.destination,
            "start_date": trip_input.start_date.isoformat(),
            "end_date": trip_input.end_date.isoformat(),
            "budget_cny": trip_input.budget_cny,
            "people": trip_input.people,
            "preferences": trip_input.preferences or ""
        }
        
        itinerary: ItineraryResponse = await self.ai_service.llm_plan_decision(
            user_data=user_data,
            poi_list=poi_list
        )
        
        # 3. 获取交通耗时预估并更新activities
        daily_plans_dict = []
        for daily_plan in itinerary.daily_plans:
            activities_list = []
            for idx, activity in enumerate(daily_plan.activities):
                activity_dict = activity.dict()
                # 过滤掉无效占位活动：关键字段均为 None/空
                if (
                    (activity_dict.get("poi_id") is None)
                    and (activity_dict.get("poi_name") in (None, ""))
                    and (activity_dict.get("estimated_time_slot") in (None, ""))
                    and (activity_dict.get("transport_to_next") in (None, {}))
                ):
                    continue
                
                # 如果有下一个POI，获取耗时
                if activity.transport_to_next and activity.transport_to_next.next_poi_id:
                    # 找到下一个POI的坐标
                    next_poi = next(
                        (p for p in poi_list if p["id"] == activity.transport_to_next.next_poi_id),
                        None
                    )
                    # 需要当前与下一个都有坐标
                    if next_poi and activity.latitude is not None and activity.longitude is not None \
                       and next_poi.get("lat") is not None and next_poi.get("lng") is not None:
                        eta = await self.map_service.get_eta(
                            point_a={"lat": activity.latitude, "lng": activity.longitude},
                            point_b={"lat": next_poi["lat"], "lng": next_poi["lng"]},
                            mode=self._map_transport_mode(activity.transport_to_next.mode)
                        )
                        activity_dict["estimated_duration_minutes"] = eta["duration_minutes"]
                        if activity.transport_to_next:
                            activity_dict["transport_to_next"]["estimated_minutes"] = eta["duration_minutes"]
                
                activities_list.append(activity_dict)
            
            daily_plans_dict.append({
                "day": daily_plan.day,
                "theme": daily_plan.theme,
                "hotel_recommendation": daily_plan.hotel_recommendation,
                "activities": activities_list
            })
        
        # 4. 存储TripHeader
        trip_header = trip_repo.create_trip_header(
            user_id=user_id,
            trip_name=itinerary.trip_name,
            destination=trip_input.destination,
            start_date=trip_input.start_date.isoformat(),
            end_date=trip_input.end_date.isoformat(),
            status="generated"
        )
        
        # 5. 存储TripDetail
        trip_repo.save_trip_details(trip_header.trip_id, daily_plans_dict)
        
        # 6. 估算预算
        trip_details_for_budget = {
            "trip_name": itinerary.trip_name,
            "daily_plans": daily_plans_dict
        }
        user_budget = trip_input.budget_cny
        budget = await self.ai_service.estimate_budget(trip_details_for_budget, user_data, user_budget)
        budget.trip_id = trip_header.trip_id
        
        # 将BudgetCategory转换为字典列表
        categories_list = [cat.dict() for cat in budget.categories]
        expense_repo.create_budget(
            trip_id=budget.trip_id,
            user_budget=user_budget,
            estimated_total=budget.estimated_total_cny,
            categories=categories_list
        )
        
        # 7. 为每一天生成静态地图
        await self._generate_daily_maps(trip_header.trip_id, daily_plans_dict)
        
        return trip_header.trip_id
    
    async def _generate_daily_maps(self, trip_id: str, daily_plans: List[Dict[str, Any]]):
        """为每一天生成静态地图并保存"""
        map_repo = get_map_repository()
        
        for daily_plan in daily_plans:
            day_number = daily_plan["day"]
            activities = daily_plan.get("activities", [])
            
            # 过滤出有经纬度的活动
            valid_activities = [
                act for act in activities 
                if act.get("latitude") is not None and act.get("longitude") is not None
            ]
            
            if not valid_activities:
                # 如果没有有效坐标点，跳过该天的地图生成
                continue
            
            try:
                # 生成静态地图URL（使用最大尺寸1024*1024）
                map_url = await self.map_service.generate_static_map(
                    activities=valid_activities,
                    zoom=13,
                    size="1024*1024"
                )
                
                # 保存地图URL到数据库
                map_repo.save_map(
                    trip_id=trip_id,
                    day_number=day_number,
                    map_url=map_url
                )
            except Exception as e:
                # 地图生成失败不影响整体流程，只记录错误
                print(f"生成第{day_number}天地图失败: {e}")
                continue
    
    def _map_transport_mode(self, mode: str) -> str:
        """将中文交通方式转换为API所需的格式"""
        mode_map = {
            "步行": "walking",
            "地铁": "transit",
            "公交": "transit",
            "打车": "driving",
            "私家车": "driving",
            "开车": "driving"
        }
        return mode_map.get(mode, "driving")
    
    async def get_trip_details(self, trip_id: str) -> Dict[str, Any]:
        """获取行程详情"""
        trip_repo = get_trip_repository()
        expense_repo = get_expense_repository()
        map_repo = get_map_repository()
        
        trip_header = trip_repo.get_trip_by_id(trip_id)
        if not trip_header:
            raise ValueError(f"行程不存在: {trip_id}")
        
        trip_details = trip_repo.get_trip_details_by_trip_id(trip_id)
        budget = expense_repo.get_budget_by_trip_id(trip_id)
        
        # 获取所有地图
        trip_maps = map_repo.get_maps_by_trip_id(trip_id)
        # 构建 day_number -> map_url 的映射
        map_dict = {map_obj.day_number: map_obj.map_url for map_obj in trip_maps}
        
        # 为每个trip_detail添加map_url
        trip_details_dict = []
        for detail in trip_details:
            detail_dict = detail.dict()
            detail_dict["map_url"] = map_dict.get(detail.day_number)  # 如果没有地图则为None
            trip_details_dict.append(detail_dict)
        
        return {
            "trip_header": trip_header.dict(),
            "trip_details": trip_details_dict,
            "budget": budget.dict() if budget else None
        }
    
    async def get_trip_list(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的行程列表"""
        trip_repo = get_trip_repository()
        trips = trip_repo.get_trips_by_user_id(user_id)
        return [trip.dict() for trip in trips]
    
    async def update_trip(self, trip_id: str, updates: Dict[str, Any]) -> bool:
        """更新行程"""
        trip_repo = get_trip_repository()
        return trip_repo.update_trip_header(trip_id, **updates)


# 全局行程服务实例
trip_service = TripService()

