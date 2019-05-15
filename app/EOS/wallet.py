import json
import random
# from celery import Celery
import requests
from bitcoinrpc.authproxy import AuthServiceProxy
import logging

from app import consul_clinet
# 这两个类方法是网上fork下来的,后续如何eos的接口有问题请先确认包还能不能用!!!!!!!!!
from app.EOS.eospy.cleos import Cleos
from app.EOS.eospy.keys import EOSKey
from app.base.base import DigiccyBase
from app.models import Config
from decimal import Decimal

from app.utils.commons import decryptSeed

COIN_NAME = 'EOS'
class EosWallet():
    def __init__(self, app=None, consul_client=None):
        nodefo_host = "https://public.eosinfra.io"
        self.ce = Cleos(url=nodefo_host)
        if consul_client:
            self.init_consul(app, consul_client)

    # 生成账号的规则
    def randomString(self, choice=12):
        seed = list("12345abcdefghijklmnopqrstuvwxyz")
        random.shuffle(seed)
        sa = []
        for i in range(choice):
            sa.append(random.choice(seed))
        salt = ''.join(sa)
        print("新账号：", salt)
        # 如果存在，则递归
        try:
            ret = self.ce.get_account(salt)
            if ret:
                print("账号已经被注册！！！")
                self.randomString(12)
            else:
                return salt
        # 否则，肯定会报异常，那就直接返回
        except:
            print("用户名注册成功！！！")
            return salt

    def init_consul(self, app, consul_client):
        try:
            self.usdtcoin_cli = AuthServiceProxy("http://%s:%s@47.244.167.70:8888" % ('', ''))
            if self.usdtcoin_cli:
                print("Succeed to connect to the EOS consul")
                return True
            else:
                print("Failed to connect to the EOS consul")
                return False
        except Exception as e:
            logging.error(e, "Failed to connect to the EOS consul")

    # 连接eos节点
    def init_eos(self, nodefo_host="https://public.eosinfra.io"):
        self.ce = None
        self.nodefo_host = nodefo_host
        # self.xiandaConsulClient = xiandaConsulClient
        try:
            self.ce = Cleos(url=nodefo_host)
        except Exception as e:
            print(str(e))
        if self.ce is None or not self.is_syncing():
            print("Failed to connect to the EOS node")
            return False
        else:
            print("Succeed to connect to the EOS node")
            return True

    # 判断钱包是否连接
    def is_syncing(self):
        try:
            results = self.ce.get_info()
            print("连接成功!", results)
            if results:
                return True
            return False
        except Exception as e:
            return False

    # 获取指定区域块的信息
    def get_message_block(self, block_name):
        ret = self.ce.get_block(block_num=block_name)
        print(ret)

    # 获取最新区域块的信息
    def get_block_num(self):
        """获取最新区块数"""
        try:
            url = 'https://api.eospark.com/api?module=block&action=get_latest_block&apikey=a9564ebc3289b7a14551baf8ad5ec60a'
            ret = requests.get(url)
            data_obj = ret.text
            data_json = json.loads(data_obj)
            lock_mun = data_json.get("data").get("block_num")
            return lock_mun
        except:
            logging.error("error for get new block num")

    # 获取指定账户的信息，验证账号
    def is_valid_address(self, account_name):
        try:
            ret = self.ce.get_account(acct_name=account_name)
            print("用户信息：", ret)
            return ret
        except:
            logging.error("error for get message of account")



    # hash获取信息
    def get_transaction(self, transaction_id):
        # 交易是否被确认.status=1(被确认)
        is_confirm = False  # 是否确认
        is_success = False  # 如果已确认,交易是否成功
        msg = None  # 未被确认返回异常信息(一般超时),确认失败:失败的细节,确认成功:交易详情
        fee = 0  # 确认成功交易的手续费
        try:
            ret = self.ce.get_transaction(transaction_id)  # 获取交易细节
            print(ret)
        except Exception as e:
            msg = str(e)
            return is_confirm, is_success, msg, fee

        result = ret['trx']['receipt']['status']
        if result != "executed":  # 确认交易失败
            msg = dict(fail_detail=str(ret))
            return is_confirm, is_success, msg, fee
        else:  # 确认交易成功
            is_confirm = True
            is_success = True
            fee = 0
            msg = dict(confirm=str(ret), tx_detail=str(ret))
            return is_confirm, is_success, msg, fee

    # 获取账户的所有交易信息
    def eos_transaction_record(self, account_name):
        try:
            ret = self.ce.get_actions(account_name)
            return ret
        except:
            logging.error("error for get message of transaction")

    # 获取账户余额
    def get_balance(self, account):
        try:
            ret = self.ce.get_currency_balance(account=account)
            print(ret)
            if len(ret) != 0:
                balance = float(ret[0].split(" ")[0])
                print(balance)
                return balance
            else:
                return 0
        except:
            logging.error("error for get balance ")

    # 创建新账户
    def create_account(self):
        try:
            creator_privkey = consul_clinet.get_digiccy_base_privatekey(COIN_NAME)
            creator = consul_clinet.get_digiccy_base_account(COIN_NAME,is_seed=False)
            creator_privkey = eval(decryptSeed(creator_privkey)).get("seed")
            # 创建账号名
            acct_name = self.randomString(12)
            eosKey = EOSKey()
            privKey = eosKey.to_wif()
            owner_key = str(eosKey)
            # 创建账号
            self.ce.create_account(creator,
                                   creator_privkey,
                                   acct_name,
                                   owner_key,
                                   active_key='',
                                   stake_net='0.0500 EOS',
                                   stake_cpu='0.1500 EOS',
                                   ramkb=2,
                                   permission='active',
                                   transfer=False,
                                   broadcast=True,
                                   timeout=30)
            print("私钥：", privKey, "用户：", acct_name)
            return privKey, acct_name
        except Exception as e:
            logging.error("error for create account")
            print(str(e))
            return '', e

    # 获取账户的RAM，CPU，NET余额，主要用来防止RAM余额不足无法进行各项操作
    def get_account_ram_cup_net(self, account_name, user_digiccy_secret):
        creator = consul_clinet.get_digiccy_base_account(COIN_NAME, is_seed=False)
        creator_privkey = consul_clinet.get_digiccy_base_privatekey(COIN_NAME)
        creator_privkey = eval(decryptSeed(creator_privkey)).get("seed")
        try:
            url = f"https://api.eospark.com/api?module=account&action=get_account_resource_info" \
                f"&apikey=a9564ebc3289b7a14551baf8ad5ec60a&account={account_name}"
            ret = requests.get(url)
            data_obj = ret.text
            data_json = json.loads(data_obj)
            data = data_json.get("data")
            ram = data.get("ram").get("available")
            cpu = data.get("cpu").get("available")
            net = data.get("net").get("available")
            if ram < 3000:
                self.system_buy_ram(creator=creator,
                                    creator_privkey=creator_privkey,
                                    acct_name=account_name)
                self.payment(user_digiccy_secret, account_name, creator, 0.1)
            elif cpu < 2000 or net < 3000:
                self.system_buy_cpu_net(creator=creator,
                                        creator_privkey=creator_privkey,
                                        acct_name=account_name)
                self.payment(user_digiccy_secret, account_name, creator, 0.03)
            elif ram==0 and cpu==0 and net==0:
                logging.error("error for get account ram,cup,net")
            print(f"RAM可用:{ram},CPU可用:{cpu},NET口可用:{net}")
            return ram, cpu, net
        except:
            logging.error("error for get account ram,cup,net")

    # 转账交易
    def payment(self, privKey, fromAddr="", toAddre="", value=None, timeout=30):
        quantity = '%.4f' % value
        quantity = quantity + ' EOS'
        print('充值的金额：', quantity)
        payload = [
            {
                'args': {
                    "from": fromAddr,  # sender
                    "to": toAddre,  # receiver
                    "quantity": quantity,  # In EOS
                    "memo": "EOS to the moon",
                },
                "account": "eosio.token",
                "name": "transfer",
                "authorization": [{
                    "actor": fromAddr,
                    "permission": "active",
                }],
            }
        ]
        try:
            # 转为二进制
            data = self.ce.abi_json_to_bin(payload[0]['account'], payload[0]['name'], payload[0]['args'])
            # 插入到data
            payload[0]['data'] = data['binargs']
            # 去除args字段
            payload[0].pop('args')
            # 形成交易
            trx = {"actions": [payload[0]]}

            resp = self.ce.push_transaction(trx, privKey, broadcast=True, timeout=timeout)
            if 'transaction_id' not in resp:
                return False, '', str(resp)
            print("充值成功！！")
            print(resp)
            trx_id = resp['transaction_id']
            return True, trx_id,
        except Exception as e:
            print(e)
            return False, str(e)

    # 为用户充值2kb,RAM,从客户账号转0.1eos费用
    def system_buy_ram(self, creator, creator_privkey, acct_name, ramkb=2, broadcast=True, permission='active',
                       timeout=30):
        buyram_data = self.ce.abi_json_to_bin('eosio', 'buyrambytes',
                                              {'payer': creator, 'receiver': acct_name, 'bytes': ramkb * 1024})
        buyram_json = {
            'account': 'eosio',
            'name': 'buyrambytes',
            'authorization': [
                {
                    'actor': creator,
                    'permission': permission
                }],
            'data': buyram_data['binargs']
        }
        trx = {"actions": [buyram_json]}
        ret = self.ce.push_transaction(trx, creator_privkey, broadcast=broadcast, timeout=timeout)
        print("充值ram记录：", ret)
        # TODO

    # 为用户抵押CPU，NET
    def system_buy_cpu_net(self, creator, creator_privkey, acct_name, stake_cpu='0.0100 EOS', stake_net='0.0100 EOS',
                           broadcast=True, transfer=False, permission='active',
                           timeout=30):
        delegate_data = self.ce.abi_json_to_bin('eosio', 'delegatebw',
                                                {'from': creator, 'receiver': acct_name,
                                                 'stake_net_quantity': stake_net,
                                                 'stake_cpu_quantity': stake_cpu, 'transfer': transfer})
        delegate_json = {
            'account': 'eosio',
            'name': 'delegatebw',
            'authorization': [
                {
                    'actor': creator,
                    'permission': permission
                }],
            'data': delegate_data['binargs']
        }
        trx = {"actions": [delegate_json]}
        return self.ce.push_transaction(trx, creator_privkey, broadcast=broadcast, timeout=timeout)


if __name__ == '__main__':
    eos = EosWallet()
    eos.init_consul("", "")
    # eos.payment("5Jb46jpSGwuXJXcom6e5PdLsaW1rMwc3MUqhZnVTApqVynMcXxA","jianghui1111","ekhsleic1fyt",0.01)
    eos.init_eos()
    # eos.get_balance("jianghui1111")
    # eos.eos_transaction_record("k231zuayfnwj")


