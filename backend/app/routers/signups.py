"""报名模块路由：报名、取消报名、报名审核、报名列表、我的报名"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.exceptions import BizException
from app.models import (
    ACTIVITY_STATUS_APPROVED,
    SIGNUP_STATUS_CONFIRMED,
    SIGNUP_STATUS_PENDING,
    SIGNUP_STATUS_REJECTED,
    Activity,
    Checkin,
    Signup,
    SignupCancellation,
    User,
)
from app.responses import ok
from app.schemas import CancelSignupIn, MaliciousIn, SignupReviewIn

router = APIRouter(tags=["报名"])


@router.post("/api/activities/{activity_id}/signup")
def signup(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """报名活动

    防超卖：SELECT ... FOR UPDATE 锁定活动行，把"查人数 + 插入"变成原子操作——
    并发报名同一活动会被串行化，第二个请求必须等第一个提交后才能重新查人数。
    """
    # 锁定活动行（事务开始，锁持有到 commit/rollback）
    activity = db.execute(
        select(Activity).where(Activity.id == activity_id).with_for_update()
    ).scalar_one_or_none()
    if activity is None or activity.status != ACTIVITY_STATUS_APPROVED:
        db.rollback()
        raise BizException(30001, "活动不存在或未通过审核")

    # 锁内校验：报名截止时间
    if datetime.now() >= activity.signup_deadline:
        db.rollback()
        raise BizException(30002, "报名已截止")

    # 锁内校验：是否已报名（含被拒绝的历史记录）
    existing = db.scalar(
        select(Signup).where(Signup.user_id == user.id, Signup.activity_id == activity_id)
    )
    if existing is not None:
        db.rollback()
        if existing.status == SIGNUP_STATUS_REJECTED:
            raise BizException(30005, "报名已被拒绝，不能再次报名")
        raise BizException(30004, "已报名，请勿重复报名")

    # 锁内校验：已确认人数是否已满
    confirmed = db.scalar(
        select(func.count(Signup.id)).where(
            Signup.activity_id == activity_id,
            Signup.status == SIGNUP_STATUS_CONFIRMED,
        )
    )
    if confirmed >= activity.max_participants:
        db.rollback()
        raise BizException(30003, "名额已满")

    # 报名状态：一律 pending，由管理员在"报名信息"模块确认/拒绝
    status = SIGNUP_STATUS_PENDING

    signup = Signup(user_id=user.id, activity_id=activity_id, status=status)
    db.add(signup)
    db.commit()  # 提交并释放行锁
    db.refresh(signup)

    # 群信息只在确认后可见：pending 报名不返回（与详情页可见性规则一致）
    group_info = activity.group_info if status == SIGNUP_STATUS_CONFIRMED else None
    group_qr_code = activity.group_qr_code if status == SIGNUP_STATUS_CONFIRMED else None
    return ok(
        {
            "id": signup.id,
            "activity_id": activity_id,
            "status": signup.status,
            "created_at": signup.created_at,
            "group_info": group_info,
            "group_qr_code": group_qr_code,
        }
    )


@router.post("/api/activities/{activity_id}/signup/cancel")
def cancel_signup(
    activity_id: int,
    body: CancelSignupIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """退出报名：必须填写原因（记入退出记录，管理员可标记恶意退出）

    取消 = 删除报名 + 留存退出记录（原因、时间），取消后可重新报名。
    """
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise BizException(30001, "活动不存在或未通过审核")
    if datetime.now() >= activity.signup_deadline:
        raise BizException(30007, "已过报名截止时间，无法取消")

    signup = db.scalar(
        select(Signup).where(Signup.user_id == user.id, Signup.activity_id == activity_id)
    )
    if signup is None:
        raise BizException(30006, "未报名该活动")
    if signup.status == SIGNUP_STATUS_REJECTED:
        raise BizException(30005, "报名已被拒绝，无法取消")

    # 留存退出记录 + 删除报名
    cancellation = SignupCancellation(
        user_id=user.id, activity_id=activity_id, reason=body.reason
    )
    db.add(cancellation)
    db.delete(signup)
    db.commit()
    return ok({"message": "已退出报名"})


@router.get("/api/signups/all")
def all_signups(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """全部报名记录（管理面板"报名信息"页，含完整身份信息）"""
    rows = db.execute(
        select(Signup, User, Activity)
        .join(User, User.id == Signup.user_id)
        .join(Activity, Activity.id == Signup.activity_id)
        .order_by(Signup.created_at.desc())
    ).all()
    items = [
        {
            "id": s.id,
            "status": s.status,
            "created_at": s.created_at,
            "user": {
                "id": u.id,
                "nickname": u.nickname,
                "real_name": u.real_name,
                "gender": u.gender,
                "student_id": u.student_id,
                "college": u.college,
                "phone": u.phone,
                "id_card": u.id_card,
                "wechat": u.wechat,
                "qq": u.qq,
            },
            "activity": {"id": a.id, "title": a.title},
        }
        for s, u, a in rows
    ]
    return ok(items)


@router.get("/api/signups/no-shows")
def no_shows(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """违约清单：已确认报名、活动已结束、但从未签到

    违约由数据推导（能算的不存）：confirmed 报名 + 活动结束 + 无签到记录。
    """
    rows = db.execute(
        select(Signup, User, Activity)
        .join(User, User.id == Signup.user_id)
        .join(Activity, Activity.id == Signup.activity_id)
        .where(
            Signup.status == SIGNUP_STATUS_CONFIRMED,
            Activity.end_time < datetime.now(),
            ~exists().where(
                Checkin.user_id == Signup.user_id,
                Checkin.activity_id == Signup.activity_id,
            ),
        )
        .order_by(Activity.end_time.desc())
    ).all()
    items = [
        {
            "id": s.id,
            "user": {"id": u.id, "nickname": u.nickname, "real_name": u.real_name},
            "activity": {"id": a.id, "title": a.title, "end_time": a.end_time},
        }
        for s, u, a in rows
    ]
    return ok(items)


@router.get("/api/signups/cancellations")
def list_cancellations(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """全部退出报名记录（管理面板"退出记录"页）"""
    rows = db.execute(
        select(SignupCancellation, User, Activity)
        .join(User, User.id == SignupCancellation.user_id)
        .join(Activity, Activity.id == SignupCancellation.activity_id)
        .order_by(SignupCancellation.created_at.desc())
    ).all()
    items = [
        {
            "id": c.id,
            "reason": c.reason,
            "is_malicious": c.is_malicious,
            "created_at": c.created_at,
            "user": {"id": u.id, "nickname": u.nickname, "real_name": u.real_name},
            "activity": {"id": a.id, "title": a.title},
        }
        for c, u, a in rows
    ]
    return ok(items)


@router.put("/api/signups/cancellations/{cancellation_id}/malicious")
def mark_malicious(
    cancellation_id: int,
    body: MaliciousIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员标记/取消标记恶意退出（用于统计恶意退出次数）"""
    cancellation = db.get(SignupCancellation, cancellation_id)
    if cancellation is None:
        raise BizException(30011, "退出记录不存在")
    cancellation.is_malicious = body.is_malicious
    db.commit()
    return ok(
        {
            "id": cancellation.id,
            "is_malicious": cancellation.is_malicious,
        }
    )


@router.put("/api/signups/{signup_id}/review")
def review_signup(
    signup_id: int,
    body: SignupReviewIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员确认/拒绝报名（约跑活动的 pending 报名）

    确认时同样防超员：锁定活动行后统计，已满则拒绝确认。
    """
    signup = db.get(Signup, signup_id)
    if signup is None:
        raise BizException(30008, "报名记录不存在")
    if signup.status != SIGNUP_STATUS_PENDING:
        raise BizException(30009, "该报名已处理，不能重复审核")

    if body.action == "confirm":
        # 锁活动行，串行化同一活动的并发确认
        activity = db.execute(
            select(Activity).where(Activity.id == signup.activity_id).with_for_update()
        ).scalar_one_or_none()
        confirmed = db.scalar(
            select(func.count(Signup.id)).where(
                Signup.activity_id == signup.activity_id,
                Signup.status == SIGNUP_STATUS_CONFIRMED,
            )
        )
        if activity is None or confirmed >= activity.max_participants:
            db.rollback()
            raise BizException(30010, "名额已满，无法确认报名")
        signup.status = SIGNUP_STATUS_CONFIRMED
    else:
        signup.status = SIGNUP_STATUS_REJECTED

    db.commit()
    db.refresh(signup)
    return ok({"id": signup.id, "status": signup.status})


@router.get("/api/activities/{activity_id}/signups")
def list_signups(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """某活动的报名列表：仅创建者或管理员可见"""
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise BizException(30001, "活动不存在或未通过审核")
    if not (user.is_admin or activity.creator_id == user.id):
        raise BizException(20002, "无权限操作该活动")

    rows = db.execute(
        select(Signup, User)
        .join(User, User.id == Signup.user_id)
        .where(Signup.activity_id == activity_id)
        .order_by(Signup.created_at)
    ).all()
    items = []
    for s, u in rows:
        item = {
            "id": s.id,
            "user_id": u.id,
            "nickname": u.nickname,
            "status": s.status,
            "created_at": s.created_at,
        }
        # 具体身份信息仅管理员可见（发起人和其他人只能看到昵称+状态）
        if user.is_admin:
            item.update(
                {
                    "real_name": u.real_name,
                    "gender": u.gender,
                    "student_id": u.student_id,
                    "college": u.college,
                    "phone": u.phone,
                    "id_card": u.id_card,
                    "wechat": u.wechat,
                    "qq": u.qq,
                }
            )
        items.append(item)
    return ok({"activity_id": activity_id, "total": len(items), "items": items})


@router.get("/api/signups/pending")
def pending_signups(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """全部待确认报名列表（管理员面板用，按提交时间排序）"""
    rows = db.execute(
        select(Signup, Activity, User)
        .join(Activity, Activity.id == Signup.activity_id)
        .join(User, User.id == Signup.user_id)
        .where(Signup.status == SIGNUP_STATUS_PENDING)
        .order_by(Signup.created_at)
    ).all()
    items = [
        {
            "id": s.id,
            "status": s.status,
            "created_at": s.created_at,
            "activity": {"id": a.id, "title": a.title},
            "user": {
                "id": u.id,
                "nickname": u.nickname,
                "real_name": u.real_name,
                "student_id": u.student_id,
                "college": u.college,
            },
        }
        for s, a, u in rows
    ]
    return ok(items)


@router.get("/api/signups/mine")
def my_signups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我报名的活动列表（个人主页"参加过的活动"），含是否已签到"""
    rows = db.execute(
        select(Signup, Activity, Checkin.id)
        .join(Activity, Activity.id == Signup.activity_id)
        .outerjoin(
            Checkin,
            (Checkin.activity_id == Signup.activity_id) & (Checkin.user_id == Signup.user_id),
        )
        .where(Signup.user_id == user.id)
        .order_by(Signup.created_at.desc())
    ).all()
    items = [
        {
            "id": s.id,
            "status": s.status,
            "checked_in": checkin_id is not None,
            "created_at": s.created_at,
            "activity": {
                "id": a.id,
                "title": a.title,
                "location": a.location,
                "start_time": a.start_time,
                "status": a.status,
            },
        }
        for s, a, checkin_id in rows
    ]
    return ok(items)
