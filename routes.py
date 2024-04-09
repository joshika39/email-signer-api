from typing import Optional

from fastapi import APIRouter
from pathlib import Path
import sys
import os
from pydantic import BaseModel
import base64
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")
SELF_URL = os.getenv('SELF_URL')

if not SELF_URL:
    raise ValueError('SELF_URL not found in .env file')

if ENV == "development":
    path_root = Path(__file__).parents[1]
    sys.path.append(os.path.join(path_root))
    sys.path.append(os.path.join(path_root, 'backend'))
else:
    print("Production")
    print(os.getcwd())
    print(os.path.dirname(__file__))
    print(os.listdir('/'))
    sys.path.append('/')
    sys.path.append('/backend')


from backend.signer import Signer, SignatureType, SMTPConfig, UserConfig, EmailConfig
from backend.rsa import RSA, verify_by_base64_key

router = APIRouter()


class EmailVerifyModel(BaseModel):
    email: str
    ps_message: str
    ps_signature: str


class KeyVerifyModel(BaseModel):
    base64_key: str
    ps_message: str
    ps_signature: str


class SendModel(BaseModel):
    name: str
    role: str
    email: str
    latin_name: str
    latin_role: str
    password: str
    recipients: Optional[str | list[str]] = None
    cc: Optional[str | list[str]] = None
    bcc: Optional[str | list[str]] = None
    subject: str
    message_body: str


def convert_recipients(recipients):
    if isinstance(recipients, str):
        return [recipients]
    elif isinstance(recipients, list):
        return recipients
    return None


def verify_by_email(email: str, ps_message: str, ps_signature: str) -> bool:
    rsa = RSA(email)
    return rsa.verify(ps_signature, ps_message)


@router.get("/")
def read_root():
    return { "message": "Hello World" }


@router.get("/key")
def get_public_key(user_email: str):
    rsa = RSA(user_email)
    key_str = rsa.get_public_key()
    base64_str = base64.b64encode(key_str).decode()
    return {"public_key": base64_str}


@router.post("/verify/email")
def verify_email(verify_model: EmailVerifyModel):
    result = verify_by_email(verify_model.email, verify_model.ps_message, verify_model.ps_signature)
    if result:
        return {"verified": True}

    return {"verified": False}


@router.get("/verify/email")
def verify_email_get_japanese(email: str, ps_message: str, ps_signature: str):
    try:
        result = verify_by_email(email, ps_message, ps_signature)
        if result:
            return {
                "email": email,
                "ps_message": ps_message,
                "signature": {
                    'status': 'valid',
                    "ps": ps_signature,
                },
                "comment": {
                    "jp": "この電子メールは正しいです。",
                    "en": "This email is valid."
                }
            }

        return {
            "email": email,
            "ps_message": ps_message,
            "signature": {
                'status': 'invalid',
                "ps": ps_signature,
            },
            "comment": {
                "jp": "この電子メールは無効です。",
                "en": "This email is invalid."
            }
        }
    except Exception as e:
        return {
            "email": email,
            "ps_message": ps_message,
            "signature": {
                'status': 'error',
                "ps": ps_signature,
            },
            "comment": {
                "jp": "エラーが発生しました。" + str(e),
                "en": "An error occurred: " + str(e)
            }
        }



@router.post("/verify/key")
def verify_key(verify_model: KeyVerifyModel):
    result = verify_by_base64_key(verify_model.base64_key, verify_model.ps_message, verify_model.ps_signature)
    if result:
        return {"verified": True}

    return {"verified": False}


@router.post("/send/{provider}")
def send_email(provider: str, send_model: SendModel):
    if provider not in ['gmail', 'outlook']:
        return {"error": "Invalid provider"}
    server = 'smtp.gmail.com' if provider == 'gmail' else 'smtp.office365.com'
    user_config = UserConfig(
        send_model.name,
        send_model.email,
        send_model.password,
        send_model.role,
        send_model.latin_name,
        send_model.latin_role
    )

    recipients = convert_recipients(send_model.recipients)
    cc = convert_recipients(send_model.cc)
    bcc = convert_recipients(send_model.bcc)
    subject = send_model.subject
    message_body = send_model.message_body
    email_config = EmailConfig(
        subject,
        message_body,
        [recipients] if isinstance(recipients, str) else recipients,
        [cc] if isinstance(cc, str) else cc,
        [bcc] if isinstance(bcc, str) else bcc
    )

    if not email_config.is_valid():
        return {"error": "Invalid email configuration"}

    smp_config = SMTPConfig(server, 587)
    signer = Signer(
        user_config,
        smp_config,
        os.path.join('backend', 'email.html'),
        SELF_URL,
        SignatureType.SIMPLE
    )

    result = signer.send_email(email_config)
    if result is None:
        return {"sent": True}

    return {"sent": False, "error": result}
