from email.message import EmailMessage
import mimetypes
import os
import smtplib
from threading import Thread

SENDER = "you@example.com"
SMTP_USERNAME = "you@example.com"  # TODO добавить чтение из конфигурации
SMTP_PASSWORD = "yourpassword"
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587


def send_email_sync(msg: EmailMessage):
    with smtplib.SMTP(host=SMTP_SERVER, port=SMTP_PORT) as server:
        server.starttls()  # шифрование

        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(user=SMTP_USERNAME, password=SMTP_PASSWORD)

        server.send_message(msg)


def send_email_async(msg: EmailMessage):
    Thread(target=send_email_sync, args=(msg, SMTP_SERVER, SMTP_PORT)).start()


def send_email(subject, text_body, recipients=SENDER, attachments=None, sync=False):  # позже можно добавить html_body
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER
    msg['To'] = recipients
    msg['Body'] = text_body
    msg.set_content(text_body)

    attachments = attachments or []
    for path in attachments:
        if not os.path.isfile(path):
            continue
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or 'application/octet-stream'
        maintype, subtype = mime_type.split('/', 1)

        with open(path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(path)
            msg.add_attachment(
                file_data,
                maintype=maintype,
                subtype=subtype,
                filename=file_name
            )

    if sync:
        send_email_sync(msg)
    else:
        send_email_async(msg)

    print("Email sent!")


