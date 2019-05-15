import json
import logging

from flask_restplus import Namespace, Resource
from stellar_base.utils import account_xdr_object
from app.utils.code_msg import create_response, CodeMsg
from app.utils.cover_resource import CoverRequestParser
from app.models import User
from app.base.base import get_coin_types, get_coin_limit

currency_ns = Namespace("currency", description="充提币列表，查询接口")


@currency_ns.route('/get_currency')
class RechargeList(Resource):
    @currency_ns.doc(
        params={
            'user_address': '用户公匙, 必须',
            'currency_letter': '币种名查询字段, 非必须',
        },
        description=u'充币的列表与搜索'
    )
    def get(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("user_address", type=str, required=True)
        parser_.add_argument("currency_letter", type=str, required=False)
        params = parser_.parse_args()
        user_address = params.get("user_address")
        currency_letter = params.get("currency_letter")
        try:
            account_xdr_object(user_address)
        except Exception as e:
            return create_response(CodeMsg.CM(1031, '账户地址错误'))

        try:
            coin_types = get_coin_types()
        except Exception as e:
            logging.error('find coin_types error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询失败'))
        coin_list = []
        if currency_letter is not None:
            currency_letter = currency_letter.upper()
            for coin_type in coin_types:
                if currency_letter in coin_type:
                    coin_list.append(coin_type)
        else:
            coin_list = list(coin_types.keys())

        ret_data = []
        if len(coin_list) == 0:
            return create_response(CodeMsg.CM(200, '查询成功'), data=ret_data)
        else:
            for coin_name in coin_list:
                try:
                    user = User.query.filter_by(stellar_account=user_address, coin_name=coin_name).first()
                except Exception as e:
                    logging.error('Db query user error:{}'.format(e))
                    return create_response(CodeMsg.CM(1030, '查询错误'))
                ret_data.append({"asset_code": coin_name, "is_bind": 0 if user is None else 1})
            return create_response(CodeMsg.CM(200, '查询成功'), data=ret_data)


@currency_ns.route('/amount_limit')
class AmountLimit(Resource):
    @currency_ns.doc(
        params={
            'coin_name': '币种名称',
        },
        description=u'查询提币数量限制'
    )
    def get(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("coin_name", type=str, required=True)
        params = parser_.parse_args()
        coin_name = params.get("coin_name")
        coin_name = coin_name.upper()
        try:
            coin_types = get_coin_types()
        except Exception as e:
            logging.error('find coin_types error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询失败'))
        if coin_name not in coin_types:
            return create_response(CodeMsg.CM(1031, '币种名错误'))
        coin_name = coin_name.upper()
        try:
            amount_limit = get_coin_limit()
        except Exception as e:
            logging.error('find amount limit error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询限额失败'))
        coin_limit = amount_limit.get(coin_name)
        if coin_limit is None:
            return create_response(CodeMsg.CM(1030, '币种名称错误'))
        return create_response(CodeMsg.CM(200, '查询限额成功'), data=coin_limit)
