import requests
from decimal import Decimal
from app.common.sms import SmsService
import app
from app import consul_clinet
from app.base.base import get_min_balances

sms_service = SmsService()
mobile1, mobile2 = consul_clinet.get_mobiles()

digiccy_min_balances = get_min_balances("digiccy")
stellar_min_balances = get_min_balances("stellar")


def send_sms():
    msg = ""
    balance_msg = ""
    stellar_balance_msg = ""
    for coin_type in digiccy_min_balances:
        wallet_str = "{}_wallet".format(coin_type.lower())
        wallet = getattr(app, wallet_str)
        if not wallet.is_connected():
            msg += '{} 钱包节点不可用 \n'.format(coin_type)
    if msg != "":
        for mobile in mobile1:
            sms_service.send_sms(msg, mobile)

    for coin_type, min_balance in digiccy_min_balances.items():
        base_address = consul_clinet.get_digiccy_base_account(coin_type, is_seed=False)
        wallet_str = "{}_wallet".format(coin_type.lower())
        wallet = getattr(app, wallet_str)
        base_balance = wallet.get_balance(base_address)

        if base_balance < int(min_balance):
            balance_msg += 'VTOKEN项目 {} base 账户余额较少需要充值,目前余额{} \n'.format(coin_type, str(base_balance))

    if balance_msg != "":
        for mobile in mobile2:
            code = "1"
            num = 0
            while code != "0" and num < 5:
                ret = sms_service.send_sms(balance_msg, mobile)
                code = ret.get("code")
                num += 1

    for coin_type, min_balance in stellar_min_balances.items():
        stellar_address = consul_clinet.get_stellar_base_account(coin_type, is_seed=False)
        stellar_node = app.stellar_service.stellar_node()
        url = stellar_node + '/accounts/{}'.format(stellar_address)
        response = requests.get(url).json()
        balances = response.get('balances')
        balance = 0
        for balance_info in balances:
            if balance_info.get("asset_code") == coin_type:
                balance = balance_info.get("balance")
        if Decimal(balance) < int(min_balance):
            stellar_balance_msg += 'VTOKEN项目 {} stellar_base 账户余额较少需要充值,目前余额{} \n'.format(coin_type, str(balance))

    if stellar_balance_msg != "":
        for mobile in mobile2:
            code = "1"
            num = 0
            while code != "0" and num < 5:
                ret = sms_service.send_sms(stellar_balance_msg, mobile)
                code = ret.get("code")
                num += 1


if __name__ == '__main__':
    print(5040000000000000 / (10 ** 18))
