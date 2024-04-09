import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText 
import pyperclip
import re
import datetime
import os
from uuid import uuid4
from bs4 import BeautifulSoup
from pathlib import Path
import sys
from enum import Enum

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))

from rsa import RSA
rsa = RSA()

use_encryption = True

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
            base64_string = ""
            if os.path.exists(img_path):
                with open(img_path, 'r') as f:
                    base64_string = f.read()
            else:
                print(f"No image found for {svg_id}. In {img_path}")
                continue

            img_tag = f'<img src="{base64_string}">'
            svg_tag.replace_with(BeautifulSoup(img_tag, 'html.parser'))

    return str(soup)

def create_fields(name: str, email: str, role: str, **kwargs):
    fields = {
        'name': name,
        'email': email,
        'role': role
    }
    for key, value in kwargs.items():
        fields[key] = value
    return fields

def fill_template(template, **kwargs):
    with open(template, 'r') as f:
        content = f.read()
    for key, value in kwargs.items():
        content = content.replace(f"{{{{ {key} }}}}", value)
    
    return content

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
    return template.replace("<!-- STYLES -->", styles_str)


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
    HTML = 1
    TEXT = 2

class Signer:
    def __init__(self, sender_email: str, sender_password: str, smtp_config: SMTPConfig, signature_file: str, signature_type: SignatureType = SignatureType.HTML):
        self.__sender_email = sender_email
        self.__sender_password = sender_password
        self.__smtp_config = smtp_config
        self.__signature_file = signature_file
        self.__signature_type = signature_type

    def inject_rsa_signature(self, funny_quote: str = ""):
        """
        Returns the encrypted contents of the email and the formatting object.
        """

        if use_encryption:
            id = str(uuid4())
            data = f"{self.__sender_email} {datetime.datetime.now()} {funny_quote}"
            signature = rsa.create_signed_message(data)
            return {
                'verified_title': signature,
                'verified_href': id,
                'verified': '.verified',
                'data': data
            }
        else:
            return {
                'verified_title': '',
                'verified_href': '',
                'verified': '.not-verified',
                'data': ''
            }

    def __generate_html_signature(self, signature_file: str):
        with open(signature_file, 'r') as f:
            html_signature = f.read()

        verifications = self.inject_rsa_signature("I'm a developer.")
        all_fields = create_fields('Joshua Hegedus', 'josh.hegedus@outlook.com', 'Developer')
        all_fields.update(verifications)
        html_signature = fill_template(self.__signature_file, **all_fields)
        html_signature = convert_links_to_images(html_signature)
        html_signature = combine_template_with_styles(html_signature, ['styles.css'])

        pyperclip.copy(html_signature)
        return html_signature

    def __generate_text_signature(self, signature_file: str):
        with open(signature_file, 'r') as f:
            text_signature = f.read()

        # Replace '\n' with '<br>
        # text_signature = text_signature.replace('\n', '<br>\n')
        verifications = self.inject_rsa_signature("I'm a developer.")
        misc_fields = {
            "jp_name": "ヘゲティス・ジョシュア",
            "jp_role": "開発者",
        }
        all_fields = create_fields('Joshua Hegedus', 'josh.hegedus@outlook.com', 'Developer')
        all_fields.update(verifications)
        all_fields.update(misc_fields)
        text_signature = fill_template(self.__signature_file, **all_fields)
        text_signature = combine_template_with_styles(text_signature, ['txt-styles.css'])

        pyperclip.copy(text_signature)
        print(text_signature)
        return text_signature

    def send_email(self, recipient_email, subject, message_body):
        try:
            server = self.__smtp_config.get_smtp_server()
        except Exception as e:
            print(f"Failed to connect to SMTP server. Error: {str(e)}")
            return
        
        try:
            server.login(self.__sender_email, self.__sender_password)
            msg = MIMEMultipart('alternative')
            msg['From'] = self.__sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            if self.__signature_type == SignatureType.HTML:
                signature = self.__generate_html_signature(self.__signature_file)
            else:
                signature = self.__generate_text_signature(self.__signature_file)

            message_body = f'{message_body}<br><br>--<br>{signature}'

            msg.attach(MIMEText(message_body, 'html'))

            print("Sending email...")
            server.sendmail(self.__sender_email, recipient_email, msg.as_string())
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email. Error: {str(e)}")
        finally:
            # Close the connection to the SMTP server
            server.quit()
