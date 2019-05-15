import logging
import json

from decimal import Decimal
from web3 import Web3
from eth_account import Account
from web3.utils.encoding import to_hex

from app import session_pool
from app.common.consul import ConsulServiceName
from app.models import Config, Order


class EthWallet():
    """ETH钱包节点"""
    ETH_API_KEY = '6RJPUEST3V8UR737RS89YZQ9HZIYU73PA7'
    ETH_BLOCK_API = 'https://api.etherscan.io/api?module=proxy&action=eth_blockNumber'
    ETH_TX_API = "http://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock={start_block}&endblock={end_block}&sort={sort}&apikey={api_key}"

    def __init__(self, app=None, consul_client=None):
        if consul_client and app:
            self.init_app(app, consul_client)

    def init_app(self, app, consul_client):
        self.passphrase = app.config.get('GETH_ETH_PASSPHRASE')
        self.consul_client = consul_client
        self.wallet_url = "http://47.102.40.120:8221"
        self.w3 = Web3(Web3.HTTPProvider(self.wallet_url))
        if not self.w3.isConnected():
            logging.error('Connect ETH wallet node fial')
        # TODO:查询钱包节点区块与公网区块是否同步

    def is_connected(self):
        """钱包是否链接"""
        return self.w3.isConnected()

    def create_account(self):
        """创建eth账户"""
        account = Account.create()
        private_key = account._key_obj
        public_key = private_key.public_key
        address = public_key.to_checksum_address()
        return private_key, address

    def is_valid_address(self, address):
        if address is None or address == '':
            return False
        else:
            try:
                self.w3.eth.getCode(address)
            except:
                return False
            return True

    def get_balance(self,address, block_identifier='latest'):
        """获取余额,默认最新区块"""
        try:
            balance = self.w3.eth.getBalance(address, block_identifier)
        except Exception as e:
            logging.error('Eth node get balance error:{}'.format(str(e)))
            raise Exception('Eth node get balance error')
        return Decimal(balance) / (10**18)

    def is_syncing(self):
        """节点是否在同步中"""
        # 注意返回Flase表示节点同步完成
        return self.w3.eth.syncing

    def get_nonce(self, address):
        """获取账户nonce值"""
        # pending 获得最新已使用的nonce,对nonce进行加1
        nonce = self.w3.eth.getTransactionCount(address, 'pending')
        return nonce

    def payment(self, addrfrom, addrto, amount):
        """普通付款"""
        # 单位换算
        amount = int(amount * (10 ** 18))
        payload = {
            'from': addrfrom,
            'to': addrto,
            'value': amount
        }
        try:
            ret = self.w3.personal.sendTransaction(payload, self.passphrase)
            tx_hash = to_hex(ret)
            return True, tx_hash
        except Exception as e:
            payload.update(dict(errormsg=str(e)))
            logging.error('eth payment error:{}'.format(str(payload)))
            return False, str(e)

    def raw_transaction(self, privkey, addrto, amount, gasPrice, gasLimit):
        value = amount * (10 ** 18)  # 单位转转
        # 通过private key实例化账户
        account = Account.privateKeyToAccount(privkey)
        nonce = self.w3.eth.getTransactionCount(account.address)
        # 创建交易的json文件(将value从科学计数法变为浮点数)
        value = int(value)
        gasLimit = int(gasLimit)
        gasPrice = int(gasPrice)
        payload = {
            'to': addrto,
            'value': value,
            'gas': gasLimit,
            'gasPrice': gasPrice,
            'nonce': nonce,
        }
        try:
            # 使用发送方账户对裸交易对象进行签名
            signed = account.signTransaction(payload)
            tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
            return True, to_hex(tx_hash), ''
        except ValueError as e:
            print('ValueError:', e)
            return False, '', str(e)


    def get_db_base_account(self):
        """数据库获取eth base账户"""
        try:
            eth_base_address = Config.query.first_by(key='digiccyEthBaseAccount').frirst().value
        except Exception as e:
            logging.error('DB get digiccyEthBaseAccount error:{}'.format(str(e)))
            raise Exception('DB get digiccyEthBaseAccount error')
        return eth_base_address

    def get_node_base_account(self):
        """本地节点获取eth base账户"""
        try:
            eth_base_address = self.w3.personal.listAccounts[0]
        except Exception as e:
            logging.error('node get digiccyEthBaseAccount error:{}'.format(str(e)))
            raise Exception('node get digiccyEthBaseAccount error')
        return eth_base_address

    def get_block_num(self):
        """获取最新区块数"""
        try:
            block_num = self.w3.eth.getBlock('latest')['number']
        except Exception as e:
            logging.error('Get eth node block number error:{}'.format(str(e)))
            return
        return block_num

    def get_mian_block_num(self):
        """获取公链上的最新区块数"""
        try:
            ret = session_pool.get(self.ETH_BLOCK_API, timeout=30).json()
            block_num = int(ret.get('result'), 16)  # 16进制转int
        except Exception as e:
            logging.error('Get eth main chain block number error:{}'.format(e))
            return
        return block_num  # int

    @classmethod
    def eth_transaction_record(cls, address, last_timestamp, start_block=None, end_block=99999999, sort='asc',):
        """查询账户交易记录"""
        if start_block is None:
            start_block = 0

        url = cls.ETH_TX_API.format(address=address,             # eth账户地址
                                    start_block=start_block,     # 开始区块
                                    end_block=end_block,         # 结束区块
                                    sort=sort,                   # 排序 desc降序 asc 升序
                                    api_key=cls.ETH_API_KEY)     # eth api KEY
        try:
            ret = session_pool.get(url, timeout=50).json()
        except Exception as e:
            logging.error('Request ETH_TX_API error address:{},error:{},url:{}'.format(address, str(e), url))
            # raise Exception('Request ETH_TX_API error')
            ret = None

        new_records = []
        if ret is None:
            return new_records

        status = ret.get('status')
        message = ret.get('message')
        records = ret.get('result')  # list
        if status == '1' and message == 'OK':
            for record in records:
                is_error = record['isError']  # 为0表示交易正常
                to_address = record['to']  # 是否为收款记录
                current_timestamp = int(record['timeStamp'])  # 当前记录时间戳
                confirmations = int(record['confirmations'])  # 交易记录确认数
                record_hash = record['hash']
                amount = round(Decimal(record['value'])/(10**18), 7)
                if is_error != '0':
                    continue
                if to_address.lower() != address.lower():
                    continue
                if last_timestamp > current_timestamp:
                    continue
                if Order.hash_is_exist(record_hash):
                    continue
                if amount < Decimal('0.0000001'):
                    continue
                if confirmations < 12:
                    break
                else:
                    new_records.append(record)
                    # yield record
        else:
            if records is None:
                logging.error('Request ETH_TX_API fail address:{} ret:{}, url:{}'.format(address, str(ret), url))
                # raise Exception('Request ETH_TX_API error:{}'.format(str(ret)))
        return new_records

    def hash_get_detail(self, tx_hash):
        """hash获取交易细节,用于确认链外交易是否被确认"""
        # 交易是否被确认.status=1(被确认)
        is_confirm = False  # 是否确认
        is_success = False  # 如果已确认,交易是否成功
        msg = None  # 未被确认返回异常信息(一般超时),确认失败:失败的细节,确认成功:交易详情
        fee = None  # 确认成功交易的手续费
        try:
            ret = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=10)
        except Exception as e:
            # waitForTransactionReceipt　API 如果交易处理pending状态,api会一直阻塞,这里设置超时时间为10秒
            msg = str(e)
            return is_confirm, is_success, msg, fee

        # 交易被确认
        is_confirm = True
        status = ret.get('status')
        msg = dict(fail_detail=str(ret))
        if status != 1:  # 确认交易失败
            return is_confirm, is_success, msg, fee
        else:  # 确认交易成功
            is_success = True
            gas_used = Decimal(ret.get('gasUsed'))  # 燃料使用个数
            tx_detail = self.w3.eth.getTransaction(tx_hash)  # 获取交易细节
            gas_price = Decimal(tx_detail.get('gasPrice'))  # 燃料价格
            fee = round((gas_used * gas_price) / (10 ** 18), 7)
            msg = dict(confirm=str(ret),tx_detail=str(tx_detail))
            return is_confirm, is_success, msg, fee

if __name__ == '__main__':
    # a = EthWallet()
    w3 = Web3(Web3.HTTPProvider('http://47.244.167.70:8221'))
    # print(w3.eth.getTransactionCount('0xf8E05aB2b3FF11191f139144b46C25B6B0b957b7', 'pending'))
