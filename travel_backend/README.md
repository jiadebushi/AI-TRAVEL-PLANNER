# AI智能旅行规划后端

基于 FastAPI + LangChain + 千问LLM 的智能旅行规划后端服务。

## 功能特性

- ✅ 用户认证与管理（注册/登录/JWT）
- ✅ 语音处理与文本解析（科大讯飞语音转文本 + LLM意图解析）
- ✅ 智能行程规划（地图POI检索 + LLM决策 + 交通耗时预估）
- ✅ 费用预算与管理（LLM预算估算 + 实时开销记录）
- ✅ 数据持久化（Supabase数据库）

## 技术栈

- **Web框架**: FastAPI
- **LLM**: 通义千问（通过LangChain调用）
- **语音服务**: 科大讯飞
- **地图服务**: 高德/百度地图API
- **数据库**: Supabase (PostgreSQL)
- **认证**: JWT

## 项目结构

```
travel_backend/
├── app/
│   ├── api/              # API路由层
│   │   ├── auth.py       # 认证路由
│   │   ├── plan.py       # 行程规划路由
│   │   └── budget.py     # 费用管理路由
│   ├── services/         # 业务逻辑层
│   │   ├── ai_service.py      # AI/LLM服务
│   │   ├── voice_service.py   # 语音处理服务
│   │   ├── map_service.py     # 地图服务
│   │   ├── trip_service.py    # 行程规划服务
│   │   └── expense_service.py # 费用管理服务
│   ├── data/            # 数据访问层
│   │   ├── database.py        # 数据库连接
│   │   ├── user_repository.py
│   │   ├── trip_repository.py
│   │   └── expense_repository.py
│   └── models/          # 数据模型层
│       ├── api_models.py      # API数据模型
│       ├── db_models.py       # 数据库模型
│       └── llm_models.py      # LLM输出模型
├── config/              # 配置模块
│   └── settings.py      # 配置管理
├── main.py              # 应用入口
├── requirements.txt     # Python依赖
└── .env                 # 环境变量（需要创建）
```

## 安装和配置

### 1. 安装依赖

#### 1.1 安装 Python 依赖

```bash
pip install -r requirements.txt
```

#### 1.2 安装 ffmpeg（用于音频格式转换）

**Windows:**
1. 下载 ffmpeg: https://ffmpeg.org/download.html
2. 解压并添加到系统 PATH
3. 或在命令行验证: `ffmpeg -version`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**验证安装:**
```bash
ffmpeg -version
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下内容：

```env
# 千问API
QIANWEN_API_KEY=your_qianwen_api_key_here
QIANWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# 科大讯飞API
XUNFEI_APP_ID=your_xunfei_app_id
XUNFEI_API_KEY=your_xunfei_api_key
XUNFEI_API_SECRET=your_xunfei_api_secret

# 地图API（选择高德或百度）
MAP_API_TYPE=amap  # 或 baidu
AMAP_API_KEY=your_amap_api_key
BAIDU_API_KEY=your_baidu_api_key

# Supabase配置
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# JWT配置
SECRET_KEY=your_secret_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. 初始化数据库

在 Supabase 中创建以下表结构：

见[数据库表](./database_schema.sql)

## 运行应用

### 开发环境

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 生产环境

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

访问 API 文档：http://localhost:8000/docs

## API 端点

### 认证相关
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录

### 用户资料
- `GET /api/v1/users/me` - 获取用户档案（返回 user_id, email, preferences, create_time, update_time）
- `PUT /api/v1/users/me` - 更新用户偏好（仅更新 preferences 字段）

### 行程规划
- `POST /api/v1/plan/text` - 文本输入行程需求
- `POST /api/v1/plan/voice` - 语音输入行程需求
- `GET /api/v1/plan/{trip_id}` - 获取行程详情
- `GET /api/v1/plan/` - 获取用户的行程列表
- `PUT /api/v1/plan/{trip_id}` - 修改行程

### 费用管理
- `GET /api/v1/budget/{trip_id}` - 获取预算与开销
- `POST /api/v1/budget/expense/text` - 文本录入开销
- `POST /api/v1/budget/expense/voice` - 语音录入开销

## 注意事项

1. **LangChain与千问API**: 使用LangChain的ChatOpenAI兼容接口调用千问API，确保API密钥和端点配置正确。

2. **数据库**: 本项目使用Supabase作为数据库，也可以使用其他PostgreSQL数据库，只需修改数据库连接配置。

3. **生产环境**: 生产环境部署时，请：
   - 修改CORS配置为具体的前端域名
   - 使用强密钥替换SECRET_KEY
   - 配置HTTPS
   - 使用环境变量管理敏感信息

## License

MIT


