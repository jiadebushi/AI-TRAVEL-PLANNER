# 脚本说明

## generate_maps_for_existing_trips.py

为已有行程生成静态地图的脚本。

### 功能

- 为指定行程或所有行程生成地图
- 自动跳过已有地图的行程
- 自动跳过没有有效坐标点的行程
- 显示详细的进度和统计信息

### 使用方法

#### 方式1：处理所有行程

```bash
python scripts/generate_maps_for_existing_trips.py
```

运行后会：
1. 自动获取数据库中所有行程
2. 询问是否继续
3. 为每个行程的每一天生成地图

#### 方式2：处理指定行程

```bash
python scripts/generate_maps_for_existing_trips.py <trip_id1> <trip_id2> <trip_id3> ...
```

例如：
```bash
python scripts/generate_maps_for_existing_trips.py 040faef8-69b9-4e05-8c6c-0e9e98d2efcd
```

### 输出说明

- `✓` 成功生成地图
- `⚠️` 跳过（已有地图或无坐标点）
- `✗` 生成失败

### 注意事项

1. 确保已配置 `.env` 文件中的 `AMAP_API_KEY`
2. 确保数据库连接正常
3. 脚本会自动跳过已有地图的行程，不会重复生成
4. 如果某天的活动没有有效坐标点，会跳过该天的地图生成

