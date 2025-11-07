#!/bin/bash

# Docker 镜像构建和导出脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AI Travel Planner Docker 构建脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 镜像名称
BACKEND_IMAGE="ai-travel-backend:latest"
FRONTEND_IMAGE="ai-travel-frontend:latest"

# 导出文件名
BACKEND_TAR="ai-travel-backend-latest.tar"
FRONTEND_TAR="ai-travel-frontend-latest.tar"

# 1. 构建后端镜像
echo -e "\n${YELLOW}[1/4] 构建后端镜像...${NC}"
docker build -t $BACKEND_IMAGE ./travel_backend
echo -e "${GREEN}✓ 后端镜像构建完成${NC}"

# 2. 构建前端镜像
echo -e "\n${YELLOW}[2/4] 构建前端镜像...${NC}"
docker build -t $FRONTEND_IMAGE ./travel_frontend
echo -e "${GREEN}✓ 前端镜像构建完成${NC}"

# 3. 导出后端镜像
echo -e "\n${YELLOW}[3/4] 导出后端镜像到 $BACKEND_TAR...${NC}"
docker save -o $BACKEND_TAR $BACKEND_IMAGE
echo -e "${GREEN}✓ 后端镜像导出完成${NC}"

# 4. 导出前端镜像
echo -e "\n${YELLOW}[4/4] 导出前端镜像到 $FRONTEND_TAR...${NC}"
docker save -o $FRONTEND_TAR $FRONTEND_IMAGE
echo -e "${GREEN}✓ 前端镜像导出完成${NC}"

# 显示文件大小
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  构建完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "后端镜像文件: ${GREEN}$BACKEND_TAR${NC} ($(du -h $BACKEND_TAR | cut -f1))"
echo -e "前端镜像文件: ${GREEN}$FRONTEND_TAR${NC} ($(du -h $FRONTEND_TAR | cut -f1))"
echo -e "\n${YELLOW}导入镜像命令:${NC}"
echo -e "  docker load -i $BACKEND_TAR"
echo -e "  docker load -i $FRONTEND_TAR"
echo -e "\n${YELLOW}运行容器命令:${NC}"
echo -e "  docker-compose up -d"
echo -e "  或单独运行:"
echo -e "  docker run -d -p 8000:8000 --env-file ./travel_backend/.env $BACKEND_IMAGE"
echo -e "  docker run -d -p 3000:80 $FRONTEND_IMAGE"


