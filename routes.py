from fastapi import APIRouter
from pathlib import Path
import sys
import os
from pydantic import BaseModel

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))
sys.path.append(os.path.join(path_root, 'email'))

from email.signer import Signer, SignatureType, SMTPConfig
from email.rsa import RSA

router = APIRouter()


class VerifyModel(BaseModel):
    email: str
    ps_message: str
    ps_signature: str


class SendModel(BaseModel):
    sender_email: str
    sender_password: str
    recipient_email: str
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


@router.post("/send")
def send_email(send_model: SendModel):
    sender_email = send_model.sender_email
    sender_password = send_model.sender_password
    recipient_email = send_model.recipient_email
    subject = send_model.subject
    message_body = send_model.message_body

    smp_config = SMTPConfig('smtp.gmail.com', 587)
    signer = Signer(sender_email, sender_password, smp_config, 'signature.txt.html', SignatureType.TEXT)

    signer.send_email(recipient_email, subject, message_body)
    return {"sent": True}
