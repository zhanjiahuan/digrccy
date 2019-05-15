import json
import time
import uuid
import logging

from decimal import Decimal
from stellar_base.utils import account_xdr_object
from flask import request
from flask_restplus import Namespace, Resource

from app.models import *
from app import eth_wallet
from app.base.base import DigiccyBase
from app.utils.commons import rsaEncryptToken, rsa_params_decrypt, verify_googleauth
from app.utils.cover_resource import CoverRequestParser
from app.utils.code_msg import CodeMsg, create_response


eth_ns = Namespace("eth", description="ETH冲提币接口")

COIN_NAME = 'ETH'

digiccy_base = DigiccyBase(COIN_NAME)


@eth_ns.route('/bind')
class CreateAccount(Resource):
    @eth_ns.doc(

        params={
            'encryption_parameters': '加密参数',
        },
        description=u'stellar账户提取第三方货币\n'
                    u'原生参数:\n'
                    u'encrypt_seed:加密stellar秘钥'

        # params={
        #     'encrypt_seed': '提现stellar加密秘钥',
        # },
        # description=u'stellar账户提取第三方货币'
    )
    def post(self):
        # parser_ = CoverRequestParser()
        # parser_.add_argument("encrypt_seed", type=str, required=True)
        # params = parser_.parse_args()
        # encrypt_seed = params['encrypt_seed']

        parser_ = CoverRequestParser()
        parser_.add_argument("encryption_parameters", type=str, required=True)

        params = parser_.parse_args()
        encryption_parameters = params['encryption_parameters']

        # 整体参数解密
        try:
            params = json.loads(rsa_params_decrypt(encryption_parameters))
        except:
            return create_response(CodeMsg.CM(1022, '参数无效'))

        # 参数提取,验证完整性
        encrypt_seed = params.get('encrypt_seed')
        if not encrypt_seed or encrypt_seed == '':
            return create_response(CodeMsg.CM(1022, '参数不完整'))

        # stellar account
        result = digiccy_base.bind_compulsory(encrypt_seed)
        if isinstance(result, CodeMsg.CM):
            return create_response(result)
        stellar_address = result

        # digiccy account
        bind_secret, bind_account = eth_wallet.create_account()
        print(type(bind_secret), bind_secret)
        bind_secret = rsaEncryptToken(str(bind_secret))  # 加密

        # instert db
        is_success = digiccy_base.bind_insert(stellar_address, bind_account, bind_secret)
        if not is_success:
            return create_response(CodeMsg.BIND_ERROR)
        return create_response(CodeMsg.SUCCESS)


@eth_ns.route('/withdraw')
class Withdraw(Resource):
    @eth_ns.doc(
        params={
            'encryption_parameters': '加密参数',
        },
        description=u'提币\n'
                    u'原生参数:\n'
                    u'fee:提币手续费,字符串\n'
                    u'amount:金额,字符串\n'
                    u'encrypt_seed:stellar加密秘钥\n'
                    u'digiccy_address:提币地址'

        # params={
        #     'fee': '提币手续费,字符串',
        #     'amount': '金额,字符串',
        #     'encrypt_seed': 'stellar加密秘钥',
        #     'digiccy_address': '提币地址',
        # },
        # description=u'提币'
    )
    def post(self):
        # parser_ = CoverRequestParser()
        # parser_.add_argument("fee", type=str, required=True)
        # parser_.add_argument("amount", type=str, required=True)
        # parser_.add_argument("encrypt_seed", type=str, required=True)
        # parser_.add_argument("digiccy_address", type=str, required=True)

        # params = parser_.parse_args()
        # fee = params['fee']
        # amount = params['amount']
        # encrypt_seed = params['encrypt_seed']
        # digiccy_address = params['digiccy_address']

        parser_ = CoverRequestParser()
        parser_.add_argument("encryption_parameters", type=str, required=True)

        params = parser_.parse_args()
        encryption_parameters = params['encryption_parameters']

        # 整体参数解密
        try:
            params = json.loads(rsa_params_decrypt(encryption_parameters))
        except:
            return create_response(CodeMsg.CM(1022, '参数无效'))

        # 参数提取
        fee = params.get('fee')
        amount = params.get('amount')
        encrypt_seed = params.get('encrypt_seed')
        digiccy_address = params.get('digiccy_address')
        google_code = params.get('google_verification_code')

        # 参数完整性
        if not all([fee, amount, encrypt_seed, digiccy_address]):
            return create_response(CodeMsg.CM(1024, '参数不完整'))

        # 谷歌验证码
        auth = request.headers.get('Authorization')
        is_success, msg = verify_googleauth(auth, google_code)
        if not is_success:
            return create_response(CodeMsg.CM(1023, '验证谷歌验证码失败'), msg=msg)

        # 校验eth钱包节点是否链接
        if not eth_wallet.is_connected():
            return create_response(CodeMsg.CM(1019, '节点离线'))

        # 本地节点是否同步
        if eth_wallet.is_syncing():
            return create_response(CodeMsg.CM(1020, 'eth节点未同步,请勿执行提现操作'))

        # 提币地址校验
        if not eth_wallet.is_valid_address(digiccy_address):
            return create_response(CodeMsg.CM(1021, '提币地址无效'))

        # stellar账户校验,转账
        ret = digiccy_base.withdraw_compulsory(encrypt_seed, amount, fee, digiccy_address)
        if ret.code == CodeMsg.SUCCESS.code:
            return create_response(CodeMsg.CM(200, '提现成功,最多三个工作日到账,请耐心等待'))
        else:
            return create_response(ret)


@eth_ns.route('/bindAddress')
class BindAddress(Resource):
    @eth_ns.doc(
        params={
            'user_address': '用户链内账户地址',
        },
        description=u'查询充币地址'
    )
    def get(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("user_address", type=str, required=True)
        params = parser_.parse_args()
        user_address = params.get("user_address")

        try:
            account_xdr_object(user_address)
        except Exception as e:
            return create_response(CodeMsg.CM(1003, '账户地址错误'))
        try:
            user = User.query.filter_by(stellar_account=user_address, coin_name=COIN_NAME).first()
        except Exception as e:
            logging.error('Db query user error:{}'.format(e))
            return create_response(CodeMsg.CM(1003, '查询错误'))
        if user is None:
            return create_response(CodeMsg.CM(1003, '地址不存在或没绑定对应币种'))
        address = user.address
        return create_response(CodeMsg.CM(200, '充币地址查询成功'), data=address)


# @eth_ns.route('/withdraw')
# class CreateAccount(Resource):
#     @eth_ns.doc(
#         params={
#             'fee': '提币手续费,字符串',
#             'amount': '金额,字符串',
#             'encrypt_seed': 'stellar加密秘钥',
#             'digiccy_address': '提币地址',
#         },
#         description=u'提币'
#     )
#     def post(self):
#         parser_ = CoverRequestParser()
#         parser_.add_argument("fee", type=str, required=True)
#         parser_.add_argument("amount", type=str, required=True)
#         parser_.add_argument("encrypt_seed", type=str, required=True)
#         parser_.add_argument("digiccy_address", type=str, required=True)
#
#         params = parser_.parse_args()
#         fee = params['fee']
#         amount = params['amount']
#         encrypt_seed = params['encrypt_seed']
#         digiccy_address = params['digiccy_address']
#
#         # 校验eth钱包节点是否链接
#         if not eth_wallet.is_connected():
#             return create_response(CodeMsg.CM(1003, '节点离线'))
#
#         # 本地节点是否同步
#         if eth_wallet.is_syncing():
#             return create_response(CodeMsg.CM(1003, 'eth节点未同步,请勿执行提现操作'))
#
#         # 提币地址校验
#         if not eth_wallet.is_valid_address(digiccy_address):
#             return create_response(CodeMsg.CM(1003, '提币地址无效'))
#
#         # stellar账户校验,转账
#         ret = digiccy_base.withdraw_compulsory(encrypt_seed, amount, fee, digiccy_address)
#         if isinstance(ret, CodeMsg.CM):
#             return create_response(ret)
#
#         withdraw_order = ret
#
#         # 获取eth base 账户
#         addrfrom = eth_wallet.get_node_base_account()
#         print(addrfrom)
#
#         # 生产链外充值订单详情记录
#         withdraw_order.order_from = addrfrom  # 订单付款地址
#         request_json = json.dumps(withdraw_order.to_dict())
#         withdraw_order_detail = OrderDetail(
#             id=str(uuid.uuid1()),
#             order_id=withdraw_order.id,
#             act_type=2,
#             request_json=request_json,
#             status=3
#         )
#
#         try:
#             db.session.add_all([withdraw_order,withdraw_order_detail])
#             db.session.commit()
#         except Exception as e:
#             logging.error('update withdraw_order error:{}'.format(str(e)))
#             return create_response(CodeMsg.CM(1003, '链被扣款成功,链外转账失败,请联系客服'))
#
#         # 发起链外转账
#         is_success, msg = eth_wallet.payment(addrfrom,digiccy_address, Decimal(amount))
#         if not is_success:
#             # 提现详情
#             response_json = json.dumps(dict(errormsg=str(msg)))
#             withdraw_order_detail.status = 0
#             withdraw_order_detail.response_json = response_json
#
#             # 提现链外转账订单
#             withdraw_order.status = 0  # 失败
#             code_msg = CodeMsg.CM(1003, '链内扣款成功,链外转账失败,请联系客服')
#         else:
#             # 提现详情
#             response_json = msg
#             withdraw_order_detail.status = 2  # 交易发出成功待确认
#             withdraw_order_detail.response_json = response_json
#
#             # 提现链外转账订单
#             withdraw_order.status = -2  # 交易发出成功待确认
#             withdraw_order.order_hash = msg
#             code_msg = CodeMsg.CM(200, '提现成功,最多三个工作日到账,请耐心等待')
#         try:
#             print(withdraw_order.order_hash)
#             print(withdraw_order.status)
#             db.session.add_all([withdraw_order, withdraw_order_detail])
#             db.session.commit()
#         except Exception as e:
#             logging.error('update withdraw_order error:{}'.format(str(e)))
#             return create_response(CodeMsg.CM(1003, '链被扣款成功,链外转账失败,请联系客服'))
#
#         return create_response(code_msg)

