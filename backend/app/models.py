"""SQLAlchemy 表模型：与 backend/sql/init.sql 一一对应

约定：建表以 init.sql 为唯一来源（source of truth），模型只做映射。
这样避免"SQL 里一套结构、代码里一套结构"的漂移问题。
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# ---------- 状态常量（避免散落的字符串字面量） ----------
# 活动审核状态
ACTIVITY_STATUS_PENDING = "pending"      # 待审核
ACTIVITY_STATUS_APPROVED = "approved"    # 已通过
ACTIVITY_STATUS_REJECTED = "rejected"    # 已拒绝

# 报名状态
SIGNUP_STATUS_PENDING = "pending"        # 待确认
SIGNUP_STATUS_CONFIRMED = "confirmed"    # 已确认
SIGNUP_STATUS_REJECTED = "rejected"      # 已拒绝


class User(Base):
    """用户表（手机号备案 + 密码登录 + 实名信息）"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="手机号/管理员序号（登录名）")
    password: Mapped[str] = mapped_column(String(100), nullable=False, comment="bcrypt 加密密码")
    nickname: Mapped[str | None] = mapped_column(String(50), comment="昵称")
    # 实名信息：普通用户必填，管理员账号为空
    real_name: Mapped[str | None] = mapped_column(String(50), comment="真实姓名")
    gender: Mapped[str | None] = mapped_column(String(10), comment="性别")
    student_id: Mapped[str | None] = mapped_column(String(30), unique=True, comment="学号")
    college: Mapped[str | None] = mapped_column(String(100), comment="学院")
    id_card: Mapped[str | None] = mapped_column(String(20), unique=True, comment="身份证号")
    wechat: Mapped[str | None] = mapped_column(String(50), comment="微信号")
    qq: Mapped[str | None] = mapped_column(String(20), comment="QQ号")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像URL（预留）")
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否管理员")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Activity(Base):
    """活动表"""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="活动名称")
    description: Mapped[str | None] = mapped_column(Text, comment="活动描述")
    image_urls: Mapped[str | None] = mapped_column(Text, comment="活动图片URL列表(JSON数组)")
    location: Mapped[str] = mapped_column(String(255), nullable=False, comment="活动地点")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="结束时间")
    signup_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="报名截止时间")
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False, comment="人数上限")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="浏览数（热度）")
    group_info: Mapped[str | None] = mapped_column(String(255), comment="加群方式文字")
    group_qr_code: Mapped[str | None] = mapped_column(String(255), comment="群二维码图片URL")
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="创建者ID")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ACTIVITY_STATUS_PENDING, index=True, comment="审核状态"
    )
    reject_reason: Mapped[str | None] = mapped_column(String(255), comment="拒绝理由")
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, comment="审核人ID")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="审核时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PostReview(Base):
    """回顾帖表（管理员/发起人在活动结束后发布的活动总结）"""

    __tablename__ = "post_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, comment="活动ID（一个活动一篇）")
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="发布人ID")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="活动整体情况介绍")
    image_urls: Mapped[str | None] = mapped_column(Text, comment="图片URL列表(JSON数组)")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PostLike(Base):
    """帖子点赞表（活动结束后开放互动）"""

    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_id", name="uk_user_activity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="点赞用户ID")
    activity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="活动ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PostComment(Base):
    """帖子评论表"""

    __tablename__ = "post_comments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="评论用户ID")
    activity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="活动ID")
    content: Mapped[str] = mapped_column(String(200), nullable=False, comment="评论内容")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Signup(Base):
    """报名表"""

    __tablename__ = "signups"
    __table_args__ = (
        # 数据库层面杜绝重复报名（并发安全的最终防线）
        UniqueConstraint("user_id", "activity_id", name="uk_user_activity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="报名用户ID")
    activity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="活动ID")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SIGNUP_STATUS_PENDING, comment="报名状态"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SignupCancellation(Base):
    """退出报名记录表（退出必须填原因，管理员可标记恶意退出）"""

    __tablename__ = "signup_cancellations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="退出用户ID")
    activity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="活动ID")
    reason: Mapped[str] = mapped_column(String(255), nullable=False, comment="退出报名原因")
    is_malicious: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否恶意退出")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Checkin(Base):
    """签到表"""

    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_id", name="uk_user_activity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="签到用户ID")
    activity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="活动ID")
    checkin_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="签到时间")


