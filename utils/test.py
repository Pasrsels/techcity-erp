from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def load_private_key_from_pem(file_path, password=None):
    """
    Load a private key from a PEM file
    
    :param file_path: Path to the PEM file containing the private key
    :param password: Optional password for encrypted private key
    :return: Loaded private key object
    """
    try:
        with open(file_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=password.encode() if password else None,
                backend=default_backend()
            )
        return private_key
    except Exception as e:
        print(f"Error loading private key: {e}")
        return None

# Example usage in signature generation
def generate_signature_with_loaded_key(file_path, password=None):
    """
    Generate a signature using a private key loaded from a PEM file
    
    :param file_path: Path to the PEM file
    :param password: Optional password for the key
    :return: Signature details
    """
    # Load the private key
    private_key = load_private_key_from_pem(file_path, password)
    
    if private_key is None:
        return None
    
    # Determine key type (RSA or ECC)
    # You might need to adjust this based on your specific key type
    if isinstance(private_key, rsa.RSAPrivateKey):
        key_type = 'rsa'
    elif isinstance(private_key, ec.EllipticCurvePrivateKey):
        key_type = 'ecc'
    else:
        print("Unsupported key type")
        return None
    
    # Example usage with receipt signature
    receipt_taxes = [
        {
            'taxID': 1,
            'taxCode': 'A',
            'salesAmountWithTax': 2500.00,
            'taxPercent': 0,
            'taxAmount': 0.00
        }
    ]
    
    receipt_signature = SignatureGenerator.generate_receipt_device_signature(
        device_id='321',
        receipt_type='FISCALINVOICE',
        receipt_currency='ZWL',
        receipt_global_no='432',
        receipt_date='2019-09-19T15:43:12',
        receipt_total=94500,
        receipt_taxes=receipt_taxes,
        private_key=private_key,
        key_type=key_type
    )
    
    return receipt_signature

# Usage example
def main():
    # Path to your PEM file
    pem_file_path = 'cert_private.pem'
    
    # Optional: If the key is password-protected
    # password = 'your_password_here'
    
    # Generate signature
    signature_result = generate_signature_with_loaded_key(pem_file_path)
    
    if signature_result:
        print("Hash:", signature_result['hash'])
        print("Signature:", signature_result['signature'])
        print("Concatenation Line:", signature_result['concat_line'])

if __name__ == '__main__':
    main()