import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText 
import pyperclip
import re
import datetime
import sys
import os
from pathlib import Path
from uuid import uuid4
import base64
from io import BytesIO
from bs4 import BeautifulSoup
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

use_encryption = True

path_root = Path(__file__).parents[1]
sys.path.append(os.path.join(path_root))

from rsa import RSA
rsa = RSA()

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
            # Replace the <svg> tag with the <img> tag
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

def inject_rsa_signature(email: str, funny_quote: str = ""):
    """
    Returns the encrypted contents of the email and the formatting object.
    """

    if use_encryption:
        id = str(uuid4())
        data = f"{email} {datetime.datetime.now()} {funny_quote}"
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

    

def get_smtp_server(smtp_server: str = 'smtp.gmail.com', smtp_port: int = 587):
    print("Connecting to SMTP server...")
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    print("Connected to SMTP server successfully.")
    return server

def send_email(sender_email, sender_password, recipient_email, subject, message_body, signature_file):
    try:
        server = get_smtp_server()
    except Exception as e:
        print(f"Failed to connect to SMTP server. Error: {str(e)}")
        return
    
    try:
        server.login(sender_email, sender_password)
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        with open(signature_file, 'r') as f:
            html_signature = f.read()

        verifications = inject_rsa_signature(sender_email, "I'm a developer.")
        all_fields = create_fields('Joshua Hegedus', 'josh.hegedus@outlook.com', 'Developer')
        all_fields.update(verifications)
        html_signature = fill_template(signature_file, **all_fields)
        html_signature = convert_links_to_images(html_signature)
        html_signature = combine_template_with_styles(html_signature, ['styles.css'])

        pyperclip.copy(html_signature)
        message_body = f"{message_body}<br><br>Public key: <br>{rsa.get_public_key()}"
        if verifications['data'] != '':
            message_body = f'{message_body}<br><br>PS: {verifications["data"]}'
        print(f"Public key: {rsa.get_public_key()}")
        complete_message = message_body + '<br><br>--<br>' + html_signature
        msg.attach(MIMEText(complete_message, 'html'))

        print("Sending email...")
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email. Error: {str(e)}")
    finally:
        # Close the connection to the SMTP server
        server.quit()

sender_email = 'jhegedus9@gmail.com'
sender_password = 'gczq ving zqnm byas '
recipient_email = 'josh.hegedus@outlook.com'
subject = 'Test Email with HTML Signature'
message_body = 'This is a test email with an HTML signature.<br>'
signature_file = 'signature.html'  # File containing the HTML signature

# Send email
send_email(sender_email, sender_password, recipient_email, subject, message_body, signature_file)
