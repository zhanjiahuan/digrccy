import json
import logging
import uuid
import app
from flask_restplus import Namespace, Resource
from app import db
from flask import request
from app.base.base import DigiccyBase
from app.models import OrderAuditor
from app.utils.cover_resource import CoverRequestParser
from app.utils.code_msg import create_response, CodeMsg
from app.base.base import get_coin_types
from app.utils.commons import rsa_params_decrypt, verify_googleauth

audit_ns = Namespace("audit", description="审核")


@audit_ns.route('/')
class Audit(Resource):
    @audit_ns.doc(
        params={
            'encryption_parameters': '加密参数',
            'coin_name': '币种名称'
        },
        description=u'生成提币审核表'
    )
    def post(self):
        parser_ = CoverRequestParser()
        parser_.add_argument("encryption_parameters", type=str, required=True)
        parser_.add_argument("coin_name", type=str, required=True)
        params = parser_.parse_args()
        encryption_parameters = params['encryption_parameters']
        coin_name = params.get('coin_name')

        # 整体参数解密
        try:
            params = json.loads(rsa_params_decrypt(encryption_parameters))
        except:
            return create_response(CodeMsg.CM(1022, '参数无效'))
        fee = params.get('fee')
        amount = params.get('amount')
        encrypt_seed = params.get('encrypt_seed')
        digiccy_address = params.get('digiccy_address')
        google_code = params.get('google_verification_code')

        # 参数完整性
        if not all([fee, amount, encrypt_seed, digiccy_address, coin_name]):
            return create_response(CodeMsg.CM(1024, '参数不完整'))

        try:
            coin_types = get_coin_types()
        except Exception as e:
            logging.error('find coin_types error:{}'.format(e))
            return create_response(CodeMsg.CM(1030, '查询币种名失败'))

        if coin_name is not None and coin_name not in coin_types:
            return create_response(CodeMsg.CM(1031, '币种名错误'))
        # 谷歌验证码
        # auth = request.headers.get('Authorization')
        # is_success, msg = verify_googleauth(auth, google_code)
        # if not is_success:
        #     return create_response(CodeMsg.CM(1023, '验证谷歌验证码失败'), msg=msg)
        wallet_str = "{}_wallet".format(coin_name.lower())
        wallet = getattr(app, wallet_str)
        # 校验eth钱包节点是否链接
        if not wallet.is_connected():
            return create_response(CodeMsg.CM(1019, '节点离线'))

        # 本地节点是否同步
        if wallet.is_syncing():
            return create_response(CodeMsg.CM(1020, 'eth节点未同步,请勿执行提现操作'))

        # 提币地址校验
        if not wallet.is_valid_address(digiccy_address):
            return create_response(CodeMsg.CM(1021, '提币地址无效'))

        digiccy_base = DigiccyBase(coin_name)

        ret = digiccy_base.audit_compulsory(encrypt_seed, amount, fee)
        if isinstance(ret, CodeMsg.CM):
            return create_response(ret)
        stellar_address = ret

        order_auditor_id = str(uuid.uuid1())
        order_auditor = OrderAuditor(
            id=order_auditor_id,
            stellar_account=stellar_address,
            coin_name=coin_name,
            amount=amount,
            data=encryption_parameters,
            status=1
        )
        db.session.add(order_auditor)
        try:
            db.session.commit()
        except Exception as e:
            logging.error('Db insert order_auditor order error:{}'.format(str(e)))
            return CodeMsg.CM(1012, '生成审核表出错,请稍后再试!')
        return create_response(CodeMsg.CM(200, '正在审核'))
