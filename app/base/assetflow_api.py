import json
import logging
import time
from flask_restplus import Namespace, Resource
from stellar_base.utils import account_xdr_object
from app.base.base import get_coin_types
from app import stellar_service
from app.utils.asset_flow import StellarAssetFlow
from app.utils.code_msg import create_response, CodeMsg
from app.utils.cover_resource import CoverRequestParser

assetflow_ns = Namespace("assetflow", description="资产流水，查询接口")


@assetflow_ns.route('/')
class AssetFlow(Resource):
    @assetflow_ns.doc(
        params={
            "stellar_account": "stellar账户 , 必须",
            "asset": "资产类型 , 非必须",
            "payment_type": "转帐类型:1=转入 2=转出 3=全部 , 非必须",
            "trades_type": "挂单类型 1=买入 2=卖出 3=全部 , 非必须",
            "create_time": "过滤时间 , 非必须",
        },
        description=u'返回账户转帐、挂单流水'
    )
    def get(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("stellar_account", type=str, required=True)
        parser_.add_argument("asset", type=str, required=False)
        parser_.add_argument("payment_type", type=int, required=False)
        parser_.add_argument("trades_type", type=int, required=False)
        parser_.add_argument("create_time", type=str, required=False)
        params = parser_.parse_args()

        account = params.get('stellar_account')
        asset = params.get('asset')
        payment_type = params.get('payment_type')
        trades_type = params.get('trades_type')
        create_time = params.get('create_time')

        try:
            account_xdr_object(account)
        except Exception as e:
            return create_response(CodeMsg.CM(1031, '账户地址错误'))

        try:
            coin_types = get_coin_types()
        except Exception as e:
            logging.error('find coin_types error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询失败'))
        if asset is not None and asset not in coin_types:
            return create_response(CodeMsg.CM(1031, '资产名错误'))

        if payment_type is not None and int(payment_type) not in (1, 2, 3):
            return create_response(CodeMsg.CM(1031, '转帐类型错误'))
        if trades_type is not None and int(trades_type) not in (1, 2, 3):
            return create_response(CodeMsg.CM(1031, '挂单类型错误'))

        if create_time is not None:
            try:
                time.strptime(create_time, "%Y-%m-%d %H:%M:%S")
            except Exception as e:
                return create_response(CodeMsg.CM(1031, '时间参数错误'))

        native_code = 'VTOKEN'
        stellar_http_node = stellar_service.stellar_node()  # 'http://101.132.188.48:8000'
        try:
            asset_flow = StellarAssetFlow(account, stellar_http_node, native_code, asset_code=asset, create_time=create_time)
        except Exception as e:
            logging.error('查询转帐、挂单流水错误:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询错误'))
        if payment_type is not None:
            payment_type = int(payment_type)
            if payment_type == 3:
                asset_flow.payment_records()
            else:
                asset_flow.payment_records(payment_type)
        if trades_type is not None:
            trades_type = int(trades_type)
            if trades_type == 3:
                asset_flow.trades_records()
            else:
                asset_flow.trades_records(trades_type)

        flow_list = asset_flow.records
        return create_response(CodeMsg.CM(200, '查询成功'), data=flow_list)
