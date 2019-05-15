import os
import logging
import atexit
import fcntl

import requests
from flask import Flask
from flask_apscheduler import APScheduler
from flask_environments import Environments
from flask_restplus import Api
from flask_redis import FlaskRedis
from requests.adapters import HTTPAdapter

from app.models import db

redisService = FlaskRedis()

# requests连接池
POOL_CONNECTIONS = 20
POOL_MAXSIZE = 2000
session_pool = requests.Session()
session_pool.mount('http://', HTTPAdapter(pool_connections=POOL_CONNECTIONS, pool_maxsize=POOL_MAXSIZE))
session_pool.mount('https://', HTTPAdapter(pool_connections=POOL_CONNECTIONS, pool_maxsize=POOL_MAXSIZE))

from app.common.consul import ConsulClient
from app.common.stellar import StellarService

SERVICE_NAME = 'DigiccyService'
APP_URL_PREFIX = '/v1/api/digiccy_coin'

# 数据库对象
# db = SQLAlchemy()

consul_clinet = ConsulClient()
stellar_service = StellarService()

# eth钱包节点
from app.ETH.wallet import EthWallet

eth_wallet = EthWallet()

# vrt钱包节点
from app.VRT.wallet import VrtWallet

vrt_wallet = VrtWallet()

# btc钱包节点
from app.BTC.wallet import BtcWallet
btc_wallet = BtcWallet()

from app.ETH.api import eth_ns
from app.VRT.api import vrt_ns
from app.BTC.api import btc_ns
# ipchain钱包节点
from app.IPCHAIN.wallet import IPChainWallet

ipchain_wallet = IPChainWallet()

# abs钱包节点
from app.ABS.wallet import ABSWallet
abs_wallet = ABSWallet()

# yec钱包节点
from app.YEC.wallet import YECWallet
yec_wallet = YECWallet()

# vpc钱包节点
from app.VPC.wallet import VPCWallet
vpc_wallet = VPCWallet()

# usdt钱包节点
from app.USDT.wallet import UsdtWallet

usdt_wallet = UsdtWallet()

# eos钱包节点
from app.EOS.wallet import EosWallet

eos_wallet = EosWallet()


from app.ETH.api import eth_ns
from app.VRT.api import vrt_ns
from app.USDT.api import usdt_ns
from app.EOS.api import eos_ns
from app.IPCHAIN.api import ipchain_ns
from app.ABS.api import abs_ns
from app.YEC.api import yec_ns
from app.VPC.api import vpc_ns
from app.base.orders_api import order_ns
from app.help.api import help_ns
from app.base.api import base_ns
from app.base.currency_api import currency_ns
from app.base.assetflow_api import assetflow_ns
from app.base.audit_api import audit_ns
from app.base.baseaccount import balance_ns
from app.base.create_ethaccount import ethaccount_ns

# from celery import Celery
# from config import Config
# celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

def create_app_api():
    """构成项目所需要的服务实例"""

    app = Flask(SERVICE_NAME)

    # APP所需配置
    config_env = Environments(app, default_env="DEVELOPMENT")
    config_env.from_object('config')

    tasks_enabled = app.config["SCHEDULER_ENABLED"]

    # 自动保存提交
    app.config['SQLALCHEMY_COMMIT_TEARDOWN'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

    mysql_username = app.config["MYSQL_USERNAME"]
    mysql_password = app.config["MYSQL_PASSWORD"]
    mysql_ipport = app.config["MYSQL_IPPORT"]
    mysql_database = app.config["MYSQL_DATABASE"]

    config_redis_pwd = app.config["CONFIG_REDIS_PWD"]
    config_redis_ipport = app.config['CONFIG_REDIS_IPPORT']
    app.config['REDIS_URL'] = "redis://:" + config_redis_pwd + "@" + config_redis_ipport + "/8"

    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://{}:{}@{}/{}".format(mysql_username,
                                                                                 mysql_password,
                                                                                 mysql_ipport,
                                                                                 mysql_database)
    btc_rpc_user = app.config.get('CONFIG_BITCOIND_RPC_USER')
    btc_rpc_password = app.config.get('CONFIG_BITCOIND_RPC_PASSWORD')

    # 初始化数据库
    db.app = app
    db.init_app(app)

    # redis
    redisService.init_app(app, decode_responses=True)

    # consul服务
    consul_clinet.init_app(app)

    # 初始化ETH钱包节点
    # eth_wallet.init_app(app, consul_clinet)

    # 初始化VRT钱包节点
    # vrt_wallet.init_consul(app, consul_clinet)

    # 初始化BTC节点
    btc_wallet.init_consul(app, consul_clinet)

    # 初始化IPCHAIN钱包节点
    # ipchain_wallet.init_consul(app, consul_clinet)

    # 初始化ABS钱包节点
    # abs_wallet.init_consul(app, consul_clinet)

    # 初始化YEC钱包节点
    yec_wallet.init_consul(app, consul_clinet)

    # 初始化VPC钱包节点
    # vpc_wallet.init_consul(app, consul_clinet)

    # 初始化USDT錢包
    # usdt_wallet.init_consul(app, consul_clinet)

    # # 初始化EOS錢包
    # eos_wallet.init_consul(app, consul_clinet)

    # stellar服务
    stellar_service.init_app(consul_clinet, app)



    # 初始化api对象
    api = Api(app, version="v1.0.0", title=SERVICE_NAME, prefix=APP_URL_PREFIX)

    # eth api
    ETH_URL_PREFIX = "/eth"
    api.add_namespace(eth_ns, ETH_URL_PREFIX)

    # vrt api
    VRT_URL_PREFIX = "/vrt"
    api.add_namespace(vrt_ns, VRT_URL_PREFIX)

    # btc api
    BTC_URL_PREFIX = "/btc"
    api.add_namespace(btc_ns, BTC_URL_PREFIX)
    # usdt api
    USDT_URL_PREFIX = "/usdt"
    api.add_namespace(usdt_ns, USDT_URL_PREFIX)

    # ipchain api
    IPCHAIN_URL_PREFIX = "/ipchain"
    api.add_namespace(ipchain_ns, IPCHAIN_URL_PREFIX)

    # eos api
    EOS_URL_PREFIX = "/eos"
    api.add_namespace(eos_ns, EOS_URL_PREFIX)

    # abs api
    ABS_URL_PREFIX = "/abs"
    api.add_namespace(abs_ns, ABS_URL_PREFIX)

    # yec api
    YEC_URL_PREFIX = "/yec"
    api.add_namespace(yec_ns, YEC_URL_PREFIX)

    # yec api
    VPC_URL_PREFIX = "/vpc"
    api.add_namespace(vpc_ns, VPC_URL_PREFIX)

    # base api
    api.add_namespace(base_ns, '/base')

    # orders_api
    ORDER_URL_PREFIX = "/orders"
    api.add_namespace(order_ns, ORDER_URL_PREFIX)

    # currency_api
    CURRENCY_URL_PREFIX = "/currency"
    api.add_namespace(currency_ns, CURRENCY_URL_PREFIX)

    # CreateAccount
    ACCOUNT_URL_PREFIX = "/account"
    api.add_namespace(ethaccount_ns, ACCOUNT_URL_PREFIX)

    # assetflow_api
    ASSETFLOW_URL_PREFIX = "/assetflow"
    api.add_namespace(assetflow_ns, ASSETFLOW_URL_PREFIX)

    BALANCE_URL_PREFIX = "/basebalance"
    api.add_namespace(balance_ns, BALANCE_URL_PREFIX)

    # # audit_api
    # AUDIT_URL_PREFIX = "/audit"
    # api.add_namespace(audit_ns, AUDIT_URL_PREFIX)

    if os.environ.get("FLASK_ENV") != 'PRODUCTION':
        # help
        HELP_URL_PREFIX = "/help"
        api.add_namespace(help_ns, HELP_URL_PREFIX)


    if tasks_enabled == "True":
        # 首先打开（或创建）一个scheduler.lock文件，并加上非阻塞互斥锁。成功后创建scheduler并启动。
        f = open("scheduler.lock", "wb")
        try:

            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            print("准备开启APScheduler")
            scheduler = APScheduler()
            scheduler.api_enabled = True
            scheduler.init_app(app)
            scheduler.start()
            print("开启APScheduler")
        except Exception as ex:
            # 如果加文件锁失败，说明scheduler已经创建，就略过创建scheduler的部分。
            print("", ex)
            pass

        # 最后注册一个退出事件，如果这个flask项目退出，则解锁并关闭scheduler.lock文件的锁。
        def unlock():
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

        atexit.register(unlock)

    logging.info('app config:{}'.format(str(app.config)))
    return app, api



