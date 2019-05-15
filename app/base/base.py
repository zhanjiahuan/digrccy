import re
import time
import uuid
import json
import random
import logging

from datetime import datetime
from decimal import Decimal
from stellar_base.asset import Asset
from stellar_base.keypair import Keypair
from stellar_base.operation import Payment

from app import db, consul_clinet, redisService
from app import stellar_service
from app.utils.code_msg import CodeMsg
from app.models import User, Order, OrderDetail
from app.utils.commons import str_num_to_decimal, decrypt_seed


def get_coin_types():
    return consul_clinet.get_digiccy_coin_types()

def get_coin_limit():
    return consul_clinet.get_digiccy_coin_limit()

def get_min_balances(chain):
    return consul_clinet.get_digiccy_min_balances(chain)

class StellarAccount():
    endpoint_account = '/accounts/{stellar_address}'
    endpoint_offers = '/accounts/{stellar_address}/offers'

    def __init__(self, stellar_address):
        self.stellar_address = stellar_address
        self.stellar_service = stellar_service
        self._stellar_node = None
        self._account_info = None

    def get_stellar_node(self):
        """获取恒星节点"""
        if self._stellar_node is None:
            self._stellar_node = self.stellar_service.stellar_node()
        return self._stellar_node

    def get_stellar_account_info(self):
        """获取账户信息"""
        stellar_node = self.stellar_service.stellar_node()
        url = stellar_node + self.endpoint_account.format(stellar_address=self.stellar_address)
        try:
            response = self.stellar_service.session_pool.get(url,timeout=10).json()
        except Exception as e:
            logging.error(e)
            raise Exception('get stellar account info error')
        self._account_info = response

    def get_stellar_sequence(self):
        """获取stellar序列号"""
        if self._account_info is None:
            self.get_stellar_account_info()
        return self._account_info.get('sequence')

    def get_stellar_balances(self):
        """获取资产列表"""
        if self._account_info is None:
            self.get_stellar_account_info()
        return self._account_info.get('balances')

    def get_stellar_asset_balance(self, stellar_asset_code):
        """获取指定货币余额"""
        balances = self.get_stellar_balances()
        if balances is None:
            return
        asset_info = [coin for coin in balances if coin.get('asset_code')==stellar_asset_code and coin.get('asset_issuer')==self.stellar_service.assets_issuer]
        if not asset_info:
            return
        return Decimal(asset_info[0].get('balance'))

    def get_stellar_user_offers(self):
        """获取用户所有挂单"""
        stellar_node = self.stellar_service.stellar_node(is_full=True)
        url = stellar_node + self.endpoint_offers.format(stellar_address=self.stellar_address)
        params = dict(
            order='desc',
            limit=200
        )
        try:
            response = self.stellar_service.session_pool.get(url, params=params, timeout=10).json()
        except Exception as e:
            logging.error(e)
            raise Exception('get stellar user offers error')
        user_offers = response['_embedded']['records']
        return user_offers

    def get_stellar_user_asset_freeze(self, asset_code):
        """获取用户资产冻结数量"""
        user_offers = self.get_stellar_user_offers()
        asset_freeze = 0
        for offer in user_offers:
            offer_sell_asset_code = offer['selling'].get('asset_code')
            offer_sell_asset_issuer = offer['selling'].get('asset_issuer')
            if offer_sell_asset_code == asset_code and offer_sell_asset_issuer == self.stellar_service.assets_issuer:
                asset_freeze += Decimal(offer['amount'])
        return asset_freeze


class DigiccyBase():
    """充提币通用代码"""
    def __init__(self, coin_name):
        self.coin_name = coin_name

    def stellar_keypair(self, stellar_encrypt_seed, time_verify=True):
        """stellar kp 对象"""
        # todo:stellar 私钥解密

        seed_info = decrypt_seed(stellar_encrypt_seed)
        if not seed_info:
            return CodeMsg.CM(1088, '无效秘钥-1')

        try:
            seed_info = json.loads(seed_info)
        except:
            return CodeMsg.CM(1088, '无效秘钥-2')

        seed_encrypt_time = seed_info.get('time')
        if seed_encrypt_time + 30 < int(time.time()):
            return CodeMsg.SEDD_TIME_OUT

        if time_verify:
            seed_encrypt_time = seed_info.get('time')
            if seed_encrypt_time + 30 < int(time.time()):
                return CodeMsg.SEDD_TIME_OUT
        #
        stellar_seed = seed_info.get('seed')
        # stellar_seed = stellar_encrypt_seed
        try:
            stellar_kp = Keypair.from_seed(stellar_seed)
        except:
            return CodeMsg.CM(1001, '无效秘钥-3')
        return stellar_kp

    def bind_compulsory(self, encrypt_seed):
        """绑定必要条件"""
        stellar_kp = self.stellar_keypair(encrypt_seed)  # stellar_base.keypair.Keypair obj
        if isinstance(stellar_kp, CodeMsg.CM):
            return stellar_kp

        stellar_address = stellar_kp.address().decode('utf-8')
        # query db
        if User.query.filter_by(stellar_account=stellar_address, coin_name=self.coin_name).first():
            return CodeMsg.CM(1002, '绑定已存在')

        stellar_account = StellarAccount(stellar_address)  # StellarAccount obj
        if not stellar_account.get_stellar_sequence():
            return CodeMsg.CM(1003, '账户未激活')

        asset_balance = stellar_account.get_stellar_asset_balance(self.coin_name)
        if asset_balance is None:
            return CodeMsg.CM(1004, '货币未信任')
        return stellar_address

    def bind_insert(self,stellar_address, bind_account, bind_secret):
        """插入绑定记录"""
        digiccy_account = User(
                            id=str(uuid.uuid1()),
                            stellar_account=stellar_address,
                            address=bind_account,
                            secret=bind_secret,
                            coin_name=self.coin_name,
                            )
        try:
            db.session.add(digiccy_account)
            db.session.commit()
            return True
        except Exception as e:
            logging.error(e)
            db.session.rollback()
            return False

    def transfer_compulsory(self, encrypt_seed, amount, fee, order_limit=True):
        """stellar转账必要条件"""
        ret = self.stellar_keypair(encrypt_seed, time_verify=False)
        if isinstance(ret, CodeMsg.CM):
            return ret
        stellar_kp = ret

        # stellar账户
        stellar_address = stellar_kp.address().decode('utf-8')
        stellar_account = StellarAccount(stellar_address)

        # stellar账户校验
        sequence = stellar_account.get_stellar_sequence()
        if not sequence:
            return CodeMsg.CM(1005, '账户未激活')
        asset_balance = stellar_account.get_stellar_asset_balance(self.coin_name)
        if asset_balance is None:
            return CodeMsg.CM(1004, '货币未信任')

        user_coin_balance = stellar_account.get_stellar_asset_balance(self.coin_name)
        if order_limit:
            user_coin_freeze = stellar_account.get_stellar_user_asset_freeze(self.coin_name)
        else:
            user_coin_freeze = 0
        if amount + fee + user_coin_freeze > user_coin_balance:
            return CodeMsg.CM(1007, '余额不足')
        return sequence, stellar_kp

    def transfer_te(self, sequence, amount, stellar_kp, destination, memo):
        """组建请求stellar te参数"""
        memo += re.sub(r'\.','',str(time.time()) + str(random.randint(1000, 9999)))
        print('stellar备注:',memo)
        op = Payment({
                'destination': destination,
                'asset': Asset(self.coin_name, stellar_service.assets_issuer),
                'amount': str(amount)
            })
        te, tx_hash = stellar_service.create_te(stellar_kp, sequence, memo, op)
        return te, tx_hash

    def transfer_submit(self, te):
        """stellar转账提交"""
        return stellar_service.submit(te=te)

    def get_stellar_base_account(self):
        """获取提现stellar收款账户"""
        stellar_base_account = consul_clinet.get_stellar_base_account(self.coin_name, is_seed=False)
        return stellar_base_account

    def audit_compulsory(self, encrypt_seed, amount, fee):
        """审核通用代码"""
        # 金额手续费参数验证
        amount = str_num_to_decimal(amount)
        fee = str_num_to_decimal(fee)
        if not amount:
            return CodeMsg.CM(1008, '金额有误')
        if not fee:
            return CodeMsg.CM(1009, '手续费有误')

        # 提币最小数量限制
        withdraw_min_amount = consul_clinet.get_withdraw_min_amount(self.coin_name)
        if amount < withdraw_min_amount:
            return CodeMsg.CM(1009, '提笔数量过小')

        # stellar转账账户验证
        ret = self.transfer_compulsory(encrypt_seed, amount, fee)
        if isinstance(ret, CodeMsg.CM):
            return ret
        sequence, stellar_kp = ret

        # 设置redis锁
        redis_seq_key = self.coin_name + "." + stellar_kp.address().decode('utf-8')
        if not redisService.setnx(redis_seq_key, str(sequence)):
            return CodeMsg.CM(1009, '请务频繁操作')
        redisService.expire(redis_seq_key, 10)
        # 绑定是否存在
        stellar_address = stellar_kp.address().decode('utf-8')
        user = User.query.filter_by(stellar_account=stellar_address, coin_name=self.coin_name).first()
        if not user:
            return CodeMsg.CM(1010, '币种未绑定')
        return stellar_address

    def withdraw_compulsory(self, encrypt_seed, amount, fee, digiccy_address):
        """提币通用代码"""
        # 金额手续费参数验证
        amount = str_num_to_decimal(amount)
        fee = str_num_to_decimal(fee)
        if not amount:
            return CodeMsg.CM(1008, '金额有误')
        if not fee:
            return CodeMsg.CM(1009, '手续费有误')

        # 提币最小数量限制
        withdraw_min_amount = consul_clinet.get_withdraw_min_amount(self.coin_name)
        if amount < withdraw_min_amount:
            return CodeMsg.CM(1009, '提币数量过小')

        # stellar转账账户验证
        ret = self.transfer_compulsory(encrypt_seed, amount, fee)
        if isinstance(ret, CodeMsg.CM):
            return ret

        sequence, stellar_kp = ret

        # 设置redis锁
        redis_seq_key = self.coin_name + "." + stellar_kp.address().decode('utf-8')
        if not redisService.setnx(redis_seq_key, str(sequence)):
            return CodeMsg.CM(1009, '请务频繁操作')
        redisService.expire(redis_seq_key, 10)

        # 绑定是否存在
        stellar_address = stellar_kp.address().decode('utf-8')
        user = User.query.filter_by(stellar_account=stellar_address, coin_name=self.coin_name).first()
        if not user:
            return CodeMsg.CM(1010, '币种未绑定')

        # stellar代币收款账户
        destination = self.get_stellar_base_account()
        # destination = 'GBAPRZYI3DDFYEN3IO54DXVPWS4GCXFNUUOION5HIRTDMFQJ3QF7CO7M'

        # stellart提交te
        te, tx_hash = self.transfer_te(sequence, amount+fee, stellar_kp, destination, memo='w')

        # 查询stellar提现hash是否存在
        if Order.query.filter_by(order_hash=tx_hash).first():
            return CodeMsg.CM(1011, '请勿重复提交')

        # 提现订单存库
        chain_in_order_id = str(uuid.uuid1())
        chain_out_order_id = str(uuid.uuid1())
        chain_in_order = Order(  # 链内提现订单
            id=chain_in_order_id,
            relate_id=chain_out_order_id,
            user_id=user.id,
            stellar_account=stellar_address,
            order_type=2,
            chain_type=1,
            coin_name=self.coin_name,
            order_from=stellar_address,
            order_to=destination,
            amount=amount,
            fee=fee,
            order_hash=tx_hash,
            relate_order_status=1,  # 关联订单状态
            add_time=datetime.now(),
            status=-1,  # 待转账
        )
        chain_out_order = Order(  # 链外提现订单
            id=chain_out_order_id,
            relate_id=chain_in_order_id,
            user_id=user.id,
            stellar_account=stellar_address,
            order_type=2,
            chain_type=2,
            coin_name=self.coin_name,
            order_from='',
            order_to=digiccy_address,
            amount=amount,
            fee=0,
            order_hash='',
            status=0,  # 默认失败,等待链内转账结果
            add_time=datetime.now(),
            notice_status=0,
        )
        chain_in_order_detail = OrderDetail(  # 链内提现订单详情
            id=str(uuid.uuid1()),
            order_id=chain_in_order.id,
            act_type=1,  # 提币操作
            query_json=json.dumps(dict(stellar_hash=tx_hash)),
            response_json='',
            status=-1  # 待操作

        )
        db.session.add_all([chain_in_order, chain_out_order, chain_in_order_detail])
        try:
            db.session.commit()
        except Exception as e:
            logging.error('Db insert withdraw order error:{}'.format(str(e)))
            return CodeMsg.CM(1012, '生成订单出错,请稍后再试!')

        # stellar发送扣款请求
        result = stellar_service.submit(te)

        chain_in_order_detail.response_json = json.dumps(result)
        # 扣款成功
        if result.get('hash') is not None:
            # 更新链内体现订单状态
            chain_in_order.status = 1
            chain_out_order.status = -1  # 链内提现成功,待链外转账
            chain_in_order_detail.status = 1
            print(id(chain_in_order))
            db.session.add_all([chain_in_order, chain_in_order_detail, chain_out_order])
            try:
                db.session.commit()
            except Exception as e:
                logging.error('Db update withdraw order error:{}'.format(str(e)))
                # stellar扣款成功,但是存入数据库失败
                return CodeMsg.CM(1013, '链内扣款成功,更新数据出错,请联系客服!')
            return CodeMsg.SUCCESS

        else:
            chain_in_order_detail.status = 0  # 提现链内转账失败
            if result.get('status') == 504 or result.get('except_msg') is not None:
                # 扣款失败504,或扣款请求异常
                chain_in_order.status = 2  # 提现链内扣款待确认
            else:
                # 其他扣款失败请情况
                chain_in_order.status = 0  # 提现链内扣款失败

        db.session.add_all([chain_in_order, chain_in_order_detail])
        try:
            db.session.commit()
        except Exception as e:
            logging.error('Db update withdraw order error:{}'.format(str(e)))
            if chain_in_order.status == 0:
                # stellar扣款失败,存入数据库失败
                return CodeMsg.CM(1015, '链内扣款失败,更新数据出错,请稍后再试!')
            else:
                return CodeMsg.CM(1016, '链内扣款待确认,更新数据出错,如果余额已扣除请联系客服!')

        if chain_in_order.status == 0:
            return CodeMsg.CM(1017, '链内扣款失败,请稍后再试!')
        else:
            # return CodeMsg.CM(1018, '链内扣款待确认!')
            return CodeMsg.CM(1018, '链内扣款待审核!')