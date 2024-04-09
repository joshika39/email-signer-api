from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import os
import base64


def get_secret_key_path(email: str):
    sender_email = email.replace("@", "").replace(".", "")
    filename = f"{sender_email}.pem"
    secret_key_path = os.path.join("keys", "private", filename)
    if not os.path.exists(secret_key_path):
        os.makedirs(os.path.dirname(secret_key_path), exist_ok=True)
    return secret_key_path


def verify_by_base64_key(base64_key: str, ps_message: str, ps_signature: str) -> bool:
    public_key = serialization.load_pem_public_key(
        base64.b64decode(base64_key),
        backend=default_backend()
    )
    signature = bytes.fromhex(ps_signature)
    message = ps_message.encode()
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except:
        return False


class RSA:
    def __init__(self, sender_email: str):
        private_key_path = get_secret_key_path(sender_email)
        if os.path.exists(private_key_path):
            print("Loading private key from file")
            with open(private_key_path, "rb") as f:
                private_key_pem = f.read()

            self.__private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend()
            )
        else:
            print("Generating new private key")
            self.__private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            private_key_pem = self.__private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(private_key_path, "wb") as f:
                f.write(private_key_pem)

        self.__public_key = self.__private_key.public_key()

    def sign(self, message: str):
        b_message = message.encode()
        return self.__private_key.sign(
            b_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    def verify_raw(self, signature: bytes, message: bytes):
        return self.__public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    def verify(self, signature_str: str, message: str) -> bool:
        b_message = message.encode()
        signature = bytes.fromhex(signature_str)
        try:
            self.verify_raw(signature, b_message)
            return True
        except:
            return False

    # Use the private key to encrypt the message, so that only the public key can decrypt it
    def encrypt(self, message: str) -> str:
        b_message = message.encode()
        encrypted = self.__public_key.encrypt(
            b_message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        b64_encrypted = encrypted.hex()
        return b64_encrypted

    def create_signed_message(self, message: str) -> str:
        signature = self.sign(message)

        signature_base64 = signature.hex()
        signed_message = f"{signature_base64}"

        return signed_message

    def __get_public_key(self):
        return self.__public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def get_public_key(self):
        return self.__get_public_key().decode('utf-8')
