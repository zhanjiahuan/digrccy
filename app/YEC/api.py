import json
import logging
from stellar_base.utils import account_xdr_object
from flask_restplus import Namespace, Resource

from app.models import *
from app import yec_wallet
from flask import request
from app.base.base import DigiccyBase
from app.utils.commons import rsaEncryptToken, rsa_params_decrypt, verify_googleauth
from app.utils.cover_resource import CoverRequestParser
from app.utils.code_msg import CodeMsg, create_response

yec_ns = Namespace("yec", description="YEC冲提币接口")

COIN_NAME = 'YEC'

digiccy_base = DigiccyBase(COIN_NAME)


@yec_ns.route('/bind')
class CreateAccount(Resource):
    @yec_ns.doc(

        params={
            'encryption_parameters': '加密参数',
        },
        description=u'stellar账户提取第三方货币\n'
                    u'原生参数:\n'
                    u'encrypt_seed:加密stellar秘钥'

    )
    def post(self):

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
        bind_secret, bind_account = yec_wallet.create_account()
        # print(type(bind_secret), bind_secret)
        bind_secret = rsaEncryptToken(str(bind_secret))  # 加密

        # instert db
        is_success = digiccy_base.bind_insert(stellar_address, bind_account, bind_secret)
        if not is_success:
            return create_response(CodeMsg.BIND_ERROR)
        return create_response(CodeMsg.SUCCESS)


@yec_ns.route('/withdraw')
class Withdraw(Resource):
    @yec_ns.doc(
        params={
            'encryption_parameters': '加密参数',

        },
        description=u'提币\n'
                    u'原生参数:\n'
                    u'fee:提币手续费,字符串\n'
                    u'amount:金额,字符串\n'
                    u'encrypt_seed:stellar加密秘钥\n'
                    u'digiccy_address:提币地址'

    )
    def post(self):

        parser_ = CoverRequestParser()
        parser_.add_argument("encryption_parameters", type=str, required=True)

        params = parser_.parse_args()
        encryption_parameters = params['encryption_parameters']

        # 整体参数解密
        try:
            params = json.loads(rsa_params_decrypt(encryption_parameters))
        except:
            return create_response(CodeMsg.CM(1022, '参数无效'))

        # print(params)

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
        # auth = request.headers.get('Authorization')
        # is_success, msg = verify_googleauth(auth, google_code)
        # if not is_success:
        #     return create_response(CodeMsg.CM(1023, '验证谷歌验证码失败'), msg=msg)

        # 校验yec钱包节点是否链接
        if not yec_wallet.is_connected():
            return create_response(CodeMsg.CM(1019, '节点离线'))

        # 本地节点是否同步
        if yec_wallet.is_syncing():
            return create_response(CodeMsg.CM(1020, 'yec节点未同步,请勿执行提现操作'))

        # 提币地址校验
        if not yec_wallet.is_valid_address(digiccy_address):
            return create_response(CodeMsg.CM(1021, '提币地址无效'))

        # stellar账户校验,转账
        ret = digiccy_base.withdraw_compulsory(encrypt_seed, amount, fee, digiccy_address)
        if ret.code == CodeMsg.SUCCESS.code:
            return create_response(CodeMsg.CM(200, '提现成功,最多三个工作日到账,请耐心等待'))
        else:
            return create_response(ret)


@yec_ns.route('/bindAddress')
class BindAddress(Resource):
    @yec_ns.doc(
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
            return create_response(CodeMsg.CM(1031, '账户地址错误'))
        try:
            user = User.query.filter_by(stellar_account=user_address, coin_name=COIN_NAME).first()
        except Exception as e:
            logging.error('Db query user error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询错误'))
        if user is None:
            return create_response(CodeMsg.CM(1010, '没有绑定对应币种'))
        address = user.address
        return create_response(CodeMsg.CM(200, '充币地址查询成功'), data=address)
