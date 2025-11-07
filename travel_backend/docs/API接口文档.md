# AI智能旅行规划后端 API 接口文档

## 目录
- [基础说明](#基础说明)
- [认证相关接口](#认证相关接口)
- [用户资料接口](#用户资料接口)
- [行程规划接口](#行程规划接口)
- [费用管理接口](#费用管理接口)
- [错误码说明](#错误码说明)

---

## 基础说明

### 基础URL
```
http://localhost:8000
```

### 认证方式
大部分接口需要 JWT Token 认证，在请求头中添加：
```
Authorization: Bearer <access_token>
```

### 请求格式
- **Content-Type**: `application/json` (JSON请求)
- **Content-Type**: `application/x-www-form-urlencoded` (表单请求，如登录)
- **Content-Type**: `multipart/form-data` (文件上传)

### 响应格式
所有接口返回 JSON 格式数据。

---

## 认证相关接口

### 1. 用户注册

**接口**: `POST /api/v1/auth/register`

**说明**: 注册新用户账号

**请求头**: 无需认证

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "preferences": "喜欢美食和动漫"  // 可选
}
```

**响应示例** (200 OK):
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "preferences": "喜欢美食和动漫"
}
```

**错误响应**:
- `400 Bad Request`: 邮箱已被注册
  ```json
  {
    "detail": "邮箱已被注册"
  }
  ```

---

### 2. 用户登录

**接口**: `POST /api/v1/auth/login`

**说明**: 用户登录获取访问令牌

**请求头**: 无需认证

**请求体** (表单格式):
```
username=user@example.com&password=password123
```

**响应示例** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**错误响应**:
- `401 Unauthorized`: 用户名或密码错误
  ```json
  {
    "detail": "用户名或密码错误"
  }
  ```

---

## 用户资料接口

### 3. 获取用户档案

**接口**: `GET /api/v1/users/me`

**说明**: 获取当前登录用户的档案信息

**请求头**: 
```
Authorization: Bearer <access_token>
```

**请求参数**: 无

**响应示例** (200 OK):
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "preferences": "喜欢美食和动漫",
  "create_time": "2024-11-20T10:00:00",
  "update_time": "2024-11-20T10:00:00"
}
```

**错误响应**:
- `401 Unauthorized`: Token无效或过期
- `404 Not Found`: 用户不存在

---

### 4. 更新用户偏好

**接口**: `PUT /api/v1/users/me`

**说明**: 更新当前用户的偏好设置

**请求头**: 
```
Authorization: Bearer <access_token>
```

**请求体**:
```json
{
  "preferences": "喜欢美食、动漫和亲子旅游"
}
```

**响应示例** (200 OK):
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "preferences": "喜欢美食、动漫和亲子旅游",
  "create_time": "2024-11-20T10:00:00",
  "update_time": "2024-11-20T15:30:00"
}
```

---

## 行程规划接口

### 5. 文本创建行程

**接口**: `POST /api/v1/plan/text`

**说明**: 通过文本输入创建行程规划（需要调用LLM和地图API，可能需要30-60秒）

**请求头**: 
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "destination": "东京",
  "start_date": "2024-12-01",
  "end_date": "2024-12-07",
  "budget_cny": 15000.0,
  "people": "2大1小",
  "preferences": "喜欢美食和动漫，带孩子旅游"
}
```

**字段说明**:
- `destination`: 目的地（字符串）
- `start_date`: 开始日期（ISO格式：YYYY-MM-DD）
- `end_date`: 结束日期（ISO格式：YYYY-MM-DD）
- `budget_cny`: 预算（人民币，浮点数）
- `people`: 同行人数（字符串，如"2大1小"）
- `preferences`: 旅行偏好（字符串）

**响应示例** (200 OK):
```json
{
  "message": "行程生成成功",
  "trip_id": "uuid-string"
}
```

**错误响应**:
- `500 Internal Server Error`: 生成行程失败
  ```json
  {
    "detail": "生成行程失败: 错误信息"
  }
  ```

---

### 6. 语音创建行程

**接口**: `POST /api/v1/plan/voice`

**说明**: 通过语音文件输入创建行程规划（需要调用LLM和地图API，可能需要30-60秒）

**请求头**: 
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**请求体** (表单格式):
```
file: <音频文件>  // 字段名必须为 "file"，支持 .webm 或 .wav 格式
```

**音频格式说明**:
- **推荐格式**: WebM（浏览器录音常用格式）
- **支持格式**: WebM, WAV
- **自动转换**: 后端会自动使用 ffmpeg 将 WebM 转换为 WAV (PCM格式) 供科大讯飞API使用
- **转换参数**: 16kHz采样率, 16bit, 单声道, PCM编码

**响应示例** (200 OK):
```json
{
  "message": "行程生成成功",
  "trip_id": "uuid-string"
}
```

**错误响应**:
- `500 Internal Server Error`: 处理语音输入失败
  ```json
  {
    "detail": "处理语音输入失败: 错误信息"
  }
  ```

---
### 6.1. 语音创建行程(前端解析语音，传入自然语言)
接口规范
POST /api/v1/plan/voice-text
Header:
Authorization: Bearer <access_token>
Content-Type: application/json
Body:
{ "text": "我打算6月10号到6月15号和女朋友去东京玩，大概预算1万。" }
Response 200:
{ "message": "行程生成成功", "trip_id": "uuid-string" }
错误:
401/403: 未登录或无权限
500: { "detail": "从文本生成行程失败: <错误信息>" }

---

### 7. 获取行程列表

**接口**: `GET /api/v1/plan/`

**说明**: 获取当前用户的所有行程列表（包括已规划完成和正在规划的）

**请求头**: 
```
Authorization: Bearer <access_token>
```

**请求参数**: 无

**响应示例** (200 OK):
```json
{
  "trips": [
    {
      "trip_id": "uuid-string",
      "user_id": "uuid-string",
      "trip_name": "五天东京亲子美食动漫之旅",
      "destination": "东京",
      "start_date": "2024-12-01",
      "end_date": "2024-12-07",
      "status": "generated",
      "created_at": "2024-11-20T10:00:00",
      "updated_at": "2024-11-20T10:05:00"
    }
  ]
}
```

**状态说明**:
- `draft`: 草稿（刚创建，未生成）
- `generated`: 已生成（规划完成）
- `active`: 进行中
- `completed`: 已完成

---

### 8. 获取行程详情

**接口**: `GET /api/v1/plan/{trip_id}`

**说明**: 获取指定行程的详细信息，包括每日行程安排（含每日酒店推荐、活动类型等）和预算

**请求头**: 
```
Authorization: Bearer <access_token>
```

**路径参数**:
- `trip_id`: 行程ID（UUID字符串）

**响应示例** (200 OK):
```json
{
  "trip_header": {
    "trip_id": "uuid-string",
    "user_id": "uuid-string",
    "trip_name": "五天东京亲子美食动漫之旅",
    "destination": "东京",
    "start_date": "2024-12-01",
    "end_date": "2024-12-07",
    "status": "generated",
    "created_at": "2024-11-20T10:00:00",
    "updated_at": "2024-11-20T10:05:00"
  },
  "trip_details": [
    {
      "detail_id": "uuid-string",
      "trip_id": "uuid-string",
      "day_number": 1,
      "theme": "动漫与美食初体验",
      "hotel_recommendation": {
        "poi_id": "H001",
        "name": "东京新宿希尔顿酒店",
        "reasoning": "国际连锁酒店，交通便利，适合亲子入住"
      },
      "activities": [
        {
          "poi_id": "P001",
          "poi_name": "秋叶原",
          "activity_type": "Attraction",
          "latitude": 35.6999,
          "longitude": 139.7712,
          "estimated_time_slot": "10:00 - 12:30",
          "estimated_duration_minutes": 150,
          "notes": "动漫周边购物，留足时间排队购限定",
          "transport_to_next": {
            "mode": "地铁",
            "recommendation": "步行至最近地铁站后转乘JR前往午餐地点",
            "next_poi_id": "R001"
          }
        },
        {
          "poi_id": null,
          "poi_name": "新宿美食街",
          "activity_type": "Meal_Lunch",
          "latitude": null,
          "longitude": null,
          "estimated_time_slot": "12:30 - 13:30",
          "estimated_duration_minutes": 60,
          "notes": "在美食街自由选择当地料理",
          "transport_to_next": null
        }
      ],
      "created_at": "2024-11-20T10:05:00",
      "updated_at": "2024-11-20T10:05:00",
      "map_url": "https://restapi.amap.com/v3/staticmap?location=139.7712,35.6999&zoom=13&size=750*300&markers=mid,0xFF0000,A:139.7712,35.6999&paths=10,0x0000ff,1,,:139.7712,35.6999;139.7730,35.7005&key=your_key"
    }
  ],
  "budget": {
    "budget_id": "uuid-string",
    "trip_id": "uuid-string",
    "user_budget": 15000.0,  -- 用户准备的预算
    "estimated_total": 11250.0,  -- LLM估算的总预算（控制在用户预算的60%-85%之间）
    "categories": [
      {
        "name": "住宿",
        "estimated_cny": 5000.0
      },
      {
        "name": "餐饮",
        "estimated_cny": 4000.0
      },
      {
        "name": "交通",
        "estimated_cny": 3000.0
      },
      {
        "name": "门票",
        "estimated_cny": 2000.0
      },
      {
        "name": "购物",
        "estimated_cny": 1000.0
      }
    ],
    "created_at": "2024-11-20T10:05:00",
    "updated_at": "2024-11-20T10:05:00"
  }
}
```

**错误响应**:
- `403 Forbidden`: 无权访问此行程
- `404 Not Found`: 行程不存在

**字段说明与兼容性**:
- `trip_details[*].hotel_recommendation`：每日酒店推荐（JSON 对象），在同一城市内各天通常相同；跨城行程可能变化。
- `trip_details[*].activities[*].activity_type`：活动类型（如 `Meal_Breakfast`/`Meal_Lunch`/`Meal_Dinner`/`Attraction`）。
- `trip_details[*].activities[*].poi_id/poi_name/lat/long`：当活动为泛指场景（如"美食街""酒店早餐"）时，可能为 `null`。
- `trip_details[*].activities[*].transport_to_next`：若无后续行程或无需建议，可能为 `null` 或空对象。服务端会忽略关键字段均为空的占位活动。
- `trip_details[*].map_url`：该天的静态地图图片URL（高德地图API生成），展示该天所有行程点的位置和路径。如果该天没有有效的坐标点，则为 `null`。

---

### 9. 修改行程

**接口**: `PUT /api/v1/plan/{trip_id}`

**说明**: 修改行程的基本信息

**请求头**: 
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**路径参数**:
- `trip_id`: 行程ID（UUID字符串）

**请求体**:
```json
{
  "trip_name": "修改后的行程名称",
  "status": "active"
}
```

**响应示例** (200 OK):
```json
{
  "message": "行程更新成功",
  "trip_id": "uuid-string"
}
```

**错误响应**:
- `403 Forbidden`: 无权修改此行程
- `400 Bad Request`: 更新行程失败

---

## 费用管理接口

### 10. 获取预算与开销

**接口**: `GET /api/v1/budget/{trip_id}`

**说明**: 获取指定行程的预算信息和实际开销，包括预算对比分析

**请求头**: 
```
Authorization: Bearer <access_token>
```

**路径参数**:
- `trip_id`: 行程ID（UUID字符串）

**响应示例** (200 OK):
```json
{
  "budget": {
    "budget_id": "uuid-string",
    "trip_id": "uuid-string",
    "user_budget": 15000.0,  -- 用户准备的预算
    "estimated_total": 11250.0,  -- LLM估算的总预算（控制在用户预算的60%-85%之间）
    "categories": [
      {
        "name": "住宿",
        "estimated_cny": 5000.0
      },
      {
        "name": "餐饮",
        "estimated_cny": 4000.0
      }
    ],
    "created_at": "2024-11-20T10:05:00",
    "updated_at": "2024-11-20T10:05:00"
  },
  "expenses": [
    {
      "expense_id": "uuid-string",
      "trip_id": "uuid-string",
      "category": "餐饮",
      "amount": 500.0,
      "currency": "CNY",
      "description": "今天在餐厅吃了日式料理",
      "timestamp": "2024-12-01T12:30:00",
      "created_at": "2024-12-01T12:30:00"
    }
  ],
  "summary": {
    "total_expense": 500.0,
    "expense_by_category": {
      "餐饮": 500.0
    },
    "variance": {
      "total": {
        "estimated": 15000.0,
        "actual": 500.0,
        "difference": 14500.0,  -- 剩余预算（正数表示剩余，负数表示超支）
        "percentage": 96.67  -- 剩余百分比（正数表示剩余比例，负数表示超支比例）
      },
      "餐饮": {
        "estimated": 4000.0,
        "actual": 500.0,
        "difference": 3500.0,  -- 剩余预算（正数表示剩余，负数表示超支）
        "percentage": 87.5  -- 剩余百分比（正数表示剩余比例，负数表示超支比例）
      }
    }
  }
}
```

**错误响应**:
- `403 Forbidden`: 无权访问此行程的费用信息
- `404 Not Found`: 行程不存在

---

### 11. 文本录入开销

**接口**: `POST /api/v1/budget/expense/text`

**说明**: 通过文本输入记录开销（LLM会自动解析文本中的金额和类别）

**请求头**: 
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:
```json
{
  "trip_id": "uuid-string",
  "text_input": "今天在餐厅吃了日式料理，花费了500元"
}
```

**响应示例** (200 OK):
```json
{
  "expense_id": "uuid-string",
  "trip_id": "uuid-string",
  "category": "餐饮",
  "amount": 500.0,
  "currency": "CNY",
  "description": "今天在餐厅吃了日式料理，花费了500元",
  "timestamp": "2024-12-01T12:30:00"
}
```

**错误响应**:
- `403 Forbidden`: 无权操作此行程
- `404 Not Found`: 行程不存在
- `500 Internal Server Error`: 记录开销失败

---

### 12. 语音录入开销

**接口**: `POST /api/v1/budget/expense/voice`

**说明**: 通过语音文件输入记录开销（LLM会自动解析语音中的金额和类别）

**请求头**: 
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**请求体** (表单格式):
```
trip_id: <行程ID>
file: <音频文件>  // 字段名必须为 "file"，支持 .webm 或 .wav 格式
```

**音频格式说明**:
- **推荐格式**: WebM（浏览器录音常用格式）
- **支持格式**: WebM, WAV
- **自动转换**: 后端会自动使用 ffmpeg 将 WebM 转换为 WAV (PCM格式) 供科大讯飞API使用
- **转换参数**: 16kHz采样率, 16bit, 单声道, PCM编码

**响应示例** (200 OK):
```json
{
  "expense_id": "uuid-string",
  "trip_id": "uuid-string",
  "category": "餐饮",
  "amount": 500.0,
  "currency": "CNY",
  "description": "今天在餐厅吃了日式料理",
  "timestamp": "2024-12-01T12:30:00"
}
```

**错误响应**:
- `403 Forbidden`: 无权操作此行程
- `404 Not Found`: 行程不存在
- `500 Internal Server Error`: 记录开销失败

---

## 错误码说明

### HTTP 状态码

| 状态码 | 说明 | 常见场景 |
|--------|------|----------|
| 200 | 成功 | 请求处理成功 |
| 400 | 请求错误 | 参数格式错误、邮箱已被注册等 |
| 401 | 未授权 | Token无效、过期或未提供 |
| 403 | 禁止访问 | 无权访问其他用户的资源 |
| 404 | 未找到 | 资源不存在（用户、行程等） |
| 422 | 无法处理 | 请求参数验证失败 |
| 500 | 服务器错误 | 内部错误、LLM调用失败等 |

### 错误响应格式

所有错误响应都遵循以下格式：
```json
{
  "detail": "错误描述信息"
}
```

### 常见错误示例

**Token过期**:
```json
{
  "detail": "无法验证凭证"
}
```

**无权访问**:
```json
{
  "detail": "无权访问此行程"
}
```

**资源不存在**:
```json
{
  "detail": "行程不存在"
}
```

---

## 注意事项

1. **Token有效期**: Token默认有效期为30分钟，过期后需要重新登录
2. **异步处理**: 创建行程和录入开销的接口可能需要较长时间（30-60秒），因为需要调用LLM和地图API
3. **文件上传**: 
   - 音频文件支持 `.webm` 和 `.wav` 格式
   - 推荐使用 WebM 格式（浏览器录音常用格式）
   - 后端会自动使用 ffmpeg 将 WebM 转换为 WAV (PCM格式)
   - 建议文件大小不超过10MB
   - **ffmpeg要求**: 后端服务器需要安装 ffmpeg 并添加到系统 PATH
4. **日期格式**: 所有日期字段使用 ISO 8601 格式：`YYYY-MM-DD` 或 `YYYY-MM-DDTHH:mm:ss`
5. **时区**: 所有时间戳使用 UTC 时区
6. **权限验证**: 所有涉及行程的操作都会验证行程归属，确保用户只能操作自己的行程

---

## 接口调用示例

### JavaScript/TypeScript (fetch)

```javascript
// 登录获取Token
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: 'username=user@example.com&password=password123'
});
const { access_token } = await loginResponse.json();

// 获取行程列表
const tripsResponse = await fetch('http://localhost:8000/api/v1/plan/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});
const tripsData = await tripsResponse.json();

// 上传WebM音频文件创建行程
const formData = new FormData();
formData.append('file', audioBlob, 'audio.webm'); // audioBlob 是浏览器录音得到的 Blob 对象

const voiceResponse = await fetch('http://localhost:8000/api/v1/plan/voice', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
    // 注意：不要设置 Content-Type，让浏览器自动设置（包含 boundary）
  },
  body: formData
});
const voiceResult = await voiceResponse.json();

// 上传WebM音频文件录入开销
const expenseFormData = new FormData();
expenseFormData.append('trip_id', 'your_trip_id');
expenseFormData.append('file', audioBlob, 'expense.webm');

const expenseVoiceResponse = await fetch('http://localhost:8000/api/v1/budget/expense/voice', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
  },
  body: expenseFormData
});
const expenseResult = await expenseVoiceResponse.json();
```

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8000"

# 登录
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    data={"username": "user@example.com", "password": "password123"}
)
token = login_response.json()["access_token"]

# 获取行程列表
headers = {"Authorization": f"Bearer {token}"}
trips_response = requests.get(f"{BASE_URL}/api/v1/plan/", headers=headers)
trips_data = trips_response.json()

# 上传WebM音频文件创建行程
with open("audio.webm", "rb") as audio_file:
    files = {"file": ("audio.webm", audio_file, "audio/webm")}
    response = requests.post(
        f"{BASE_URL}/api/v1/plan/voice",
        headers=headers,
        files=files
    )
    result = response.json()

# 上传WebM音频文件录入开销
with open("expense.webm", "rb") as audio_file:
    files = {"file": ("expense.webm", audio_file, "audio/webm")}
    data = {"trip_id": "your_trip_id"}
    response = requests.post(
        f"{BASE_URL}/api/v1/budget/expense/voice",
        headers=headers,
        files=files,
        data=data
    )
    result = response.json()
```

### curl

```bash
# 登录
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"

# 获取行程列表（使用返回的token）
curl -X GET "http://localhost:8000/api/v1/plan/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 上传WebM音频文件创建行程
curl -X POST "http://localhost:8000/api/v1/plan/voice" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@audio.webm"

# 上传WebM音频文件录入开销
curl -X POST "http://localhost:8000/api/v1/budget/expense/voice" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "trip_id=YOUR_TRIP_ID" \
  -F "file=@expense.webm"
```

---

## 更新日志

- **v1.0.0** (2024-11-20): 初始版本
  - 用户认证与注册
  - 用户资料管理
  - 行程规划（文本/语音）
  - 费用管理

---

**文档版本**: 1.0.0  
**最后更新**: 2024-11-20  
**维护者**: AI智能旅行规划后端团队

