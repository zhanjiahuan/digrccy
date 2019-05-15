import time
import json
import logging
import uuid

from datetime import datetime
from decimal import Decimal

from app import db, btc_wallet, consul_clinet, stellar_service
from app.base.base import DigiccyBase
from app.utils.code_msg import CodeMsg
from app.models import User, Order, OrderDetail, Config

COIN_NAME = 'BTC'
digiccy_base = DigiccyBase(COIN_NAME)


def task_chain_out_recharge():
    """链外充值记录存入数据库"""
    with db.app.app_context():
        # block_num = Config.query.filter(key="btc_block_num").first().value
        while True:
            block_num = int(Config.get_btc_block_num())
            # 如果Btc官网区块高度减一，还是大于block_num
            btc_block_num = btc_wallet.get_block_num()
            print(btc_block_num, block_num)
            if btc_block_num is None:
                return
            if (btc_block_num - 1) >= block_num:
                # 对区块高度扫描，获取到的地址与user表中的地址进行对比，如果有，则说明进行了充值
                records = btc_wallet.btc_transaction_record(block_num)
                print('1111111111111', records)

                for record in records:
                    user = User.address_query_user(COIN_NAME, record[1])

                    # hash是否已经存在
                    if Order.query.filter_by(order_hash=record[3], order_type=1).first():
                        continue

                    record_order = Order(
                        id=str(uuid.uuid1()),
                        user_id=user.id,
                        stellar_account=user.stellar_account,
                        order_type=1,
                        chain_type=2,
                        coin_name=COIN_NAME,
                        order_from=record[0],
                        order_to=record[1],  # 充值的地址
                        amount=record[2],  # 充值数量
                        fee=0,
                        order_hash=record[3],  # 充值hash
                        relate_order_status=0,
                        add_time=datetime.now(),
                        status=1,
                    )
                    record_order_detail = OrderDetail(
                        id=str(uuid.uuid1()),
                        order_id=record_order.id,
                        act_type=2,
                        query_json=json.dumps(dict(btc_hash=record[3])),
                        response_json=json.dumps(record),
                        status=1,
                    )
                    try:
                        db.session.add_all([record_order, record_order_detail])
                        db.session.commit()
                    except Exception as e:
                        logging.error('Insert {} chain out recharge order error:{}'.format(COIN_NAME, str(e)))
                        return
                # 更新数据库block_num信息
                block_num += 1
                block_num_sql = Config.query.first()
                block_num_sql.value = block_num
                db.session.commit()
                time.sleep(0.5)  # btc api 接口访问频率限制1秒2次
            else:
                return


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
                    user_id=order.user_id,
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
                    record_order.status = 2  # 链内转账失败待确认
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

        # 从consul获取BTC base账户address
        btc_base_address = consul_clinet.get_digiccy_base_account(COIN_NAME, is_seed=False)
        # 根据address得到BTC base账户的account
        btc_base_account = btc_wallet.get_accounts(btc_base_address)
        if btc_base_account is None:
            return
        # 查询链外status为-1的订单
        orders = Order.chain_out_withdraw(COIN_NAME, 100)
        for order in orders:
            # 定时任务开关
            if not consul_clinet.get_task_switch():
                logging.warning('{}链内充值定时任务被手动关闭!'.format(COIN_NAME))
                return

            # 节点是否链接,是否同步
            if not btc_wallet.is_connected():
                logging.error('{}节点离线!'.format(COIN_NAME))
                return
            if not btc_wallet.is_sync():
                logging.error('{}节点同步未完成!'.format(COIN_NAME))
                return

            # 链外账户的收款地址
            order_to = order.order_to
            # 转账数量
            amount = order.amount

            # 检查财务账户链外余额， 即付款账户余额
            base_account_balance = btc_wallet.get_balance_by_account(btc_base_account)  # decimal.Decimal
            # 链外转账手续费
            fee = btc_wallet.estimate_fee()
            if base_account_balance or fee is None:
                return
            if amount + fee > base_account_balance:
                logging.error('base账户余额不足,支付金额{}'.format(str(amount)))
                print('base账户余额不足,支付金额{}'.format(str(amount)))
                continue

            # 当前区块信息
            block_num = btc_wallet.get_block_num()

            # 改变订单状态
            order.order_from = btc_base_account
            order.status = 0

            order_detail = OrderDetail(
                id=str(uuid.uuid1()),
                order_id=order.id,
                act_type=2,
                query_json=json.dumps(dict(addrfrom=btc_base_account, addrto=order_to, block_num=block_num)),
                response_json='',
                status=-1
            )
            try:
                db.session.add_all([order, order_detail])
                db.session.commit()
            except Exception as e:
                logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                return

            # 链外转账
            is_success, txid = btc_wallet.payment(btc_base_account, order_to, amount)
            print('定时任务链外转账结果', is_success, txid)
            if is_success:
                order_detail.status = 1  # 订单请求成功
                order_detail.response_json = txid
                order.order_hash = txid
                order.status = 2  # 成功发起转账,转账是否成功,待确认
                try:
                    db.session.add_all([order, order_detail])
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return
            else:
                order_detail.status = 0  # 订单请求失败
                order_detail.response_json = json.dumps(txid)
                try:
                    db.session.add(order_detail)
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return


def task_chain_out_confirm():
    """链外转账确认"""
    with db.app.app_context():
        # status为2的订单
        orders = Order.btc_chain_out_unconfirm(COIN_NAME, 100)
        print(orders)
        for order in orders:

            # 获取tx_id
            order_hash = order.order_hash
            # time.sleep(10)
            # 本地节点是否链接,是否同步
            print(btc_wallet.is_connected(),btc_wallet.is_sync())
            if not btc_wallet.is_connected():
                logging.error('{}节点离线123!'.format(COIN_NAME))
                return
            if not btc_wallet.is_sync():
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
            is_confirm, is_success, msg, fee = btc_wallet.hash_get_detail(order_hash)
            print('确认结果', is_confirm, is_success, msg, fee)
            # 未确认
            if not is_confirm:
                order_confirm_detail.status = 0
                order_confirm_detail.response_json = json.dumps(dict(msg=msg))
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


def task_chain_out_collect():
    """链外资金归集"""

    with db.app.app_context():
        # 归集地址:项目方提供boss地址
        btc_boss_address = consul_clinet.get_digiccy_boss_address(COIN_NAME)
        # 最小归集数量
        collect_min_amount = consul_clinet.get_digiccy_collect_min(COIN_NAME)
        # 归集手续费
        fee = Decimal(consul_clinet.get_btc_collect_fee(COIN_NAME))
        start_num = 0
        limit_num = 100
        len_num = 0
        success_num = 0
        fail_num = 0
        while True:
            users = User.coin_bind_users(COIN_NAME, start_num, limit_num)
            len_num += len(users)
            if not users:
                logging.info('{}链外归集处理完毕,处理条数:{},归集成功条数:{},归集失败条数:{}'.format(COIN_NAME, len_num, success_num, fail_num))
                print('{}链外归集处理完毕,处理条数:{},归集成功条数:{},归集失败条数:{}'.format(COIN_NAME, len_num, success_num, fail_num))
                break
            for user in users:
                if not consul_clinet.get_task_switch():
                    logging.warning('链外充值定时任务被手动关闭!')
                    return
                # 本地节点是否链接,是否同步
                if not btc_wallet.is_connected():
                    logging.error('{}节点离线!'.format(COIN_NAME))
                    return
                if not btc_wallet.is_sync():
                    logging.error('BTC 节点同步未完成')
                    return

                # 用户是否有归集未确认订单
                if Order.is_collect(user.stellar_account, COIN_NAME):
                    print('用户有归集未确认订单')
                    continue

                # 用户绑定地址
                digiccy_address = user.address
                # 获取btc余额
                # btc_account = btc_wallet.get_accounts(digiccy_address)
                # amount = btc_wallet.get_balance_by_account(btc_account)
                amount = btc_wallet.get_balance(digiccy_address)
                collect_amount = round(amount - fee, 8)
                if amount is None:
                    continue
                # 归集数量小于最小归集数量，则跳过
                if collect_amount < collect_min_amount:
                    continue

                # 创建归集订单
                order_collect = Order(
                    id=str(uuid.uuid1()),
                    user_id=user.id,
                    stellar_account=user.stellar_account,
                    coin_name=user.coin_name,
                    order_type=3,
                    chain_type=2,
                    order_from=digiccy_address,
                    order_to=btc_boss_address,
                    amount=collect_amount,
                    fee=fee,
                    order_hash='',
                    add_time=datetime.now(),
                )
                # 创建裸交易发出
                is_success, tx_hash, msg = btc_wallet.raw_payment(digiccy_address, btc_boss_address, collect_amount)
                if is_success is None:
                    continue
                print(is_success, tx_hash, msg)

                if is_success:
                    success_num += 1
                    order_collect.status = 2  # 发出成功待确认
                    order_collect.order_hash = tx_hash
                    order_collect.done_time = datetime.now()
                else:
                    fail_num += 1
                    order_collect.status = 0  # 发出成功失败

                try:
                    db.session.add(order_collect)
                    db.session.commit()
                except Exception as e:
                    logging.error('chain_out_withdraw update order error:{}'.format(str(e)))
                    return

            start_num += limit_num


def task_chain_in_confirm():
    """链内转账504,或timeout错误确认"""
    with db.app.app_context():
        # order的status为2
        orders = Order.chain_in_unconfirm(COIN_NAME, 100)
        for order in orders:
            # 定时任务开关
            if not consul_clinet.get_task_switch():
                logging.warning('链外充值定时任务被手动关闭!')
                return

            # 查询链内哈希
            stellar_hash = order.order_hash
            stellar_node = stellar_service.stellar_node(is_full=True)
            ret = stellar_service.query_hash(stellar_hash, stellar_node=stellar_node)
            # 请求失败
            if not ret:
                continue

            relate_order = None
            if ret.get('hash') is None:
                order.status = 0  # hash 不存在,链内转账失败
                # 当前订单为充值订单
                if order.order_type == 1:
                    relate_order = Order.query.filter_by(id=order.relate_id).first()
                    relate_order.relate_order_status = 0  # 待重新生成链内转账订单
            else:
                order.status = 1  # hash 存在,链内转账成功
                # 当前订单为提现订单
                if order.order_type == 2:
                    relate_order = Order.query.filter_by(id=order.relate_id).first()
                    relate_order.status = -1  # 更新链外提现订单状态为-1(待转账)
                elif order.order_type == 1:
                    order.done_time = datetime.now()  # 链内充值订单完成时间

            # 无需更改关联订单状态
            if relate_order is None:
                try:
                    db.session.add(order)
                    db.session.commit()
                except Exception as e:
                    logging.error('task_chain_in_confirm update db error:{}'.format(str(e)))
                    db.session.rollback()
                    return
            # 更改关联订单状态
            else:
                try:
                    db.session.add_all([order, relate_order])
                    db.session.commit()
                except Exception as e:
                    logging.error('task_chain_in_confirm update db error:{}'.format(str(e)))
                    db.session.rollback()
                    return

            is_relate = '否' if not relate_order else '是,关联订单id:{}'.format(relate_order.id)
            print('确认hash订单id:{},是否更改关联订单:{}'.format(order.id,is_relate))
            logging.info('确认hash订单id:{},是否更改关联订单:{}'.format(order.id,is_relate))