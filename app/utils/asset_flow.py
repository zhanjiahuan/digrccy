# coding:utf-8

import requests
import time
import pytz
import datetime


class TimeConvert(object):
    """
    时间转换工具类
    """
    @staticmethod
    def utc_to_local(utc_time_str):
        """UTC时间转换"""
        utc_format = '%Y-%m-%dT%H:%M:%SZ'
        local_format = "%Y-%m-%d %H:%M:%S"
        local_tz = pytz.timezone('Asia/Shanghai')
        utc_dt = datetime.datetime.strptime(utc_time_str, utc_format)
        local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
        time_str = local_dt.strftime(local_format)
        timeArray = time.localtime(int(time.mktime(time.strptime(time_str, local_format))))
        local_datatime = time.strftime(local_format, timeArray)
        local_timestamp = int(time.mktime(time.strptime(str(local_datatime), local_format)))
        return local_datatime, local_timestamp

    @staticmethod
    def datatime_to_timestamp(datatime_str):
        """本地时间转时间戳"""
        number_time = int(time.mktime(time.strptime(str(datatime_str), "%Y-%m-%d %H:%M:%S")))
        return number_time


class StellarAssetFlow(object):
    """
    恒星资产流水查询
    """

    endpoint_payments_for_account = '/accounts/{}/payments'
    endpoint_trades_for_account = '/accounts/{}/trades'

    def __init__(self, account, stellar_http_node, native_code, create_time=None, asset_code=None):
        self.account = account
        self.stellar_http_node = stellar_http_node
        self.time_convert = TimeConvert
        self.native_code = native_code
        self.records = []
        self.asset_code = asset_code
        if create_time is not None:
            try:
                self.create_timestamp = self.time_convert.datatime_to_timestamp(create_time)
            except:
                raise Exception('Error in time format')
        else:
            self.create_timestamp = None

    def stellar_request(self, stellar_api):
        cursor = 'now'
        while True:
            # 参数
            params = {
                'limit': 50,
                'cursor': cursor,
                'order': 'desc'
            }
            # 发送请求
            try:
                records = requests.get(stellar_api, timeout=10, params=params).json()['_embedded']['records']
            except:
                return
            if not records:
                break
            cursor = records[-1]['paging_token']

            for record in records:
                yield record

    def payment_records(self, payment_type=None):
        """
        :param payment_type: 1=转入 2=转出
        :return: list
        """
        stellar_api = self.stellar_http_node + self.endpoint_payments_for_account.format(self.account)
        all_records = self.stellar_request(stellar_api)

        is_sort = True if self.records else False  # 是否需要排序

        for record in all_records:
            # 操作过滤
            if record.get('type') != 'payment':
                continue

            # 时间过滤数据
            record_datatime,record_timestamp = self.time_convert.utc_to_local(record['created_at'])
            # 获取的数据为倒序获取,时间小于过滤时间 退出循环
            if self.create_timestamp and record_timestamp < self.create_timestamp:
                break

            # 资产过滤
            record_asset_code = record.get('asset_code', self.native_code)
            if self.asset_code is not None and record_asset_code != self.asset_code:
                continue

            # 转入转出过滤
            record_from = record['from']
            record_to = record['to']
            if record_to == self.account:
                record_payment_type = 1
            else:
                record_payment_type = 2
            if payment_type and payment_type != record_payment_type:
                continue

            record_info = {
                "type": "pay_in" if record_payment_type == 1 else "pay_out",
                "asset_code": record_asset_code,
                "amount": record['amount'],
                "datatime": record_datatime,
                "timestamp": record_timestamp,
                "from": record_from,
                "to": record_to
            }
            self.records.append(record_info)
        if is_sort:
            self.records.sort(key=lambda x:x['timestamp'], reverse=True)
        return self.records

    def trades_records(self, trades_type=None):
        """
        :param trades_type: 1=买入 2=卖出
        :return:
        """
        stellar_api = self.stellar_http_node + self.endpoint_trades_for_account.format(self.account)
        all_records = self.stellar_request(stellar_api)

        is_sort = True if self.records else False  # 是否需要排序

        for record in all_records:
            # print record
            # 时间过滤数据
            record_datatime, record_timestamp = self.time_convert.utc_to_local(record['ledger_close_time'])
            # 获取的数据为倒序获取,时间小于过滤时间 退出循环
            if self.create_timestamp and record_timestamp < self.create_timestamp:
                break

            # 资产过滤
            base_asset = record.get('base_asset_code', self.native_code)
            counter_asset = record.get('counter_asset_code', self.native_code)
            if self.asset_code and self.asset_code not in (base_asset,counter_asset):
                continue

            # 买入卖出过滤
            base_account = record['base_account']
            counter_account = record['counter_account']
            if self.account == base_account:
                if self.asset_code == base_asset:
                    record_trades_type = 2  # 卖出
                    sell_code = base_asset
                    sell_amount = record['base_amount']
                    buy_code = counter_asset
                    buy_amount = record['counter_amount']
                else:
                    record_trades_type = 1  # 买入
                    sell_code = counter_asset
                    sell_amount = record['counter_amount']
                    buy_code = base_asset
                    buy_amount = record['base_amount']
            else:
                if self.asset_code == counter_asset:
                    record_trades_type = 2  # 卖出
                    sell_code = counter_asset
                    sell_amount = record['counter_amount']
                    buy_code = base_asset
                    buy_amount = record['base_amount']
                else:
                    record_trades_type = 1  # 买入
                    sell_code = base_asset
                    sell_amount = record['base_amount']
                    buy_code = counter_asset
                    buy_amount = record['counter_amount']

            if trades_type and trades_type != record_trades_type:
                continue
            record_info = {
                "type": "trade_in" if record_trades_type == 1 else "trade_out",
                "sell_asset": sell_code,
                "sell_amount": sell_amount,
                "buy_asset": buy_code,
                "buy_amount": buy_amount,
                "account": self.account,
                "datatime": record_datatime,
                "timestamp": record_timestamp,
            }
            self.records.append(record_info)
        if is_sort:
            self.records.sort(key=lambda r:r['timestamp'],reverse=True)
        return self.records




if __name__ == '__main__':
    account = 'GBD5WFMGOMFPH5MATYSOL6PUZUJFEDJ2CZXVHESJ46NYMHFR4OZKSQKA'
    stellar_http_node = 'http://101.132.188.48:8000'
    native_code = 'VTOKEN'
    asset = 'VPC'
    create_time='2019-02-28 03:53:40'
    a = StellarAssetFlow(account, stellar_http_node, native_code, asset_code=asset,create_time=create_time)

    a.payment_records()
    a.trades_records()

    for i in a.records:
        print(i)