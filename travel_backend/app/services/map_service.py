"""地图服务 - POI检索和路线规划"""
from config import settings
import httpx
from typing import List, Dict, Any, Optional
import json


class MapService:
    """地图服务类，支持高德和百度地图API"""
    
    def __init__(self):
        self.api_type = settings.map_api_type
        self.amap_key = settings.amap_api_key
        self.baidu_key = settings.baidu_api_key
    
    async def search_poi(self, destination: str, preference: str = "", 
                        keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        搜索POI（兴趣点）
        
        Args:
            destination: 目的地城市
            preference: 用户偏好描述
            keywords: 搜索关键词列表（如：["景点", "餐厅", "酒店"]）
        
        Returns:
            POI列表，每个POI包含：id, name, category, lat, lng, description
        """
        if keywords is None:
            keywords = ["景点", "餐厅", "酒店"]
        
        all_pois = []
        
        for keyword in keywords:
            if self.api_type == "amap":
                pois = await self._search_poi_amap(destination, keyword)
            else:
                pois = await self._search_poi_baidu(destination, keyword)
            all_pois.extend(pois)
        
        # 去重（基于名称和坐标）
        unique_pois = []
        seen = set()
        for poi in all_pois:
            key = (poi["name"], round(poi["lat"], 4), round(poi["lng"], 4))
            if key not in seen:
                seen.add(key)
                unique_pois.append(poi)
        
        return unique_pois
    
    async def _search_poi_amap(self, city: str, keyword: str) -> List[Dict[str, Any]]:
        """使用高德地图API搜索POI"""
        url = "https://restapi.amap.com/v3/place/text"
        params = {
            "key": self.amap_key,
            "keywords": keyword,
            "city": city,
            "output": "json",
            "offset": 20,  # 每页记录数
            "page": 1,
            "extensions": "all"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                pois = []
                if data.get("status") == "1" and data.get("pois"):
                    for idx, poi in enumerate(data["pois"], 1):
                        location = poi.get("location", "").split(",")
                        if len(location) == 2:
                            poi_id = f"P{idx:03d}"
                            # 处理 type 字段，可能是字符串或列表
                            poi_type = poi.get("type", "")
                            if isinstance(poi_type, list):
                                poi_type = ", ".join(poi_type)
                            poi_address = poi.get("address", "")
                            description = f"{poi_type} | {poi_address}" if poi_type else poi_address
                            
                            pois.append({
                                "id": poi_id,
                                "name": poi.get("name", ""),
                                "category": keyword,
                                "lat": float(location[1]),
                                "lng": float(location[0]),
                                "description": description
                            })
                return pois
        except Exception as e:
            print(f"高德地图POI搜索失败: {e}")
            return []
    
    async def _search_poi_baidu(self, city: str, keyword: str) -> List[Dict[str, Any]]:
        """使用百度地图API搜索POI"""
        url = "https://api.map.baidu.com/place/v2/search"
        params = {
            "ak": self.baidu_key,
            "query": keyword,
            "region": city,
            "output": "json",
            "page_size": 20
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                pois = []
                if data.get("status") == 0 and data.get("results"):
                    for idx, poi in enumerate(data["results"], 1):
                        location = poi.get("location", {})
                        if location:
                            poi_id = f"P{idx:03d}"
                            pois.append({
                                "id": poi_id,
                                "name": poi.get("name", ""),
                                "category": keyword,
                                "lat": location.get("lat", 0),
                                "lng": location.get("lng", 0),
                                "description": poi.get("detail_info", {}).get("tag", "")
                            })
                return pois
        except Exception as e:
            print(f"百度地图POI搜索失败: {e}")
            return []
    
    async def get_eta(self, point_a: Dict[str, float], point_b: Dict[str, float], 
                     mode: str = "driving") -> Dict[str, Any]:
        """
        获取两点间的预估耗时和距离
        
        Args:
            point_a: 起点 {"lat": float, "lng": float}
            point_b: 终点 {"lat": float, "lng": float}
            mode: 交通方式 driving/walking/transit
        
        Returns:
            {"duration_minutes": int, "distance_meters": int}
        """
        if self.api_type == "amap":
            return await self._get_eta_amap(point_a, point_b, mode)
        else:
            return await self._get_eta_baidu(point_a, point_b, mode)
    
    async def _get_eta_amap(self, point_a: Dict[str, float], point_b: Dict[str, float],
                           mode: str) -> Dict[str, Any]:
        """使用高德地图API获取路线规划"""
        # 根据交通方式选择不同的API端点
        mode_map = {
            "driving": "driving",
            "walking": "walking",
            "transit": "transit"
        }
        amap_mode = mode_map.get(mode, "driving")
        
        # 构建正确的API URL
        url = f"https://restapi.amap.com/v3/direction/{amap_mode}"
        
        origin = f"{point_a['lng']},{point_a['lat']}"
        destination = f"{point_b['lng']},{point_b['lat']}"
        
        params = {
            "key": self.amap_key,
            "origin": origin,
            "destination": destination,
            "output": "json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "1" and data.get("route"):
                    route = data["route"]
                    
                    # 根据不同交通方式，数据结构不同
                    if amap_mode == "transit":
                        # 公交路线：返回 transits 数组
                        transits = route.get("transits", [])
                        if not transits:
                            return {"duration_minutes": 0, "distance_meters": 0}
                        transit = transits[0]
                        duration_seconds = transit.get("duration", 0)
                        distance_meters = transit.get("distance", 0)
                    else:
                        # 步行和驾车：返回 paths 数组
                        paths = route.get("paths", [])
                        if not paths:
                            return {"duration_minutes": 0, "distance_meters": 0}
                        path = paths[0]
                        duration_seconds = path.get("duration", 0)
                        distance_meters = path.get("distance", 0)
                    
                    # 转换为数字（如果是字符串则先转浮点数再转整数）
                    try:
                        duration_seconds = float(duration_seconds) if duration_seconds else 0
                        distance_meters = float(distance_meters) if distance_meters else 0
                    except (ValueError, TypeError) as e:
                        print(f"高德地图路线规划数据转换失败: {e}, duration={duration_seconds}, distance={distance_meters}")
                        duration_seconds = 0
                        distance_meters = 0
                    
                    return {
                        "duration_minutes": int(duration_seconds / 60) if duration_seconds > 0 else 0,
                        "distance_meters": int(distance_meters) if distance_meters > 0 else 0
                    }
                else:
                    # API返回错误，记录详细信息
                    print(f"高德地图路线规划API返回错误: status={data.get('status')}, info={data.get('info', '')}")
                return {"duration_minutes": 0, "distance_meters": 0}
        except Exception as e:
            print(f"高德地图路线规划失败: {e}")
            return {"duration_minutes": 0, "distance_meters": 0}
    
    async def _get_eta_baidu(self, point_a: Dict[str, float], point_b: Dict[str, float],
                            mode: str) -> Dict[str, Any]:
        """使用百度地图API获取路线规划"""
        url = "https://api.map.baidu.com/direction/v2/driving"
        
        origin = f"{point_a['lat']},{point_a['lng']}"
        destination = f"{point_b['lat']},{point_b['lng']}"
        
        params = {
            "ak": self.baidu_key,
            "origin": origin,
            "destination": destination,
            "tactics": 11,  # 最短时间
            "output": "json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == 0 and data.get("result"):
                    route = data["result"]["routes"][0]
                    duration_seconds = route.get("duration", {}).get("value", 0)
                    distance_meters = route.get("distance", {}).get("value", 0)
                    
                    return {
                        "duration_minutes": int(duration_seconds / 60),
                        "distance_meters": int(distance_meters)
                    }
                return {"duration_minutes": 0, "distance_meters": 0}
        except Exception as e:
            print(f"百度地图路线规划失败: {e}")
            return {"duration_minutes": 0, "distance_meters": 0}
    
    async def generate_static_map(self, activities: List[Dict[str, Any]], 
                                 zoom: int = 13, size: str = "1024*1024") -> str:
        """
        生成静态地图图片（高德地图API）
        
        Args:
            activities: 活动列表，每个活动包含 latitude, longitude, poi_name 等字段
            zoom: 地图缩放级别 [1,17]，默认13
            size: 图片大小，格式 "宽度*高度"，最大1024*1024，默认 "1024*1024"
        
        Returns:
            静态地图图片的URL
        """
        if self.api_type != "amap":
            raise ValueError("静态地图功能仅支持高德地图API")
        
        if not self.amap_key:
            raise ValueError("高德地图API Key未配置")
        
        # 提取有经纬度的活动点
        points = []
        for activity in activities:
            lat = activity.get("latitude")
            lng = activity.get("longitude")
            if lat is not None and lng is not None:
                points.append({
                    "lng": lng,
                    "lat": lat,
                    "name": activity.get("poi_name", "")
                })
        
        if not points:
            raise ValueError("没有有效的坐标点")
        
        # 构建 markers 参数（标注点）- 使用large放大标记
        # 格式: markers=large,0xFF0000,A:lng1,lat1;lng2,lat2
        # 每个点使用不同的标签：A, B, C... Z
        marker_parts = []
        for idx, point in enumerate(points):
            # 使用字母标签：A, B, C... Z
            label = chr(65 + (idx % 26))  # A-Z循环
            marker_locations = f"{point['lng']},{point['lat']}"
            marker_parts.append(f"large,0xFF0000,{label}:{marker_locations}")
        
        markers = "|".join(marker_parts)  # 多个marker用|分隔
        
        # 构建 labels 参数（地点名称标签）- 除了abcd外标出地点名
        # 格式: labels=content,font,bold,fontSize,fontColor,background:location1;location2
        label_parts = []
        for point in points:
            # 只显示地点名，不显示abcd标签
            poi_name = point.get("name", "")
            if poi_name:
                # 限制标签内容长度（最大15个字符）
                label_content = poi_name[:15] if len(poi_name) <= 15 else poi_name[:12] + "..."
                # labels格式: content,font,bold,fontSize,fontColor,background
                # 使用较大字体(14)，白色字体，蓝色背景
                label_style = f"{label_content},0,1,14,0xFFFFFF,0x5288d8"
                label_location = f"{point['lng']},{point['lat']}"
                label_parts.append(f"{label_style}:{label_location}")
        
        labels = "|".join(label_parts) if label_parts else None
        
        # 构建 paths 参数（路径，连接各个点）- 线条宽度减小到1/3
        # 格式: paths=weight,color,transparency,,:lng1,lat1;lng2,lat2;lng3,lat3
        # weight从10减小到约3（10的1/3），但最小值为2，所以使用2
        path_locations = ";".join([f"{p['lng']},{p['lat']}" for p in points])
        paths = f"2,0x0000ff,1,,:{path_locations}"
        
        # 计算中心点（所有点的中心）
        center_lng = sum(p["lng"] for p in points) / len(points)
        center_lat = sum(p["lat"] for p in points) / len(points)
        location = f"{center_lng},{center_lat}"
        
        # 构建请求URL
        url = "https://restapi.amap.com/v3/staticmap"
        params = {
            "key": self.amap_key,
            "location": location,
            "zoom": zoom,
            "size": size,
            "markers": markers,
            "paths": paths
        }
        
        # 如果有labels，添加到参数中
        if labels:
            params["labels"] = labels
        
        # 高德静态地图API直接返回图片URL，可以直接使用
        # 构建完整的URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        map_url = f"{url}?{query_string}"
        
        return map_url


# 全局地图服务实例
map_service = MapService()


