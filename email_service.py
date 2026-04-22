import smtplib
from email.mime.text import MIMEText
import os

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_email_otp(to_email, otp):
    msg = MIMEText(f"Your OTP is: {otp}")
    msg['Subject'] = "Your OTP Code"
    msg['From'] = EMAIL
    msg['To'] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)