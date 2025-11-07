# Docker 部署指南

本文档说明如何构建和运行 AI Travel Planner 的 Docker 镜像。

## 前置要求

- Docker 已安装（版本 20.10+）
- Docker Compose 已安装（版本 2.0+）

## 快速开始

### 方式一：使用 Docker Compose（推荐）

1. **配置后端环境变量**

   在 `travel_backend/` 目录下创建 `.env` 文件：

   ```env
   # 千问API
   QIANWEN_API_KEY=your_qianwen_api_key_here
   QIANWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

   # 科大讯飞API
   XUNFEI_APP_ID=your_xunfei_app_id
   XUNFEI_API_KEY=your_xunfei_api_key
   XUNFEI_API_SECRET=your_xunfei_api_secret

   # 地图API
   MAP_API_TYPE=amap
   AMAP_API_KEY=your_amap_api_key

   # Supabase配置
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_KEY=your_supabase_service_key

   # JWT配置
   SECRET_KEY=your_secret_key_here_change_in_production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

2. **配置前端环境变量（可选）**

   在 `travel_frontend/` 目录下创建 `.env` 文件（通常不需要，默认使用相对路径）：

   ```env
   # 默认使用相对路径，nginx 会自动代理
   VITE_API_BASE_URL=/api/v1
   
   # 如果需要指定完整后端地址（开发环境）
   # VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

3. **构建并启动服务**

   ```bash
   docker-compose up -d
   ```

4. **访问服务**

   - 前端: http://localhost:3000
   - 后端 API: http://localhost:8000
   - API 文档: http://localhost:8000/docs

### 方式二：单独构建和运行

#### 构建镜像

**Linux/macOS:**
```bash
chmod +x build-docker.sh
./build-docker.sh
```

**Windows (PowerShell):**
```powershell
.\build-docker.ps1
```

#### 运行容器

**后端:**
```bash
docker run -d \
  --name ai-travel-backend \
  -p 8000:8000 \
  --env-file ./travel_backend/.env \
  ai-travel-backend:latest
```

**前端:**
```bash
docker run -d \
  --name ai-travel-frontend \
  -p 3000:80 \
  ai-travel-frontend:latest
```

## 导出和导入镜像

### 导出镜像为 tar 文件

构建脚本会自动导出镜像为 tar 文件：
- `ai-travel-backend-latest.tar`
- `ai-travel-frontend-latest.tar`

### 导入镜像

在其他机器上导入镜像：

```bash
docker load -i ai-travel-backend-latest.tar
docker load -i ai-travel-frontend-latest.tar
```

然后使用 `docker-compose up -d` 或单独运行容器。

## 常用命令

### 查看运行中的容器
```bash
docker-compose ps
# 或
docker ps
```

### 查看日志
```bash
docker-compose logs -f
# 或查看特定服务
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 重新构建镜像
```bash
docker-compose build --no-cache
docker-compose up -d
```

### 进入容器
```bash
# 进入后端容器
docker exec -it ai-travel-backend bash

# 进入前端容器
docker exec -it ai-travel-frontend sh
```

## 生产环境建议

1. **使用环境变量文件**: 确保 `.env` 文件包含正确的生产环境配置
2. **配置 CORS**: 修改 `travel_backend/main.py` 中的 `allow_origins` 为具体的前端域名
3. **使用 HTTPS**: 在生产环境中使用反向代理（如 Nginx）配置 HTTPS
4. **数据持久化**: 如果需要持久化数据，配置数据库连接和卷挂载
5. **资源限制**: 在 `docker-compose.yml` 中添加资源限制：

   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '1'
             memory: 1G
   ```

## 故障排查

### Docker 镜像源 403 错误

如果遇到 `403 Forbidden` 错误，通常是 Docker 镜像源配置问题：

**解决方案 1: 使用修复脚本（推荐）**
```powershell
.\fix-docker-mirror.ps1
```

**解决方案 2: 手动配置**

1. 打开 Docker Desktop
2. 点击 Settings (设置) -> Docker Engine
3. 编辑 JSON 配置，添加或修改镜像源：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

4. 点击 "Apply & Restart"

**解决方案 3: 使用官方 Docker Hub**

如果网络允许，可以移除镜像源配置，直接使用官方源。

**常用镜像源：**
- 中科大: `https://docker.mirrors.ustc.edu.cn`
- 网易: `https://hub-mirror.c.163.com`
- 腾讯云: `https://mirror.ccs.tencentyun.com`
- 阿里云: 需要登录后获取专属地址

### 后端无法启动
- 检查 `.env` 文件是否存在且配置正确
- 查看日志: `docker-compose logs backend`
- 检查端口是否被占用: `netstat -an | findstr 8000` (Windows)

### 前端无法连接后端
- 检查后端是否正常运行
- 确认前端配置中的 API 地址正确
- 检查 CORS 配置

### 镜像构建失败
- 检查网络连接（需要下载基础镜像）
- 查看构建日志中的错误信息
- 确保 Docker 有足够的磁盘空间
- 如果使用镜像源，尝试更换其他镜像源

## 注意事项

1. **环境变量**: `.env` 文件包含敏感信息，不要提交到 Git
2. **数据库**: 确保 Supabase 数据库已正确配置
3. **API 密钥**: 所有 API 密钥都需要正确配置才能正常使用
4. **端口冲突**: 确保 8000 和 3000 端口未被占用

