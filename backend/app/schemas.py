"""Pydantic 请求/响应模型：负责接口出入参的校验与序列化

注意：因为统一响应格式是 {code, message, data}，路由不设置 response_model，
出参序列化在各路由里用 Out 模型显式转换（见 routers/users.py 的示例）。
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------- 用户模块 ----------

class RegisterIn(BaseModel):
    """注册入参：手机号备案 + 密码 + 实名信息一次提交"""

    phone: str = Field(pattern=r"^1\d{10}$", description="手机号（11位）")
    password: str = Field(min_length=6, max_length=32, description="密码：6~32 位")
    nickname: str | None = Field(default=None, min_length=1, max_length=50, description="昵称（选填，留空默认跑友+尾号）")
    real_name: str = Field(min_length=1, max_length=50, description="真实姓名")
    gender: Literal["男", "女"] = Field(description="性别")
    student_id: str = Field(min_length=1, max_length=30, description="学号")
    college: str = Field(min_length=1, max_length=100, description="学院")
    id_card: str = Field(pattern=r"^\d{17}[\dXx]$", description="身份证号（18位）")
    wechat: str = Field(min_length=1, max_length=50, description="微信号")
    qq: str = Field(min_length=1, max_length=20, description="QQ号")


class LoginIn(BaseModel):
    """登录入参：学生 11 位手机号，管理员序号 000~004"""

    phone: str = Field(pattern=r"^(1\d{10}|00[0-4])$", description="手机号或管理员序号")
    password: str = Field(min_length=1)


class ChangePasswordIn(BaseModel):
    """修改密码入参"""

    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=32, description="新密码：6~32 位")


class UpdateProfileIn(BaseModel):
    """修改个人信息入参：所有字段选填，只更新提交的字段

    （手机号/学号/身份证号修改前会做唯一性校验）
    """

    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, pattern=r"^1\d{10}$", description="手机号（登录账号）")
    real_name: str | None = Field(default=None, min_length=1, max_length=50)
    gender: Literal["男", "女"] | None = Field(default=None, description="性别")
    student_id: str | None = Field(default=None, min_length=1, max_length=30)
    college: str | None = Field(default=None, min_length=1, max_length=100)
    id_card: str | None = Field(default=None, pattern=r"^\d{17}[\dXx]$")
    wechat: str | None = Field(default=None, min_length=1, max_length=50)
    qq: str | None = Field(default=None, min_length=1, max_length=20)


class UserOut(BaseModel):
    """用户信息输出模型（永远不包含 password 字段）

    仅用于"本人视角"接口（登录/注册返回、查看自己），
    他人视角（报名列表等）由各接口手动脱敏构造。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    nickname: str | None = None
    # 实名信息（管理员账号为 None）
    real_name: str | None = None
    gender: str | None = None
    student_id: str | None = None
    college: str | None = None
    id_card: str | None = None
    wechat: str | None = None
    qq: str | None = None
    avatar: str | None = None
    is_admin: bool = False
    created_at: datetime


# ---------- 活动模块 ----------

class ActivityCreateIn(BaseModel):
    """创建活动入参"""

    title: str = Field(min_length=1, max_length=100, description="活动名称")
    description: str | None = Field(default=None, max_length=2000, description="活动描述")
    image_urls: list[str] = Field(default_factory=list, max_length=9, description="活动图片URL列表（最多9张）")
    location: str = Field(min_length=1, max_length=255, description="活动地点")
    start_time: datetime = Field(description="开始时间")
    end_time: datetime = Field(description="结束时间")
    signup_deadline: datetime = Field(description="报名截止时间")
    max_participants: int = Field(ge=1, le=100000, description="人数上限")
    group_info: str | None = Field(default=None, max_length=255, description="加群方式文字（群号/链接）")
    group_qr_code: str | None = Field(default=None, max_length=255, description="群二维码图片URL")

    @field_validator("start_time", "end_time", "signup_deadline", mode="after")
    @classmethod
    def to_local_naive(cls, v: datetime) -> datetime:
        """前端 Date 对象序列化后是 UTC 格式（带 Z），转成本地时间并去掉时区标记

        否则带时区和不带时区的时间比较会抛异常（500），且用户选的时间会偏移 8 小时。
        """
        if v.tzinfo is not None:
            return v.astimezone().replace(tzinfo=None)
        return v

    @model_validator(mode="after")
    def check_time_order(self):
        """参数间联动校验：字段本身合法，但字段之间的关系也要合法

        单字段校验（长度、类型）用 Field，字段间关系用 model_validator。
        """
        if self.end_time <= self.start_time:
            raise ValueError("end_time 必须晚于 start_time")
        if self.signup_deadline > self.start_time:
            raise ValueError("signup_deadline 不能晚于 start_time")
        return self


class ActivityUpdateIn(BaseModel):
    """编辑活动入参：所有字段选填，只更新提交的字段

    时间关系校验在路由里合并新老值后进行（与创建接口共用同一套规则）。
    """

    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    image_urls: list[str] | None = Field(default=None, max_length=9, description="活动图片URL列表（传空数组清空）")
    location: str | None = Field(default=None, min_length=1, max_length=255)
    start_time: datetime | None = None
    end_time: datetime | None = None
    signup_deadline: datetime | None = None
    max_participants: int | None = Field(default=None, ge=1, le=100000)
    group_info: str | None = Field(default=None, max_length=255, description="加群方式（传空字符串清空）")
    group_qr_code: str | None = Field(default=None, max_length=255, description="群二维码图片URL")

    @field_validator("start_time", "end_time", "signup_deadline", mode="after")
    @classmethod
    def to_local_naive(cls, v: datetime | None) -> datetime | None:
        """与创建接口一致：带时区的时间转本地并去掉时区标记"""
        if v is not None and v.tzinfo is not None:
            return v.astimezone().replace(tzinfo=None)
        return v


# ---------- 报名模块 ----------

class SignupReviewIn(BaseModel):
    """报名审核入参"""

    action: Literal["confirm", "reject"] = Field(description="confirm 确认 / reject 拒绝")


class CancelSignupIn(BaseModel):
    """退出报名入参（必须填写原因）"""

    reason: str = Field(min_length=1, max_length=255, description="退出报名原因")


class MaliciousIn(BaseModel):
    """恶意退出标记入参"""

    is_malicious: bool = Field(description="是否标记为恶意退出")


# ---------- 帖子互动模块 ----------

class CommentIn(BaseModel):
    """发表评论入参"""

    content: str = Field(min_length=1, max_length=200, description="评论内容（1~200字）")


class ReviewPostIn(BaseModel):
    """发布回顾帖入参"""

    content: str = Field(min_length=1, max_length=2000, description="活动整体情况介绍（1~2000字）")
    image_urls: list[str] = Field(default_factory=list, max_length=9, description="图片URL列表（最多9张）")
