import json
import logging
import time
import uuid

from datetime import datetime
from decimal import Decimal

from app.utils.commons import rsa_params_decrypt
from app import db, vpc_wallet, consul_clinet, stellar_service
from app.base.base import DigiccyBase
from app.utils.code_msg import CodeMsg
from app.models import User, Order, OrderDetail

COIN_NAME = 'VPC'
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
                    balance = vpc_wallet.get_balance(address)
                    if balance <= 0:
                        continue
                except Exception as e:
                    logging.error('get {} balance error:{}'.format(address, str(e)))
                    continue
                last_block = user.last_block
                last_time = user.last_time
                records = vpc_wallet.eth_transaction_record(address, last_time, start_block=last_block)
                if records is None:
                    continue
                for record in records:
                    block_number = record['blockNumber']  # 区块数
                    timestamp = record['timeStamp']  # 时间戳
                    gas_price = Decimal(record['gasPrice'])  # 燃料价格
                    gas_used = Decimal(record['gasUsed'])  # 燃料使用个数

                    user.last_block = block_number
                    user.last_time = timestamp
                    record_hash = record['hash']
                    # print("------------------------------", record_hash)
                    if Order.hash_is_exist(record_hash):
                        # print('hash 存在',user.address)
                        continue

                    record_order = Order(
                        id=str(uuid.uuid1()),
                        user_id=user.id,
                        stellar_account=user.stellar_account,
                        order_type=1,
                        chain_type=2,
                        coin_name=COIN_NAME,
                        order_from=record['from'],
                        order_to=record['to'],
                        amount=round(Decimal(record['value']) / (10 ** 18), 7),
                        fee=round(gas_price * gas_used / (10 ** 18), 7),
                        order_hash=record_hash,
                        relate_order_status=0,
                        add_time=datetime.now(),
                        status=1,
                    )
                    record_order_detail = OrderDetail(
                        id=str(uuid.uuid1()),
                        order_id=record_order.id,
                        act_type=2,
                        query_json=json.dumps(dict(eth_hash=record_hash)),
                        response_json=json.dumps(record),
                        status=1,
                    )
                    try:
                        db.session.add_all([user, record_order, record_order_detail])
                        db.session.commit()
                    except Exception as e:
                        logging.error('Insert {} chain out recharge order error:{}'.format(COIN_NAME, str(e)))
                        return
                time.sleep(0.2)
            start_num += limit_num


def task_chain_in_recharge():
    """链内充值定时任务"""
    with db.app.app_context():

        # stellar base 账户
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

        # VPC base账户address
        vpc_base_address = consul_clinet.get_digiccy_base_account(COIN_NAME, is_seed=False)
        # vpc_base_seed = consul_clinet.get_digiccy_base_account(COIN_NAME)
        #
        # gas_limit, gas_price = consul_clinet.get_digiccy_collect_fee(COIN_NAME)

        # 待链外转账订单
        orders = Order.chain_out_withdraw(COIN_NAME, 100)
        for order in orders:
            # 定时任务开关
            if not consul_clinet.get_task_switch():
                logging.warning('{}链内充值定时任务被手动关闭!'.format(COIN_NAME))
                return

            # 本地节点是否链接,是否同步
            if not vpc_wallet.is_connected():
                logging.error('{}节点离线!'.format(COIN_NAME))
                return
            if vpc_wallet.is_syncing():
                logging.error('{}节点同步未完成!'.format(COIN_NAME))
                return

            # 订单收款账户,数量
            order_to = order.order_to
            amount = order.amount

            # 链外账户余额
            base_account_balance = vpc_wallet.get_balance(vpc_base_address)  # decimal.Decimal
            minerfee = vpc_wallet.get_minerFee(vpc_base_address)
            if minerfee < 0.0001:
                logging.error('base账户矿工费余额不足,余额{}'.format(str(minerfee)))
                return

            if amount + Decimal('0.002') > base_account_balance:
                logging.error('base账户余额不足,支付金额{}'.format(str(amount)))
                print('base账户余额不足,支付金额{}'.format(str(amount)))
                continue

            # 付款账户信息
            # 当前区块
            block_num = vpc_wallet.get_block_num()
            nonce_num = vpc_wallet.get_nonce(vpc_base_address)

            # 改变订单状态
            order.order_from = vpc_base_address
            order.status = 0

            order_detail = OrderDetail(
                id=str(uuid.uuid1()),
                order_id=order.id,
                act_type=2,
                query_json=json.dumps(
                    dict(addrfrom=vpc_base_address, addrto=order_to, block_num=block_num, nonce_num=nonce_num)),
                response_json='',
                status=-1
            )
            try:
                db.session.add_all([order, order_detail])
                db.session.commit()
            except Exception as e:
                logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                return
            is_success, msg = vpc_wallet.payment(vpc_base_address, order_to, amount)
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
    """链外转账确认"""
    with db.app.app_context():
        orders = Order.chain_out_unconfirm(COIN_NAME, 100)
        # print(orders)
        for order in orders:
            # 定时任务开关
            if not consul_clinet.get_task_switch():
                logging.warning('{}链外转账确认定时任务被手动关闭!'.format(COIN_NAME))
                return
            order_hash = order.order_hash

            # 本地节点是否链接,是否同步
            if not vpc_wallet.is_connected():
                logging.error('{}节点离线!'.format(COIN_NAME))
                return
            if vpc_wallet.is_syncing():
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
            is_confirm, is_success, msg, fee = vpc_wallet.hash_get_detail(order_hash)
            print('确认结果', is_confirm, is_success, msg, fee)
            # 未确认
            if not is_confirm:
                try:
                    times = OrderDetail.confirm_times(order.id)
                except Exception as e:
                    logging.error('confirm_times query order_detail error:{}'.format(str(e)))
                    return
                if times > 4:
                    order.status = 0
                    try:
                        db.session.add(order)
                        db.session.commit()
                        continue
                    except Exception as e:
                        logging.error('chain_out_confirm update order error:{}'.format(str(e)))
                        return
                order_confirm_detail.status = 0
                order_confirm_detail.response_json = json.dumps(msg)
                order.update_time = datetime.now()
                try:
                    db.session.add_all([order, order_confirm_detail])
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
                order.status = 3
                # 如果为充值订单
                if order.order_type == 1:
                    relate_order = Order.query.filter_by(id=order.relate_id).first()
                    relate_order.relate_order_status = 0  # 进入task_chain_in_recharge 重新生成订单
            else:
                order.status = 3
                if order.order_type == 1:
                    order.done_time = datetime.now()
                else:
                    relate_order = Order.query.filter_by(id=order.relate_id).first()
                    # relate_order.status = -1  # 链外待转帐，relate_order进入task_chain_out_withdraw

            if relate_order is None:
                try:
                    db.session.add(order)
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
        vpc_boss_address = consul_clinet.get_digiccy_boss_address(COIN_NAME)

        # 获取矿工费转帐地址
        minerfee_address = consul_clinet.get_digiccy_minerfee_address(COIN_NAME)

        # 最小归集数量
        collect_min_amount = consul_clinet.get_digiccy_collect_min(COIN_NAME)

        # 归集手续费
        gas_limit, gas_price = consul_clinet.get_digiccy_collect_fee(COIN_NAME)
        gas_limit_fee = Decimal((gas_limit * gas_price) / (10 ** 18))

        # 转帐手续费
        miner_minfee = consul_clinet.get_miner_fee(COIN_NAME)

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
                if not vpc_wallet.is_connected():
                    logging.error('{}节点离线!'.format(COIN_NAME))
                    return
                if vpc_wallet.is_syncing():
                    logging.error('VPC 节点同步未完成')
                    return

                # 用户是否有归集未确认订单
                if Order.is_collect(user.stellar_account, COIN_NAME):
                    print('用户有归集未确认订单')
                    continue

                # 用户绑定地址
                user_digiccy_address = user.address
                user_digiccy_secret = rsa_params_decrypt(user.secret)
                # 用户绑定地址余额,小于最小归集数量跳过
                balance = round(vpc_wallet.get_balance(user_digiccy_address), 7)
                if balance <= collect_min_amount:
                    continue
                # print(type(balance), balance, user_digiccy_address, user_digiccy_secret)

                # 归集数量:余额-最小归集数
                collect_amount = balance - collect_min_amount
                miner_fee = vpc_wallet.get_minerFee(user_digiccy_address)
                if miner_fee < miner_minfee:
                    is_success, tx_hash = vpc_wallet.minerfee_transaction(minerfee_address, user_digiccy_address,
                                                                          miner_minfee)
                    if not is_success:
                        logging.error('矿工费转账失败:{}'.format(tx_hash))
                        print("矿工费转账失败:{}".format(tx_hash))
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
                    order_to=vpc_boss_address,
                    amount=collect_amount,
                    fee=gas_limit_fee,
                    order_hash='',
                    add_time=datetime.now(),
                )
                # 创建裸交易发出
                is_success, msg = vpc_wallet.raw_transaction(user_digiccy_secret, vpc_boss_address,
                                                             collect_amount, gas_price, gas_limit)

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
