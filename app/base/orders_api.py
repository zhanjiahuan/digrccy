import logging
from flask_restplus import Namespace, Resource
from stellar_base.utils import account_xdr_object

from app.base.base import get_coin_types
from app.utils.code_msg import create_response, CodeMsg
from app.utils.cover_resource import CoverRequestParser
from app.models import Order

order_ns = Namespace("orders", description="order查询接口")


@order_ns.route('/')
class Orders(Resource):
    @order_ns.doc(
        params={
            "stellar_account": "stellar账户",
            "coin_name": "币种类型",
            "order_type": "订单类型:1=充值 2=提现 3=归集",
            "chain_type": "链类型 1=链内 2=链外",
        },
        description=u'订单查询返回订单信息'
    )
    def get(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("stellar_account", type=str, required=True)
        parser_.add_argument("coin_name", type=str, required=False)
        parser_.add_argument("order_type", type=int, required=False)
        parser_.add_argument("chain_type", type=int, required=False)
        params = parser_.parse_args()

        user_address = params.get('stellar_account')
        coin_name = params.get('coin_name')
        order_type = params.get('order_type')
        chain_type = params.get('chain_type')
        try:
            account_xdr_object(user_address)
        except Exception as e:
            return create_response(CodeMsg.CM(1031, '账户地址错误'))
        try:
            coin_types = get_coin_types()
        except Exception as e:
            logging.error('find coin_types error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询失败'))
        if coin_name is not None and coin_name not in coin_types:
            return create_response(CodeMsg.CM(1031, '币种名错误'))
        if order_type is not None and int(order_type) not in (1, 2, 3):
            return create_response(CodeMsg.CM(1031, '订单类型错误'))
        if chain_type is not None and int(chain_type) not in (1, 2):
            return create_response(CodeMsg.CM(1031, '链类型错误'))

        params_dict = dict(stellar_account=user_address,
                           coin_name=coin_name,
                           order_type=order_type,
                           chain_type=chain_type,
                           )
        filter = {}
        for param in params_dict:
            if params_dict[param] is not None:
                filter[param] = params_dict[param]
        # print(filter)
        ret_list = []
        try:
            query_dict = Order.query.filter_by(**filter).all()
            for query in query_dict:
                ret_dict = {}
                ret_dict["user_id"] = query.user_id
                ret_dict["order_from"] = query.order_from
                ret_dict["order_to"] = query.order_to
                ret_dict["amount"] = str(query.amount)
                ret_dict["fee"] = str(query.fee)
                ret_dict["status"] = str(query.status)
                ret_dict["add_time"] = str(query.add_time)
                ret_dict["coin_name"] = query.coin_name

                ret_list.append(ret_dict)
        except Exception as e:
            logging.error('Db query order error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询错误'))

        return create_response(CodeMsg.CM(200, '查询成功'), data=ret_list)
