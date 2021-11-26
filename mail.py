# -*- coding: utf-8 -*-
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

sender_email = "*******.ru"
receiver_email = "******@yandex.ru"

msg = MIMEMultipart()
msg['Subject'] = "Тема ..."
msg['From'] = sender_email
msg['To'] = receiver_email

plain_text = MIMEText('Текст\n1\n2\n3', _subtype='plain', _charset='UTF-8')
msg.attach(plain_text)
server = smtplib.SMTP('localhost')
server.sendmail(sender_email, receiver_email, msg.as_string())
server.quit()

