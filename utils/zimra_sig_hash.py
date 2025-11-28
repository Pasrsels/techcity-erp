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
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCl2YE9kDPVh1OW
eHY6M6Hi2yU2zQmf2yM2z0ybl2iUQKXceYdfxBOL1kZmtoELKKIbESdgWYldtYuO
gvUwe4m7stnUtpdD36U2+UbYPhajUrz/lijxCC6fh8OdULDBsMHYKKIFovDBM6+r
aVW6G9+LeyGhwITzvf4CuatAJjEp2Zwrie+w52Q/ArtNfJ8pjLP6x8rx4OpFe2nN
VJoHODxSRHp//CweJjliDzxW/tePY1sXVYk9bIV1Z03VNFeLsAyI4KNnlocf16m2
Yy3uLhzx4YW/UyYHrh2RwRNpyVNPUSFgS3o2HwPos8OCfLS5bvSeZfjP7sT2UbKt
2CpfbByvAgMBAAECggEADnSSQ1uTFlc+DbKV2hsk+Yu7RyGrkeonkWqTv/NRngEH
09sogEwr80zBBHPUyd8H82RVMnHWELu28bwardf0AyRNazEM/Hv86k6OLQvgV5Tp
vJHfI1RgvUPij2QjO9vxpqsH+tt0W4qV6FKn3QRP7C2BGsLtHlI0K72jc6sV2ZKm
KJBowS073WIN/VuqCi3+8RScdBA8XsZgPImCYSh2iBs/SXN6Kzm+8C0rN3KcsQbX
y3zIav1kSD4yvQXHyytrCmKUCqHJkx4SvxLAj2505e2Eq/vkFSr3El9Ts96HYDEN
ZmIhmf4gQgBqzcLZFLOniuFIg1A8ngUX4NY5H1f5aQKBgQDcbYWq8HCf2NUzif9Q
hdGJ60UlfLVzCLujFO45qUCswCtqmsb/TKHip6OycXRMJadfi/WH6Yej6LL4WzAA
1KwBHRghSKtqB3nF2nxtidigEuM2gNvLjFDOLM875V2f7qncPKiGS7puo2WcWFwE
BDx7D3Wsmigv8XcIVDq4BB4TlwKBgQDAnTU3aFUjTtq61/LnMeNI4EVws2G4IZvu
DuozZqk6UaOcJ65ryqgHIyqp9xZMiVu9S1YHvyYVoqxEin5h84BTnU7IPAMWuHXE
vBi5OlzHMnfVM2azekOr+GdD+N+wqAEyr2NnTEMfrHU0VxJsWk5VFWOMZeewk7//
I4Y39SYCqQKBgC4kgyG4eWsMwfyq+5ZInQeJB42EYJt3DYhi/kd1xcMj6zLCubuB
uDWxMBRPqa+zBil7K+fKnAlU0fopZJAX9PW6uG1nP/LPI8+mH/vyKjXAHm4vZVNj
yRqPyMXaCtJK7KXc0M5kFd/JNqEW4hQ5Ksv7/X8nOhhnLKrCrxQMUJt7AoGAaazW
qZOAQmLc9m3MQrPIMw94iaChGFi4KB/etly4s9penSnYNCN3lJLisWVywoMJ5g0T
IiTpTC13vhMNy8fAvB8uPgVO3IRPeKSKG/W9OTyjKkGNMyL9Rbh/T3eXomBKZ/h5
3Q6mNRZ1J0YuQWw6VcvqVfkC6InnaJ+g38qMFCECgYEAlrjpOCWc9UD0CxjsCaaT
2RLoArv1J176qoVqnJCJV+fJdPNRLyhuqgIFp4oWhs3ldBJ0gOQ0tHJII0vSk72q
4sBfJfEvx5KeEFCnHgrsI8hXzr5/NkoM3E91wJntxSk4FgtO5k+VOkA2b24CPUF5
30c5hnvctiIPLki3ixRi8aA=
-----END PRIVATE KEY-----"""
    
    signature = sign_data(signature_input, private_key)
    print(f"Signature: {signature}")
    
    return {
        "hash": hash_value,
        "signature": signature
    }

