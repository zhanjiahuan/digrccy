import random
import consulate
import time
import json
import logging

from decimal import Decimal
from random import randint


class ConsulServiceName():
    """注册在consul的服务对应服务名"""
    STELLAR_BASE = "xfin_blockchain_base-8000"

    APM_ZIPKIN = "xfin_zipkin"

    ETHEREUM_CLI = "eth_test"

    BTC_CLI = "bitcoin_test"

    USDTEREUM_CLI = "usdtcoin_cli"

    EOSEREUM_CLI = "eos_t1"

    STELLAR_FULL = "xfin_blockchain_base-8000"

    DAPP_PHPSERVICE = "xfin_dapp_phpservice"


class ConsulClient():
    SERVICE_IPPORTLIST_MEMSTORE = {}

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        self._token = app.config.get('CONSUL_TOKEN')
        ipport = app.config.get('CONSUL_IP')
        self.consul = consulate.Consul(host=ipport, port=8500, token=self._token)

    def getAvailableServices(self, serviceName):
        return self.consul.catalog.service(serviceName)

    def getRandomOneAvailableService(self, serviceName):
        ava_services = self.consul.catalog.service(serviceName)
        if len(ava_services) == 0:
            return None
        else:
            return ava_services[randint(0, len(ava_services) - 1)]

    # 20181205优化 存储在mem 时效3s
    def getRandomOneAvailableServiceIpPort(self, serviceName, withHttpPrefix=False):
        service_updatets = serviceName + "_updatets"
        realnowts = time.time()
        # service ip列表信息保存在内存3秒，超过3秒从consul上取
        # from mem
        if serviceName in self.SERVICE_IPPORTLIST_MEMSTORE and self.SERVICE_IPPORTLIST_MEMSTORE[
            service_updatets] + 3 > realnowts:
            if withHttpPrefix is True:
                ret = "http://" + random.choice(self.SERVICE_IPPORTLIST_MEMSTORE[serviceName])
            else:
                ret = random.choice(self.SERVICE_IPPORTLIST_MEMSTORE[serviceName])
            return ret
        # from consul
        else:
            ava_services = self.getAvailableServices(serviceName)
            if ava_services is not None and len(ava_services) != 0:
                self.SERVICE_IPPORTLIST_MEMSTORE[serviceName] = [
                    ava_service["ServiceAddress"] + ":" + str(ava_service["ServicePort"]) for ava_service in
                    ava_services]
                self.SERVICE_IPPORTLIST_MEMSTORE[service_updatets] = time.time()
            else:
                logging.error(
                    "can not find service :{} in consul. serviceName or consul error . auto use mem route list .".format(
                        serviceName))

            if self.SERVICE_IPPORTLIST_MEMSTORE[serviceName] is not None and len(
                    self.SERVICE_IPPORTLIST_MEMSTORE[serviceName]) != 0:
                if withHttpPrefix is True:
                    ret = "http://" + random.choice(self.SERVICE_IPPORTLIST_MEMSTORE[serviceName])
                else:
                    ret = random.choice(self.SERVICE_IPPORTLIST_MEMSTORE[serviceName])
                return ret
            else:
                logging.error("can not find service :{} in consul. serviceName or consul error".format(serviceName))
                raise Exception("can not find service : " + serviceName + "  in consul. serviceName or consul error")

    # 配置添加
    def putKVToConsul(self, key, value):
        return self.consul.kv.set(key, value)

    # 配置获取
    def getValueByKeyFromConsul(self, key, default=None):
        ret = self.consul.kv.get(key)
        if ret is None:
            logging.error(
                "No this consul kv key:" + key + " or consul kv token:" + self._token + " is wrong ,have no right ")
        return ret

    def get_task_switch(self):
        """定时任务开关1=开启其余关闭"""
        result = self.getValueByKeyFromConsul('digiccy.tasks.switch')
        if result != '1':
            return False
        else:
            return True

    def get_stellar_base_account(self, coin_name, is_seed=True):
        """获取货币stellar base账户,用户代币充值"""
        if not is_seed:
            consul_key = 'digiccy.stellar.{}.base.address'.format(coin_name)
        else:
            consul_key = 'digiccy.stellar.{}.base.seed'.format(coin_name)
        result = self.getValueByKeyFromConsul(consul_key)
        return result

    def get_digiccy_base_account(self, coin_name, is_seed=True):
        """获取地三方货币账户"""
        if not is_seed:
            consul_key = 'digiccy.digiccy.{}.base.address'.format(coin_name)
        else:
            consul_key = 'digiccy.digiccy.{}.base.seed'.format(coin_name)
        result = self.getValueByKeyFromConsul(consul_key)
        return result

    def get_digiccy_collect_min(self, coin_name):
        """获取第三方货币归集最小数量"""
        consul_key = 'digiccy.digiccy.{}.collect.min'.format(coin_name)
        min_amount = self.getValueByKeyFromConsul(consul_key)
        min_amount = Decimal(min_amount)
        return min_amount

    def get_miner_fee(self, coin_name):
        """获取第三方货币矿工费转帐数"""
        consul_key = 'digiccy.digiccy.{}.miner.fee'.format(coin_name)
        min_amount = self.getValueByKeyFromConsul(consul_key)
        min_amount = Decimal(min_amount)
        return min_amount

    def get_digiccy_minerfee_privatekey(self, coin_name):
        consul_key = 'digiccy.digiccy.{}.minerfee.privatekey'.format(coin_name)
        privatekey = self.getValueByKeyFromConsul(consul_key)
        return privatekey

    def get_digiccy_minerfee_address(self, coin_name):
        consul_key = 'digiccy.digiccy.{}.minerfee.address'.format(coin_name)
        address = self.getValueByKeyFromConsul(consul_key)
        return address

    def get_digiccy_boss_address(self, coin_name):
        """获取boss账户,归集使用"""
        consul_key = 'digiccy.digiccy.{}.boss.address'.format(coin_name)
        return self.getValueByKeyFromConsul(consul_key)

    def get_digiccy_collect_fee(self, coin_name):
        """归集手续费"""
        consul_key = 'digiccy.digiccy.{}.collect.gas'.format(coin_name)
        gas = self.getValueByKeyFromConsul(consul_key)
        gas = json.loads(gas)
        gas_limit = Decimal(gas['gas_limit'])
        gas_price = Decimal(gas['gas_price'])
        return gas_limit, gas_price

    def get_digiccy_coin_types(self):
        """返回币种名称"""
        consul_key = 'digiccy.coin.types'
        ret = self.getValueByKeyFromConsul(consul_key)
        ret = json.loads(ret)
        return ret

    def get_digiccy_min_balances(self, chain):
        consul_key = 'digiccy.{}.minbalance'.format(chain)
        ret = self.getValueByKeyFromConsul(consul_key)
        ret = json.loads(ret)
        return ret

    def get_digiccy_coin_limit(self):
        """返回币种名称"""
        consul_key = 'digiccy.withdraw.limit'
        ret = self.getValueByKeyFromConsul(consul_key)
        ret = json.loads(ret)
        return ret

    def get_withdraw_min_amount(self, coin_name):
        """提笔最小数量"""
        ret = self.get_digiccy_coin_limit()
        min_amount = ret.get(coin_name)
        min_amount = Decimal(min_amount)
        return min_amount

    def get_mobiles(self):
        """归集手续费"""
        consul_key = 'digiccy.digiccy.mobiles'
        mobiles_str = self.getValueByKeyFromConsul(consul_key)
        mobiles_dict = json.loads(mobiles_str)
        mobile1 = mobiles_dict['mobile1']
        mobile2 = mobiles_dict['mobile2']
        return mobile1, mobile2

    def get_btc_collect_fee(self, coin_name):
        """btc归集手续费"""
        consul_key = 'digiccy.digiccy.{}.collect'.format(coin_name)
        gas = self.getValueByKeyFromConsul(consul_key)
        gas = json.loads(gas)
        return gas

    def get_digiccy_base_privatekey(self, coin_name):
        consul_key = 'digiccy.digiccy.{}.base.privatekey'.format(coin_name)

        return self.getValueByKeyFromConsul(consul_key)
