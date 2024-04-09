from typing import Optional

from fastapi import APIRouter
from pathlib import Path
import sys
import os
from pydantic import BaseModel

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))
sys.path.append(os.path.join(path_root, 'backend'))

from backend.signer import Signer, SignatureType, SMTPConfig, UserConfig, EmailConfig
from backend.rsa import RSA

router = APIRouter()


class VerifyModel(BaseModel):
    email: str
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


@router.get("/")
def read_root():
    return {"Hello": "World"}


@router.post("/verify")
def verify_email(verify_model: VerifyModel):
    rsa = RSA(verify_model.email)
    signature = bytes.fromhex(verify_model.ps_signature)
    message = verify_model.ps_message.encode()
    result = rsa.verify_raw(signature, message)
    if result:
        return {"verified": True}

    return {"verified": False}


def convert_recipients(recipients):
    if isinstance(recipients, str):
        return [recipients]
    elif isinstance(recipients, list):
        return recipients
    return None


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
        os.path.join('backend', 'signature.txt.html'),
        SignatureType.TEXT
    )

    result = signer.send_email(email_config)
    if result is None:
        return {"sent": True}

    return {"sent": False, "error": result}
