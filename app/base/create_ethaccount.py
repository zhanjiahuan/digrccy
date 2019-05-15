from eth_account import Account
from flask_restplus import Namespace, Resource
from app.utils.code_msg import create_response, CodeMsg

ethaccount_ns = Namespace("ethaccount", description="创建并返回以太坊账户")


@ethaccount_ns.route('/get_ethaccount')
class CreateAccount(Resource):
    @ethaccount_ns.doc(
        params={
        },
        description=u'创建并返回以太坊账户'
    )
    def get(self):
        try:
            account = Account.create()
            private_key = account._key_obj
            public_key = private_key.public_key
            address = public_key.to_checksum_address()
            ret_data = {
                "private_key": str(private_key),
                "public_key": str(public_key),
                "address": str(address)
            }
            print(ret_data)
            return create_response(CodeMsg.CM(200, '创建账户成功'), data=ret_data)
        except Exception as e:
            return create_response(CodeMsg.CM(1030, '创建帐号错误，请重试'))

