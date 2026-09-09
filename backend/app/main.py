"""RUNhub 后端入口：创建 FastAPI 应用、注册中间件、异常处理和路由"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import BACKEND_DIR
from app.database import get_db
from app.exceptions import register_exception_handlers
from app.responses import ok
from app.routers import activities, checkins, posts, signups, users

app = FastAPI(
    title="RUNhub API",
    description="RUNhub 跑步活动管理系统后端接口",
    version="0.1.0",
)

# 跨域配置：开发阶段前端运行在 5173 端口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理：所有异常统一转为 {code, message, data} 格式
register_exception_handlers(app)

# 注册各模块路由
app.include_router(users.router)
app.include_router(activities.router)
app.include_router(signups.router)
app.include_router(checkins.router)
app.include_router(posts.router)

# 静态文件：上传的活动图片/二维码通过 /uploads/xxx 访问
uploads_dir = BACKEND_DIR / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/api/health")
def health():
    """健康检查：验证后端服务是否正常运行"""
    return ok({"service": "RUNhub", "status": "up"})


@app.get("/api/health/db")
def health_db(db=Depends(get_db)):
    """数据库连通性检查：验证后端能否连接 MySQL"""
    db.execute(text("SELECT 1"))
    return ok({"database": "connected"})
