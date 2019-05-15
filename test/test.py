import base64
import json
import os
import time
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA

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


def seedEncrypt(data):
    # 用户秘钥加密
    PASSWORD = os.environ.get("DECRUPT_KEY", "kyCBHrg8cFJOOrXWyBBQw7sUww8EcEdi")  # 正式： OBiDDdPurYQJVue5WvhpahG75O5XtGfg
    IV = os.environ.get("ENCRYPT_IV", "IzLkAuX7WlhYBsjH")  # 正式 EM5qXxSdOTsRWzku
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


if __name__ == '__main__':
    stellar_seed = "SC2G5UG2FPM5GYMG5LRCVN6JPUHINXWP3FCGWDABXHA7AESHQUIRNUPH"
    user_seed_dict = {'seed': stellar_seed, 'time': 365*20 * 24 * 60 * 60 + int(time.time())}
    user_seed_str = json.dumps(user_seed_dict)
    enstellar_seed = seedEncrypt(user_seed_str)
    data = dict(
        digiccy_address="5jiexyjpl4bz",
        amount="0.0001",
        fee="0.00015",
        encrypt_seed=enstellar_seed
    )
    data = json.dumps(data)
    # #
    ret = rsaEncryptToken(data)
    # ret2 = seedEncrypt(data)
    print(ret)
    print(enstellar_seed)
    print(seedEncrypt('5Jb46jpSGwuXJXcom6e5PdLsaW1rMwc3MUqhZnVTApqVynMcXxA'))
