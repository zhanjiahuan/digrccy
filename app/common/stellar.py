import hashlib
import logging

from stellar_base import network
from stellar_base.memo import TextMemo
from stellar_base.keypair import Keypair
from stellar_base.operation import Payment
from stellar_base.transaction import Transaction
from stellar_base.transaction_envelope import TransactionEnvelope as Te

from app import session_pool
from app.common.consul import ConsulServiceName


class StellarService(object):
    endpoint_submit = '/transactions'
    endpoint_hash = '/transactions/{tx_hash}'

    def __init__(self, consul_client=None, app=None):
        self.session_pool = session_pool

        if app and consul_client:
            self.init_app(consul_client, app)

    def init_app(self, consul_client, app):
        self.consul_client = consul_client
        self._network_id = app.config.get('STELLAR_NETWORK_ID')
        self._network_passphrase = app.config.get('STELLAR_NETWORK_PASSPHRASE')  # STELLAR_NETWORK_PASSPHRASE
        network.NETWORKS[self._network_id] = self._network_passphrase
        self.assets_issuer = app.config.get('ASSETS_ISSUER')

    def stellar_node(self, is_full=False):
        """获取stellar节点url"""
        if is_full:
            try:
                # TODO:测试服没有全节点.  ConsulServiceName.STELLAR_FULL
                stellar_node = self.consul_client.getRandomOneAvailableServiceIpPort(ConsulServiceName.STELLAR_FULL,
                                                                                     withHttpPrefix=True)
            except Exception as e:
                logging.error(e)
                raise Exception('consul get node error')
        else:
            try:
                stellar_node = self.consul_client.getRandomOneAvailableServiceIpPort(ConsulServiceName.STELLAR_BASE,
                                                                                           withHttpPrefix=True)
            except Exception as e:
                logging.error(e)
                raise Exception('consul get node error')
        return stellar_node

    def submit(self, te):
        """事物提交stellar"""
        stellar_node = self.stellar_node()
        url = stellar_node + self.endpoint_submit
        params = dict(tx=te)
        try:
            ret = self.session_pool.post(url, data=params,timeout=50).json()
        except Exception as e:
            logging.error(e)
            ret = dict(except_msg=str(e))
        return ret

    def create_te(self, user_kaykair, sequence, memo, op, FEE=200):
        """创建te"""
        tx = Transaction(source=user_kaykair.address().decode(),
                         opts={'sequence': sequence,
                               'memo': TextMemo(memo),
                               'fee': FEE,
                               'operations': [op], }, )
        envelope = Te(tx=tx, opts=dict(network_id=self._network_id))
        envelope.sign(user_kaykair)
        te = envelope.xdr()
        tx_hash = hashlib.sha256(envelope.signature_base()).hexdigest()
        return te, tx_hash

    def query_hash(self,tx_hash, stellar_node=None):
        """hash查询:使用全节点查询hash,需要注意全节点是否同步.账本是否同步"""
        if stellar_node is None:
            stellar_node = self.stellar_node()

        # stellar节点是否同步.账本是否同步
        try:
            ret = self.session_pool.get(stellar_node, timeout=10).json()
            history_latest_ledger = ret['history_latest_ledger']
            core_latest_ledger = ret['history_latest_ledger']
        except Exception as e:
            logging.error("get stellar full node info error:{}".format(str(e)))
            # 查询失败
            return None

        # 节点账本未同步
        if history_latest_ledger != core_latest_ledger:
            logging.error('stellar full node unsync:node:{},ret:{}'.format(str(stellar_node), str(ret)))
            return None

        # stellar hash 查询
        url = stellar_node + self.endpoint_hash.format(tx_hash=tx_hash)
        try:
            res = self.session_pool.get(url, timeout=10).json()
        except Exception as e:
            logging.error('query stellar hash error,hash:{},msg{}'.format(tx_hash, str(e)))
            return None

        # 查询hash不存在时,看看stellar返回状态码是否为404,如果不为404(其他未知情况,记录log)返回查询失败
        if res.get('hash') is None:
            if res['status'] != 404:
                logging.error("query stellar hash return unknown ret:{}".format(str(res)))
                return None
        return res



