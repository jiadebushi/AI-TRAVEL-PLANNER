# Docker 镜像源修复脚本 (PowerShell)
# 用于修复 Docker 镜像源 403 错误

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Docker 镜像源修复脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker Desktop 是否运行
$dockerRunning = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

Write-Host "当前 Docker 配置位置:" -ForegroundColor Yellow
Write-Host "  Windows: C:\ProgramData\docker\config\daemon.json" -ForegroundColor Gray
Write-Host "  或通过 Docker Desktop: Settings -> Docker Engine" -ForegroundColor Gray
Write-Host ""

# 提供多个镜像源选项
Write-Host "请选择镜像源配置:" -ForegroundColor Yellow
Write-Host "  1. 使用官方 Docker Hub（推荐，如果网络允许）" -ForegroundColor Green
Write-Host "  2. 使用阿里云镜像源" -ForegroundColor Green
Write-Host "  3. 使用腾讯云镜像源" -ForegroundColor Green
Write-Host "  4. 使用网易镜像源" -ForegroundColor Green
Write-Host "  5. 使用中科大镜像源" -ForegroundColor Green
Write-Host "  6. 查看当前配置" -ForegroundColor Yellow
Write-Host ""

$choice = Read-Host "请输入选项 (1-6)"

$configPath = "$env:ProgramData\docker\config\daemon.json"

# 读取现有配置
$currentConfig = @{}
if (Test-Path $configPath) {
    try {
        $currentConfig = Get-Content $configPath -Raw | ConvertFrom-Json -AsHashtable
    } catch {
        Write-Host "警告: 无法读取现有配置，将创建新配置" -ForegroundColor Yellow
    }
}

switch ($choice) {
    "1" {
        # 移除镜像源配置，使用官方源
        if ($currentConfig.ContainsKey("registry-mirrors")) {
            $currentConfig.Remove("registry-mirrors")
            Write-Host "已移除镜像源配置，将使用官方 Docker Hub" -ForegroundColor Green
        } else {
            Write-Host "当前已使用官方 Docker Hub" -ForegroundColor Green
        }
    }
    "2" {
        # 阿里云镜像源（需要登录获取专属地址）
        Write-Host "注意: 阿里云镜像源需要登录后获取专属地址" -ForegroundColor Yellow
        Write-Host "访问: https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors" -ForegroundColor Cyan
        $mirrorUrl = Read-Host "请输入您的阿里云镜像源地址（如: https://xxx.mirror.aliyuncs.com）"
        $currentConfig["registry-mirrors"] = @($mirrorUrl)
    }
    "3" {
        # 腾讯云镜像源
        $currentConfig["registry-mirrors"] = @("https://mirror.ccs.tencentyun.com")
        Write-Host "已配置腾讯云镜像源" -ForegroundColor Green
    }
    "4" {
        # 网易镜像源
        $currentConfig["registry-mirrors"] = @("https://hub-mirror.c.163.com")
        Write-Host "已配置网易镜像源" -ForegroundColor Green
    }
    "5" {
        # 中科大镜像源
        $currentConfig["registry-mirrors"] = @("https://docker.mirrors.ustc.edu.cn")
        Write-Host "已配置中科大镜像源" -ForegroundColor Green
    }
    "6" {
        # 查看当前配置
        Write-Host "当前 Docker 配置:" -ForegroundColor Cyan
        if (Test-Path $configPath) {
            Get-Content $configPath | Write-Host
        } else {
            Write-Host "配置文件不存在，使用默认配置" -ForegroundColor Yellow
        }
        exit 0
    }
    default {
        Write-Host "无效选项" -ForegroundColor Red
        exit 1
    }
}

# 保存配置
try {
    # 确保目录存在
    $configDir = Split-Path $configPath -Parent
    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    }
    
    # 保存配置
    $currentConfig | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
    
    Write-Host ""
    Write-Host "配置已保存到: $configPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "请重启 Docker Desktop 使配置生效！" -ForegroundColor Yellow
    Write-Host "  1. 右键点击系统托盘中的 Docker 图标" -ForegroundColor Gray
    Write-Host "  2. 选择 'Restart Docker Desktop'" -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host "错误: 无法保存配置 - $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "请手动编辑 Docker Desktop 配置:" -ForegroundColor Yellow
    Write-Host "  1. 打开 Docker Desktop" -ForegroundColor Gray
    Write-Host "  2. 点击 Settings (设置)" -ForegroundColor Gray
    Write-Host "  3. 选择 Docker Engine" -ForegroundColor Gray
    Write-Host "  4. 编辑 JSON 配置" -ForegroundColor Gray
    Write-Host ""
    Write-Host "示例配置:" -ForegroundColor Cyan
    $exampleConfig = @{
        "registry-mirrors" = @("https://docker.mirrors.ustc.edu.cn")
    }
    $exampleConfig | ConvertTo-Json | Write-Host
}

