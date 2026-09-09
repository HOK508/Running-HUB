-- =====================================================
-- RUNhub 跑步活动管理系统 - 数据库初始化脚本
-- 执行方式：mysql -u root -p < init.sql
-- 说明：脚本可重复执行（IF NOT EXISTS / INSERT IGNORE）
-- =====================================================

CREATE DATABASE IF NOT EXISTS runhub
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE runhub;

-- -----------------------------------------------------
-- 1. 用户表（手机号备案 + 密码登录 + 实名信息）
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          BIGINT       AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID（固定 userid，一人一号）',
    phone       VARCHAR(20)  NOT NULL COMMENT '手机号/管理员序号（登录名）',
    password    VARCHAR(100) NOT NULL COMMENT 'bcrypt 加密后的密码',
    nickname    VARCHAR(50)  DEFAULT NULL COMMENT '昵称',
    real_name   VARCHAR(50)  DEFAULT NULL COMMENT '真实姓名（管理员为空）',
    gender      VARCHAR(10)  DEFAULT NULL COMMENT '性别（管理员为空）',
    student_id  VARCHAR(30)  DEFAULT NULL COMMENT '学号（管理员为空）',
    college     VARCHAR(100) DEFAULT NULL COMMENT '学院（管理员为空）',
    id_card     VARCHAR(20)  DEFAULT NULL COMMENT '身份证号（管理员为空）',
    wechat      VARCHAR(50)  DEFAULT NULL COMMENT '微信号（管理员为空）',
    qq          VARCHAR(20)  DEFAULT NULL COMMENT 'QQ号（管理员为空）',
    avatar      VARCHAR(255) DEFAULT NULL COMMENT '头像URL（预留）',
    is_admin    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否管理员：0否 1是',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_phone (phone),
    UNIQUE KEY uk_student_id (student_id),
    UNIQUE KEY uk_id_card (id_card)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- -----------------------------------------------------
-- 2. 活动表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    id               BIGINT       AUTO_INCREMENT PRIMARY KEY COMMENT '活动ID',
    title            VARCHAR(100) NOT NULL COMMENT '活动名称',
    description      TEXT         COMMENT '活动描述',
    image_urls       TEXT         COMMENT '活动图片URL列表(JSON数组)',
    location         VARCHAR(255) NOT NULL COMMENT '活动地点',
    start_time       DATETIME     NOT NULL COMMENT '开始时间',
    end_time         DATETIME     NOT NULL COMMENT '结束时间',
    signup_deadline  DATETIME     NOT NULL COMMENT '报名截止时间',
    max_participants INT          NOT NULL COMMENT '人数上限',
    view_count       INT          NOT NULL DEFAULT 0 COMMENT '浏览数（热度）',
    group_info       VARCHAR(255) DEFAULT NULL COMMENT '加群方式文字',
    group_qr_code    VARCHAR(255) DEFAULT NULL COMMENT '群二维码图片URL',
    creator_id       BIGINT       NOT NULL COMMENT '创建者ID',
    status           VARCHAR(20)  NOT NULL DEFAULT 'pending' COMMENT '审核状态：pending待审核 approved已通过 rejected已拒绝',
    reject_reason    VARCHAR(255) DEFAULT NULL COMMENT '拒绝理由',
    reviewed_by      BIGINT       DEFAULT NULL COMMENT '审核人ID',
    reviewed_at      DATETIME     DEFAULT NULL COMMENT '审核时间',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_creator (creator_id),
    KEY idx_status (status),
    KEY idx_view_count (view_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='活动表';

-- -----------------------------------------------------
-- 3. 报名表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS signups (
    id          BIGINT      AUTO_INCREMENT PRIMARY KEY COMMENT '报名ID',
    user_id     BIGINT      NOT NULL COMMENT '报名用户ID',
    activity_id BIGINT      NOT NULL COMMENT '活动ID',
    status      VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '报名状态：pending待确认 confirmed已确认 rejected已拒绝',
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报名时间',
    UNIQUE KEY uk_user_activity (user_id, activity_id),
    KEY idx_activity (activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报名表';

-- -----------------------------------------------------
-- 4. 退出报名记录表（退出必须填原因，管理员可标记恶意退出）
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS signup_cancellations (
    id           BIGINT       AUTO_INCREMENT PRIMARY KEY COMMENT '退出记录ID',
    user_id      BIGINT       NOT NULL COMMENT '退出用户ID',
    activity_id  BIGINT       NOT NULL COMMENT '活动ID',
    reason       VARCHAR(255) NOT NULL COMMENT '退出报名原因',
    is_malicious TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '管理员标记：是否恶意退出',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '退出时间',
    KEY idx_user (user_id),
    KEY idx_activity (activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='退出报名记录表';

-- -----------------------------------------------------
-- 5. 签到表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS checkins (
    id           BIGINT   AUTO_INCREMENT PRIMARY KEY COMMENT '签到ID',
    user_id      BIGINT   NOT NULL COMMENT '签到用户ID',
    activity_id  BIGINT   NOT NULL COMMENT '活动ID',
    checkin_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '签到时间',
    UNIQUE KEY uk_user_activity (user_id, activity_id),
    KEY idx_activity (activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='签到表';

-- -----------------------------------------------------
-- 6. 回顾帖表（管理员/发起人在活动结束后发布的活动总结）
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS post_reviews (
    id          BIGINT   AUTO_INCREMENT PRIMARY KEY COMMENT '回顾帖ID',
    activity_id BIGINT   NOT NULL COMMENT '活动ID（一个活动一篇）',
    author_id   BIGINT   NOT NULL COMMENT '发布人ID（管理员或发起人）',
    content     TEXT     NOT NULL COMMENT '活动整体情况介绍',
    image_urls  TEXT     DEFAULT NULL COMMENT '图片URL列表(JSON数组)',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
    UNIQUE KEY uk_activity (activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回顾帖表';

-- -----------------------------------------------------
-- 7. 帖子点赞表（活动结束后开放互动）
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS post_likes (
    id          BIGINT   AUTO_INCREMENT PRIMARY KEY COMMENT '点赞ID',
    user_id     BIGINT   NOT NULL COMMENT '点赞用户ID',
    activity_id BIGINT   NOT NULL COMMENT '活动ID',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
    UNIQUE KEY uk_user_activity (user_id, activity_id),
    KEY idx_activity (activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='帖子点赞表';

-- -----------------------------------------------------
-- 8. 帖子评论表
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS post_comments (
    id          BIGINT       AUTO_INCREMENT PRIMARY KEY COMMENT '评论ID',
    user_id     BIGINT       NOT NULL COMMENT '评论用户ID',
    activity_id BIGINT       NOT NULL COMMENT '活动ID',
    content     VARCHAR(200) NOT NULL COMMENT '评论内容',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论时间',
    KEY idx_activity (activity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='帖子评论表';

-- -----------------------------------------------------
-- 预置 5 个管理员席位：序号 000~004（管理员只凭序号+密码登录，无需实名信息）
-- 安全说明：种子哈希对应随机不可知密码，部署后必须执行
--   backend/.venv/bin/python backend/scripts/reset_admin_password.py <序号> <新密码>
-- 为每个管理员设置自己的密码后才能登录
-- -----------------------------------------------------
INSERT IGNORE INTO users (phone, password, nickname, is_admin) VALUES
('000', '$2b$12$nyO3QxMEt0fccO1cqAi8yuljSzcYTeDZ/LP.W7lxTQ9yaC20OYUJu', '管理员', 1),
('001', '$2b$12$nyO3QxMEt0fccO1cqAi8yuljSzcYTeDZ/LP.W7lxTQ9yaC20OYUJu', '管理员1', 1),
('002', '$2b$12$nyO3QxMEt0fccO1cqAi8yuljSzcYTeDZ/LP.W7lxTQ9yaC20OYUJu', '管理员2', 1),
('003', '$2b$12$nyO3QxMEt0fccO1cqAi8yuljSzcYTeDZ/LP.W7lxTQ9yaC20OYUJu', '管理员3', 1),
('004', '$2b$12$nyO3QxMEt0fccO1cqAi8yuljSzcYTeDZ/LP.W7lxTQ9yaC20OYUJu', '管理员4', 1);
