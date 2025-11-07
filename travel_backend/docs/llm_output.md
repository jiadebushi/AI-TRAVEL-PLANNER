### 2. 期望的 JSON 输出结构 (`/generate_itinerary` API 输出)

这是后端程序从 LLM API 接收后，可以直接解析并存入数据库的结构。

```json
{
  "trip_name": "五天东京亲子美食动漫之旅",
  "daily_plans": [
    {
      "day": 1,
      "theme": "动漫与美食初体验",
      "activities": [
        {
          "poi_id": "P001",
          "poi_name": "秋叶原",
          "estimated_time_slot": "9:30 - 12:30",
          "notes": "重点参观电器街和动漫周边店，为孩子购买小礼物。",
          "transport_to_next": {
            "mode": "地铁",
            "recommendation": "乘坐JR山手线（外环）到有乐町，转日比谷线至筑地。效率最高。",
            "next_poi_id": "P002"
          }
        },
        {
          "poi_id": "P002",
          "poi_name": "筑地场外市场",
          "estimated_time_slot": "13:30 - 15:00 (午餐)",
          "notes": "品尝新鲜的海鲜丼和玉子烧。",
          "transport_to_next": {
            "mode": "步行",
            "recommendation": "前往附近的酒店办理入住，步行即可到达。",
            "next_poi_id": "H001" // 假设 H001 是酒店
          }
        }
      ]
    },
    {
      "day": 2,
      "theme": "迪士尼亲子欢乐日",
      "activities": [
        // ... Day 2 activities
      ]
    }
  ]
}