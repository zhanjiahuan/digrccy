import json
import logging
import time
import uuid

from datetime import datetime
from decimal import Decimal

from app.utils.commons import rsa_params_decrypt, decryptSeed
from app import db, eos_wallet, consul_clinet, stellar_service
from app.base.base import DigiccyBase
from app.utils.code_msg import CodeMsg
from app.models import User, Order, OrderDetail

COIN_NAME = 'EOS'
digiccy_base = DigiccyBase(COIN_NAME)


def task_chain_out_recharge():
    """链外充值记录存入数据库"""
    with db.app.app_context():
        start_num = 0
        limit_num = 100
        len_num = 0
        while True:
            users = User.coin_bind_users(COIN_NAME, start_num, limit_num)
            len_num += len(users)
            if not users:
                logging.info('{}链外充值确认完毕,确认条数:{}'.format(COIN_NAME, len_num))
                print('{}链外充值确认完毕,确认条数:{}'.format(COIN_NAME, len_num))
                break
            for user in users:
                if not consul_clinet.get_task_switch():
                    logging.warning('{}链外充值定时任务被手动关闭!'.format(COIN_NAME))
                    return

                address = user.address
                # balance为0的账户跳过
                try:
                    balance = eos_wallet.get_balance(address)
                    if balance == 0:
                        continue
                except Exception as e:
                    logging.error('get {} balance error:{}'.format(address, str(e)))
                    continue
                    # 获取交易信息
                records = eos_wallet.eos_transaction_record(address)
                if records is None:
                    continue
                for record in records['actions']:
                    block_number = record['block_num']  # 区块数
                    timestamp = record['block_time']  # 时间戳
                    timestamp = timestamp.replace("T", " ", )
                    timestamp = timestamp.replace(timestamp.split(":")[-1], timestamp.split(":")[-1].split(".")[0])
                    timeArray = time.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    timestamp = int(time.mktime(timeArray))  # 转换成时间戳

                    gas_price = Decimal(0)  # 燃料价格
                    gas_used = Decimal(0)  # 燃料使用个数

                    user.last_block = block_number
                    user.last_time = timestamp
                    record_hash = record['action_trace']['trx_id']
                    if Order.hash_is_exist(record_hash):
                        # print('hash 存在',user.address)
                        continue
                    order_from = record['action_trace']['act']['data']['from']
                    order_to = record['action_trace']['act']['data']['to']
                    amount = record['action_trace']['act']['data']['quantity'].split(" ")[0]
                    amount = Decimal(amount)
                    fee = round(gas_price * gas_used / (10 ** 18), 7)
                    order_hash = record['action_trace']['trx_id']
                    eth_hash = json.dumps(dict(eth_hash=record['action_trace']['trx_id']))
                    record_order = Order(
                        id=str(uuid.uuid1()),
                        user_id=user.id,
                        stellar_account=user.stellar_account,
                        order_type=1,
                        chain_type=2,
                        coin_name=COIN_NAME,
                        order_from=order_from,
                        order_to=order_to,
                        amount=amount,
                        fee=fee,
                        order_hash=order_hash,
                        relate_order_status=0,
                        add_time=datetime.now(),
                        status=1,
                    )
                    record_order_detail = OrderDetail(
                        id=str(uuid.uuid1()),
                        order_id=record_order.id,
                        act_type=2,
                        query_json=eth_hash,
                        response_json=json.dumps(record),
                        status=1,
                    )
                    try:
                        db.session.add_all([record_order, record_order_detail])
                        db.session.commit()
                    except Exception as e:
                        logging.error('Insert {} chain out recharge order error:{}'.format(COIN_NAME, str(e)))
                        return
            start_num += limit_num


def task_chain_in_recharge():
    """链内充值定时任务"""
    with db.app.app_context():
        stellar_base_seed = consul_clinet.get_stellar_base_account(COIN_NAME)
        limit_num = 100
        len_num = 0
        success_num = 0
        while True:
            orders = Order.chain_out_recharge(COIN_NAME, limit_num)
            len_num += len(orders)
            if not orders:
                print('{}链内充值处理完毕,处理条数:{},成功条数:{}'.format(COIN_NAME, len_num, success_num))
                logging.info('{}链内充值处理完毕,处理条数:{},成功条数:{}'.format(COIN_NAME, len_num, success_num))
                break

            for order in orders:
                if not consul_clinet.get_task_switch():
                    logging.warning('{}链内充值定时任务被手动关闭!'.format(COIN_NAME))
                    return

                destination = order.stellar_account
                amount = order.amount

                result = digiccy_base.transfer_compulsory(stellar_base_seed, amount, fee=0, order_limit=False)
                if isinstance(result, CodeMsg.CM):
                    logging.error('Stellar {} base account error:{}'.format(COIN_NAME, result.msg))
                    return
                sequence, stellar_kp = result
                te, stellar_hash = digiccy_base.transfer_te(sequence, amount, stellar_kp, destination, memo='r')
                record_order = Order(
                    id=str(uuid.uuid1()),
                    relate_id=order.id,
                    user_id=order.id,
                    stellar_account=destination,
                    coin_name=COIN_NAME,
                    order_type=1,
                    chain_type=1,
                    order_from=stellar_kp.address().decode('utf-8'),
                    order_to=destination,
                    amount=amount,
                    fee=0,
                    order_hash=stellar_hash,
                    status=0,
                    add_time=datetime.now(),
                    notice_status=0,
                )
                order.relate_id = record_order.id
                order.relate_order_status = 1
                record_order_detail = OrderDetail(
                    id=str(uuid.uuid1()),
                    order_id=record_order.id,
                    act_type=1,
                    query_json=json.dumps(dict(stellar_hash=stellar_hash)),
                    response_json='',
                    status=-1,
                )
                try:
                    db.session.add_all([record_order, order, record_order_detail])
                    db.session.commit()
                except Exception as e:
                    logging.error('Insert {} chain in recharge order error:{}'.format(COIN_NAME, str(e)))
                    db.session.rollback()
                    print('保存出错', str(e))
                    return

                response = digiccy_base.transfer_submit(te)
                response_hash = response.get('hash')
                if response_hash:
                    record_order.status = 1
                    record_order.notice_status = -1  # 待通知
                    record_order.done_time = datetime.now()
                    record_order_detail.status = 1
                    success_num += 1
                else:
                    record_order.status = 2  # 待确认
                    record_order_detail.status = 0
                record_order_detail.response_json = json.dumps(response)
                try:
                    db.session.add_all([record_order, record_order_detail])
                    db.session.commit()
                except Exception as e:
                    logging.error('Insert {} chain in recharge order error:{}'.format(COIN_NAME, str(e)))
                    db.session.rollback()
                    return


def task_chain_out_withdraw():
    """提现链外转账"""
    with db.app.app_context():

        # EOS base账户address
        eos_base_address = consul_clinet.get_digiccy_base_account(COIN_NAME, is_seed=False)
        privKey = consul_clinet.get_digiccy_base_privatekey(COIN_NAME)
        # privKey = digiccy_base.stellar_keypair(stellar_encrypt_seed=privKey)

        privKey = eval(decryptSeed(privKey)).get("seed")
        # privKey = "5Jb46jpSGwuXJXcom6e5PdLsaW1rMwc3MUqhZnVTApqVynMcXxA"
        # 待链外转账订单
        orders = Order.chain_out_withdraw(COIN_NAME, 100)
        for order in orders:
            # 定时任务开关
            if not consul_clinet.get_task_switch():
                logging.warning('{}链内充值定时任务被手动关闭!'.format(COIN_NAME))
                return

            # 本地节点是否链接,是否同步
            if not eos_wallet.init_consul("", ""):
                logging.error('{}节点离线!'.format(COIN_NAME))
                return
            if not eos_wallet.is_syncing():
                logging.error('{}节点同步未完成!'.format(COIN_NAME))
                return

            # 订单收款账户,数量
            order_to = order.order_to
            amount = order.amount

            # 链外账户余额
            base_account_balance = eos_wallet.get_balance(eos_base_address)  # decimal.Decimal
            if base_account_balance < amount:
                logging.error('eos base账户余额不足,支付金额{}'.format(str(amount)))

            # 当前区块
            block_num = eos_wallet.get_block_num()

            # 改变订单状态
            order.order_from = eos_base_address
            order.status = 0

            order_detail = OrderDetail(
                id=str(uuid.uuid1()),
                order_id=order.id,
                act_type=2,
                query_json=json.dumps(
                    dict(addrfrom=eos_base_address, addrto=order_to, block_num=block_num)),
                response_json='',
                status=-1
            )
            try:
                db.session.add_all([order, order_detail])
                db.session.commit()
            except Exception as e:
                logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                return
            is_success, msg = eos_wallet.payment(privKey, eos_base_address, order_to, amount)
            print('定时任务链外转账结果', is_success, msg)
            if is_success:
                order_detail.status = 1  # 订单请求成功
                order_detail.response_json = msg
                order.order_hash = msg
                order.status = 2  # 转账发起成功待确认
                try:
                    db.session.add_all([order, order_detail])
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return
            else:
                order_detail.status = 0  # 订单请求失败
                order_detail.response_json = json.dumps(msg)
                try:
                    db.session.add(order_detail)
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return


def task_chain_out_confirm():
    """链外转账确认test-ok"""
    with db.app.app_context():
        orders = Order.chain_out_unconfirm(COIN_NAME, 100)
        print(orders)
        for order in orders:
            # 定时任务开关
            if not consul_clinet.get_task_switch():
                logging.warning('{}链外转账确认定时任务被手动关闭!'.format(COIN_NAME))
                return
            order_hash = order.order_hash

            # 本地节点是否链接,是否同步
            if not eos_wallet.init_consul("", ""):
                logging.error('{}节点离线!'.format(COIN_NAME))
                return
            if not eos_wallet.is_syncing():
                logging.error('{}节点同步未完成!'.format(COIN_NAME))
                return

            # 订单确认详情
            order_confirm_detail = OrderDetail(
                id=str(uuid.uuid1()),
                order_id=order.id,
                act_type=4,
                query_json=json.dumps(dict(hash=order_hash)),
                status=-1
            )
            # 查询交易是否被确认
            is_confirm, is_success, msg, fee = eos_wallet.get_transaction(order_hash)
            print('确认结果', is_confirm, is_success, msg, fee)
            # 未确认
            if not is_confirm:
                order_confirm_detail.status = 0
                order_confirm_detail.response_json = json.dumps(msg)
                try:
                    db.session.add(order_confirm_detail)
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return
            # 已确认
            else:
                order_confirm_detail.response_json = json.dumps(msg)
                order_confirm_detail.status = 1
                # 确认交易失败
                if not is_success:
                    order.status = 0
                # 确认交易成功
                else:
                    order.status = 1
                    order.done_time = datetime.now()
                    order.fee = fee
                    order.notice_status = -2  # 待通知
                try:
                    db.session.add_all([order, order_confirm_detail])
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return


def task_chain_in_confirm():
    """链内转帐确认"""
    with db.app.app_context():
        orders = Order.chain_in_unconfirm(COIN_NAME, 100)
        for order in orders:
            # 定时任务开关
            if not consul_clinet.get_task_switch():
                logging.warning('{}链内转帐确认定时任务被手动关闭!'.format(COIN_NAME))
                return
            order_hash = order.order_hash
            stellar_node = stellar_service.stellar_node(is_full=True)
            ret = stellar_service.query_hash(order_hash, stellar_node=stellar_node)
            if ret is None:
                return
            relate_order = None
            if ret.get("hash") is None:
                order.status = 0
                # 如果为充值订单
                if order.order_type == 1:
                    relate_order = Order.query.filter_by(id=order.relate_id).first()
                    relate_order.relate_order_status = 0  # 进入task_chain_in_recharge 重新生成订单
            else:
                order.status = 1
                if order.order_type == 1:
                    order.done_time = datetime.now()
                else:
                    relate_order = Order.query.filter_by(id=order.relate_id).first()
                    relate_order.status = -1  # 链外待转帐，relate_order进入task_chain_out_withdraw

            if relate_order is None:
                try:
                    db.session.add_all(order)
                    db.session.commit()
                except Exception as e:
                    logging.error('task_chain_in_confirm update db error:{}'.format(str(e)))
                    db.session.rollback()
                    return
            else:
                try:
                    db.session.add_all([order, relate_order])
                    db.session.commit()
                except Exception as e:
                    logging.error('task_chain_in_confirm update db error:{}'.format(str(e)))
                    db.session.rollback()
                    return


def task_chain_out_collect():
    """链外资金归集"""
    with db.app.app_context():
        # 归集地址:项目方提供地址boss账户
        eos_boss_address = consul_clinet.get_digiccy_boss_address(COIN_NAME)
        # 最小归集数量
        collect_min_amount = consul_clinet.get_digiccy_collect_min(COIN_NAME)
        # collect_min_amount = 0.01
        start_num = 0
        limit_num = 100
        len_num = 0
        while True:
            users = User.coin_bind_users(COIN_NAME, start_num, limit_num)
            len_num += len(users)
            if not users:
                logging.info('{}链外归集处理完毕,处理条数:{}'.format(COIN_NAME, len_num))
                print('{}链外归集处理完毕,处理条数:{}'.format(COIN_NAME, len_num))
                break
            for user in users:
                if not consul_clinet.get_task_switch():
                    logging.warning('链外充值定时任务被手动关闭!')
                    return
                # 本地节点是否链接,是否同步
                if not eos_wallet.init_consul("", ""):
                    logging.error('{}节点离线!'.format(COIN_NAME))
                    return
                if not eos_wallet.init_eos():
                    logging.error('EOS 节点同步未完成')
                    return
                # 用户是否有归集未确认订单
                if Order.is_collect(user.stellar_account, COIN_NAME):
                    print('用户有归集未确认订单')
                    continue
                # 用户绑定地址
                user_digiccy_address = user.address
                # 解密私钥
                user_digiccy_secret = rsa_params_decrypt(user.secret)
                # 用户绑定地址余额,小于最小归集数量跳过
                balance = round(eos_wallet.get_balance(user_digiccy_address), 7)





                if balance <= collect_min_amount:
                    continue
                print(type(balance), balance, user_digiccy_address, user_digiccy_secret)
                # 查询客户账号ram，cup，net余额，并判断是否充值
                # 充值的费用是按照2019.3.28号的ram，cup，net价格计算的，后续关注是否需要调整
                ram, cpu, net = eos_wallet.get_account_ram_cup_net(user_digiccy_address, user_digiccy_secret)
                if ram < 3000:
                    balance = balance - 0.1
                elif cpu < 2000 or net < 3000:
                    balance = balance - 0.03
                elif ram == 0 and cpu == 0 and net == 0:
                    continue
                # 创建归集订单
                order_collect = Order(
                    id=str(uuid.uuid1()),
                    user_id=user.id,
                    stellar_account=user.stellar_account,
                    coin_name=user.coin_name,
                    order_type=3,
                    chain_type=2,
                    order_from=user_digiccy_address,
                    order_to=eos_boss_address,
                    amount=balance,
                    fee=0,
                    order_hash='',
                    add_time=datetime.now(),
                )
                # 创建裸交易发出
                is_success, msg = eos_wallet.payment(privKey=user_digiccy_secret,
                                                     fromAddr=user_digiccy_address,
                                                     toAddre=eos_boss_address,
                                                     value=balance)

                if is_success:
                    order_collect.status = 2  # 发出成功待确认
                    order_collect.order_hash = msg
                    order_collect.done_time = datetime.now()
                else:
                    print("发出交易失败")
                    continue

                try:
                    db.session.add(order_collect)
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return

            start_num += limit_num
