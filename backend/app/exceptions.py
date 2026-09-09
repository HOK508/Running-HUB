"""统一异常体系：业务异常 + 全局异常处理

保证所有接口（无论成功、业务失败、参数错误、404）都返回 {code, message, data} 格式。
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BizException(Exception):
    """业务异常：代码里主动抛出，由全局处理器转为统一响应

    用法：raise BizException(40001, "名额已满")
    """

    def __init__(self, code: int, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器：三类异常统一转成 {code, message, data} 格式"""

    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        # 业务异常：按业务错误码返回
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Pydantic 参数校验失败：取第一条错误，拼出可读提示
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query", "path"))
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": f"参数错误：{field} {first.get('msg', '')}", "data": None},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # 兜底：其他 HTTPException 异常
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": str(exc.detail), "data": None},
        )

    # 注意：路由层的 404/405 不是 HTTPException 类实例（是其他内部异常类型），
    # 类处理器匹配不上，必须按"状态码"注册才能命中
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": "接口不存在", "data": None},
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        return JSONResponse(
            status_code=405,
            content={"code": 405, "message": "请求方法不允许", "data": None},
        )
