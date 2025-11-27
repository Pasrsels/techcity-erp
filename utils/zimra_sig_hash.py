import base64
import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import argparse
from loguru import logger

def get_hash(request):
    """Generate SHA-256 hash of input data and encode as base64"""
    hash_obj = hashlib.sha256(request.encode())
    return base64.b64encode(hash_obj.digest()).decode()

def sign_data(data, private_key_pem):
    """Sign data using RSA private key with SHA-256"""
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
        )
        
        signature = private_key.sign(
            data.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode()
    except Exception as e:
        print(f"Signing Error: {e}")
        return None

def run(signature_input):
    """Process input: hash and sign it"""
    hash_value = get_hash(signature_input)
    print(f"Hash: {hash_value}")
    
    private_key = """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCjW1I0Em+ShlNi
9OHNkNU1oEDK/jZRyda1vVb+VUp7z1iI7J6tLGB5XTZe44nVOZmh3UuaIwo7L7+L
Yws3RqaqPBl2QkBBPbSqPFYCwXpvYkK4CWqsygdmAgM48CFQC16Lyvp0rvtmdsKw
RPmBmMW78ZOCTY/LUgJGjwX+m37cT6ZuwM+CB5OFoAxoaC3jdU+0oKl48mj+twX1
9TPgrT64jvcwUIln2Q8jWCza00LyrzrHZES3saj3QPbzDsMYQll8kEgYL6YM9JaK
u8HVGo4xdIB9iPluILk+jg+PPcLjfoCf2dND2RHkyVOo1ioYDLfwu8bsn11Rjjrn
EnplgzufAgMBAAECggEACWWlcu1kka88eMLRgnvEaBNR5tt80HOl8Ep2CKdrY3fo
BehmsFuPKSwdhpPcR/HKTq9mO/WsDv+OKzyFVqavy7ctV8oz3AzqqahS4lGy81lZ
sTCJfGsaxdlzygC2Sd59j9kbUz8Foz1Nscol+DiLl2YsMCC6Ft4e12Q+2gij4ZRz
sw4bPQjwCwks8cUMBJoIclUGDUjZSH29ogR9ZlnyS0hDg47jqSvnLOA4LRaMOZ0a
FU+mTwajt20GIa5Vim7iyt2YVPUntoqaJfGw9Eev1TM/kbgyCVVRZKZdCx6SPcpA
OBm0iz6RW6mK7GHGr85TYAbhUiuLHHAxCqetCcnvMQKBgQDmPLTEXj2ILRp1lvzU
LW71Idah4kjGo57zaS4ibbfYdUPdtBYnutq44lZBTAO/mEfzb8/PTbEGyMvx1I6i
Kbz32SHftUuB3WkMH9QVX5btHHh2C011byrLVH/yUhoLZ4KgMKEs/5hWWd6FtNV2
EbF7gEF8RzuDFP/oMKVqUq2pbQKBgQC1osgee6VNfJB0h6z16k7N/HwMl7AdTs07
t2nOkusIvimi76NqOkO2N9BHRqWYQbtdc3Bb+M8mDC7WN5fytF2kVma4nKUUlppM
C05ri1X9XzLa+6/rpnT/TM4IfsLtpceW8BvzNLH01qMxgZqjWURXCLPIeD4ledpp
VdEsw/+9uwKBgQCZiEvnUwznXWRym+A3waBneUw+ob50MDJUEYTBUrcxcmlyU6Ae
mF04wz5PxtgNEQiSDrLeg+mUI5zUxDDldL3d7X7IRoZ2sGZXvnXYVuk3by/pT/o0
YJCCDPRRbGyPxFP4bNVeQ4ebtcxND1z1ojDfsZR5wqqt6/gHJ0F3mHDUNQKBgQCA
2CTvArTC3561Gt1FYF1gXz87y4phb9nEB5plr/BLtmFgtG8OVqBbrQHw3ZtwAwi/
BLlqdHe1PKUozizaPLnEbonVYUD09tQjJ04Mmb14y0QO9MTY+644v6nTeuAZpiSL
3G1nOzUVQgBniNFCGHuS5Zhql2k2OlcFq5uDDtHmKwKBgQCdY737x7Gl375TGAOJ
QMo9CaoNTHWlpyBvvsqDHiWq2osZh7L1SjtYPMrGminPeUdiw7l7dxZ/kmRqI+CF
xc+alpkRxSqYfeeQMVC1P1BghiX6BnaTOYwjWEPjDbtuAiafnIVM3YsOK0pV74ft
jKpjBBXB4mnyFQIqTub8us2X0g==
-----END PRIVATE KEY-----"""
    
    signature = sign_data(signature_input, private_key)
    print(f"Signature: {signature}")
    
    return {
        "hash": hash_value,
        "signature": signature
    }

