import os
import base64
import json
import time

from requests import Timeout
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_v1_5
from Crypto import Random
from Crypto.PublicKey import RSA
from decimal import Decimal
from stellar_base.utils import account_xdr_object

from app import session_pool
from app import consul_clinet
from app.common.consul import ConsulServiceName

# from app.constant import PRIV_KEY_STR, GUARANTEE_AMOUNT, NATIVE_CODE

PUB_KEY_STR = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvCwWU+YK2Z4WLZ08PQg1
M5dwnlIuMqW7EMH0sKVwHWfhqBR0mmNQAiJG4M81/HIVHTKHLR5141Ujf4p3n+pl
IH03oIjN3iQofCiYmZs7RO11SYKB7i5HUJRSVmKH0yYzrJgaC+cv8GBO6D2GtBN9
2+Oz/PubP815n7LEldGFF3FisnE/pSLb9QyV3h9ATYVx9MYZpwJ/Gn1xzUZ8YYOn
M4o7JXdOIsTM0GCLbLX5vQb9wbhg/QmF+7mBxSWDoG4CCnqmiPIiMBIXCOLclDgX
QYXIhqpG1PACXIs+XalUYyrJ1f1jiaRwsHNWweDrm2yLFQi5hFId3+RIpL+Av4qf
UvRAIPCMva6g8HTDaiklqyFzIYx2466Yheqh/hbDp8M3VTLglGUr94VHMjjYeaJ8
Zl53GH1YMCGAJNNJ7G/J4+7Mcr2Xq8OyqfYEa6r56CrxvcNerE07YBpKMrifIpdO
BgtJIHG+XmUMT7NIrVEyaI/ygc22mMQaaMLaaAcUVRFL1/HIE/g0+5QwdCYzGd+z
sXrZWJ7BZiO7E0vsWQjueWUSXeL5+7BHcTLsB08RglZwvL+Y3OXTgx3aDwz19aaF
SilcJqF4rWhM5pzsNp44eCDT+ISMEGpqrb0jUFgFdpfNyactmvGQ8py94icO86Dk
RP3Ug6aS+BElIRg4/MuCrj0CAwEAAQ==
-----END PUBLIC KEY-----"""

PRIV_KEY_STR = """-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----"""


def decryptSeed(encrypt_user_seed):
    """解密stellar seed"""
    PASSWORD = os.environ.get("DECRUPT_KEY", "kyCBHrg8cFJOOrXWyBBQw7sUww8EcEdi")
    IV = os.environ.get("ENCRYPT_IV", "IzLkAuX7WlhYBsjH")
    # 与python2的版本有区别，需要加上b
    key = bytes(PASSWORD, encoding="utf8")  # 16,24,32位长的密码
    iv = bytes(IV, encoding="utf8")
    unpad = lambda s: s[0:-ord(s[-1])]
    decrypted_bytes = bytes(encrypt_user_seed, encoding='utf-8')
    try:
        data = base64.b64decode(decrypted_bytes)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        # AES解密
        data = unpad(cipher.decrypt(data).decode('utf-8'))
    except Exception as ex:
        data = None
    return data

# 用户秘钥加密
def seedEncrypt(data):
    PASSWORD = os.environ.get("DECRUPT_KEY", "kyCBHrg8cFJOOrXWyBBQw7sUww8EcEdi")
    IV = os.environ.get("ENCRYPT_IV", "IzLkAuX7WlhYBsjH")
    bs = AES.block_size
    pad = lambda s: s + (bs - len(s) % bs) * chr(bs - len(s) % bs)
    iv = bytes(IV, encoding="utf8")
    password = bytes(PASSWORD, encoding="utf8")  # 16,24,32位长的密码
    cipher = AES.new(password, AES.MODE_CBC, iv)
    data = cipher.encrypt((pad(data)).encode(encoding='utf-8'))

    data = base64.b64encode(data)
    data = data.decode("utf-8")
    return data

def rsaEncryptToken(token):
    # 加密
    if not isinstance(token, bytes):
        token = bytes(token, encoding='utf-8')
    rsakey = RSA.importKey(PUB_KEY_STR)
    cipher = PKCS1_v1_5.new(rsakey)
    # 加密时使用base64加密
    r = cipher.encrypt(token)
    cipher_text = base64.b64encode(r)
    return cipher_text.decode('utf-8')


def rsa_params_decrypt(msg):
    """解密前端传递的加密字符串获得参数"""
    random_generator = Random.new().read
    rsakey = RSA.importKey(PRIV_KEY_STR)
    cipher = PKCS1_v1_5.new(rsakey)
    # 使用base64解密，(在前端js加密时自动是base64加密)
    params = cipher.decrypt(base64.b64decode(msg), random_generator).decode('utf-8')
    return params


def checkStellarAccount(account):
    """检查stellar账户是否有效"""
    try:
        account_xdr_object(account)
        return True
    except:
        return False


def str_num_to_decimal(num):
    n = 0
    for i in num:
        if i == '.':
            n += 1
    if n > 1:
        return False
    if n > 0:
        float_len = num.split('.')[1]
        if len(float_len) > 7:
            return False
    if 'e' in num or 'E' in num:
        return False
    try:
        num = Decimal(num)
    except:
        return False
    else:
        return num


def decrypt_seed(encrypt_user_seed):
    PASSWORD = os.environ.get("CONFIG_DECRUPT_KEY", "kyCBHrg8cFJOOrXWyBBQw7sUww8EcEdi") # OBiDDdPurYQJVue5WvhpahG75O5XtGfg
    IV = os.environ.get("CONFIG_ENCRYPT_IV", "IzLkAuX7WlhYBsjH") # EM5qXxSdOTsRWzku
    # 与python2的版本有区别，需要加上b
    key = bytes(PASSWORD, encoding="utf8")  # 16,24,32位长的密码
    iv = bytes(IV, encoding="utf8")
    unpad = lambda s: s[0:-ord(s[-1])]
    decrypted_bytes = bytes(encrypt_user_seed, encoding='utf-8')
    try:
        data = base64.b64decode(decrypted_bytes)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        # AES解密
        data = unpad(cipher.decrypt(data).decode('utf-8'))
    except Exception as ex:
        data = None
    return data


def verify_googleauth(auth, goog_code):
    """谷歌验证码"""
    if auth == "" or auth is None:
        return False, 'no Authorization'

    header = dict(Authorization=auth)
    data = dict(code=goog_code)

    try:
        urlPrefix = consul_clinet.getRandomOneAvailableServiceIpPort(ConsulServiceName.DAPP_PHPSERVICE,
                                                                          withHttpPrefix=True)
    except:
        return False, 'consul service time out'
    try:
        url = urlPrefix + '/api/verify_googleauth'
        ret = session_pool.post(url=url, headers=header, data=data, timeout=10).json()
    except Timeout:
        return False, 'php token validate api time out'
    if ret.get('code') != 200:
        return False, ret.get('msg')
    else:
        return True, None


if __name__ == "__main__":
    encrypt_user_seed = "ypZiSNr2g/jwBaUxSSvcyIIPLsxnlL/VOhWWH1mGetIhr75bMvuYWRiq7gtpV6uHn9FC6yXW0ThZONNrWOM1DJBXAAvm2i2uUWAonUU+9w/Y0shRpDzQAlp73gLIL74l"
    # encrypt_user_seed = "bhNxtOdSJv7b0l8UUqwBBjYH1x8YYws+BAVv86UApOK4FQfBSWeZmuovQNCTIZ4hlvkrcq/ZA0DLjBF1mCtUCjDMd5J4b7bwJvMuD1ubgDKY4iWaOz2ZF5/K6PqPje+T"
    # stellar_seed = "SBWBJUNWO4UTRAJPMO6ULCWCQF6VAKGY3EFKP4L3567XSESSHOUDVQVN"
    # params = 'NZmZpZUzFibV1BDX33krnGmUhromRmWqy2OfX340azetCTvSp6+GOJhuVJq2EfRrJSDmMSSDo1xzcwHWRQoPhn+sD7/wX/ZGXFoMlM1UG6QbFBZVL2q9mJHx/Z0gjq1vFynfkyqFOcqYfNxGM7ktNunDMmIkfatA34mhgHhZ0X8WGSj3/k9el62W8dPIcHXwdIOwj95uZd3XgjvocZ4rJ3KJGowWNf45rLf2ggjkEUB1xRQ1PqSx+1AmBKIz/bLBMtnQ1Es115hYIjB9HR36uffkNduWX4ZMOdrPA8VZF/mMtkQVQVore1Ozkklj/128ta/UkpwoTkDadSK+MYrrTMSshOJEZFNuffzCycGn9eluwOz6aPnwbfwysod0oD7R5+Tas/O96dYrheE+ghWJoI+YnF0UDQ4UEgAaJ4942gr6bYksHgFmcBtAibkR8sbqiT1IeaMsdxnDZf+g+oibwg01DjH8ARI/AZtlS93Yy2cCLfHdl3foEyKUKblnSeucgPjvzq7Fhk88JX8a1V2jlvwZj6sRbnkY1GozslXkiosr9b+SDqRJgKttHVj2LtS4K0kV1IxHZuYztc8Fmrcs+71tcbgH8K9Xguz3eukq5SJtI1mK9o/NbVmgh6UHnbkmUOJXGlRfaHAD9gl3tHNlyTNOvJymImhLUqzzGwvA2nw='
    # params = 'eWADQLPqGmayutB8AXvj+Sttqn7POBMeZ1XB/+efpsUDuBKEkiwCIGJZiZsnPzHHwlZv2hSNJ/n3oQLaHfUe0pAudncaiwqXVfp2512V1xTI9rT/+9/64h9uE/jGh1F3sSkk6u76xY8a5tK6qU+Zi9GvxMxoX9xbnyN3QfLCZQ5QPqWR/3FdAbaAkFaKzY4zN6YMJjQ3LZaJW5Jz6V7yX+JGvXYq8R/7Z0VK9M7K5A8+6fc4UHgZlRRfWzKmRJb4k8ALvuP1vQJRyl5BF/sT858ihVeUJ+gjs9KGMxxgdWFQ+0ekMxTGH8vSoUjxCXehEpnUTAkdlSlOywbDSuoMUh82CB3kVRJ/pvXhlM5fCqsenrVz2lfhWHB8c3+BKORIJ7JVYfw30k3ZWimLpd2XI2S9s0sPY2O+L5YqLGp2iJYrJoMEeEcqNIsHALUk7+lBF8f3JAeQFhUKlv3JsKWSZnoB6wGoAAgiMP2G+sNAz/i4rkkmRQnhF1hcmsTrQw/NUT8WRDgyXrRUN5T3pVXXbI1/47EpOnDtq+E+2tsfnzEuPZBHEhhuOUqRY8OnPmeSE0pkL7B5A6g7vEpwb3HsKf93GXpQE9AECUB6UR2Ej9F72JJ850r4TN/QclaKhxPQ6Ak9HJ3UDQUqSMD+dvFytj0bPU4wn3HLYMHbPFRh/oQ='
    # r = rsa_params_decrypt(params)
    # user_seed_dict = {'seed':stellar_seed,'time':365*20*24*60*60+int(time.time())}
    # user_seed_str = json.dumps(user_seed_dict)
    # enstellar_seed = seedEncrypt(user_seed_str)
    # data = {"encrypt_seed":enstellar_seed}
    #
    data = decrypt_seed(encrypt_user_seed)
    # print(r)
    # data = dict(
    #     digiccy_address="0x0C7d3974485C812D28B8aD347240327387aE2931",
    #     amount="0.001",
    #     fee="0.00015",
    #     encrypt_seed=enstellar_seed
    # )
    # data = json.dumps(data)
    #
    #
    # ret = rsaEncryptToken(data)
    print(data)
# {"seed": "SC2WNKD44J53O3TFEKCNCDTQASDRAGBSXLBXXZ5J3SV56AUO7SQ3DO5W", "time": 2184543251}
