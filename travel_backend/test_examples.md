# API 测试示例文档

本文档提供各种API测试的示例和说明。

## 快速开始

### 1. 启动后端服务

```bash
# 确保已配置.env文件
python main.py
```

### 2. 运行测试脚本

```bash
# 基础同步测试
python test_api.py

# 异步测试
python test_api_async.py
```

## 使用 curl 测试

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

### 2. 用户注册

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456",
    "preferences": "喜欢美食和动漫"
  }'
```

### 3. 用户登录

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123456"
```

保存返回的 `access_token` 供后续使用。

### 4. 获取当前用户信息

```bash
TOKEN="your_access_token_here"

curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. 创建行程（文本输入）

```bash
TOKEN="your_access_token_here"

curl -X POST "http://localhost:8000/api/v1/plan/text" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "东京",
    "start_date": "2024-12-01",
    "end_date": "2024-12-07",
    "budget_cny": 15000.0,
    "people": "2大1小",
    "preferences": "喜欢美食和动漫，带孩子旅游"
  }'
```

### 6. 获取行程列表

```bash
TOKEN="your_access_token_here"

curl -X GET "http://localhost:8000/api/v1/plan/" \
  -H "Authorization: Bearer $TOKEN"
```

### 7. 获取行程详情

```bash
TOKEN="your_access_token_here"
TRIP_ID="your_trip_id_here"

curl -X GET "http://localhost:8000/api/v1/plan/$TRIP_ID" \
  -H "Authorization: Bearer $TOKEN"
```

### 8. 文本录入开销

```bash
TOKEN="your_access_token_here"
TRIP_ID="your_trip_id_here"

curl -X POST "http://localhost:8000/api/v1/budget/expense/text" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trip_id": "'$TRIP_ID'",
    "text_input": "今天在餐厅吃了日式料理，花费了500元"
  }'
```

### 9. 语音录入开销

```bash
TOKEN="your_access_token_here"
TRIP_ID="your_trip_id_here"

curl -X POST "http://localhost:8000/api/v1/budget/expense/voice" \
  -H "Authorization: Bearer $TOKEN" \
  -F "trip_id=$TRIP_ID" \
  -F "file=@test_audio.wav"
```

### 10. 获取行程费用信息

```bash
TOKEN="your_access_token_here"
TRIP_ID="your_trip_id_here"

curl -X GET "http://localhost:8000/api/v1/budget/$TRIP_ID" \
  -H "Authorization: Bearer $TOKEN"
```

## 使用 Python requests 测试

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. 登录
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    data={"username": "test@example.com", "password": "test123456"}
)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. 创建行程
trip_data = {
    "destination": "东京",
    "start_date": "2024-12-01",
    "end_date": "2024-12-07",
    "budget_cny": 15000.0,
    "people": "2大1小",
    "preferences": "喜欢美食和动漫"
}

trip_response = requests.post(
    f"{BASE_URL}/api/v1/plan/text",
    json=trip_data,
    headers=headers
)
trip_id = trip_response.json()["trip_id"]

# 3. 获取行程详情
detail_response = requests.get(
    f"{BASE_URL}/api/v1/plan/{trip_id}",
    headers=headers
)
print(json.dumps(detail_response.json(), indent=2, ensure_ascii=False))
```

## 测试检查清单

- [ ] 健康检查 `/health`
- [ ] 用户注册 `/api/v1/auth/register`
- [ ] 用户登录 `/api/v1/auth/login`
- [ ] 获取用户信息 `/api/v1/auth/me`
- [ ] 创建行程（文本） `/api/v1/plan/text`
- [ ] 获取行程列表 `/api/v1/plan/`
- [ ] 获取行程详情 `/api/v1/plan/{trip_id}`
- [ ] 文本录入开销 `/api/v1/budget/expense/text`
- [ ] 获取费用信息 `/api/v1/budget/{trip_id}`

## 常见问题

### 1. 创建行程超时

**原因**: LLM和地图API调用需要时间（通常30-60秒）

**解决方案**:
- 检查 `.env` 中的API密钥是否正确
- 查看后端日志是否有错误
- 增加客户端超时时间

### 2. 401 未授权错误

**原因**: Token已过期或无效

**解决方案**:
- 重新登录获取新Token
- 检查请求头中的Authorization格式: `Bearer {token}`

### 3. 403 禁止访问

**原因**: 尝试访问其他用户的资源

**解决方案**:
- 确保使用正确的用户Token
- 检查 `trip_id` 是否属于当前用户

## 压力测试

使用 `locust` 进行压力测试：

```bash
pip install locust

# 创建 locustfile.py 后运行
locust -f locustfile.py --host=http://localhost:8000
```

## API 文档

访问 Swagger UI 查看完整的API文档和交互式测试：

```
http://localhost:8000/docs
```


