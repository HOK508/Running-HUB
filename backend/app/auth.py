"""JWT 认证与密码哈希：token 生成与校验、获取当前用户、管理员权限校验"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import ALGORITHM, SECRET_KEY, TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.exceptions import BizException
from app.models import User

# auto_error=False：请求头缺失时不自动报错，由 get_current_user 统一返回友好提示
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    """明文密码 → bcrypt 哈希（自带随机盐，同样明文每次结果不同）"""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与库中哈希是否匹配"""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int) -> str:
    """登录成功后签发 token，sub 存用户ID，24 小时过期"""
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖：校验 token 并返回当前登录用户

    任何需要登录的接口，在参数里声明 user: User = Depends(get_current_user) 即可。
    """
    if credentials is None:
        raise BizException(401, "未登录，请先登录", http_status=401)
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise BizException(401, "登录已过期，请重新登录", http_status=401)
    except jwt.InvalidTokenError:
        raise BizException(401, "无效的登录凭证", http_status=401)

    user = db.get(User, user_id)
    if user is None:
        raise BizException(401, "用户不存在", http_status=401)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """FastAPI 依赖：管理员专属接口使用，非管理员返回 403"""
    if not user.is_admin:
        raise BizException(403, "无权限：需要管理员身份", http_status=403)
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """可选登录：不带 token 返回 None（游客），带 token 则校验后返回用户

    用于"登录可选"的公开接口（如活动详情：公开活动游客可看，
    未审核活动需要判断查看者身份）。
    """
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise BizException(401, "登录已过期，请重新登录", http_status=401)
    except jwt.InvalidTokenError:
        raise BizException(401, "无效的登录凭证", http_status=401)

    user = db.get(User, user_id)
    if user is None:
        raise BizException(401, "用户不存在", http_status=401)
    return user
