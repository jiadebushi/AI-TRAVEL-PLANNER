"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, plan, budget
from app.api import voice_realtime
from config import settings

# 创建FastAPI应用实例
app = FastAPI(
    title="AI智能旅行规划后端API",
    description="基于AI的智能旅行规划平台后端服务",
    version="1.0.0"
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(auth.users_router)
app.include_router(plan.router)
app.include_router(budget.router)
app.include_router(voice_realtime.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI智能旅行规划后端API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )


