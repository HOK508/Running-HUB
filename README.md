# RUNing HUB

从活动发布、实名报名、签到管理到回顾互动的一站式跑步活动系统。

## 功能特性

### 账号体系
- **实名注册**：手机号 + 密码，姓名、性别、学号、学院、身份证号、微信号、QQ号 一次绑定
- 手机号 / 学号 / 身份证号三重唯一约束，一人一号（固定 userid）
- **5 个管理员席位**（序号 `000`~`004`）：只凭序号 + 密码登录，无需实名信息
- 统一登录入口：学生输手机号、管理员输序号

### 活动管理
- 管理员发布活动：文字介绍 + 图片（最多 9 张）+ 加群方式 + 群二维码
- 活动**实时编辑**：信息、时间、图片、二维码随时更新（如微信群二维码过期更换）
- **热度排序**：浏览数实时统计，最火的活动排前面

### 报名与签到
- 报名提交后进入**待确认**，管理员在报名信息台逐条确认 / 拒绝
- 被拒绝后不能再次报名同一活动；名额上限并发保护（数据库行锁防超卖）
- 报名确认后可见加群方式（弹窗直达 + 详情页展示）
- **退出报名必须填写原因**，管理员可标记"恶意退出"，按人统计退出次数
- 签到清单**重点标注未签到人员**；活动结束后自动生成**违约记录**（按人统计违约次数）

### 回顾互动
- 活动结束后管理员发布**回顾帖**（活动总结 + 图片）
- 点赞（幂等）、评论互动
- 互动区一律使用昵称展示，实名信息严格保护

### 隐私设计
- 互动区（点赞/评论/回顾）只显示昵称
- 报名者的实名信息（姓名/学号/学院/手机号/身份证号等）**仅管理员可见**

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.13 · FastAPI · SQLAlchemy 2 · PyMySQL |
| 数据库 | MySQL 8（utf8mb4） |
| 前端 | Vue 3 · Vite · Vue Router · Axios · Element Plus |
| 认证 | JWT（HS256）+ bcrypt 密码加密 |
| 部署 | Nginx + systemd（配置见 deploy/） |

## 目录结构

```
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 应用入口
│   │   ├── config.py       # 配置（环境变量 / .env）
│   │   ├── models.py       # SQLAlchemy 表模型
│   │   ├── schemas.py      # Pydantic 请求/响应模型
│   │   ├── auth.py         # JWT 签发与校验、权限依赖
│   │   └── routers/        # 各模块路由
│   ├── scripts/            # 管理员密码重置、演示数据与配图生成脚本
│   ├── sql/init.sql        # 建库建表脚本（含 5 个管理员席位）
│   └── .env.example        # 环境变量模板
├── frontend/               # Vue 3 前端（手机端优先）
│   └── src/
│       ├── api/            # 接口封装
│       ├── components/     # 公共组件
│       ├── composables/    # 组合式函数
│       ├── router/         # 路由与守卫
│       └── views/          # 页面
└── deploy/                 # 生产部署配置（Nginx / systemd）
```

## 快速开始

### 1. 初始化数据库

```bash
# 启动 MySQL 后执行
mysql -u root -p < backend/sql/init.sql
```

### 2. 配置后端

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # 填入数据库密码和 JWT 密钥
```

### 3. 启动后端（端口 8080）

```bash
.venv/bin/uvicorn app.main:app --reload --port 8080
```

### 4. 启动前端（端口 5173）

```bash
cd frontend
npm install
npm run dev
```

### 访问地址

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端页面 |
| http://localhost:8080/docs | 接口文档（Swagger UI） |

## 管理员账号

- 5 个管理员席位，序号 `000`~`004`，登录时输序号 + 密码
- 初始密码不可用（安全设计），部署后为每个席位设置密码：

```bash
backend/.venv/bin/python backend/scripts/reset_admin_password.py 000 你的密码
```

- 演示数据脚本（50 名用户 + 完整活动数据，可重复执行）：

```bash
# 1. 生成活动封面和群二维码（一次性，生成到 backend/uploads/activities/demo/）
backend/.venv/bin/python backend/scripts/generate_demo_images.py
# 2. 生成演示数据（自动引用配图；未生成配图时自动跳过，不会破图）
backend/.venv/bin/python backend/scripts/seed_demo.py
```

## 部署

- 前端构建：`cd frontend && npm run build`（产物在 dist/）
- Nginx 配置模板：`deploy/nginx.conf`
- 后端服务托管：`deploy/runhub.service`（systemd）
- 生产配置通过环境变量注入（见 `.env.example`）

