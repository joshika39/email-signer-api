from pathlib import Path
import sys
import os

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))

from signer import Signer, SMTPConfig, SignatureType

sender_email = 'jhegedus9@gmail.com'
sender_password = 'gczq ving zqnm byas '
recipient_email = 'josh.hegedus@outlook.com'
subject = 'Test Email with HTML Signature'
message_body = 'This is a test email with an HTML signature.<br>'
signature_file = 'signature.html'  # File containing the HTML signature

smp_config = SMTPConfig('smtp.gmail.com', 587)
signer = Signer(sender_email, sender_password, smp_config, 'signature.txt.html', SignatureType.TEXT)

signer.send_email(recipient_email, subject, message_body)
