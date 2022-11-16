from .common import CommonException


class BadRequestException(CommonException):
    """
    错误请求异常
    """

    def __init__(self, msg="请求错误"):
        super().__init__()
        self.status = 400
        self.msg = msg


class InvalidPassword(BadRequestException):
    """
    密码不符合规范异常
    """

    def __init__(self, msg="密码不符合规范异常"):
        super().__init__(msg)