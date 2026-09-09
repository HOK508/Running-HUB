"""签到模块路由：签到、签到列表、我的签到"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.exceptions import BizException
from app.models import (
    ACTIVITY_STATUS_APPROVED,
    SIGNUP_STATUS_CONFIRMED,
    Activity,
    Checkin,
    Signup,
    User,
)
from app.responses import ok

router = APIRouter(tags=["签到"])


@router.post("/api/activities/{activity_id}/checkin")
def checkin(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """签到：已报名且报名已确认的用户可签到，一人一活动一次

    防重复签到：与报名不同，签到没有人数统计，不需要行锁——
    代码查询 + 唯一索引兜底即可（并发重复由索引拦截）。
    """
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status != ACTIVITY_STATUS_APPROVED:
        raise BizException(30001, "活动不存在或未通过审核")

    signup = db.scalar(
        select(Signup).where(Signup.user_id == user.id, Signup.activity_id == activity_id)
    )
    if signup is None:
        raise BizException(40001, "未报名该活动，无法签到")
    if signup.status != SIGNUP_STATUS_CONFIRMED:
        raise BizException(40002, "报名未确认，无法签到")

    exists = db.scalar(
        select(Checkin.id).where(Checkin.user_id == user.id, Checkin.activity_id == activity_id)
    )
    if exists:
        raise BizException(40003, "已签到，请勿重复签到")

    checkin = Checkin(user_id=user.id, activity_id=activity_id)
    db.add(checkin)
    try:
        db.commit()
    except IntegrityError:
        # 并发重复签到的兜底：唯一索引 (user_id, activity_id) 拦截
        db.rollback()
        raise BizException(40003, "已签到，请勿重复签到")
    db.refresh(checkin)
    return ok(
        {
            "id": checkin.id,
            "user_id": checkin.user_id,
            "activity_id": checkin.activity_id,
            "checkin_time": checkin.checkin_time,
        }
    )


@router.get("/api/activities/{activity_id}/checkins")
def list_checkins(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """签到列表：仅创建者或管理员可见"""
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise BizException(30001, "活动不存在或未通过审核")
    if not (user.is_admin or activity.creator_id == user.id):
        raise BizException(20002, "无权限操作该活动")

    rows = db.execute(
        select(Checkin, User)
        .join(User, User.id == Checkin.user_id)
        .where(Checkin.activity_id == activity_id)
        .order_by(Checkin.checkin_time)
    ).all()
    items = []
    for c, u in rows:
        item = {
            "id": c.id,
            "user_id": u.id,
            "nickname": u.nickname,
            "checkin_time": c.checkin_time,
        }
        # 具体身份信息仅管理员可见
        if user.is_admin:
            item.update(
                {
                    "real_name": u.real_name,
                    "gender": u.gender,
                    "student_id": u.student_id,
                    "college": u.college,
                    "phone": u.phone,
                }
            )
        items.append(item)
    return ok({"activity_id": activity_id, "total": len(items), "items": items})


@router.get("/api/activities/{activity_id}/attendance")
def attendance(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """签到清单：已确认报名者的签到情况，未签到的排前面重点标注

    管理员可见实名信息，发起人只见昵称。
    """
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise BizException(30001, "活动不存在或未通过审核")
    if not (user.is_admin or activity.creator_id == user.id):
        raise BizException(20002, "无权限操作该活动")

    rows = db.execute(
        select(Signup, User, Checkin.checkin_time)
        .join(User, User.id == Signup.user_id)
        .outerjoin(
            Checkin,
            (Checkin.activity_id == Signup.activity_id)
            & (Checkin.user_id == Signup.user_id),
        )
        .where(Signup.activity_id == activity_id, Signup.status == SIGNUP_STATUS_CONFIRMED)
    ).all()

    items = []
    for s, u, checkin_time in rows:
        item = {
            "signup_id": s.id,
            "user_id": u.id,
            "nickname": u.nickname,
            "checked_in": checkin_time is not None,
            "checkin_time": checkin_time,
        }
        if user.is_admin:
            item.update(
                {
                    "real_name": u.real_name,
                    "student_id": u.student_id,
                    "college": u.college,
                    "phone": u.phone,
                }
            )
        items.append(item)

    # 未签到的排前面（重点标注）
    items.sort(key=lambda x: x["checked_in"])
    return ok(
        {
            "activity_id": activity_id,
            "total": len(items),
            "checked_in_count": sum(1 for i in items if i["checked_in"]),
            "items": items,
        }
    )


@router.get("/api/checkins/mine")
def my_checkins(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的签到记录"""
    rows = db.execute(
        select(Checkin, Activity)
        .join(Activity, Activity.id == Checkin.activity_id)
        .where(Checkin.user_id == user.id)
        .order_by(Checkin.checkin_time.desc())
    ).all()
    items = [
        {
            "id": c.id,
            "checkin_time": c.checkin_time,
            "activity": {"id": a.id, "title": a.title, "start_time": a.start_time},
        }
        for c, a in rows
    ]
    return ok(items)
