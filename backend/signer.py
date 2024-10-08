import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pyperclip
import re
import datetime
import os
from uuid import uuid4
from bs4 import BeautifulSoup
import base64
from pathlib import Path
import sys
from enum import Enum
from dotenv import load_dotenv

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))
sys.path.append(os.path.join(path_root, 'backend'))

from rsa import RSA

load_dotenv()
use_encryption = True
ENV = os.getenv('ENV') or 'dev'


def convert_links_to_images(html_content):
    print("Converting links to images...")
    soup = BeautifulSoup(html_content, 'html.parser')
    links_to_convert = soup.find_all('a', class_='convert-to-image')

    for link in links_to_convert:
        sub_soup = BeautifulSoup(str(link), 'html.parser')
        svg_tags = sub_soup.find_all('svg')
        for svg_tag in svg_tags:
            if 'id' not in svg_tag.attrs:
                print("Invalid <svg> tag.")
                continue
            svg_id = svg_tag['id']
            print(f"Converting {svg_id} to image...")

            img_path = f'assets/{svg_id}-base64.txt'

            if os.path.exists(img_path):
                with open(img_path, 'r') as f:
                    base64_string = f.read()
            else:
                print(f"No image found for {svg_id}. In {img_path}")
                continue

            img_tag = f'<img src="{base64_string}">'
            svg_tag.replace_with(BeautifulSoup(img_tag, 'html.parser'))

    return str(soup)


def clean_up_html(html_content):
    print("Cleaning up HTML content...")
    remove_strings = [
        '<link rel="stylesheet" href="txt-styles.css">',
        '<meta charset="utf-8">',
    ]
    for remove_string in remove_strings:
        html_content = html_content.replace(remove_string, "")

    return html_content


def create_fields(name: str, email: str, role: str, **kwargs):
    fields = {
        'main_name': name,
        'email': email,
        'main_role': role
    }
    for key, value in kwargs.items():
        fields[key] = value
    return fields


def fill_template_str(template, start_tag='{{', end_tag='}}', **kwargs):
    content = template
    for key, value in kwargs.items():
        content = content.replace(f"{start_tag} {key} {end_tag}", value)
    return content


def fill_template_file(template, start_tag='{{', end_tag='}}', **kwargs):
    with open(template, 'r') as f:
        content = f.read()

    return fill_template_str(content, start_tag, end_tag, **kwargs)


def substitute_css_colors(css_string: str):
    """
    Substitute CSS color values with the corresponding hex values. From the :root object on the top of the CSS file.

    :param css_string: The CSS string.
    """

    # Get the color values from the :root object
    root_values = re.findall(r":root {.*}", css_string, re.DOTALL)[0]
    color_values = re.findall(r"--.*:.*;", root_values)
    color_dict = {}
    for color in color_values:
        color_name, color_value = color.split(':')
        color_dict[color_name] = color_value

    # Substitute the color values in the CSS string
    for color_name, color_value in color_dict.items():
        css_string = css_string.replace(f'var({color_name})', color_value)
    return css_string


def combine_template_with_styles(template: str, styles: list):
    """
    Combine the email template with the styles.

    :param template: The email template string.
    :param styles: A list of style.css file paths.
    """
    styles_str = ""
    for style in styles:
        with open(style, 'r') as f:
            styles_str += f"{f.read()}\n"

    styles_str = substitute_css_colors(styles_str)
    styles_str = f"<style>\n{styles_str}\n</style>"
    obj = {
        'STYLES': styles_str
    }
    return fill_template_str(template, **obj, start_tag='<!--', end_tag='-->')


class SMTPConfig:
    def __init__(self, smtp_server: str = 'smtp.gmail.com', smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def get_smtp_server(self):
        print("Connecting to SMTP server...")
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.starttls()
        print("Connected to SMTP server successfully.")
        return server


class SignatureType(Enum):
    COMPLEX = 1
    SIMPLE = 2


def is_message_body_base64(message_body: str):
    return message_body.startswith("base64:")


def obfuscate_email_in_str(data: str, email: str):
    """
    Obfuscate the email address by adding the &#173; entity before the domain (.com, .org, etc.).
    """
    formatted_email = email.replace('@', '&#173;@')
    formatted_email = formatted_email.replace('.', '&#173;.')
    return data.replace(email, formatted_email)


def atou(b64: str, has_prefix=True):
    formatted = b64.replace("base64:", "") if has_prefix else b64
    decoded_bytes = base64.b64decode(formatted)
    decoded_string = urllib.parse.unquote(decoded_bytes.decode('utf-8'))
    return decoded_string


class EmailConfig:
    def __init__(
            self,
            subject: str,
            message_body: str,
            recipients: list[str] = None,
            cc: list[str] = None,
            bcc: list[str] = None,
            reply_to: str = None,
    ):
        self.subject = subject
        self.recipients = recipients
        self.cc = cc
        self.bcc = bcc
        self.reply_to = reply_to
        self.message_body = atou(message_body, is_message_body_base64(message_body))

    def is_valid(self):
        return self.subject and self.message_body and (self.recipients or self.cc or self.bcc)

    def get_recipients_string(self):
        return ','.join(self.recipients) if self.recipients else None

    def get_cc_string(self):
        return ','.join(self.cc) if self.cc else None

    def get_bcc_string(self):
        return ','.join(self.bcc) if self.bcc else None

    def combine_recipients(self):
        all_recipients = []
        if self.recipients:
            all_recipients += self.recipients
        if self.cc:
            all_recipients += self.cc
        if self.bcc:
            all_recipients += self.bcc
        return all_recipients


class SignerResponse:
    def __init__(self, success: bool, response: str | None, error: str):
        self.success = success
        self.response = response
        self.error = error


class UserConfig:
    def __init__(self, name: str, email: str, password: str, role: str, latin_name: str, latin_role: str, **kwargs):
        self.name = name
        self.email = email
        self.password = password
        self.latin_name = latin_name
        self.role = role
        self.latin_role = latin_role
        self.__dict__.update(kwargs)


class Signature:
    def __init__(self, content: str, signed_content: str, rsa_signature: str, email: str):
        self.content = content
        self.signed_content = signed_content
        self.rsa_signature = rsa_signature
        self.email = email


class Signer:
    def __init__(
            self,
            user: UserConfig,
            smtp_config: SMTPConfig,
            signature_file: str,
            verify_url: str,
            signature_type: SignatureType = SignatureType.SIMPLE,
    ):
        self.__smtp_config = smtp_config
        self.__signature_file = signature_file
        self.__signature_type = signature_type
        self.__user = user
        self.__rsa = RSA(user.email)
        self.__verify_url = verify_url

    def inject_rsa_signature(self, funny_quote: str = ""):
        """
        Returns the encrypted contents of the email and the formatting object.
        """

        if use_encryption:
            mail_id = str(uuid4())
            end = f'-{funny_quote}' if funny_quote else ''
            formatted_date_ja = datetime.datetime.now().strftime('%Y年%m月%d日-%H:%M:%S')
            data = obfuscate_email_in_str(f"{str(mail_id)}-{formatted_date_ja}{end}", self.__user.email)
            signature = self.__rsa.create_signed_message(data)
            return {
                'verified_title': signature,
                'verified_href': mail_id,
                'verified': '.verified',
                'sig_message': data,
            }
        else:
            return {
                'verified_title': '',
                'verified_href': '',
                'verified': '.not-verified',
            }

    def __generate_complex_signature(self, body: str) -> Signature:
        verifications = self.inject_rsa_signature()

        obj = {
            'EMAIL_CONTENT': body,
        }
        all_fields = create_fields(self.__user.name, self.__user.email, self.__user.role)
        all_fields.update(verifications)
        all_fields.update(obj)
        template = fill_template_file(self.__signature_file, **all_fields)
        template = convert_links_to_images(template)
        template = combine_template_with_styles(template, [os.path.join('backend', 'styles.css')])

        return Signature(template, verifications['data'], verifications['verified_title'], self.__user.email)

    def __generate_simple_signature(self, body: str, subject: str) -> Signature:
        verifications = self.inject_rsa_signature()
        simple_template = os.path.join('backend', 'sig-simple.html')
        with open(simple_template, 'r') as f:
            simple_template_content = f.read()

        email_structure = {
            'EMAIL_CONTENT': body,
            'SIGNATURE': simple_template_content
        }

        template = fill_template_file(self.__signature_file, **email_structure, start_tag='<!--', end_tag='-->')

        misc_fields = {
            "latin_name": self.__user.latin_name,
            "latin_role": self.__user.latin_role,
            'signature': verifications['verified_title'],
            'sig_message': verifications['sig_message'],
            'verify_url': self.__verify_url,
            'subject': subject
        }
        all_fields = create_fields(self.__user.name, self.__user.email, self.__user.role)
        all_fields.update(verifications)
        all_fields.update(misc_fields)
        text_signature = fill_template_str(template, **all_fields)
        text_signature = combine_template_with_styles(text_signature, [os.path.join('backend', 'txt-styles.css')])

        return Signature(text_signature, verifications['sig_message'], verifications['verified_title'],
                         self.__user.email)

    def send_email(self, email: EmailConfig) -> SignerResponse:
        if self.__signature_type == SignatureType.COMPLEX:
            signature = self.__generate_complex_signature(email.message_body)
        else:
            signature = self.__generate_simple_signature(email.message_body, email.subject)

        html_content = clean_up_html(signature.content)
        if ENV == 'dev':
            pyperclip.copy(html_content)
            # Test back the verification
            print(f"Verification: {signature.signed_content}")
            rsa = RSA(signature.email)
            print(f"Verification result: {rsa.verify(signature.rsa_signature, signature.signed_content)}")
            print("Stopping execution because the environment is dev.")
            return SignerResponse(True, "Email sent successfully!", "")

        try:
            server = self.__smtp_config.get_smtp_server()
        except Exception as e:
            print(f"Failed to connect to SMTP server. Error: {str(e)}")
            return SignerResponse(False, None, str(e))

        try:
            server.login(self.__user.email, self.__user.password)
            msg = MIMEMultipart('alternative')
            msg['From'] = self.__user.email
            msg['Subject'] = email.subject

            if email.recipients:
                msg['To'] = email.get_recipients_string()
            else:
                msg['To'] = ""

            if email.cc:
                msg['Cc'] = email.get_cc_string()
            else:
                msg['Cc'] = ""

            if email.bcc:
                msg['Bcc'] = email.get_bcc_string()
            else:
                msg['Bcc'] = ""

            if email.reply_to:
                msg.add_header('In-Reply-To', email.reply_to)
                msg.add_header('References', email.reply_to)

            msg.attach(MIMEText(html_content, 'html'))
            print("Sending email...")
            recipients = email.combine_recipients()
            if ENV == 'test' or ENV == 'prod':
                server.sendmail(self.__user.email, recipients, msg.as_string())
            else:
                print(f"Recipients: {recipients}")
                print("Email not sent because the environment is not prod or test.")
            print("Email sent successfully!")
            return SignerResponse(True, "Email sent successfully!", "")
        except Exception as e:
            print(f"Failed to send email. Error: {str(e)}")
            return SignerResponse(False, None, str(e))
        finally:
            # Close the connection to the SMTP server
            server.quit()
