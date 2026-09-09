"""重置管理员密码脚本（管理员共 5 个席位，序号 000~004）

用法：
    backend/.venv/bin/python backend/scripts/reset_admin_password.py <序号> <新密码>
    例：backend/.venv/bin/python backend/scripts/reset_admin_password.py 001 新密码123

说明：
    1. 新密码会经过 bcrypt 加密后写入数据库，脚本本身不存储明文
    2. 忘记管理员密码、或初始化时想自定义密码时使用
    3. 登录后自己修改密码走"修改密码"接口
"""
import sys
from pathlib import Path

# 允许脚本从任意目录运行：把 backend/ 目录加入模块搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
import pymysql

from app.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


def main() -> None:
    if len(sys.argv) != 3:
        print("用法：backend/.venv/bin/python backend/scripts/reset_admin_password.py <序号> <新密码>")
        sys.exit(1)

    admin_no, new_password = sys.argv[1], sys.argv[2]
    if admin_no not in ("000", "001", "002", "003", "004"):
        print("错误：管理员序号只能是 000~004")
        sys.exit(1)
    if len(new_password) < 6:
        print("密码至少 6 位")
        sys.exit(1)

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password = %s WHERE phone = %s AND is_admin = 1",
                (hashed, admin_no),
            )
            if cur.rowcount == 0:
                print(f"错误：数据库中没有管理员账号（序号 {admin_no}）")
                sys.exit(1)
        conn.commit()
        print(f"管理员（序号 {admin_no}）密码已更新（新密码 {len(new_password)} 位，bcrypt 加密入库）")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
