import logging
import requests
from decimal import Decimal

from bitcoin.main import random_key, pubtoaddr, privtopub
from bitcoinrpc.authproxy import AuthServiceProxy

from app.models import User
from app.common.consul import ConsulServiceName


class BtcWallet():
    """btc钱包"""
    BTC_BLOCK_API = 'https://blockchain.info/'

    def __init__(self, app=None, consul_client=None):
        if app and consul_client:
            self.init_consul(app, consul_client)

    def init_consul(self, app, consul_client):
        try:
            rpc_user = app.config.get('CONFIG_BITCOIND_RPC_USER')
            rpc_pwd = app.config.get('CONFIG_BITCOIND_RPC_PASSWORD')
            wallet_passphrase = app.config.get('CONFIG_BITCOIND_WALLET_PASSWORD')
            self.ipport = consul_client.getRandomOneAvailableServiceIpPort(ConsulServiceName.BTC_CLI)
            # s = "http://%s:%s@" % (self.user, self.pwd) + self.ipport
            # print(s)

            self.bitcoin_cli = AuthServiceProxy(
                "http://%s:%s@" % (rpc_user, rpc_pwd) + self.ipport, timeout=10)
            print("Succeed to connect to the BTC node")

        except Exception as e:
            print(str(e))
            print("Failed to connect to the BTC node")

    # 是否连接BTC节点
    def is_connected(self):
        try:
            if self.bitcoin_cli.getwalletinfo().get('walletversion'):
                return True
            return False
        except Exception as e:
            print(str(e))
            print("Failed to connect to the BTC node")

    # 节点是否同步
    def is_sync(self):
        ret = self.bitcoin_cli.getblockchaininfo()
        if ret.get('blocks') != ret.get("headers"):
            return False
        else:
            return True

    # btc地址是否有效
    def is_valid_address(self, coin_address):
        if coin_address is None or coin_address == '':
            return False
        else:
            ret = self.bitcoin_cli.validateaddress(coin_address).get('isvalid')
            print('账户检查结果:', ret)
            return ret

            # return self.bitcoin_cli.validateaddress(coin_address).get('isvalid')

    # 获取账户余额, 默认经过6个区块确认
    def get_balance(self, coin_address):

        transaction_lists = self.bitcoin_cli.listunspent(1, 99999999, [coin_address])
        print(transaction_lists)
        current_amount = 0
        for transaction_list in transaction_lists:
            amount = transaction_list.get('amount')
            amount = float(amount)
            current_amount += amount
        return current_amount

    def get_balance_by_account(self, account):
        try:
            ret = self.bitcoin_cli.getbalance(account)
            return ret
        except Exception as e:
            logging.error('get balance error:{}'.format(str(e)))
            return None


    def estimate_fee(self):
        try:
            fee = self.bitcoin_cli.estimatefee(6)
            return fee
        except Exception as e:
            logging.error('get fee error:{}'.format(str(e)))
            return None

    def create_account(self, stellar_account):
        # private = random_key()
        # address = pubtoaddr(privtopub(private))
        # print(address, private)
        # return address, private
        address = self.bitcoin_cli.getnewaddress(stellar_account)
        private_key = self.bitcoin_cli.dumpprivkey(address)
        return address, private_key

    def get_block_num(self):
        """获取最新区块数"""
        try:
            block_num = self.bitcoin_cli.getblockcount()
            return block_num
        except Exception as e:
            logging.error('Get btc node block number error:{}'.format(str(e)))
            return None


    def get_chain_info(self):
        ret = self.bitcoin_cli.getblockchaininfo()
        return ret

    def get_block_info(self, block_num):
        """获取区块的详细信息"""
        param = "block-height/{}?format=json".format(block_num)
        api_url = self.BTC_BLOCK_API + param
        # print(api_url)

        blocks = requests.get(api_url, timeout=500).json()
        # print(type(blocks))
        return blocks

    # 链外转帐,普通交易
    def payment(self, btc_base_account, address_to, amount):
        try:
            txid = self.bitcoin_cli.sendfrom(btc_base_account, address_to, amount)
            return True, txid
        except Exception as e:
            logging.error('btc payment error:{}'.format(str(e)))
            return False, str(e)

    def hash_get_detail(self, tx_id):
        """
        Arguments:
        1. "txid" (string, required) The transaction id
        """
        # 根据txid获取确认链外交易信息
        ret = self.bitcoin_cli.gettransaction(tx_id)
        abandoned = ret.get("details")[0].get("abandoned")  # 获取abandon信息
        confirmation_num = ret.get('confirmations')  # 获取确认数

        # 如果确认数小于1，则未确认
        if confirmation_num < 1:
            msg = dict(confirm=str(ret))
            # msg = ret.get("details")[0]
            return False, False, msg, None
        # 如果确认数大于1，则确认
        else:
            msg = dict(confirm=str(ret))
            # msg = ret
            fee = abs(ret.get("fee"))
            if abandoned:
                return True, False, msg, None
            else:
                return True, True, msg, fee

    def raw_payment(self, address_from, address_to, collect_amount):
        inputs = []
        # 获取地址余额信息
        try:
            unspend_lists = self.bitcoin_cli.listunspent(1, 9999999, [address_from])
            for unspend_list in unspend_lists:
                # if unspend_list.get('amount') <= 0:
                #     continue
                # else:
                txid = unspend_list.get('txid')
                vout = unspend_list.get('vout')
                inputs.append({'txid': txid, 'vout': vout})

            outputs = {address_to: round(collect_amount, 8)}

            # 交易建立和签名时不用连接比特币网络,只有在执行交易时才需要将交易发送到网络
            # 创建裸交易
            transaction_hash = self.bitcoin_cli.createrawtransaction(inputs, outputs)

            # 使用私钥签名,获取16进制信息
            hex = self.bitcoin_cli.signrawtransaction(transaction_hash).get('hex')

            # 广播到p2p网络,返回交易哈希
            trading_hash = self.bitcoin_cli.sendrawtransaction(hex, False)

            return True, trading_hash, ''
        except Exception as e:
            print(e)
            return None, None, ''

    def btc_transaction_record(self, block_num):
        # 获取某一区块信息
        block_info = self.get_block_info(block_num)
        blocks = block_info.get('blocks')
        txs = blocks[0].get('tx')
        records = []
        for tx in txs:
            outs = tx.get('out')
            hash = tx.get('hash')
            inputs = tx.get('inputs')
            p_out = inputs[0].get('prev_out')
            if not p_out:
                continue
            else:
                addr_from = p_out.get('addr')
            for out in outs:
                re = []
                addr_to = out.get('addr')
                value = out.get('value') / (10 ** 8)
                # addr_to与User表中绑定的地址进行对比，如果有，则说明此address_to有冲币记录
                user = User.address_query_user('BTC', addr_to)
                if not user:
                    continue
                else:
                    re.append(addr_from)
                    re.append(addr_to)
                    re.append(value)
                    re.append(hash)
                    records.append(re)
        return records

    def get_accounts(self, addr):
        try:
            ad = self.bitcoin_cli.getaccount(addr)
            return ad
        except Exception as e:
            # logging.error('get btc_account error:{}'.format(str(e)))
            return None

    def get_address_byaccount(self, account):
        re = self.bitcoin_cli.getaddressesbyaccount(account)

        return re

    def test1(self):

        transaction_list = self.bitcoin_cli.listaccounts()
        # transaction_list = self.bitcoin_cli.getwalletinfo()
        print(transaction_list)


if __name__ == '__main__':
    class App():
        config = {}
    app = App()
    app.config['CONFIG_BITCOIND_RPC_USER'] = 'xianda'
    app.config['CONFIG_BITCOIND_RPC_PASSWORD'] = 'ABQOqmPZ0tr95f5Z'
    app.config['CONSUL_TOKEN'] = ''
    app.config['CONSUL_IP'] = '101.132.188.48'

    from app.common.consul import ConsulClient

    # 实例化
    btc_wallet = BtcWallet()
    consul_client = ConsulClient()

    # 加载配置
    consul_client.init_app(app)
    btc_wallet.init_consul(app, consul_client)
    #
    # s = btc_wallet.get_accounts('1AmntCaucDzo9NAMbUg4yenEozQ5EDRAP3')
    # print(s)
    # #
    # t = btc_wallet.get_address_byaccount('btc_base')
    # print(t)
    #

    # r = btc_wallet.get_balance("13tRCdpSgpVEiCSrmB4mJa2w1WxC66YSnT")
    # print(r)
    r = btc_wallet.is_connected()
    r1 = btc_wallet.is_sync()
    print(r, r1)

    s = btc_wallet.get_balance_by_account('GB3TIE7N5NVIJR6JIQJGG2WIY42QJGRZC6TGYP3BBF6ZG56W64SBVY67')
    s1 = btc_wallet.get_balance_by_account('GA3EJNXXKCRRH7VHLVE3OUMXIUUFXTZAMHKG6UH2PZV3KNKRKYQQN6VY')
    s2 = btc_wallet.get_balance_by_account('GATMIDOW5LNSYMHYOJC3TDCVCKEVXMX5L4IDNCSKAQ6JS5N4362FBKPT')
    s3 = btc_wallet.get_balance_by_account('boss')
    s4 = btc_wallet.get_balance_by_account('zxc')
    # s = btc_wallet.get_balance_by_account('GATMIDOW5LNSYMHYOJC3TDCVCKEVXMX5L4IDNCSKAQ6JS5N4362FBKPT')
    print(s,s1,s2,s3, s4)

    t1 = btc_wallet.get_balance('1KYY5iyVrEUi5VKggDyQGvn6qBUrSuj6ht')
    print(t1)
    # t1 = btc_wallet.get_address_byaccount('GB3TIE7N5NVIJR6JIQJGG2WIY42QJGRZC6TGYP3BBF6ZG56W64SBVY67')
    # print(t1)
    tt = btc_wallet.test1()
    print(tt)

    t3,t4 = btc_wallet.create_account('GA2XGS5QJPKGCYCBDFARYMSIAFI6BYWDG5BVQIPCTXOC5YIYE4BI25XI')
    print(t3,t4)
    # s2 = btc_wallet.get_balance('1KYY5iyVrEUi5VKggDyQGvn6qBUrSuj6ht')
    # print(s2)
    # ss = btc_wallet.test1('1GoXpXWmYxUuaxTF272gzG49d8uB7eqtWV')
    # ret = btc_wallet.is_valid_address('1GoXpXWmYxUuaxTF272gzG49d8uB7eqtWV')
    # print(ret)
    # r1 = btc_wallet.get_balance_by_account('hw')
    # print('hw的余额为', r1)
    # r2 = btc_wallet.get_balance_by_account('GA3EJNXXKCRRH7VHLVE3OUMXIUUFXTZAMHKG6UH2PZV3KNKRKYQQN6VY')
    # print('账户1的余额', r2)
    # r3 = btc_wallet.get_balance_by_account('GB3TIE7N5NVIJR6JIQJGG2WIY42QJGRZC6TGYP3BBF6ZG56W64SBVY67')
    # print('财务账号链外资产余额', r3)
    # r4 = btc_wallet.get_balance_by_account('GATMIDOW5LNSYMHYOJC3TDCVCKEVXMX5L4IDNCSKAQ6JS5N4362FBKPT')
    # print('1111', r4)

    # r3 = btc_wallet.get_balance('18MtnC1N1fdTEyADVtcBUmbgbPjrxP4E4g')
    # print(r3)
    # ss = btc_wallet.estimate_fee()
    # print(ss)
    # is_confirm, is_success, msg, fee = btc_wallet.hash_get_detail('e36c904f3957f63b7f954d6bc1022a633543fe39e165146a22065a89499cd264')
    # print(type(abs(fee)))
    # print(is_confirm, is_success, msg, abs(fee))
    # t, t1 = btc_wallet.payment('zxc', '1B7LPxgAieQ3LaMSv8jkBGDfqaR6wgbK32', 0.002)
    # print(t, t1)
    # import time
    # start = time.clock()
    # btc_wallet.btc_transaction_record("100000")
    # end = time.clock()
    # print(s)
    # print(end - start)
    # t = s.get('blocks')
    # t1 = t[0]
    # t2 = t1.get('tx')
    #
    # print(s)
    # a, p = btc_wallet.create_account('zxc')
    # print(a, p)
    # t = btc_wallet.is_valid_address(a)
    # print(t)

    # t = btc_wallet.is_connected()
    # print(t)
    # from bitcoinrpc.authproxy import AuthServiceProxy
    # 测试
    # bitcoin_cli = AuthServiceProxy("http://xianda:ABQOqmPZ0tr95f5Z@47.244.167.70:8332")
    # 正式
    # bitcoin_cli = AuthServiceProxy("http://xianda:ABQOqmPZ0tr95f5Z@47.52.131.71:8332")




    # bitcoin_cli = AuthServiceProxy("http://xianda:ABQOqmPZ0tr95f5Z@47.100.20.62:8332")
    # ret = bitcoin_cli.gettransaction('9f767bfedb03f95cd9d76c49b0f96aa20b680fc4cc00b226a6242e738b8b060d')
    # print(ret)
    # s = bitcoin_cli.getbalance("btc_base")
    # print(s)
    # r4 = bitcoin_cli.getbalance('hw')
    # print(r4)
    # # print(bitcoin_cli)
    # # address = bitcoin_cli.getnewaddress('hw')
    # # print(address)
    #
    # r1 = bitcoin_cli.getaddressesbyaccount('btc_base')
    # print(r1)
    # r2 = bitcoin_cli.getaddressesbyaccount('hw')
    # print(r2)

    # r5 = bitcoin_cli.estimatefee(6)
    # print(r5)

    # r3 = bitcoin_cli.sendfrom('btc_base', '18QPurCMeveuTrcg9YWmtsAiyxg4DkBuey', 0.018)
    # print(r3)
    # r2 = bitcoin_cli.getaccount('1AmntCaucDzo9NAMbUg4yenEozQ5EDRAP3')
    # print(r2)
    # r = bitcoin_cli.listunspent(1, 9999999, ['18QPurCMeveuTrcg9YWmtsAiyxg4DkBuey'])
    # print(r)
    # r3 = bitcoin_cli.listaddressgroupings()
    # print(r3)

    # btc_wallet = BtcWallet()
    # btc_wallet.init_consul('xianda', 'ABQOqmPZ0tr95f5Z', '47.244.167.70:8332')
    # r = btc_wallet.get_block_num()
    # is_success = btc_wallet.is_connected()
    # print(r, is_success)
