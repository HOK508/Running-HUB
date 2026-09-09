"""活动模块路由：创建、图片上传、公开列表、详情、我的活动、审核、删除"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user, require_admin
from app.config import ACTIVITY_IMAGE_DIR, ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE
from app.database import get_db
from app.exceptions import BizException
from app.models import (
    ACTIVITY_STATUS_APPROVED,
    SIGNUP_STATUS_CONFIRMED,
    Activity,
    Checkin,
    PostComment,
    PostLike,
    PostReview,
    Signup,
    User,
)
from app.responses import ok
from app.schemas import ActivityCreateIn, ActivityUpdateIn

router = APIRouter(prefix="/api/activities", tags=["活动"])

# 注意路由声明顺序：/mine、/review/list 必须声明在 /{activity_id} 之前，
# 否则 "mine" 会被 /{activity_id} 当成路径参数匹配


def _phase(activity: Activity, now: datetime) -> str:
    """活动时间阶段：实时计算不存库"""
    if now < activity.signup_deadline:
        return "signup_open"
    if now < activity.start_time:
        return "signup_closed"
    if now <= activity.end_time:
        return "ongoing"
    return "ended"


def _signup_count(db: Session, activity_id: int) -> int:
    """已确认报名人数"""
    return db.scalar(
        select(func.count(Signup.id)).where(
            Signup.activity_id == activity_id,
            Signup.status == SIGNUP_STATUS_CONFIRMED,
        )
    )


def _activity_out(
    db: Session,
    activity: Activity,
    *,
    signup_count: int | None = None,
    include_audit: bool = False,
) -> dict:
    """活动对象 → 出参字典（phase 与报名人数实时计算）"""
    # image_urls 存的是 JSON 字符串，解析成列表返回
    image_urls = []
    if activity.image_urls:
        try:
            image_urls = json.loads(activity.image_urls)
        except (ValueError, TypeError):
            image_urls = []

    data = {
        "id": activity.id,
        "title": activity.title,
        "description": activity.description,
        "image_urls": image_urls,
        "location": activity.location,
        "start_time": activity.start_time,
        "end_time": activity.end_time,
        "signup_deadline": activity.signup_deadline,
        "max_participants": activity.max_participants,
        "view_count": activity.view_count,
        "creator_id": activity.creator_id,
        "status": activity.status,
        "phase": _phase(activity, datetime.now()),
        # 列表场景外部传入聚合好的 count，避免 N+1 查询
        "signup_count": signup_count if signup_count is not None else _signup_count(db, activity.id),
        "created_at": activity.created_at,
    }
    # 审核信息（拒绝理由等）只给创建者/管理员看
    if include_audit:
        data["reject_reason"] = activity.reject_reason
        data["reviewed_by"] = activity.reviewed_by
        data["reviewed_at"] = activity.reviewed_at
    return data


def _group_fields(db: Session, activity: Activity, user: User | None) -> dict:
    """群信息可见性：报名已确认者、创建者、管理员可见，其他人返回 null"""
    visible = user is not None and (
        user.is_admin
        or activity.creator_id == user.id
        or db.scalar(
            select(Signup.id).where(
                Signup.activity_id == activity.id,
                Signup.user_id == user.id,
                Signup.status == SIGNUP_STATUS_CONFIRMED,
            )
        )
        is not None
    )
    if visible:
        return {"group_info": activity.group_info, "group_qr_code": activity.group_qr_code}
    return {"group_info": None, "group_qr_code": None}


def _can_manage(activity: Activity, user: User) -> bool:
    """是否为创建者或管理员"""
    return user.is_admin or activity.creator_id == user.id


def _post_fields(db: Session, activity: Activity, user: User | None) -> dict:
    """帖子互动字段：点赞数、评论数、我是否点过赞"""
    like_count = (
        db.scalar(select(func.count(PostLike.id)).where(PostLike.activity_id == activity.id)) or 0
    )
    comment_count = (
        db.scalar(select(func.count(PostComment.id)).where(PostComment.activity_id == activity.id)) or 0
    )
    my_liked = False
    if user is not None:
        my_liked = (
            db.scalar(
                select(PostLike.id).where(
                    PostLike.activity_id == activity.id, PostLike.user_id == user.id
                )
            )
            is not None
        )
    return {"like_count": like_count, "comment_count": comment_count, "my_liked": my_liked}


def _review_fields(db: Session, activity: Activity) -> dict:
    """回顾帖内容（管理员/发起人发布的活动总结），未发布返回 None"""
    review = db.scalar(select(PostReview).where(PostReview.activity_id == activity.id))
    if review is None:
        return {"review": None}
    author = db.get(User, review.author_id)
    image_urls = []
    if review.image_urls:
        try:
            image_urls = json.loads(review.image_urls)
        except (ValueError, TypeError):
            image_urls = []
    return {
        "review": {
            "id": review.id,
            "content": review.content,
            "image_urls": image_urls,
            "author_nickname": author.nickname if author else None,
            "created_at": review.created_at,
        }
    }


def _my_signup_fields(db: Session, activity: Activity, user: User | None) -> dict:
    """当前用户的报名状态与签到状态（未登录返回空值，前端据此渲染按钮）"""
    if user is None:
        return {"my_signup": None, "checked_in": False}
    signup = db.scalar(
        select(Signup).where(
            Signup.activity_id == activity.id,
            Signup.user_id == user.id,
        )
    )
    checked_in = (
        db.scalar(
            select(Checkin.id).where(
                Checkin.activity_id == activity.id,
                Checkin.user_id == user.id,
            )
        )
        is not None
    )
    return {
        "my_signup": {"id": signup.id, "status": signup.status} if signup else None,
        "checked_in": checked_in,
    }


@router.post("/images")
async def upload_activity_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """上传活动图片/群二维码（不做 OCR，与跑步截图上传共用校验规则）"""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE_TYPES:
        raise BizException(50001, "仅支持 JPG/PNG 图片")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise BizException(50002, "图片不能超过 5MB")

    ACTIVITY_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    saved_name = f"{user.id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{ext}"
    (ACTIVITY_IMAGE_DIR / saved_name).write_bytes(content)
    return ok({"image_url": f"/uploads/activities/{saved_name}"})


@router.post("")
def create_activity(
    body: ActivityCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建活动：仅管理员可发布，创建后直接通过审核

    （产品决策：取消普通用户发布。原"普通用户创建待审核"逻辑保留在
    status 机制中，若未来重新开放用户发布，改回 get_current_user 即可。）
    """
    if body.start_time <= datetime.now():
        raise BizException(20005, "活动开始时间不能早于当前时间")

    activity = Activity(
        title=body.title,
        description=body.description,
        image_urls=json.dumps(body.image_urls) if body.image_urls else None,
        location=body.location,
        start_time=body.start_time,
        end_time=body.end_time,
        signup_deadline=body.signup_deadline,
        max_participants=body.max_participants,
        group_info=body.group_info,
        group_qr_code=body.group_qr_code,
        creator_id=admin.id,
        status=ACTIVITY_STATUS_APPROVED,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    data = _activity_out(db, activity, include_audit=True)
    data.update(_group_fields(db, activity, admin))
    return ok(data)


@router.get("")
def list_activities(db: Session = Depends(get_db)):
    """公开活动列表：仅审核通过的，按开始时间倒序，附已确认报名人数"""
    rows = db.execute(
        select(Activity, func.count(Signup.id))
        .outerjoin(
            Signup,
            (Signup.activity_id == Activity.id) & (Signup.status == SIGNUP_STATUS_CONFIRMED),
        )
        .where(
            Activity.status == ACTIVITY_STATUS_APPROVED,
            # 只展示未结束的活动；已结束的在"回顾"Tab（回顾帖）中展示
            Activity.end_time > datetime.now(),
        )
        .group_by(Activity.id)
        # 热度排序：浏览数降序（最火的在前），同浏览数按创建时间新的在前
        .order_by(Activity.view_count.desc(), Activity.created_at.desc())
    ).all()
    return ok([_activity_out(db, a, signup_count=c) for a, c in rows])


@router.get("/mine")
def my_activities(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我创建的活动：任何审核状态，含拒绝理由"""
    rows = db.execute(
        select(Activity, func.count(Signup.id))
        .outerjoin(
            Signup,
            (Signup.activity_id == Activity.id) & (Signup.status == SIGNUP_STATUS_CONFIRMED),
        )
        .where(Activity.creator_id == user.id)
        .group_by(Activity.id)
        .order_by(Activity.created_at.desc())
    ).all()
    items = []
    for a, c in rows:
        item = _activity_out(db, a, signup_count=c, include_audit=True)
        item.update(_group_fields(db, a, user))
        items.append(item)
    return ok(items)


@router.get("/all")
def all_activities(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """全部活动列表（管理面板用，管理员专属，含任何状态和回顾帖信息）"""
    rows = db.execute(
        select(Activity, func.count(Signup.id))
        .outerjoin(
            Signup,
            (Signup.activity_id == Activity.id) & (Signup.status == SIGNUP_STATUS_CONFIRMED),
        )
        .group_by(Activity.id)
        .order_by(Activity.created_at.desc())
    ).all()
    items = []
    for a, c in rows:
        item = _activity_out(db, a, signup_count=c, include_audit=True)
        item.update(_review_fields(db, a))
        items.append(item)
    return ok(items)


@router.get("/{activity_id}")
def activity_detail(
    activity_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """活动详情：审核通过的公开可见；待审核/被拒的仅创建者和管理员可见

    未审核活动对其他人返回"不存在"，不暴露其存在性。
    """
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise BizException(20001, "活动不存在")

    # 浏览数 +1：数据库原子自增（并发安全，无需加锁），热度排序的依据
    db.execute(
        update(Activity)
        .where(Activity.id == activity_id)
        .values(view_count=Activity.view_count + 1)
    )
    db.commit()
    activity.view_count += 1

    if activity.status != ACTIVITY_STATUS_APPROVED:
        if user is None or not _can_manage(activity, user):
            raise BizException(20001, "活动不存在")
        data = _activity_out(db, activity, include_audit=True)
        data.update(_group_fields(db, activity, user))
        data.update(_my_signup_fields(db, activity, user))
        data.update(_post_fields(db, activity, user))
        data.update(_review_fields(db, activity))
        return ok(data)
    data = _activity_out(db, activity)
    data.update(_group_fields(db, activity, user))
    data.update(_my_signup_fields(db, activity, user))
    data.update(_post_fields(db, activity, user))
    data.update(_review_fields(db, activity))
    return ok(data)


@router.put("/{activity_id}")
def update_activity(
    activity_id: int,
    body: ActivityUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """编辑活动（仅管理员，实时生效）：只更新提交的字段

    典型场景：微信群二维码过期后重新上传、修改活动时间/地点/人数等。
    """
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise BizException(20001, "活动不存在")

    data = body.model_dump(exclude_unset=True)
    if not data:
        raise BizException(20009, "没有需要更新的内容")

    # 时间关系校验：合并新老值后与创建接口同一套规则
    new_start = data.get("start_time", activity.start_time)
    new_end = data.get("end_time", activity.end_time)
    new_deadline = data.get("signup_deadline", activity.signup_deadline)
    if new_end <= new_start:
        raise BizException(20008, "结束时间必须晚于开始时间")
    if new_deadline > new_start:
        raise BizException(20008, "报名截止时间不能晚于开始时间")
    if "start_time" in data and data["start_time"] <= datetime.now():
        raise BizException(20005, "活动开始时间不能早于当前时间")

    for field, value in data.items():
        if field == "image_urls":
            value = json.dumps(value) if value else None
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)
    result = _activity_out(db, activity, include_audit=True)
    result.update(_group_fields(db, activity, admin))
    return ok(result)


@router.delete("/{activity_id}")
def delete_activity(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除活动：创建者或管理员"""
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise BizException(20001, "活动不存在")
    if not _can_manage(activity, user):
        raise BizException(20002, "无权限操作该活动")

    db.delete(activity)
    db.commit()
    return ok({"message": "活动已删除"})
