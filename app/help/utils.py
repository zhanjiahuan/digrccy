from stellar_base.utils import StellarMnemonic
from stellar_base.keypair import Keypair


PAY_STELLAR_ACCOUNT_SEED = 'SDZPDZE4H5HCNR5RH2C6T32ZNORC6IQXLB6SQMJN6PVVSSMP5BCZIB2Z'

def genMnemonicKeyPair(mnemonicLang='english'):
    """生成stellar账户,字典返回"""
    sm = StellarMnemonic(mnemonicLang)
    mnemonic = sm.generate()
    keypair = Keypair.deterministic(mnemonic, lang=mnemonicLang)
    mnemonic_keyPair = dict(mnemonic=str(mnemonic), account=keypair.address(), seed=keypair.seed())
    return mnemonic_keyPair

if __name__ == '__main__':
    print(genMnemonicKeyPair())