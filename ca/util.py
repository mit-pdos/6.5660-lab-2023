from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def gen_key():
    return rsa.generate_private_key(public_exponent = 65537, key_size = 2048)

def key_to_bytes(privkey):
    return privkey.private_bytes(
        encoding = serialization.Encoding.PEM,
        format = serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm = serialization.NoEncryption(),
    )

def key_from_bytes(b):
    return serialization.load_pem_private_key(b, password = None)

def cert_to_bytes(cert):
    return cert.public_bytes(encoding = serialization.Encoding.PEM)
