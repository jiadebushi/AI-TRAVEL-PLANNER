# AI Travel Planner - 部署与运行指南

## 一、前置条件

- 已安装 Docker（建议 20.10+）和 Docker Compose（2.x+）
- 可访问网络用于拉取镜像或从文件导入镜像

## 二、获取代码与镜像

### 方式一：使用提供的 docker-compose.yml（推荐）

项目根目录的 `docker-compose.yml` 已配置为使用 Docker Hub 上的镜像，**docker-compose 会自动拉取镜像**。

> 手动拉取镜像（可选）：
>
> ```bash
> docker pull hanxi011/ai_travel_planner-backend:latest
> docker pull hanxi011/ai_travel_planner-frontend:latest
> ```
>
1. **克隆仓库**


```bash
git clone https://github.com/jiadebushi/AI-TRAVEL-PLANNER.git
cd AI_Travel_Planner
```

2. **配置环境变量**：

   具体说明见[环境配置](## 三、配置环境变量（必做）)
 ```bash
cp travel_backend/.env.example travel_backend/.env
# 编辑 travel_backend/.env，填入 API 密钥
 ```

3. **启动服务**：（在AI_Travel_Planner目录下运行）
```bash
docker-compose up -d
```

### 方式二：自己构建docker镜像

1) **克隆仓库**

```bash
git clone https://github.com/jiadebushi/AI-TRAVEL-PLANNER.git
cd AI_Travel_Planner
```

2) **准备 Docker 镜像**
- 本地构建（需要能访问基础镜像）（在AI_Travel_Planner目录下运行）

```bash
# 构建镜像
docker-compose -f docker-compose-origin.yml build
```

3. **启动服务**：（在AI_Travel_Planner目录下运行）

```
docker-compose -f docker-compose-origin.yml up -d
```

## 三、配置环境变量（必做）

后端运行依赖环境变量，不会内置在镜像中。请在首次运行前创建并填写：

```bash
cp travel_backend/.env.example travel_backend/.env

# 编辑 travel_backend/.env，填入你自己的密钥与配置
```

**关键配置（示例，完整项见 `.env.example`）：**

```env
# LLM（通义千问）
QIANWEN_API_KEY=你的_qianwen_key
QIANWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

# JWT
SECRET_KEY=随机且足够复杂的字符串
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Supabase（PostgreSQL 后端）
SUPABASE_URL=你的_supabase_url
SUPABASE_KEY=你的_supabase_anon_key
SUPABASE_SERVICE_KEY=你的_supabase_service_key
```

说明：`.env` 文件不会被打包进镜像（已通过 `.dockerignore` 与 `travel_backend/.dockerignore` 排除），他人使用时也必须填入自己的密钥，安全不外泄。

**数据库配置**

如果您使用自己的 Supabase 数据库，请按照以下步骤操作：

- 在 travel_backend 目录下找到 `database_schema.sql`文件。

- 使用 Supabase SQL Editor 运行该文件，以创建所需的数据表。

- 确保在 .env 文件中正确配置 Supabase 的 URL 和 API Key。

> ⚠️ 注意：如果未创建数据表，后端服务可能无法正常运行。
>

## 四、访问地址

- 前端：[http://localhost:3000](http://localhost:3000)
- 后端 API：[http://localhost:8000](http://localhost:8000)
- API 文档（Swagger）：[http://localhost:8000/docs](http://localhost:8000/docs)
- 健康检查：[http://localhost:8000/health](http://localhost:8000/health)

## 五、常用运维命令

- 查看状态：

```bash
docker-compose ps
```

- 查看日志：

```bash
docker-compose logs -f          # 全部
docker-compose logs -f backend  # 仅后端
docker-compose logs -f frontend # 仅前端
```

- 停止：

```bash
docker-compose stop           # 停止但不移除
docker-compose down           # 停止并移除容器与网络
docker-compose down -v        # 额外移除数据卷（谨慎）
```

## 六、镜像安全与再分发说明

- 镜像内不包含任何 `.env` 或密钥文件，运行时通过 `docker-compose.yml` 的 `env_file: ./travel_backend/.env` 从宿主机注入。
- 对外发布时，请连同 `travel_backend/.env.example` 一并提供，对方需复制为 `.env` 并填入自己的密钥后方可运行。

## 七、故障排查（FAQ）

- 前端无法访问后端
  - 确认后端容器健康：`curl http://localhost:8000/health`
  - 检查前端 `nginx` 代理是否正常（容器日志）。

- 后端启动失败（循环重启）
  - 多为 `.env` 未配置或缺少必要项，按第三步补齐。
  - 查看日志：`docker-compose logs -f backend`。

- 构建基础镜像失败 / 拉取慢
  - 配置 Docker 镜像源（参考 `README-Docker.md` 中“镜像源 403 错误”章节）。

## 八、开发者提示

- 本地开发可直接在 `travel_frontend` 使用 `npm run dev` 并通过 Vite 代理到后端；生产镜像中由 Nginx 负责前端与后端 `/api` 的转发。

