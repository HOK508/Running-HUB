"""框架层测试：统一响应格式与异常处理

运行：backend/.venv/bin/python backend/tests/test_exception_handlers.py
说明：Phase 6 会建立正式的接口测试体系，这里先用最小脚本验证框架正确性，
      重点补测此前未验证的"参数校验失败 422"场景。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.exceptions import BizException, register_exception_handlers
from app.responses import ok

# ---------- 构造最小测试应用：复用正式应用的异常处理器注册函数 ----------


class DemoIn(BaseModel):
    """带参数校验的演示请求体"""

    name: str
    age: int


demo_app = FastAPI()
register_exception_handlers(demo_app)  # 与正式应用同一套处理器


@demo_app.post("/api/demo")
def demo(body: DemoIn):
    if body.name == "boom":
        raise BizException(40001, "业务异常测试")
    return ok({"name": body.name, "age": body.age})


client = TestClient(demo_app)
passed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} {detail}")
        sys.exit(1)


# ---------- 1. 参数校验失败（422）统一格式 ----------
print("== 参数校验失败 422 ==")
r = client.post("/api/demo", json={"name": "张三"})  # 缺少必填字段 age
check("缺字段返回 422 状态码", r.status_code == 422, f"实际 {r.status_code}")
body = r.json()
check("422 响应为统一格式", body.get("code") == 422, str(body))
check("提示信息包含字段名", "参数错误" in body.get("message", "") and "age" in body.get("message", ""), str(body))
check("data 为 null", body.get("data") is None, str(body))

r = client.post("/api/demo", json={"name": "张三", "age": "不是数字"})  # 类型错误
check("类型错误返回 422", r.status_code == 422 and r.json().get("code") == 422, f"实际 {r.status_code}")

# ---------- 2. 成功响应格式 ----------
print("== 成功响应格式 ==")
r = client.post("/api/demo", json={"name": "张三", "age": 20})
body = r.json()
check("成功返回 code=0", body.get("code") == 0, str(body))
check("data 正确", body["data"] == {"name": "张三", "age": 20}, str(body))

# ---------- 3. 业务异常格式 ----------
print("== 业务异常格式 ==")
r = client.post("/api/demo", json={"name": "boom", "age": 1})
body = r.json()
check("BizException 统一格式", body.get("code") == 40001 and body.get("message") == "业务异常测试", str(body))

# ---------- 4. 404 统一格式 ----------
print("== 404 统一格式 ==")
r = client.get("/api/nothing")
check("404 统一格式", r.status_code == 404 and r.json().get("code") == 404, str(r.json()))

# ---------- 5. 正式应用抽查 ----------
print("== 正式应用抽查 ==")
from app.main import app as real_app

rc = TestClient(real_app)
r = rc.get("/api/health")
check("正式应用健康检查", r.json().get("code") == 0, str(r.json()))
r = rc.get("/api/users/me")
check("正式应用未登录返回 401", r.status_code == 401 and r.json().get("code") == 401, str(r.json()))

print(f"\n全部通过：{passed} 项检查")
