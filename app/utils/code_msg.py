# encoding=utf8

import json
import collections


class CodeMsg:
    CM = collections.namedtuple('CM', ['code', 'msg'])
    SEDD_TIME_OUT = CM(143, '秘钥过时')
    SUCCESS = CM(200, '成功')
    ACCOUNT_NOT_ACTIVE = CM(1002, '未激活账户')
    BIND_ERROR = CM(1003, '绑定失败')


def create_response(ret_cm, data=None,msg=None):
    if ret_cm.code == CodeMsg.SUCCESS.code:
        ret = CommonJsonRet(code=ret_cm.code,
                            success=True,
                            msg=ret_cm.msg if msg is None else msg,
                            data=data)
    else:
        ret = CommonJsonRet(code=ret_cm.code,
                            success=False,
                            msg=ret_cm.msg if msg is None else msg,
                            data=data)
    return ret.to_json()


class CommonJsonRet():
    """服务统一返回接口格式"""
    def __init__(self, code, success, msg, data):
        self.code = code
        self.msg = msg
        self.data = data
        self.success = success

    def to_json_str(self):
        return json.dumps(self.__dict__)

    def to_json(self):
        return self.__dict__
