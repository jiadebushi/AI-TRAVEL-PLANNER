"""
为已有行程生成地图的脚本
使用方法: python scripts/generate_maps_for_existing_trips.py
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.data.database import get_db
from app.data.trip_repository import get_trip_repository
from app.data.map_repository import get_map_repository
from app.services.map_service import map_service


async def generate_maps_for_trip(trip_id: str, trip_name: str):
    """为单个行程生成所有天的地图"""
    trip_repo = get_trip_repository()
    map_repo = get_map_repository()
    
    # 获取该行程的所有详情
    trip_details = trip_repo.get_trip_details_by_trip_id(trip_id)
    
    if not trip_details:
        print(f"  ⚠️  行程 {trip_name} (ID: {trip_id}) 没有行程详情，跳过")
        return 0
    
    generated_count = 0
    skipped_count = 0
    error_count = 0
    
    for detail in trip_details:
        day_number = detail.day_number
        activities = detail.activities if isinstance(detail.activities, list) else []
        
        # 检查是否已有地图
        existing_map = map_repo.get_map_by_trip_and_day(trip_id, day_number)
        if existing_map:
            print(f"  ✓ 第{day_number}天已有地图，跳过")
            skipped_count += 1
            continue
        
        # 过滤出有经纬度的活动
        valid_activities = [
            act for act in activities 
            if isinstance(act, dict) and act.get("latitude") is not None and act.get("longitude") is not None
        ]
        
        if not valid_activities:
            print(f"  ⚠️  第{day_number}天没有有效的坐标点，跳过")
            skipped_count += 1
            continue
        
        try:
            # 生成静态地图URL（使用最大尺寸1024*1024）
            map_url = await map_service.generate_static_map(
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
            
            print(f"  ✓ 第{day_number}天地图生成成功")
            generated_count += 1
            
        except Exception as e:
            print(f"  ✗ 第{day_number}天地图生成失败: {str(e)}")
            error_count += 1
            continue
    
    return {
        "generated": generated_count,
        "skipped": skipped_count,
        "errors": error_count
    }


async def main():
    """主函数：为所有已有行程生成地图"""
    print("=" * 60)
    print("开始为已有行程生成地图")
    print("=" * 60)
    
    trip_repo = get_trip_repository()
    
    # 获取所有行程或指定行程
    import sys
    
    if len(sys.argv) > 1:
        # 从命令行参数获取trip_id列表
        trip_ids = sys.argv[1:]
        print(f"\n将处理 {len(trip_ids)} 个指定行程")
    else:
        # 获取所有行程
        print("\n正在获取所有行程...")
        try:
            # 直接查询所有trip_headers
            db = get_db()
            result = db.table("trip_headers").select("trip_id, trip_name").execute()
            
            if not result.data:
                print("⚠️  数据库中没有行程，退出")
                return
            
            trip_ids = [trip["trip_id"] for trip in result.data]
            print(f"找到 {len(trip_ids)} 个行程")
            
            # 询问是否继续
            print("\n是否要为所有行程生成地图？(y/n): ", end="")
            confirm = input().strip().lower()
            if confirm != 'y' and confirm != 'yes':
                print("已取消")
                return
        except Exception as e:
            print(f"✗ 获取行程列表失败: {str(e)}")
            print("\n请使用命令行参数指定行程ID:")
            print("python scripts/generate_maps_for_existing_trips.py <trip_id1> <trip_id2> ...")
            return
    
    total_stats = {
        "generated": 0,
        "skipped": 0,
        "errors": 0
    }
    
    for idx, trip_id in enumerate(trip_ids, 1):
        trip = trip_repo.get_trip_by_id(trip_id)
        if not trip:
            print(f"\n[{idx}/{len(trip_ids)}] ✗ 行程 {trip_id} 不存在，跳过")
            continue
        
        print(f"\n[{idx}/{len(trip_ids)}] 处理行程: {trip.trip_name} (ID: {trip_id})")
        print("-" * 60)
        
        stats = await generate_maps_for_trip(trip_id, trip.trip_name)
        total_stats["generated"] += stats["generated"]
        total_stats["skipped"] += stats["skipped"]
        total_stats["errors"] += stats["errors"]
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("地图生成完成！")
    print("=" * 60)
    print(f"总计:")
    print(f"  ✓ 成功生成: {total_stats['generated']} 张")
    print(f"  ⊘ 跳过（已有地图或无坐标）: {total_stats['skipped']} 张")
    print(f"  ✗ 失败: {total_stats['errors']} 张")
    print("=" * 60)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())

