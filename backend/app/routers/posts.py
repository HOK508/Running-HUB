"""帖子互动路由：回顾帖发布/列表、点赞/取消点赞、评论列表、发表评论

互动对象是"已结束 + 审核通过"的活动（回顾帖与活动 1:1，互动关联活动即关联帖子）。
点赞设计为幂等：重复点赞不报错不重复计数，取消未点的点赞同样安全——
前端按钮是 toggle 切换，幂等让并发/重复点击都得到正确结果。
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.exceptions import BizException
from app.models import (
    ACTIVITY_STATUS_APPROVED,
    Activity,
    PostComment,
    PostLike,
    PostReview,
    User,
)
from app.responses import ok
from app.schemas import CommentIn, ReviewPostIn

router = APIRouter(tags=["帖子互动"])


def _get_interactable_activity(db: Session, activity_id: int) -> Activity:
    """获取可互动的活动：必须已通过审核且已结束，否则报错"""
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status != ACTIVITY_STATUS_APPROVED:
        raise BizException(20001, "活动不存在")
    if activity.end_time > datetime.now():
        raise BizException(20006, "活动尚未结束，暂不开放互动")
    return activity


def _count(db: Session, model, activity_id: int) -> int:
    """点赞数/评论数统计"""
    return db.scalar(select(func.count(model.id)).where(model.activity_id == activity_id)) or 0


def _parse_image_urls(raw: str | None) -> list[str]:
    """JSON 字符串图片列表 → 列表"""
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []


@router.post("/api/activities/{activity_id}/review-post")
def publish_review(
    activity_id: int,
    body: ReviewPostIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布回顾帖：管理员或活动发起人，活动已结束，一个活动一篇"""
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status != ACTIVITY_STATUS_APPROVED:
        raise BizException(20001, "活动不存在")
    if activity.end_time > datetime.now():
        raise BizException(20006, "活动尚未结束，无法发布回顾")
    if not (user.is_admin or activity.creator_id == user.id):
        raise BizException(20002, "无权限操作该活动")
    if db.scalar(select(PostReview.id).where(PostReview.activity_id == activity_id)):
        raise BizException(20007, "该活动已发布过回顾")

    review = PostReview(
        activity_id=activity_id,
        author_id=user.id,
        content=body.content,
        image_urls=json.dumps(body.image_urls) if body.image_urls else None,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return ok(
        {
            "id": review.id,
            "activity_id": review.activity_id,
            "content": review.content,
            "image_urls": _parse_image_urls(review.image_urls),
            "created_at": review.created_at,
        }
    )


@router.get("/api/reviews")
def list_reviews(db: Session = Depends(get_db)):
    """回顾帖列表：按发布时间倒序，含活动信息、作者、点赞评论数"""
    rows = db.execute(
        select(
            PostReview,
            Activity,
            User,
            func.count(func.distinct(PostLike.id)).label("like_count"),
            func.count(func.distinct(PostComment.id)).label("comment_count"),
        )
        .join(Activity, Activity.id == PostReview.activity_id)
        .join(User, User.id == PostReview.author_id)
        .outerjoin(PostLike, PostLike.activity_id == Activity.id)
        .outerjoin(PostComment, PostComment.activity_id == Activity.id)
        .group_by(PostReview.id)
        .order_by(PostReview.created_at.desc())
    ).all()
    items = [
        {
            "id": r.id,
            "content": r.content,
            "image_urls": _parse_image_urls(r.image_urls),
            "like_count": like_count,
            "comment_count": comment_count,
            "created_at": r.created_at,
            "activity": {
                "id": a.id,
                "title": a.title,
                "location": a.location,
                "end_time": a.end_time,
                "view_count": a.view_count,
            },
            "author": {"nickname": u.nickname},
        }
        for r, a, u, like_count, comment_count in rows
    ]
    return ok(items)


@router.post("/api/activities/{activity_id}/like")
def like_activity(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """点赞（幂等）：已点过直接返回当前状态，不重复计数"""
    _get_interactable_activity(db, activity_id)

    exists = db.scalar(
        select(PostLike.id).where(
            PostLike.activity_id == activity_id, PostLike.user_id == user.id
        )
    )
    if exists is None:
        db.add(PostLike(user_id=user.id, activity_id=activity_id))
        db.commit()  # 唯一索引兜底：极端并发下重复插入会被拦截并抛错

    return ok({"liked": True, "like_count": _count(db, PostLike, activity_id)})


@router.delete("/api/activities/{activity_id}/like")
def unlike_activity(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消点赞（幂等）：没点过也返回正常"""
    _get_interactable_activity(db, activity_id)

    like = db.scalar(
        select(PostLike).where(
            PostLike.activity_id == activity_id, PostLike.user_id == user.id
        )
    )
    if like is not None:
        db.delete(like)
        db.commit()

    return ok({"liked": False, "like_count": _count(db, PostLike, activity_id)})


@router.get("/api/activities/{activity_id}/comments")
def list_comments(activity_id: int, db: Session = Depends(get_db)):
    """评论列表：按时间正序（楼层感）"""
    _get_interactable_activity(db, activity_id)

    rows = db.execute(
        select(PostComment, User)
        .join(User, User.id == PostComment.user_id)
        .where(PostComment.activity_id == activity_id)
        .order_by(PostComment.created_at)
    ).all()
    # 互动区统一使用昵称，真实姓名等身份信息不展示
    items = [
        {
            "id": c.id,
            "user_id": u.id,
            "nickname": u.nickname,
            "content": c.content,
            "created_at": c.created_at,
        }
        for c, u in rows
    ]
    return ok(items)


@router.post("/api/activities/{activity_id}/comments")
def create_comment(
    activity_id: int,
    body: CommentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发表评论"""
    _get_interactable_activity(db, activity_id)

    comment = PostComment(user_id=user.id, activity_id=activity_id, content=body.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return ok(
        {
            "id": comment.id,
            "user_id": user.id,
            "nickname": user.nickname,
            "content": comment.content,
            "created_at": comment.created_at,
        }
    )
