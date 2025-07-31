from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
import requests
import base64

# ---- Device Details ----
DEVICE_ID = 23265
ACTIVATION_KEY = "00314405"
DEVICE_SERIAL = "pasales-1"   # Change this to your actual serial number

# ---- Generate ECC Private Key ----
private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

# ---- Build CSR ----
subject = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"ZW"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Zimbabwe Revenue Authority"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Zimbabwe"),
    x509.NameAttribute(NameOID.COMMON_NAME, f"ZIMRA-{DEVICE_SERIAL}-000000{DEVICE_ID:05d}")
])

csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(
    private_key, hashes.SHA256(), default_backend()
)

# ---- Convert CSR to PEM format ----
csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

# ---- Save Private Key (for future use) ----
with open("device_private_key.pem", "wb") as key_file:
    key_file.write(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()
        )
    )

# ---- Prepare JSON payload ----
data = {
    "deviceID": DEVICE_ID,
    "activationKey": ACTIVATION_KEY,
    "certificateRequest": csr_pem
}

# ---- Send Request to FDMS ----
url = "https://fdmsapitest.zimra.co.zw//Public/v1/23265/RegisterDevice"
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=data, headers=headers)

print("Status Code:", response.status_code)
print("Response:", response.json())
