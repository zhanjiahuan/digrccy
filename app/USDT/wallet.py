# coding:utf-8
from _decimal import Decimal
from functools import reduce

from bitcoinrpc.authproxy import AuthServiceProxy

from app import session_pool
from app.common.consul import ConsulServiceName
import logging

from app.models import Config, Order


class UsdtWallet():
    USDT_BLOCK_NUM = 'http://www.tokenview.com:8088/coin/latest/USDT'
    USDT_TX_API = 'https://api.omniexplorer.info/v1/transaction/address'
    USDT_URL_BALANCE = 'https://api.omniexplorer.info/v1/address/addr/'

    def __init__(self, consul_client=None):
        if consul_client:
            self.init_consul(consul_client)

    def init_consul(self, app, consul_client):
        self.propertyid = 31
        # self.usdt_rpc_user = app.config["USDT_RPC_USER"]
        # self.usdt_rpc_password = app.config["USDT_RPC_PWD"]
        # self.usdt_passphrase = app.config.get('GETH_USDT_PASSPHRASE')
        # self.consul_client = consul_client
        # # self.wallet_url = self.consul_client.getRandomOneAvailableServiceIpPort(ConsulServiceName.USDTEREUM_CLI)
        # self.wallet_url = '47.52.131.71:7332'
        # print(self.wallet_url)
        # self.usdtcoin_cli = AuthServiceProxy(
        #     "http://%s:%s@" % (self.usdt_rpc_user, self.usdt_rpc_password) + self.wallet_url, timeout=10)
        # if not self.is_connected():
        #     logging.error('Connect USDT wallet node fial')
        self.usdtcoin_cli = AuthServiceProxy("http://%s:%s@47.52.131.71:7332" % ('xianda', 'ABQOqmPZ0tr95f5Z'))

    def is_connected(self):
        """获取钱包状态判读是否链接"""
        try:
            if self.usdtcoin_cli.getwalletinfo().get('walletversion'):
                return True
            return False
        except Exception as e:
            return False

    def is_syncing(self):
        """节点是否在同步中"""
        # 注意返回Flase表示节点同步完成
        info = self.usdtcoin_cli.getblockchaininfo()
        # print(info['blocks'], info['headers'])
        if info['blocks'] != info['headers']:
            return False
        else:
            return True

    def accountCreate(self, accountName):
        # 否则，创建账户，并返回账户地址
        address = self.usdtcoin_cli.getaccountaddress(accountName)
        privateKey = self.usdtcoin_cli.dumpprivkey(address)
        return privateKey, address

    # 檢驗賬戶是否有效
    def is_valid_address(self, address):
        if address is None or address == '':
            return False
        else:
            try:
                # print(self.usdtcoin_cli.validateaddress(address))
                return self.usdtcoin_cli.validateaddress(address).get('isvalid')
            except:
                return False

    # 獲取餘額
    def get_balance(self, address):
        """获取余额,默认最新区块"""
        try:
            balance = str(self.usdtcoin_cli.omni_getbalance(address, self.propertyid)['balance'])
        except Exception as e:
            logging.error('USDT node get balance error:{}'.format(str(e)))
            raise Exception('USDT node get balance error')
        return Decimal(balance)

    def get_block_num(self):
        """获取最新区块数"""
        try:
            block_num = self.usdtcoin_cli.getblockcount()
        except Exception as e:
            logging.error('Get eth node block number error:{}'.format(str(e)))
            return
        return block_num

    def get_nonce(self, address):
        """获取账户nonce值"""
        try:
            # pending 获得最新已使用的nonce,对nonce进行加1
            nonce = len(self.usdtcoin_cli.omni_listpendingtransactions(address))
        except Exception as e:
            logging.error('USDT node get balance error:{}'.format(str(e)))
            raise Exception('USDT node get balance error')
        return nonce

    def get_mian_block_num(self):
        """获取公链上的最新区块数"""
        try:
            header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.75 Safari/537.36',
            }
            ret = session_pool.get(self.USDT_BLOCK_NUM, headers=header, timeout=30).json()
            if ret is None:
                logging.error('Get usdt main chain block number error')
                return
            block_num = ret.get('data')
        except Exception as e:
            logging.error('Get usdt main chain block number error:{}'.format(e))
            return
        return block_num  # int

    def get_minerFee(self, address):
        data = {'addr': address}
        try:
            balance = None
            rets = session_pool.post(self.USDT_URL_BALANCE, data=data, timeout=50).json().get('balance')
            if rets or len(rets) != 0:
                for ret in rets:
                    if ret.get('propertyinfo') and int(ret.get('propertyinfo').get('propertyid')) == 0:
                        balance = ret.get('value')
        except Exception as e:
            logging.error(
                'Request USDT_TX_API error address:{},error:{},url:{}'.format(address, str(e), self.USDT_TX_API))
            raise Exception('USDT node get balance error')
        return Decimal(balance) / 100000000

    def usdt_transaction_record(self, address, last_timestamp, start_block=None, end_block=None):
        """查询账户交易记录"""
        if start_block is None:
            start_block = 0
        if end_block is None:
            end_block = 99999999
        # 可能会有重复记录，使用此方法
        run_function = lambda x, y: x if y in x else x + [y]

        data = {'addr': address, 'page': 0}
        try:
            rets = session_pool.post(self.USDT_TX_API, data=data, timeout=50).json()
        except Exception as e:
            logging.error(
                'Request USDT_TX_API error address:{},error:{},url:{}'.format(address, str(e), self.USDT_TX_API))
            rets = None

        new_records = []
        ret = rets.get('transactions')
        if ret is None:
            return new_records
        ret_page_num = int(rets.get('pages'))
        if ret_page_num == 1:
            # print(ret_page_num)
            self.query_records(address, ret, new_records, last_timestamp, start_block, end_block)
            return (reduce(run_function, [[], ] + new_records))
        else:
            for i in range(0, ret_page_num):
                data = {'addr': address, 'page': i}
                try:
                    ret = session_pool.post(self.USDT_TX_API, data=data, timeout=50).json().get('transactions')
                except Exception as e:
                    logging.error(
                        'Request USDT_TX_API error address:{},error:{},url:{}'.format(address, str(e),
                                                                                      self.USDT_TX_API))
                    ret = None

                if ret is None:
                    return new_records
                self.query_records(address, ret, new_records, last_timestamp, start_block, end_block)
            return (reduce(run_function, [[], ] + new_records))

    def query_records(self, address, records, new_records, last_timestamp, start_block, end_block):
        for record in records:
            propertyid = record.get('propertyid')
            valid = record.get('valid')
            block = record.get('block')
            if valid and int(propertyid) == 31 and int(start_block) <= int(block) and int(block) <= int(end_block):
                to_address = record['referenceaddress']  # 是否为收款记录
                current_timestamp = int(record['blocktime'])  # 当前记录时间戳
                confirmations = int(record['confirmations'])  # 交易记录确认数
                record_hash = record['txid']
                amount = Decimal(record['amount'])
                if to_address.lower() != address.lower():
                    continue
                if int(last_timestamp) > int(current_timestamp):
                    continue
                if Order.hash_is_exist(record_hash):
                    continue
                if amount < Decimal('0.0000001'):
                    continue
                if confirmations < 2:
                    break
                else:
                    new_records.append(record)
            else:
                if records is None:
                    logging.error(
                        'Request USDT_TX_API fail address:{} ret:{}, url:{}'.format(address, str(records),
                                                                                    self.USDT_TX_API))
        return new_records

    def hash_get_detail(self, tx_hash):
        """hash获取交易细节,用于确认链外交易是否被确认"""
        # 交易是否被确认.status=1(被确认)
        is_confirm = False  # 是否确认
        is_success = False  # 如果已确认,交易是否成功
        msg = None  # 未被确认返回异常信息(一般超时),确认失败:失败的细节,确认成功:交易详情
        fee = None  # 确认成功交易的手续费
        try:
            ret = self.usdtcoin_cli.omni_gettransaction(tx_hash)  # 获取交易细节
        except Exception as e:
            msg = str(e)
            return is_confirm, is_success, msg, fee

        confirm = ret.get('confirmations')
        if confirm < 1:  # 确认交易失败
            msg = dict(fail_detail=str(ret))
            return is_confirm, is_success, msg, fee
        else:  # 确认交易成功
            is_confirm = True
            is_success = True
            fee = ret.get('fee')
            msg = dict(confirm=str(ret), tx_detail=str(ret))
            return is_confirm, is_success, msg, fee

    def payment(self, addrfrom, addrto, amount):
        """普通付款"""
        # 单位换算
        payload = {
            'from': addrfrom,
            'to': addrto,
            'value': str(amount)
        }
        try:
            # 钱包转账,返回交易哈希值
            tx_hash = self.usdtcoin_cli.omni_send(addrfrom, addrto, self.propertyid, str(amount))
            return True, tx_hash
        except Exception as e:
            payload.update(dict(errormsg=str(e)))
            logging.error('usdt payment error:{}'.format(str(payload)))
            return False, str(e)

    def raw_transaction(self, minerfee_address, fromAddr, toAddre, value, miner_minfee):
        # 查询USDT未使用的UTXO
        USDT_unspents = self.usdtcoin_cli.listunspent(1, 9999999, [fromAddr])
        if not USDT_unspents:
            return False, str('No USDT UTXO model available')
        USDT_unspent = USDT_unspents[0]
        # 查询BTC未使用的UTXO(矿工费)
        BTC_unspents = self.usdtcoin_cli.listunspent(1, 9999999, [minerfee_address])
        if not BTC_unspents:
            return False, str('No BTC UTXO model available')
        BTC_unspent = BTC_unspents[0]
        # 所用值
        from_txid = USDT_unspent['txid']
        from_scriptPubKey = USDT_unspent['scriptPubKey']
        from_vout = USDT_unspent['vout']
        from_amount = USDT_unspent['amount']
        to_txid = BTC_unspent['txid']
        to_scriptPubKey = BTC_unspent['scriptPubKey']
        to_vout = BTC_unspent['vout']
        to_amount = BTC_unspent['amount']

        rawtransactionparams = [
            dict(txid=from_txid, scriptPubKey=from_scriptPubKey, vout=from_vout),
            dict(txid=to_txid, scriptPubKey=to_scriptPubKey, vout=to_vout),
        ]
        # 创建原生BTC交易获取哈希值
        RawTxChangeparams = [
            # 转出地址必须放在第一个，矿工费地址放在下面
            dict(txid=from_txid, scriptPubKey=from_scriptPubKey, vout=from_vout, value=from_amount),
            dict(txid=to_txid, scriptPubKey=to_scriptPubKey, vout=to_vout, value=to_amount),
        ]

        # 构造发送代币类型和代币数量数据
        payload = self.usdtcoin_cli.omni_createpayload_simplesend(self.propertyid, str(value))
        print('usdt交易', payload)

        # 构造交易基本数据
        data = {}
        btc_txid = self.usdtcoin_cli.createrawtransaction(rawtransactionparams, data)

        # 在交易上绑定代币数据
        rawtx = self.usdtcoin_cli.omni_createrawtx_opreturn(btc_txid, payload)
        print('usdt交易绑定到btc交易的哈希', rawtx)

        # 在交易上添加接收地址
        rawtx = self.usdtcoin_cli.omni_createrawtx_reference(rawtx, toAddre)
        print('添加接受地址', rawtx)

        # 在交易数据上指定矿工费用
        rawtx = self.usdtcoin_cli.omni_createrawtx_change(rawtx, RawTxChangeparams, minerfee_address,
                                                          Decimal(miner_minfee))
        print('设置手续的哈希', rawtx)

        # 签名
        ret = self.usdtcoin_cli.signrawtransaction(rawtx)
        if not ret['complete']:
            return False, str('Incomplete signature')

        # 广播
        tx_hash = self.usdtcoin_cli.sendrawtransaction(ret['hex'])
        print('交易哈希', tx_hash)

        if tx_hash:
            return True, tx_hash


if __name__ == '__main__':
    usdt = UsdtWallet()
    usdt.init_consul('', '')
    # print(usdt.is_connected())
    # print(usdt.accountCreate('testimport'))  # ('L5X7YNdgAtxyAAgYyLGGSjhk7rEkqFr2zhfkbEVFaCCkutBvtkRr', '1MckVEYqe5vbZK3a8sok4rmkoDMLVM39gX')
    # print(usdt.is_valid_address('mpM35he86ZEyFmxQnDztkcz3VZYviGEJ6m'))
    # print(usdt.usdtcoin_cli.listunspent(1,99999,['1HsUNgnho9dx9AUubASpCqcsj1386E6wj2']))
    # print(usdt.hash_get_detail(' 48fd721a0354afa2e82800b4b9d2d89dbbc0ce09ab3c4b8cd15af6c566bbab29'))
    # 'https://blockchain.info/rawaddr/385cR5DM96n1HvBDMzLHPYcw89fZAXULJP'
    # print(usdt.get_nonce('1HsUNgnho9dx9AUubASpCqcsj1386E6wj2'))
    # print(usdt.hash_get_detail('a01fcf8c74e8e073192d73d7d92b4ddb820bcc1e171cc19d83633054e552114e'))
    # print(usdt.usdt_transaction_record('1EUsB3ie8u1hyj9B3auGHhFCmPNiWLVBBZ', '1554793254', start_block='570856',
    #                                    end_block=99999999))

    # print(usdt.payment('16qKzximv3LZziW7nvpvE7rtdTmoPXQPJs', '1HsUNgnho9dx9AUubASpCqcsj1386E6wj2', 0.1))
    # print(usdt.usdtcoin_cli.listunspent (1,99999999,['1HsUNgnho9dx9AUubASpCqcsj1386E6wj2']))
    # print(usdt.usdtcoin_cli.sendfrom('16qKzximv3LZziW7nvpvE7rtdTmoPXQPJs', '1HsUNgnho9dx9AUubASpCqcsj1386E6wj2', 0.1))
    # print(usdt.is_syncing())
    # print(usdt.usdtcoin_cli.importprivkey('KzZ5KMRQMLCyARzoLKb21SZMpvG6NakVy4iU6zqZpktMBqgj5UJp'))
    # print(usdt.raw_transaction('1HsUNgnho9dx9AUubASpCqcsj1386E6wj2', '1LyMjZMJ2xG4uYMgfoG8v516ePkTnYFrhv', '1HsUNgnho9dx9AUubASpCqcsj1386E6wj2', '0.0005', 0.0000273))
    # print(usdt.usdtcoin_cli.listaddressgroupings())
    # print(usdt.usdtcoin_cli.sendfrom('GDSS37FWDPXHR4J4FZI6BGFT2ZS7JBE6RNNWODTV4OKHLHYAIH7QDZNC','1HsUNgnho9dx9AUubASpCqcsj1386E6wj2', 0.08))
    # print(usdt.usdtcoin_cli.omni_send('14PntN3XmTFsjdUfGuqywsdB1VV3Y8u6wY', '1HsUNgnho9dx9AUubASpCqcsj1386E6wj2', 31, '0.0001'))
    # print(usdt.get_balance('mpM35he86ZEyFmxQnDztkcz3VZYviGEJ6m'))
    # print(usdt.usdtcoin_cli.getbalance('USDTBASE'))
    # print(usdt.usdtcoin_cli.listaccounts())
    # print(usdt.usdtcoin_cli.getaccountaddress('USDTFEADER'))
    # print(usdt.get_nonce('n4LiiZuk9hNNvEWAETohmSoNsU12QLzoih'))
    # print(usdt.is_connected())
    # print(usdt.get_balance('USDTFEADER'))
    # print(usdt.get_minerFee('1HsUNgnho9dx9AUubASpCqcsj1386E6wj2'))
    # print(usdt.usdt_transaction_record('14PntN3XmTFsjdUfGuqywsdB1VV3Y8u6wY',1514085059))
    # print(Order.hash_is_exist('fb3e12755ee7ad2a18ac07cde651670ea0b1c22f8ad73c07d002f510f23dd3b4'))
    # print(usdt.payment('1LyMjZMJ2xG4uYMgfoG8v516ePkTnYFrhv','1HsUNgnho9dx9AUubASpCqcsj1386E6wj2',0.0003))
    # 18c7fa1e2d0513c06d6e01b1807ad1c297ca2a10550a92ec1ca5857ed9d73c1f
