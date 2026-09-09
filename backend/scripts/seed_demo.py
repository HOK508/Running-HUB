"""演示数据生成脚本：清空活动相关数据，模拟 50 名用户使用系统

用法：backend/.venv/bin/python backend/scripts/seed_demo.py

生成内容：
- 模拟用户补齐到 50 名参与者 + 管理员
- 13 个活动：5 个已结束（含回顾帖/点赞/评论）、1 个进行中、7 个报名中
- 报名（含待确认/已确认/已拒绝）、签到、退出记录（含恶意退出）
- 模拟用户登录密码统一为 run123456
- 演示配图：先运行 scripts/generate_demo_images.py 生成封面和二维码，
  seed 会自动引用；未生成时自动跳过，任何环境无破图
"""
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt

from app.config import ACTIVITY_IMAGE_DIR
from app.database import SessionLocal
from app.models import (
    ACTIVITY_STATUS_APPROVED,
    SIGNUP_STATUS_CONFIRMED,
    SIGNUP_STATUS_PENDING,
    SIGNUP_STATUS_REJECTED,
    Activity,
    Checkin,
    PostComment,
    PostLike,
    PostReview,
    Signup,
    SignupCancellation,
    User,
)

random.seed(20260909)

PASSWORD_HASH = bcrypt.hashpw(b"run123456", bcrypt.gensalt()).decode()

COLLEGES = [
    "计算机学院", "电子信息学院", "通信工程学院", "自动化学院", "机械工程学院",
    "经济学院", "管理学院", "会计学院", "外国语学院", "人文艺术与数字媒体学院",
    "理学院", "材料与环境工程学院", "网络空间安全学院", "卓越学院", "国际教育学院",
]
SURNAMES = ["王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴", "徐", "孙",
            "马", "朱", "胡", "郭", "何", "林", "罗", "郑", "梁", "谢", "宋", "唐", "韩"]
GIVEN_NAMES = ["伟", "芳", "娜", "敏", "静", "磊", "军", "洋", "勇", "艳", "杰", "涛",
               "明", "超", "秀英", "霞", "平", "刚", "文轩", "子涵", "雨桐", "欣怡",
               "浩然", "梓睿", "宇轩", "诗涵", "一鸣", "思远", "嘉懿", "俊驰", "雨泽",
               "晨曦", "可欣", "若曦", "梦琪", "静怡", "志强", "建国", "晓峰", "丽丽"]
NICKNAMES = ["追风少年", "夜跑小王子", "晨跑打卡人", "风一样的女子", "半马选手",
             "越野小白", "配速五分配", "跑圈老张", "卷王跑者", "悠闲跑者",
             "操场钉子户", "环校路常客", "爬坡选手", "轻松跑选手", "间歇跑狂魔",
             "夜猫子跑者", "晨型人跑者", "慢慢跑不着急", "冲刺型选手", "快乐跑者"]

# ---------- 活动定义（细节丰富） ----------
ACTIVITIES = [
    # ---- 已结束（含回顾帖） ----
    dict(title="RUNing HUB杯·10公里耐力挑战赛", phase="ended",
         desc="本学期第一场大型耐力赛事！赛事设 10 公里全程组，赛道为田径场 400 米标准跑道 25 圈，"
              "沿途设 3 个补给点（水、电解质饮料、香蕉），配速员分 4'30/5'00/5'30/6'00 四档领跑。"
              "完赛可获得定制奖牌，前 20 名有 RUNhub 周边奖励。请提前 40 分钟到场领取号码布并热身。",
         location="学校田径场", start="2026-08-20 07:00:00", end="2026-08-20 10:00:00",
         deadline="2026-08-18 22:00:00", maxp=80, views=1256, group="QQ群 871524390",
         review=("10 公里耐力挑战赛圆满收官！本次共 76 名同学完赛，最快成绩 38 分 42 秒（计算机学院 陈浩然），"
                 "整体完赛率 96%，4 名同学因抽筋接受医疗点处理均无大碍。补给点西瓜最受欢迎，明年加量！",
                 None),
         like_range=(35, 55),
         comments=["38分42秒太强了，膜拜大佬！", "补给点的西瓜真的甜，明年再来！",
                   "第一次跑10公里，配速员带得特别稳", "完赛奖牌设计得很好看，已经挂床头了",
                   "4号补给点的志愿者小姐姐辛苦了", "明年我要进前20！", "赛后拉伸区很有用，腿没酸",
                   "第一次参加这种比赛，氛围太好了"]),
    dict(title="晨光唤醒·5公里校园晨跑", phase="ended",
         desc="一日之计在于晨！每周五 6:30 的固定晨跑活动，配速 6'30 轻松跑，路线为宿舍区→教学区→"
              "图书馆环线，全程约 5 公里。结束后食堂早餐窗口有专属优惠。适合刚接触跑步的同学，"
              "有领跑员全程陪同，掉队不慌。",
         location="宿舍区南门集合", start="2026-08-28 06:30:00", end="2026-08-28 08:00:00",
         deadline="2026-08-27 20:00:00", maxp=40, views=486, group="QQ群 672410958",
         # 已结束但未发布回顾（留给"回顾发布"模块演示）
         review=None, like_range=None, comments=[]),
    dict(title="荧光夜跑节·星空派对", phase="ended",
         desc="一年一度的荧光夜跑又来啦！环校路 3.5 公里荧光赛道，现场免费发放荧光棒、荧光手环、"
              "发光头饰，终点设星空主题拍照墙和音乐派对。欢迎穿白色 T 恤（荧光效果最佳）。"
              "温馨提示：夜跑注意安全，全程有志愿者在路口引导，请勿佩戴耳机。",
         location="环校路（南门起点）", start="2026-09-05 19:30:00", end="2026-09-05 21:30:00",
         deadline="2026-09-04 22:00:00", maxp=150, views=2143, group="QQ群 905218734",
         review=("本届荧光夜跑参与人数再创新高，共 148 人参加！荧光手环 3 分钟发光，拍照墙排队到活动结束。"
                 "音乐派对环节 15 位同学献唱。感谢 30 名志愿者的付出，我们明年见！",
                 None),
         like_range=(60, 90),
         comments=["今年规模好大，拍照墙太出片了！", "荧光手环质量比去年好，回家还亮着",
                   "夜跑路线灯光很足，安全感满满", "音乐派对藏龙卧虎，都好会唱",
                   "志愿者引导很到位，每个路口都有人", "明年一定早去抢荧光棒", "第一次夜跑，氛围绝了",
                   "白色T恤+荧光棒=最佳搭配", "和室友一起跑的，快乐加倍", "期待明年的主题！"]),
    dict(title="中秋夜跑·月下约跑", phase="ended",
         desc="中秋前夜，湖边赏月跑！校园湖畔步道 4.2 公里轻松跑，终点设赏月点，提供月饼和桂花茶。"
              "建议穿舒适跑鞋，带一件薄外套（湖边风大）。可带家属/好友一起参加（需分别报名）。",
         location="湖畔步道（东门集合）", start="2026-09-06 20:00:00", end="2026-09-06 22:00:00",
         deadline="2026-09-05 22:00:00", maxp=60, views=892, group="QQ群 521847093",
         # 已结束但未发布回顾（留给"回顾发布"模块演示）
         review=None, like_range=None, comments=[]),
    dict(title="新生杯·校园定向越野挑战赛", phase="ended",
         desc="专为新生设计的定向越野赛！校园内设 12 个打卡点，两人一组，手持地图寻找打卡点，"
              "按完成时间和打卡数排名。总路程约 6 公里。新生可借此快速熟悉校园，老生也可组队参加。"
              "请穿运动鞋，备好水。",
         location="教学区（主楼前集合）", start="2026-08-30 14:00:00", end="2026-08-30 17:00:00",
         deadline="2026-08-28 22:00:00", maxp=100, views=1047, group="QQ群 348715260",
         review=("定向越野赛共 48 支队伍完赛，最快队伍仅用 41 分钟找齐全部 12 个打卡点。"
                 "有 3 支队伍在图书馆附近迷路 20 分钟，最终在志愿者提示下完成。大家普遍反馈"
                 "比想象中累但特别有意思，已经有不少人预约了明年的比赛。",
                 None),
         like_range=(30, 50),
         comments=["迷路20分钟的就是我们队哈哈哈", "定向越野比普通跑步好玩多了",
                   "新生表示一周就把校园摸熟了", "地图画得很专业", "打卡点的隐藏位置太刁钻了",
                   "志愿者提示得很及时，感谢", "明年想挑战冠军纪录！"]),
    # ---- 进行中（今天） ----
    dict(title="教师节感恩跑·献给老师的公里数", phase="ongoing",
         desc="教师节特别活动！今天全天可在操场自由跑，每完成 1 公里记为给老师的 1 份祝福，"
              "活动结束后统计总公里数，以全体同学名义为老师们送上一份运动礼物。"
              "无需固定配速，跑多少都是心意。操场设打卡桌，跑完签到领取纪念贴纸。",
         location="学校田径场", start="2026-09-09 06:00:00", end="2026-09-09 22:00:00",
         deadline="2026-09-08 22:00:00", maxp=200, views=356, group="QQ群 714892305",
         review=None, like_range=None, comments=[]),
    # ---- 报名中 ----
    dict(title="马拉松训练营·第1期（基础配速篇）", phase="upcoming",
         desc="面向零基础到 10 公里水平同学的系统训练营第一期：讲解基础配速概念、跑步姿势纠正、"
              "呼吸节奏训练，含 40 分钟实操跑。后续还有耐力篇、间歇篇、赛前篇。"
              "报名要求：能连续跑 2 公里即可。请穿运动装到场，训练营提供统一号码背心。",
         location="田径场东侧集合", start="2026-09-15 18:30:00", end="2026-09-15 20:00:00",
         deadline="2026-09-13 22:00:00", maxp=50, views=214, group="QQ群 632948571",
         review=None, like_range=None, comments=[]),
    dict(title="秋日越野·校园后山探索跑", phase="upcoming",
         desc="校园后山越野步道首次开放！全程 8 公里，爬升约 150 米，路面为土路+碎石路混合，"
              "有一定难度，要求能完成 10 公里路跑者参加。沿途 2 个补水点，山顶观景台可俯瞰校园全景。"
              "强制装备：越野跑鞋或抓地力好的运动鞋、500ml 以上水具。",
         location="后山登山口集合", start="2026-09-20 08:00:00", end="2026-09-20 11:00:00",
         deadline="2026-09-18 22:00:00", maxp=45, views=537, group="QQ群 289437615",
         review=None, like_range=None, comments=[]),
    dict(title="国庆假期·西湖环湖半程拉练", phase="upcoming",
         desc="国庆假期第一天，环西湖半程马拉松拉练！全程 21.0975 公里，配速分 5'30 和 6'30 两组，"
              "配速员领跑，中途苏堤口设补给站。结束后南山路聚餐（自愿 AA）。"
              "要求：近一个月内完成过 15 公里以上长距离。请提前一晚保证睡眠。",
         location="西湖断桥集合", start="2026-10-02 06:00:00", end="2026-10-02 10:00:00",
         deadline="2026-09-30 22:00:00", maxp=30, views=768, group="QQ群 419683270",
         review=None, like_range=None, comments=[]),
    dict(title="情侣趣味跑·双人接力赛", phase="upcoming",
         desc="两人一组（情侣/闺蜜/兄弟均可）的双人趣味接力：每人跑 2 公里，交接点需完成趣味挑战"
              "（双人跳绳 10 个、背对背夹气球 20 米）。按总用时排名，前三名有情侣对戒造型奖杯。"
              "报名时备注队友姓名，单人报名将由组织方随机组队。",
         location="操场+环校路", start="2026-10-14 18:00:00", end="2026-10-14 20:00:00",
         deadline="2026-10-12 22:00:00", maxp=120, views=945, group="QQ群 573814902",
         review=None, like_range=None, comments=[]),
    dict(title="校庆杯·师生接力跑", phase="upcoming",
         desc="校庆 66 周年系列活动：师生混合接力赛！每队 6 人（至少 1 位老师），每人绕环校路 1 圈"
              "（约 1.8 公里）。老师们已有多支队伍报名，快来和老师同场竞技。"
              "比赛设最佳团队奖、最佳风采奖。赛后校庆纪念品人手一份。",
         location="环校路（校训石旁）", start="2026-10-18 09:00:00", end="2026-10-18 12:00:00",
         deadline="2026-10-16 22:00:00", maxp=180, views=671, group="QQ群 842563917",
         review=None, like_range=None, comments=[]),
    dict(title="双11剁手跑·燃烧卡路里", phase="upcoming",
         desc="双十一前夜，先跑步再剁手！环校路 5 公里自由跑，配速不限。完赛后在操场草坪的"
              "「卡路里夜市」凭跑步记录兑换小食券（跑 5 公里 = 1 张，跑 10 公里 = 3 张）。"
              "理性消费，从燃烧卡路里开始。",
         location="环校路（南门起点）", start="2026-11-11 19:00:00", end="2026-11-11 21:00:00",
         deadline="2026-11-09 22:00:00", maxp=150, views=312, group="QQ群 690275418",
         review=None, like_range=None, comments=[]),
    dict(title="期末减压跑·操场音乐夜", phase="upcoming",
         desc="期末周压力大？来操场边跑边听歌！操场设「点歌台」，报名时可提交想听的歌，"
              "跑步过程中循环播放。跑多少随缘，听歌为主，跑步为辅。现场提供热姜茶。",
         location="学校田径场", start="2026-12-20 19:30:00", end="2026-12-20 21:30:00",
         deadline="2026-12-18 22:00:00", maxp=100, views=158, group="QQ群 327519480",
         review=None, like_range=None, comments=[]),
]


def main() -> None:
    db = SessionLocal()

    # ---------- 1. 清空活动相关数据（保留用户） ----------
    for model in (PostComment, PostLike, PostReview, SignupCancellation, Checkin, Signup, Activity):
        db.query(model).delete()
    db.commit()
    print("已清空活动/报名/签到/退出/回顾/点赞/评论数据")

    # ---------- 2. 生成模拟用户，补齐到 50 名参与者 ----------
    TARGET_PARTICIPANTS = 50
    current = db.query(User).filter(User.is_admin == False).count()
    need = max(0, TARGET_PARTICIPANTS - current)
    existing_phones = {p for (p,) in db.query(User.phone).all()}
    existing_students = {s for (s,) in db.query(User.student_id).all()}
    new_users = []
    while len(new_users) < need:
        surname = random.choice(SURNAMES)
        given = random.choice(GIVEN_NAMES)
        gender = random.choice(["男", "女"])
        # 身份证：地区 + 出生 + 3位顺序码（第17位奇偶与性别一致）+ 校验位
        region = random.choice(["330102", "330106", "330108", "330109"])
        birth = f"{random.randint(2004, 2007)}{random.randint(1, 12):02d}{random.randint(1, 28):02d}"
        seq2 = str(random.randint(10, 99))
        last_seq = random.choice("13579" if gender == "男" else "02468")
        check = random.choice("0123456789X")
        id_card = region + birth + seq2 + last_seq + check
        phone = f"13{random.randint(3, 9)}{random.randint(10000000, 99999999)}"
        student_id = f"202{random.randint(2, 5)}{random.randint(100000, 999999)}"
        if phone in existing_phones or student_id in existing_students:
            continue
        existing_phones.add(phone)
        existing_students.add(student_id)
        nickname = f"{random.choice(NICKNAMES)}{random.randint(10, 99)}"
        user = User(
            phone=phone, password=PASSWORD_HASH, nickname=nickname,
            real_name=surname + given, gender=gender, student_id=student_id,
            college=random.choice(COLLEGES), id_card=id_card,
            wechat=f"wx_{phone[-6:]}", qq=str(random.randint(100000000, 999999999)),
        )
        db.add(user)
        new_users.append((user, id_card))
    db.commit()
    for u, _ in new_users:
        db.refresh(u)
    participants = list(db.query(User).filter(User.is_admin == False).all())
    print(f"用户就绪：共 {len(participants)} 名参与者（含现有用户），登录密码统一 run123456")

    # ---------- 3. 创建活动 ----------
    # 演示配图（backend/scripts/generate_demo_images.py 生成）：
    # 文件存在则引用（本地演示有封面和二维码）；不存在自动跳过，任何环境无破图
    def demo_img(name: str) -> str | None:
        return f"/uploads/activities/{name}" if (ACTIVITY_IMAGE_DIR / name).exists() else None

    created = []
    for i, spec in enumerate(ACTIVITIES, start=1):
        cover = demo_img(f"demo/cover_{i:02d}.png")
        qr = demo_img(f"demo/qr_{i:02d}.png")
        activity = Activity(
            title=spec["title"], description=spec["desc"],
            image_urls=json.dumps([cover]) if cover else None,
            location=spec["location"],
            start_time=datetime.strptime(spec["start"], "%Y-%m-%d %H:%M:%S"),
            end_time=datetime.strptime(spec["end"], "%Y-%m-%d %H:%M:%S"),
            signup_deadline=datetime.strptime(spec["deadline"], "%Y-%m-%d %H:%M:%S"),
            max_participants=spec["maxp"],
            view_count=spec["views"],
            group_info=spec["group"], group_qr_code=qr,
            creator_id=1, status=ACTIVITY_STATUS_APPROVED,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        created.append((activity, spec))
    print(f"活动就绪：{len(created)} 个")

    # ---------- 4. 报名 ----------
    def fill_signups(activity, spec, cap_ratio, confirmed_ratio, rejected_ratio):
        n = min(int(activity.max_participants * cap_ratio), len(participants))
        signers = random.sample(participants, n)
        for u in signers:
            r = random.random()
            if r < rejected_ratio:
                status = SIGNUP_STATUS_REJECTED
            elif r < rejected_ratio + confirmed_ratio:
                status = SIGNUP_STATUS_CONFIRMED
            else:
                status = SIGNUP_STATUS_PENDING
            db.add(Signup(user_id=u.id, activity_id=activity.id, status=status))

    for activity, spec in created:
        if spec["phase"] == "ended":
            fill_signups(activity, spec, 0.75, 0.9, 0.1)
        elif spec["phase"] == "ongoing":
            fill_signups(activity, spec, 0.4, 0.85, 0.05)
        else:
            fill_signups(activity, spec, 0.5, 0.35, 0.05)
    db.commit()
    total_signups = db.query(Signup).count()
    print(f"报名就绪：{total_signups} 条")

    # ---------- 5. 签到（已结束活动的已确认报名者，70% 签到） ----------
    checkin_count = 0
    for activity, spec in created:
        if spec["phase"] != "ended":
            continue
        confirmed = db.query(Signup).filter(
            Signup.activity_id == activity.id, Signup.status == SIGNUP_STATUS_CONFIRMED
        ).all()
        for s in random.sample(confirmed, int(len(confirmed) * 0.7)):
            t = activity.start_time + timedelta(minutes=random.randint(0, 60))
            db.add(Checkin(user_id=s.user_id, activity_id=activity.id, checkin_time=t))
            checkin_count += 1
    db.commit()
    print(f"签到就绪：{checkin_count} 条")

    # ---------- 6. 退出记录（8 条，2 条恶意） ----------
    reasons = ["临时有课冲突", "身体不适，医生建议休息", "家里临时有事", "临时要出差",
               "忘记当天有考试了", "脚踝扭伤未恢复", "课程调课撞时间了", "临时被导师叫去开会"]
    malicious_idx = {0, 4}
    cancel_count = 0
    for i in range(8):
        u = random.choice(participants)
        activity = random.choice([a for a, s in created if s["phase"] == "ended"])
        db.add(SignupCancellation(
            user_id=u.id, activity_id=activity.id, reason=reasons[i],
            is_malicious=i in malicious_idx,
            created_at=activity.signup_deadline - timedelta(days=random.randint(0, 3)),
        ))
        cancel_count += 1
    db.commit()
    print(f"退出记录就绪：{cancel_count} 条（含 {len(malicious_idx)} 条恶意）")

    # ---------- 7. 回顾帖 + 点赞 + 评论 ----------
    for activity, spec in created:
        if spec["phase"] != "ended" or not spec["review"]:
            continue
        content, images = spec["review"]
        review = PostReview(
            activity_id=activity.id, author_id=1, content=content,
            image_urls=str(images).replace("'", '"') if images else None,
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        lo, hi = spec["like_range"]
        like_n = min(hi, len(participants))
        likers = random.sample(participants, like_n)
        for u in likers:
            db.add(PostLike(user_id=u.id, activity_id=activity.id))
        for i, text in enumerate(spec["comments"]):
            u = random.choice(participants)
            db.add(PostComment(
                user_id=u.id, activity_id=activity.id, content=text,
                created_at=review.created_at + timedelta(hours=i + 1),
            ))
    db.commit()
    print(f"回顾帖/点赞/评论就绪（{db.query(PostReview).count()} 篇回顾）")

    # ---------- 汇总 ----------
    print("\n===== 演示数据生成完毕 =====")
    print(f"参与者：{len(participants)} 人（登录密码统一 run123456）")
    print(f"活动：{db.query(Activity).count()} 个（{sum(1 for a, s in created if s['phase']=='ended')} 已结束 / "
          f"{sum(1 for a, s in created if s['phase']=='ongoing')} 进行中 / "
          f"{sum(1 for a, s in created if s['phase']=='upcoming')} 报名中）")
    print(f"报名：{total_signups} 条 / 签到：{checkin_count} 条 / 退出：{cancel_count} 条")
    print(f"回顾帖：{db.query(PostReview).count()} 篇 / 点赞：{db.query(PostLike).count()} / 评论：{db.query(PostComment).count()}")
    db.close()


if __name__ == "__main__":
    main()
