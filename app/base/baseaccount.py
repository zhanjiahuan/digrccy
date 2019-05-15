import app
import logging
import requests
from app import consul_clinet
from app.base.base import get_coin_types
from app.utils.code_msg import create_response, CodeMsg
from flask_restplus import Namespace, Resource
from app.utils.cover_resource import CoverRequestParser

balance_ns = Namespace("baseaccount", description="base_account相关信息")


@balance_ns.route('/')
class Baseaccount(Resource):
    @balance_ns.doc(
        params={
            'chain_type': '链类型  1=链内, 2=链外 (必须)',
            'coin_name': '币种名称  (必须)'
        },
        description=u'获取base账户余额'
    )
    def get(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("chain_type", type=int, required=True)
        parser_.add_argument("coin_name", type=str, required=True)
        params = parser_.parse_args()
        chain_type = params['chain_type']
        coin_name = params.get('coin_name')
        base_balance = None
        try:
            coin_types = get_coin_types()
        except Exception as e:
            logging.error('find coin_types error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '获取币种失败'))
        if coin_name not in coin_types:
            return create_response(CodeMsg.CM(1031, '币种名错误'))
        if chain_type not in (1, 2):
            return create_response(CodeMsg.CM(1031, '链类型错误'))
        if chain_type == 2:
            base_address = consul_clinet.get_digiccy_base_account(coin_name, is_seed=False)
            wallet_str = "{}_wallet".format(coin_name.lower())
            wallet = getattr(app, wallet_str)
            try:
                base_balance = wallet.get_balance(base_address)
                print("-----------------", base_balance)
            except Exception as e:
                return create_response(CodeMsg.CM(1030, '链外余额查询错误'))
        else:
            stellar_address = consul_clinet.get_stellar_base_account(coin_name, is_seed=False)
            stellar_node = app.stellar_service.stellar_node()
            url = stellar_node + '/accounts/{}'.format(stellar_address)
            try:
                response = requests.get(url).json()
                balances = response.get('balances')
                for balance_info in balances:
                    if balance_info.get("asset_code") == coin_name:
                        base_balance = balance_info.get("balance")
                        break
            except Exception as e:
                return create_response(CodeMsg.CM(1030, '链内余额查询错误'))
        if base_balance is None:
            return create_response(CodeMsg.CM(1030, '余额查询错误'))
        base_balance = str(base_balance)
        return create_response(CodeMsg.CM(200, '余额查询成功'), data=base_balance)
