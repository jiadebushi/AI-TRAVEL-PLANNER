# Docker 镜像构建和导出脚本 (PowerShell)

$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Cyan "========================================"
Write-ColorOutput Cyan "  AI Travel Planner Docker 构建脚本"
Write-ColorOutput Cyan "========================================"

# 镜像名称
$BACKEND_IMAGE = "ai-travel-backend:latest"
$FRONTEND_IMAGE = "ai-travel-frontend:latest"

# 导出文件名
$BACKEND_TAR = "ai-travel-backend-latest.tar"
$FRONTEND_TAR = "ai-travel-frontend-latest.tar"

# 1. 构建后端镜像
Write-ColorOutput Yellow "[1/4] 构建后端镜像..."
docker build -t $BACKEND_IMAGE ./travel_backend
Write-ColorOutput Green "✓ 后端镜像构建完成"

# 2. 构建前端镜像
Write-ColorOutput Yellow "[2/4] 构建前端镜像..."
docker build -t $FRONTEND_IMAGE ./travel_frontend
Write-ColorOutput Green "✓ 前端镜像构建完成"

# 3. 导出后端镜像
Write-ColorOutput Yellow "[3/4] 导出后端镜像到 $BACKEND_TAR..."
docker save -o $BACKEND_TAR $BACKEND_IMAGE
Write-ColorOutput Green "✓ 后端镜像导出完成"

# 4. 导出前端镜像
Write-ColorOutput Yellow "[4/4] 导出前端镜像到 $FRONTEND_TAR..."
docker save -o $FRONTEND_TAR $FRONTEND_IMAGE
Write-ColorOutput Green "✓ 前端镜像导出完成"

# 显示文件大小
Write-ColorOutput Cyan "========================================"
Write-ColorOutput Cyan "  构建完成！"
Write-ColorOutput Cyan "========================================"

$backendSize = (Get-Item $BACKEND_TAR).Length / 1MB
$frontendSize = (Get-Item $FRONTEND_TAR).Length / 1MB

Write-ColorOutput Green "后端镜像文件: $BACKEND_TAR ($([math]::Round($backendSize, 2)) MB)"
Write-ColorOutput Green "前端镜像文件: $FRONTEND_TAR ($([math]::Round($frontendSize, 2)) MB)"

Write-ColorOutput Yellow "`n导入镜像命令:"
Write-Output "  docker load -i $BACKEND_TAR"
Write-Output "  docker load -i $FRONTEND_TAR"

Write-ColorOutput Yellow "`n运行容器命令:"
Write-Output "  docker-compose up -d"
Write-Output "  或单独运行:"
Write-Output "  docker run -d -p 8000:8000 --env-file ./travel_backend/.env $BACKEND_IMAGE"
Write-Output "  docker run -d -p 3000:80 $FRONTEND_IMAGE"


