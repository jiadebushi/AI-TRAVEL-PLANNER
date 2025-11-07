"""
重新生成指定行程的所有地图并替换数据库内容
使用方法: python scripts/regenerate_trip_maps.py <trip_id>
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


async def regenerate_trip_maps(trip_id: str):
    """重新生成指定行程的所有地图并替换数据库内容"""
    trip_repo = get_trip_repository()
    map_repo = get_map_repository()
    
    # 获取行程信息
    trip = trip_repo.get_trip_by_id(trip_id)
    if not trip:
        print(f"✗ 行程 {trip_id} 不存在")
        return False
    
    print(f"行程名称: {trip.trip_name}")
    print(f"目的地: {trip.destination}")
    print(f"行程日期: {trip.start_date} 至 {trip.end_date}")
    print("-" * 60)
    
    # 获取该行程的所有详情
    trip_details = trip_repo.get_trip_details_by_trip_id(trip_id)
    
    if not trip_details:
        print("⚠️  该行程没有行程详情，无法生成地图")
        return False
    
    print(f"找到 {len(trip_details)} 天的行程详情\n")
    
    generated_count = 0
    skipped_count = 0
    error_count = 0
    
    for detail in trip_details:
        day_number = detail.day_number
        activities = detail.activities if isinstance(detail.activities, list) else []
        
        print(f"处理第 {day_number} 天...")
        
        # 过滤出有经纬度的活动
        valid_activities = [
            act for act in activities 
            if isinstance(act, dict) and act.get("latitude") is not None and act.get("longitude") is not None
        ]
        
        if not valid_activities:
            print(f"  ⚠️  第{day_number}天没有有效的坐标点，跳过")
            skipped_count += 1
            continue
        
        print(f"  ✓ 找到 {len(valid_activities)} 个有效坐标点")
        
        try:
            # 生成静态地图URL（使用最大尺寸1024*1024）
            map_url = await map_service.generate_static_map(
                activities=valid_activities,
                zoom=13,
                size="1024*1024"
            )
            
            # 保存或更新地图URL到数据库（会自动替换已有内容）
            map_repo.save_map(
                trip_id=trip_id,
                day_number=day_number,
                map_url=map_url
            )
            
            print(f"  ✓ 第{day_number}天地图生成并保存成功")
            print(f"    地图URL: {map_url[:80]}...")
            generated_count += 1
            
        except Exception as e:
            print(f"  ✗ 第{day_number}天地图生成失败: {str(e)}")
            error_count += 1
            continue
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("地图重新生成完成！")
    print("=" * 60)
    print(f"总计:")
    print(f"  ✓ 成功生成并替换: {generated_count} 张")
    print(f"  ⊘ 跳过（无坐标点）: {skipped_count} 张")
    print(f"  ✗ 失败: {error_count} 张")
    print("=" * 60)
    
    return generated_count > 0


async def main():
    """主函数"""
    print("=" * 60)
    print("重新生成行程地图（替换数据库内容）")
    print("=" * 60)
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python scripts/regenerate_trip_maps.py <trip_id>")
        print("\n示例:")
        print("  python scripts/regenerate_trip_maps.py 5b41a958-3f23-4a64-8835-d1cb40e567be")
        return
    
    trip_id = sys.argv[1].strip()
    
    print(f"\n行程ID: {trip_id}")
    print("-" * 60)
    
    success = await regenerate_trip_maps(trip_id)
    
    if success:
        print("\n✓ 地图重新生成完成！")
    else:
        print("\n✗ 地图重新生成失败或没有可生成的地图")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())

