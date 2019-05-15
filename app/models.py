# coding: utf-8
import time
from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.schema import FetchedValue
from sqlalchemy import asc, desc
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Config(db.Model):
    __tablename__ = 'config'

    key = db.Column(db.String(255), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    @classmethod
    def get_btc_block_num(cls):
        """获取数据库区块高度"""
        btc_block_num = Config.query.filter_by(key='btc_block_num').first().value
        return btc_block_num

    @classmethod
    def task_switch(cls):
        """定时任务开关"""
        task_switch = Config.query.filter_by(key='task.switch').first().value
        if task_switch == '1':
            return True
        else:
            return False

    @classmethod
    def stellar_base_account(cls, coin_name):
        """获取stellar base 账户"""
        key = 'stellar.{}.base.account'.format(coin_name)
        stellar_base_account = Config.query.filter_by(key=key).first().value
        return stellar_base_account

    @classmethod
    def digiccy_base_account(cls, coin_name):
        """第三方货币 base 账户"""
        key = 'digiccy.{}.base.account'.format(coin_name)
        digiccy_base_account = Config.query.filter_by(key=key).first().value
        return digiccy_base_account


class Order(db.Model):
    __tablename__ = 'order'

    id = db.Column(db.String(36), primary_key=True)
    relate_id = db.Column(db.String(36), nullable=False, server_default=db.FetchedValue())
    user_id = db.Column(db.String(36), nullable=False)
    stellar_account = db.Column(db.String(56), nullable=False, index=True)
    coin_name = db.Column(db.String(12), nullable=False)
    order_type = db.Column(db.Integer, nullable=False)
    chain_type = db.Column(db.Integer, nullable=False)
    order_from = db.Column(db.String(255), nullable=False)
    order_to = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(20, 7), nullable=False)
    fee = db.Column(db.Numeric(20, 7), nullable=False)
    order_hash = db.Column(db.String(255), nullable=False, server_default=db.FetchedValue())
    status = db.Column(db.Integer, nullable=False)
    relate_order_status = db.Column(db.Integer, nullable=False, server_default=db.FetchedValue())
    notice_status = db.Column(db.Integer, nullable=False, server_default=db.FetchedValue())
    add_time = db.Column(db.DateTime, nullable=False)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    done_time = db.Column(db.DateTime)
    memo = db.Column(db.String(255), server_default=db.FetchedValue())

    @classmethod
    def chain_out_recharge(cls, coin_name, limit_num):
        """链外充值成功,链内待充值记录"""
        filter = {
            "coin_name": coin_name,
            "order_type": 1,
            "chain_type": 2,
            "relate_order_status": 0,
        }
        orders = Order.query.filter_by(**filter).order_by(Order.add_time.asc()).limit(limit_num).all()
        return orders

    @classmethod
    def chain_out_withdraw(cls, coin_name, limit_num):
        """链内提现成功,链内待提现记录"""
        filter = {
            "coin_name": coin_name,
            "order_type": 2,
            "chain_type": 2,
            "status": -1,
        }
        orders = Order.query.filter_by(**filter).order_by(Order.add_time.asc()).limit(limit_num).all()
        return orders

    @classmethod
    def hash_is_exist(cls,record_hash):
        """查询充值hash是否存在"""
        if Order.query.filter_by(order_type=1, order_hash=record_hash).first():
            print(Order.query.filter_by(order_type=1, order_hash=record_hash).first())
            return True

    @classmethod
    def chain_out_unconfirm(cls, coin_name, limit_num):
        """链外待确认订单"""
        filter = {
            "coin_name": coin_name,
            "chain_type": 2,
            "status": 2,
        }
        # orders = Order.query.filter_by(**filter).order_by(Order.add_time.asc()).limit(limit_num).all()
        time_limit = time.time() - (60 * 5)
        data_time_limit = datetime.fromtimestamp(time_limit)
        # print(Order.query.filter_by(**filter).filter(Order.update_time < data_time_limit).order_by(Order.add_time.asc()).limit(limit_num))
        orders = Order.query.filter_by(**filter).filter(Order.update_time < data_time_limit).order_by(Order.add_time.asc()).limit(limit_num).all()
        return orders

    @classmethod
    def btc_chain_out_unconfirm(cls, coin_name, limit_num):
        """btc链外待确认订单"""
        filter = {
            "coin_name": coin_name,
            "chain_type": 2,
            "status": 2,
        }
        time_limit = time.time() - (60 * 5)
        data_time_limit = datetime.fromtimestamp(time_limit)

        orders = Order.query.filter_by(**filter).filter(Order.update_time < data_time_limit).order_by(
            Order.add_time.asc()).limit(limit_num).all()
        return orders

    @classmethod
    def is_collect(cls, stellar_account, coin_name):
        """查询账户是否有处于归集待确认的订单"""
        filter = {
            "stellar_account": stellar_account,
            "coin_name": coin_name,
            "order_type": 3,
            "chain_type": 2,
            "status": 2,
        }
        if Order.query.filter_by(**filter).first():
            return True
        else:
            return False

    @classmethod
    def chain_in_unconfirm(self, coin_name, limit_num):
        """链内转账504,或timeout错误确认"""
        filter = {
            "coin_name": coin_name,
            "chain_type": 1,
            "status": 2,
        }
        time_limit = time.time() - (60 * 5)
        data_time_limit = datetime.fromtimestamp(time_limit)
        orders = Order.query.filter_by(**filter).filter(Order.update_time < data_time_limit).order_by(Order.add_time.asc()).limit(limit_num).all()
        return orders


class OrderDetail(db.Model):
    __tablename__ = 'order_detail'

    id = db.Column(db.String(36), primary_key=True)
    order_id = db.Column(db.String(36), nullable=False, index=True)
    act_type = db.Column(db.Integer, nullable=False)
    query_json = db.Column(db.String(1024), nullable=False, server_default=db.FetchedValue())
    response_json = db.Column(db.Text, nullable=False)
    add_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    memo = db.Column(db.String(255), nullable=False, server_default=db.FetchedValue())
    status = db.Column(db.Integer, nullable=False, server_default=db.FetchedValue())

    @classmethod
    def confirm_times(cls, order_id):
        """查询订单确认次数"""
        filter = {
            "act_type": 4,
            "order_id": order_id,
        }
        order_detail = OrderDetail.query.filter_by(**filter).all()
        times = len(order_detail)
        return times


class OrderAuditor(db.Model):
    __tablename__ = 'order_auditor'

    id = db.Column(db.String(36), primary_key=True)
    stellar_account = db.Column(db.String(56), nullable=False)
    coin_name = db.Column(db.String(12), nullable=False)
    amount = db.Column(db.Numeric(20, 7), nullable=False)
    data = db.Column(db.String(1024), nullable=False, server_default=db.FetchedValue())
    status = db.Column(db.Integer, nullable=False, server_default=db.FetchedValue())
    add_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    examine = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)



class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.String(36), primary_key=True)
    stellar_account = db.Column(db.String(56), nullable=False, index=True)
    coin_name = db.Column(db.String(12), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    secret = db.Column(db.Text, nullable=False)
    last_block = db.Column(db.BigInteger, nullable=False, server_default=db.FetchedValue())
    last_time = db.Column(db.BigInteger, nullable=False, server_default=db.FetchedValue())
    is_ban = db.Column(db.Integer, nullable=False, server_default=db.FetchedValue())
    add_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def coin_bind_users(cls, coin_name, start_num, limit_num):
        """绑定货币的用户"""
        users = User.query.filter_by(coin_name=coin_name).order_by(User.update_time.desc()).offset(start_num).limit(limit_num).all()
        print(users)
        return users

    @classmethod
    def address_query_user(cls, coin_name, address):
        # users = User.query.filter(coin_name=coin_name, address=address).all()
        users = User.query.filter_by(coin_name=coin_name, address=address).first()
        return users

# class Order1(object):
#
#     _mapper = {}
#
#     @staticmethod
#     def model(table_index):
#         class_name = "Order_%d" % table_index
#
#         ModelClass = Order1._mapper.get(class_name, None)
#         if ModelClass is None:
#             ModelClass = type(class_name, (db.Model,), {
#                 '__module__': __name__,
#                 '__name__': class_name,
#                 '__tablename__': 'goods_desc_%d' % table_index,
#
#                 'id': db.Column(db.String(36), primary_key=True),
#                 'relate_id': db.Column(db.String(36), nullable=False, server_default=db.FetchedValue()),
#                 'user_id': db.Column(db.String(36), nullable=False),
#                 'stellar_account': db.Column(db.String(56), nullable=False, index=True),
#                 'coin_name': db.Column(db.String(12), nullable=False),
#                 'order_tye': db.Column(db.Integer, nullable=False),
#                 'chain_type': db.Column(db.Integer, nullable=False),
#                 'order_from': db.Column(db.String(255), nullable=False),
#                 'order_to': db.Column(db.String(255), nullable=False),
#                 'amount': db.Column(db.Numeric(20, 7), nullable=False),
#                 'fee': db.Column(db.Numeric(20, 7), nullable=False),
#                 'order_hash': db.Column(db.String(255), nullable=False, server_default=db.FetchedValue()),
#                 'status': db.Column(db.Integer, nullable=False),
#                 'relate_order_status': db.Column(db.Integer, nullable=False, server_default=db.FetchedValue()),
#                 'notice_status': db.Column(db.Integer, nullable=False, server_default=db.FetchedValue()),
#                 'add_time': db.Column(db.DateTime, nullable=False, default=datetime.now),
#                 'update_time': db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now),
#                 'done_time': db.Column(db.DateTime),
#                 'memo': db.Column(db.String(255), server_default=db.FetchedValue()),
#
#             })
#             Order._mapper[class_name] = ModelClass
#             cls = ModelClass()
#             cls.table_index = table_index
#             return cls