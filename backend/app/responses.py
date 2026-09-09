"""统一成功响应格式 {code, message, data}"""


def ok(data=None):
    """成功响应：code=0 表示成功，data 携带业务数据"""
    return {"code": 0, "message": "ok", "data": data}
