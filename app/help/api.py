import requests

from stellar_base.asset import Asset
from stellar_base.keypair import Keypair
from stellar_base.operation import CreateAccount, ChangeTrust, Payment
from flask_restplus import Namespace, Resource

from app.utils.cover_resource import CoverRequestParser
from app.utils.code_msg import CodeMsg, create_response
from app.help.utils import PAY_STELLAR_ACCOUNT_SEED, genMnemonicKeyPair
from app import stellar_service

help_ns = Namespace("help", description="help")

def get_seq(account):
    try:
        url = stellar_service.stellar_node() + '/accounts/{}'.format(account)
        sequence = requests.get(url).json().get('sequence')
    except:
        return
    return sequence


@help_ns.route("/stellar_account")
class CreateStellarAccount(Resource):
    @help_ns.doc(
        params={
            'coin_name': '货币名'
        },
        description='stellar账户测试用接口'
    )
    def post(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("coin_name", type=str, required=True)

        params = parser_.parse_args()
        coin_name = params.get("coin_name")

        ret = genMnemonicKeyPair()
        seed = ret.get('seed').decode('utf-8')
        account = ret.get('account').decode('utf-8')

        # 生成并激活
        pay_account = Keypair.from_seed('SBCHAGLMZTOH2RO4AZQ55VK5QJUYVEGHHJEHZPL7O6E3P2LZCDDME77C')
        pay_sequence = get_seq(pay_account.address().decode('utf-8'))
        if not pay_sequence:
            return create_response(CodeMsg.CM(2222, '获取付款账户seq错误'),data=dict(account=account,seed=seed))
        op = CreateAccount(dict(
            destination=account,
            starting_balance=str(100)
        ))
        memo = '账户激活'
        te,tx_hash = stellar_service.create_te(pay_account,pay_sequence,memo,op)
        ret = stellar_service.submit(te)
        # print(ret)
        if not ret or ret.get('hash') is None:
            if ret.get("status") != 504:
                return create_response(CodeMsg.CM(2222,'激活失败'),data=dict(account=account,seed=seed))

        # 激活账户信任货币
        new_account = Keypair.from_seed(seed)
        new_sequence = get_seq(account)
        if not new_sequence:
            return create_response(CodeMsg.CM(2222, '获取新账户seq错误'),data=dict(account=account,seed=seed))
        trust_asset = Asset(coin_name, stellar_service.assets_issuer)
        op1 = ChangeTrust(dict(asset=trust_asset))
        memo = '信任资产'
        te, tx_hash = stellar_service.create_te(new_account, new_sequence, memo, op1)
        ret = stellar_service.submit(te)
        print('-----------------------------信任资产',ret)
        if not ret or ret.get('hash') is None:
            if ret.get("status") != 504:
                return create_response(CodeMsg.CM(2222,'信任失败'),data=dict(account=account,seed=seed))

        # 转账对应货币给新账户
        memo = u'{}转账'.format(coin_name)
        pay_sequence1 = get_seq(pay_account.address().decode('utf-8'))
        if not pay_sequence1:
            return create_response(CodeMsg.CM(2222, '获取付款账户seq错误'),data=dict(account=account,seed=seed))
        op2 = Payment({
            'destination': account,
            'asset': trust_asset,
            'amount': str(10)
        })
        te, tx_hash = stellar_service.create_te(pay_account, pay_sequence1, memo, op2)
        ret = stellar_service.submit(te)
        print('-----------------------------转账对应货币给新账户', ret)
        if not ret or ret.get('hash') is None:
            if ret.get("status") != 504:
                return create_response(CodeMsg.CM(2222,'付款失败'),data=dict(account=account,seed=seed))
        return create_response(CodeMsg.SUCCESS,data=dict(account=account,seed=seed))
