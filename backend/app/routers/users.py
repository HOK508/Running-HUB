"""用户模块路由：注册（手机号备案+实名）、登录、个人信息、修改密码"""
from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.exceptions import BizException
from app.models import User
from app.responses import ok
from app.schemas import ChangePasswordIn, LoginIn, RegisterIn, UpdateProfileIn, UserOut

router = APIRouter(prefix="/api/users", tags=["用户"])


def _user_out(user: User) -> dict:
    """用户对象 → 出参字典（永不含密码字段，本人视角含完整实名信息）"""
    return UserOut.model_validate(user).model_dump()


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """注册：手机号备案 + 密码 + 实名信息一次提交，成功后自动登录

    唯一性三重校验：手机号 / 学号 / 身份证号（一个 userid 对应一个人）。
    """
    # 1. 逐项查重（友好报错，明确告知哪一项重复）
    if db.scalar(select(User).where(User.phone == body.phone)):
        raise BizException(10001, "该手机号已注册")
    if db.scalar(select(User).where(User.student_id == body.student_id)):
        raise BizException(10005, "该学号已注册")
    if db.scalar(select(User).where(User.id_card == body.id_card)):
        raise BizException(10006, "该身份证号已注册")

    # 2. 创建用户（昵称留空默认 跑友+手机尾号）
    user = User(
        phone=body.phone,
        password=hash_password(body.password),
        nickname=body.nickname or f"跑友{body.phone[-4:]}",
        real_name=body.real_name,
        gender=body.gender,
        student_id=body.student_id,
        college=body.college,
        id_card=body.id_card.upper(),
        wechat=body.wechat,
        qq=body.qq,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发注册兜底：数据库唯一索引拦截（具体哪项重复无法区分，给通用提示）
        db.rollback()
        raise BizException(10001, "手机号/学号/身份证号已存在，请检查")

    db.refresh(user)
    # 3. 注册成功自动登录
    return ok({"token": create_token(user.id), "user": _user_out(user)})


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    """登录：手机号 + 密码"""
    user = db.scalar(select(User).where(User.phone == body.phone))
    # 统一报错文案，不区分"手机号未注册"与"密码错误"，防止撞库探测
    if user is None or not verify_password(body.password, user.password):
        raise BizException(10002, "手机号或密码错误")
    return ok({"token": create_token(user.id), "user": _user_out(user)})


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    """查看当前登录用户信息（本人视角，含完整实名信息）"""
    return ok(_user_out(user))


@router.put("/me")
def update_me(
    body: UpdateProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改个人信息：所有字段选填，只更新提交的字段

    手机号/学号/身份证号修改前做唯一性校验（排除自己）。
    手机号是登录账号，修改后下次登录用新手机号。
    """
    data = body.model_dump(exclude_unset=True)  # 只取提交了的字段

    # 唯一性校验（改了的字段才查，且排除自己）
    if "phone" in data and data["phone"] != user.phone:
        if db.scalar(select(User).where(User.phone == data["phone"], User.id != user.id)):
            raise BizException(10001, "该手机号已被其他用户使用")
    if "student_id" in data and data["student_id"] != user.student_id:
        if db.scalar(
            select(User).where(User.student_id == data["student_id"], User.id != user.id)
        ):
            raise BizException(10005, "该学号已被其他用户使用")
    if "id_card" in data and data["id_card"].upper() != user.id_card:
        if db.scalar(
            select(User).where(User.id_card == data["id_card"].upper(), User.id != user.id)
        ):
            raise BizException(10006, "该身份证号已被其他用户使用")

    # 逐字段更新
    for field, value in data.items():
        if field == "id_card":
            value = value.upper()
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return ok(_user_out(user))


@router.post("/change-password")
def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码：校验旧密码 → 校验新旧不同 → bcrypt 加密更新"""
    if not verify_password(body.old_password, user.password):
        raise BizException(10003, "旧密码错误")
    if body.old_password == body.new_password:
        raise BizException(10004, "新密码不能与旧密码相同")
    user.password = hash_password(body.new_password)
    db.commit()
    return ok({"message": "密码修改成功"})
