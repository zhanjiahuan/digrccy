import time

import requests
import json
import logging

from app.base.base import StellarAccount


class SmsService():
    sms_account = 'I1313122'
    sms_pwd = 'wg3KY@iqWwA3'
    sms_url = 'http://intapi.253.com/send/json?'

    def send_sms(self, msg, mobile):
        params = dict(
            account=self.sms_account,
            password=self.sms_pwd,
            msg=msg,
            # mobile="+86 {}".format(mobile),
            mobile=mobile,
            report=False
        )
        raw = json.dumps(params)
        ret = requests.post(self.sms_url, data=raw, headers={'Content-Type': 'application/json'}).json()
        if ret.get('msgid') is None:
            logging.error('send sms error:ret {},params {}'.format(str(ret), raw))
        return ret


if __name__ == '__main__':
    a = SmsService()
    # stellar_account = StellarAccount("GBJWXTJVJ2352TXWTJLTQFMKUQYYOCJXKAQQ73M3MTC7LPCUARSPP75A")
    stellar_node = "http://101.132.188.48:8000"
    url = stellar_node + '/accounts/{}'.format("GAFRMFBUMFDFKNPRDBKTVVNXBCCZFEYTRHX3FTTDDO5LJTOV7K2AJTRG")
    response = requests.get(url).json()
    balances = response.get('balances')
    balance = 0
    for balance_info in balances:
        if balance_info.get("asset_code") == "ABS":
            balance = balance_info.get("balance")

    code = "1"
    num = 0
    while code != "0" and num < 5:
        ret = a.send_sms('VRT stellar 余额 {}'.format(balance), '+86 13294166568')
        code = ret.get("code")
        # print(type(code), code)
        num += 1
        time.sleep(1)
