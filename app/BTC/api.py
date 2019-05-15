import logging
from flask_restplus import Namespace, Resource
from app.base.base import DigiccyBase
from app.utils.cover_resource import CoverRequestParser
from app.utils.code_msg import CodeMsg, create_response
from app import btc_wallet
from app.utils.commons import rsaEncryptToken
from stellar_base.utils import account_xdr_object
from app.models import *

btc_ns = Namespace("btc", description="BTC冲提币接口")

COIN_NAME = 'BTC'

digiccy_base = DigiccyBase(COIN_NAME)


@btc_ns.route('/bind')
class CreateAccount(Resource):
    @btc_ns.doc(
        params={
            'encrypt_seed': '提现stellar加密秘钥',
        },
        description=u'stellar账户提取第三方货币'
    )
    def post(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("encrypt_seed", type=str, required=True)
        params = parser_.parse_args()
        encrypt_seed = params['encrypt_seed']

        # stellar account
        result = digiccy_base.bind_compulsory(encrypt_seed)
        if isinstance(result, CodeMsg.CM):
            return create_response(result)
        stellar_address = result

        # digiccy account
        bind_address, bind_secret = btc_wallet.create_account(stellar_address)
        bind_secret = rsaEncryptToken(str(bind_secret))  # 加密

        # instert db
        is_success = digiccy_base.bind_insert(stellar_address, bind_address, bind_secret)
        if not is_success:
            return create_response(CodeMsg.BIND_ERROR)
        return create_response(CodeMsg.SUCCESS)


@btc_ns.route('/withdraw')
class CreateAccount(Resource):
    @btc_ns.doc(
        params={
            'fee': '提币手续费,字符串',
            'amount': '金额,字符串',
            'encrypt_seed': 'stellar加密秘钥',
            'digiccy_address': '提币地址',
        },
        description=u'提币'
    )
    def post(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("fee", type=str, required=True)
        parser_.add_argument("amount", type=str, required=True)
        parser_.add_argument("encrypt_seed", type=str, required=True)
        parser_.add_argument("digiccy_address", type=str, required=True)

        params = parser_.parse_args()
        fee = params['fee']
        amount = params['amount']
        encrypt_seed = params['encrypt_seed']
        digiccy_address = params['digiccy_address']

        # 校验btc节点是否链接
        if not btc_wallet.is_connected():
            return create_response(CodeMsg.CM(1019, 'BTC节点离线'))

        # 本地节点是否同步
        if not btc_wallet.is_sync():
            return create_response(CodeMsg.CM(1020, 'BTC节点未同步,请勿执行提现操作'))

        # 提币地址校验
        if not btc_wallet.is_valid_address(digiccy_address):
            return create_response(CodeMsg.CM(1021, '提币地址无效'))

        # stellar账户校验,转账
        ret = digiccy_base.withdraw_compulsory(encrypt_seed, amount, fee, digiccy_address)
        if ret.code == CodeMsg.SUCCESS.code:
            return create_response(CodeMsg.CM(200, '提现成功,最多三个工作日到账,请耐心等待'))
        else:
            return create_response(ret)


@btc_ns.route('/bindAddress')
class BindAddress(Resource):
    @btc_ns.doc(
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
