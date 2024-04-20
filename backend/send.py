import os
from pathlib import Path
import sys
from dotenv import load_dotenv
import base64

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))
sys.path.append(os.path.join(path_root, 'backend'))

from signer import Signer, SignatureType, SMTPConfig, UserConfig, EmailConfig

load_dotenv()

PASSWORD = os.getenv('PASS')
SELF_URL = os.getenv('SELF_URL')
FRONTEND_URL = os.getenv('FRONTEND_URL')

if not SELF_URL:
    raise ValueError('SELF_URL not found in .env file')

print(f'Password: {PASSWORD}')


def convert_to_base64(message: str):
    return f'base64:{base64.b64encode(message.encode()).decode("utf-8")}'


user_config = UserConfig(
    'ヘゲディス・ジョシュア',
    'josh.hegedus@outlook.com',
    PASSWORD,
    '開発者',
    'Joshua Hegedus',
    'Developer',
)


email = EmailConfig(
    "My subject",
    convert_to_base64("My message"),
    ["josh.hegedus@outlook.com"]
)

signer = Signer(
    user_config,
    SMTPConfig(smtp_server='smtp.office365.com'),
    os.path.join('backend', 'email.html'),
    FRONTEND_URL,
    SignatureType.SIMPLE
)

signer.send_email(email)

