# encoding=utf8
import os


class Config(object):
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    DEBUG = True

    # CELERY_BROKER_URL = 'redis://:G%E5qk1T@101.132.188.48:6379/13'
    # 定时任务
    JOBS = [
        # {
        #     'id': 'eth.task_chain_out_recharge.job',
        #     'func': 'app.ETH.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 1500  # 25分钟
        # },
        # {
        #     'id': 'eth.task_chain_in_recharge.job',
        #     'func': 'app.ETH.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 50
        # },
        # {
        #     'id': 'eth.task_chain_out_withdraw.job',
        #     'func': 'app.ETH.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eth.task_chain_out_confirm.job',
        #     'func': 'app.ETH.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eth.task_chain_out_collect.job',
        #     'func': 'app.ETH.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eth.task_chain_in_confirm.job',
        #     'func': 'app.ETH.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vrt.task_chain_out_recharge.job',
        #     'func': 'app.VRT.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vrt.task_chain_in_recharge.job',
        #     'func': 'app.VRT.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vrt.task_chain_out_withdraw.job',
        #     'func': 'app.VRT.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vrt.task_chain_out_confirm.job',
        #     'func': 'app.VRT.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vrt.task_chain_in_confirm.job',
        #     'func': 'app.VRT.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vrt.task_chain_out_collect.job',
        #     'func': 'app.VRT.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'ipchain.task_chain_out_recharge.job',
        #     'func': 'app.IPCHAIN.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'ipchain.task_chain_in_recharge.job',
        #     'func': 'app.IPCHAIN.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'ipchain.task_chain_out_withdraw.job',
        #     'func': 'app.IPCHAIN.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'ipchain.task_chain_out_confirm.job',
        #     'func': 'app.IPCHAIN.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'ipchain.task_chain_in_confirm.job',
        #     'func': 'app.IPCHAIN.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'ipchain.task_chain_out_collect.job',
        #     'func': 'app.IPCHAIN.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'abs.task_chain_out_recharge.job',
        #     'func': 'app.ABS.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'abs.task_chain_in_recharge.job',
        #     'func': 'app.ABS.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'abs.task_chain_out_withdraw.job',
        #     'func': 'app.ABS.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'abs.task_chain_out_confirm.job',
        #     'func': 'app.ABS.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'abs.task_chain_in_confirm.job',
        #     'func': 'app.ABS.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'abs.task_chain_out_collect.job',
        #     'func': 'app.ABS.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        {
            'id': 'yec.task_chain_out_recharge.job',
            'func': 'app.YEC.tasks:task_chain_out_recharge',
            'args': (),
            'trigger': 'interval',
            'seconds': 10
        },
        {
            'id': 'yec.task_chain_in_recharge.job',
            'func': 'app.YEC.tasks:task_chain_in_recharge',
            'args': (),
            'trigger': 'interval',
            'seconds': 10
        },
        {
            'id': 'yec.task_chain_out_withdraw.job',
            'func': 'app.YEC.tasks:task_chain_out_withdraw',
            'args': (),
            'trigger': 'interval',
            'seconds': 10
        },
        {
            'id': 'yec.task_chain_out_confirm.job',
            'func': 'app.YEC.tasks:task_chain_out_confirm',
            'args': (),
            'trigger': 'interval',
            'seconds': 10
        },
        {
            'id': 'yec.task_chain_in_confirm.job',
            'func': 'app.YEC.tasks:task_chain_in_confirm',
            'args': (),
            'trigger': 'interval',
            'seconds': 10
        },
        # {
        #     'id': 'yec.task_chain_out_collect.job',
        #     'func': 'app.YEC.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'usdt.task_chain_out_recharge.job',
        #     'func': 'app.USDT.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'usdt.task_chain_in_recharge.job',
        #     'func': 'app.USDT.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'usdt.task_chain_out_withdraw.job',
        #     'func': 'app.USDT.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'usdt.task_chain_out_confirm.job',
        #     'func': 'app.USDT.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'usdt.task_chain_in_confirm.job',
        #     'func': 'app.USDT.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'usdt.task_chain_out_collect.job',
        #     'func': 'app.USDT.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_out_recharge.job',
        #     'func': 'app.VPC.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_in_recharge.job',
        #     'func': 'app.VPC.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_out_withdraw.job',
        #     'func': 'app.VPC.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_out_confirm.job',
        #     'func': 'app.VPC.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_in_confirm.job',
        #     'func': 'app.VPC.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_out_recharge.job',
        #     'func': 'app.VPC.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_in_recharge.job',
        #     'func': 'app.VPC.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_out_withdraw.job',
        #     'func': 'app.VPC.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_out_confirm.job',
        #     'func': 'app.VPC.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_in_confirm.job',
        #     'func': 'app.VPC.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'vpc.task_chain_out_collect.job',
        #     'func': 'app.VPC.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },

        # {
        #     'id': 'btc.task_chain_out_recharge.job',
        #     'func': 'app.BTC.task:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 30  # 10s
        # },
        # {
        #     'id': 'btc.task_chain_in_recharge.job',
        #     'func': 'app.BTC.task:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        #
        # {
        #     'id': 'btc.task_chain_out_withdraw.job',
        #     'func': 'app.BTC.task:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 20  # 10s
        # },

        # {
        #     'id': 'btc.task_chain_out_confirm.job',
        #     'func': 'app.BTC.task:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 11  # 10s
        # },
        # {
        #     'id': 'btc.task_chain_out_collect.job',
        #     'func': 'app.BTC.task:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },

        # {
        #     'id': 'btc.task_chain_in_confirm.job',
        #     'func': 'app.BTC.task:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 12
        # },
        #  EOS
        # {
        #     'id': 'eos.task_chain_out_recharge.job',
        #     'func': 'app.EOS.tasks:task_chain_out_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eos.task_chain_in_recharge.job',
        #     'func': 'app.EOS.tasks:task_chain_in_recharge',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eos.task_chain_out_withdraw.job',
        #     'func': 'app.EOS.tasks:task_chain_out_withdraw',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eos.task_chain_out_confirm.job',
        #     'func': 'app.EOS.tasks:task_chain_out_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eos.task_chain_in_confirm.job',
        #     'func': 'app.EOS.tasks:task_chain_in_confirm',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },
        # {
        #     'id': 'eos.task_chain_out_collect.job',
        #     'func': 'app.EOS.tasks:task_chain_out_collect',
        #     'args': (),
        #     'trigger': 'interval',
        #     'seconds': 10
        # },

    ]


class Development(Config):
    REDIS_PWD = os.environ.get("CONFIG_REDIS_PWD", "G%E5qk1T")
    REDIS_IPPORT = os.environ.get("CONFIG_REDIS_IPPORT", "101.132.188.48:6479")

    CONSUL_IP = "101.132.188.48"
    CONSUL_TOKEN = os.environ.get("CONFIG_CONSUL_TOKEN", "")

    MYSQL_IPPORT = os.environ.get("CONFIG_MYSQL_IPPORT", "101.132.188.48:4406")
    MYSQL_USERNAME = os.environ.get("CONFIG_MYSQL_USERNAME", "root")
    MYSQL_PASSWORD = os.environ.get("CONFIG_MYSQL_PASSWORD", "v0iX0EEy8Ey51Cx0")
    MYSQL_DATABASE = os.environ.get("CONFIG_MYSQL_DATABASE", "dapp_digiccy")

    CONFIG_BITCOIND_RPC_USER = os.environ.get("CONFIG_BITCOIND_RPC_USER", "xianda")
    CONFIG_BITCOIND_RPC_PASSWORD = os.environ.get("CONFIG_BITCOIND_RPC_PASSWORD", "ABQOqmPZ0tr95f5Z")
    CONFIG_BITCOIND_WALLET_PASSWORD = os.environ.get("CONFIG_BITCOIND_WALLET_PASSWORD", "123")

    STELLAR_NETWORK_ID = os.environ.get("CONFIG_NETWORK_ID", "XIANDA_DEV_NET")
    STELLAR_NETWORK_PASSPHRASE = os.environ.get("CONFIG_NETWORK_PASSPHRASE",
                                                "xfin_core_network_v1.0.0 ; September 2018")

    ASSETS_ISSUER = os.environ.get("CONFIG_ASSETS_ISSUER", "GBAPRZYI3DDFYEN3IO54DXVPWS4GCXFNUUOION5HIRTDMFQJ3QF7CO7M")

    CONFIG_ZIPKIN_SAMPLERATE = 100

    GETH_ETH_PASSPHRASE = os.environ.get("CONFIG_GETH_ETH_PASSPHRASE", "")
    GETH_VRT_PASSPHRASE = os.environ.get("CONFIG_GETH_VRT_PASSPHRASE", "LMnKroB77E6Uw2h7")
    GETH_IPCHAIN_PASSPHRASE = os.environ.get("CONFIG_GETH_IPCHAIN_PASSPHRASE", "OjgjaUien0TjQZhv")
    GETH_ABS_PASSPHRASE = os.environ.get("CONFIG_GETH_ABS_PASSPHRASE", "Iyyva3VY6AwWm8Pi")
    GETH_YEC_PASSPHRASE = os.environ.get("CONFIG_GETH_YEC_PASSPHRASE", "ZPjUTyj1Wtacmhgc")
    GETH_VPC_PASSPHRASE = os.environ.get("CONFIG_GETH_VPC_PASSPHRASE", "kuRLLjrgUSikRN2r")

    USDT_RPC_USER = os.environ.get("USDT_RPC_USER", "xianda")
    USDT_RPC_PWD = os.environ.get("USDT_RPC_PWD", "ABQOqmPZ0tr95f5Z")
    GETH_USDT_PASSPHRASE = os.environ.get("CONFIG_GETH_USDT_PASSPHRASE", "")

    CONFIG_REDIS_PWD = os.environ.get("CONFIG_REDIS_PWD", "G%E5qk1T")
    CONFIG_REDIS_IPPORT = os.environ.get("CONFIG_REDIS_IPPORT", "101.132.188.48:6479")

    SCHEDULER_ENABLED = os.environ.get("SCHEDULER_ENABLED", "True")


class Production(Config):
    DEBUG = False
    REDIS_PWD = os.environ.get("CONFIG_REDIS_PWD", "")
    REDIS_IPPORT = os.environ.get("CONFIG_REDIS_IPPORT", "")

    CONSUL_IP = "xconsul"
    CONSUL_TOKEN = os.environ.get("CONFIG_CONSUL_TOKEN", "")

    MYSQL_IPPORT = os.environ.get("CONFIG_MYSQL_IPPORT", "")
    MYSQL_USERNAME = os.environ.get("CONFIG_MYSQL_USERNAME", "")
    MYSQL_PASSWORD = os.environ.get("CONFIG_MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("CONFIG_MYSQL_DATABASE", "")

    CONFIG_BITCOIND_RPC_USER = os.environ.get("CONFIG_BITCOIND_RPC_USER", "xianda")
    CONFIG_BITCOIND_RPC_PASSWORD = os.environ.get("CONFIG_BITCOIND_RPC_PASSWORD", "ABQOqmPZ0tr95f5Z")
    CONFIG_BITCOIND_WALLET_PASSWORD = os.environ.get("CONFIG_BITCOIND_WALLET_PASSWORD", "123")

    STELLAR_NETWORK_ID = os.environ.get("CONFIG_NETWORK_ID", "")
    STELLAR_NETWORK_PASSPHRASE = os.environ.get("CONFIG_NETWORK_PASSPHRASE", "")

    ASSETS_ISSUER = os.environ.get("CONFIG_ASSETS_ISSUER", "")

    CONFIG_ZIPKIN_SAMPLERATE = 1

    GETH_ETH_PASSPHRASE = os.environ.get("CONFIG_GETH_ETH_PASSPHRASE", "")
    GETH_VRT_PASSPHRASE = os.environ.get("CONFIG_GETH_VRT_PASSPHRASE", "")
    GETH_IPCHAIN_PASSPHRASE = os.environ.get("CONFIG_GETH_IPCHAIN_PASSPHRASE", "")
    GETH_ABS_PASSPHRASE = os.environ.get("CONFIG_GETH_ABS_PASSPHRASE", "")
    GETH_YEC_PASSPHRASE = os.environ.get("CONFIG_GETH_YEC_PASSPHRASE", "")
    GETH_VPC_PASSPHRASE = os.environ.get("CONFIG_GETH_VPC_PASSPHRASE", "")
    USDT_RPC_USER = os.environ.get("USDT_RPC_USER", "xianda")
    USDT_RPC_PWD = os.environ.get("USDT_RPC_PWD", "xianda")
    GETH_USDT_PASSPHRASE = os.environ.get("CONFIG_GETH_USDT_PASSPHRASE", "")

    CONFIG_REDIS_PWD = os.environ.get("CONFIG_REDIS_PWD", "")
    CONFIG_REDIS_IPPORT = os.environ.get("CONFIG_REDIS_IPPORT", "")

    SCHEDULER_ENABLED = os.environ.get("SCHEDULER_ENABLED", "")
