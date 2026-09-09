"""全局配置：数据库连接、JWT 密钥、文件存储路径等

配置来源（优先级从高到低）：环境变量 > backend/.env 文件 > 代码默认值
本地开发：复制 backend/.env.example 为 backend/.env 并填入真实值（.env 不入库）
生产部署：用环境变量注入（见 deploy/runhub.service）
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 后端根目录（backend/）
BACKEND_DIR = Path(__file__).resolve().parent.parent

# 加载 backend/.env（存在才加载，不存在则纯靠环境变量）
load_dotenv(BACKEND_DIR / ".env")

# 活动图片/二维码存储目录
ACTIVITY_IMAGE_DIR = BACKEND_DIR / "uploads" / "activities"

# 上传限制
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = ("jpg", "jpeg", "png")

# ---------- 数据库配置 ----------
DB_HOST = os.environ.get("RUNHUB_DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("RUNHUB_DB_PORT", "3306"))
DB_USER = os.environ.get("RUNHUB_DB_USER", "root")
# 密码不设默认值：未配置时启动即报错，避免带着弱密码上线
DB_PASSWORD = os.environ.get("RUNHUB_DB_PASSWORD", "")
DB_NAME = os.environ.get("RUNHUB_DB_NAME", "runhub")

# SQLAlchemy 连接串（pymysql 驱动）
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# ---------- JWT 配置 ----------
# 生产必须设置强随机值：python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.environ.get("RUNHUB_SECRET_KEY", "")
ALGORITHM = "HS256"
# token 有效期（分钟），24 小时
TOKEN_EXPIRE_MINUTES = 60 * 24
