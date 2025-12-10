import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django_server import settings
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def send_html_email(receiver: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_SENDER_MAIL
    msg['To'] = receiver
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        logger.info(f"Sending email to {receiver} with subject: {subject}")
        with smtplib.SMTP(settings.SMTP_SERVER_ADDRESS, 587) as server:
            server.starttls()
            server.login(settings.SMTP_SENDER_MAIL, settings.SMTP_SENDER_PASSWORD)
            text = msg.as_string()

            server.sendmail(settings.SMTP_SENDER_MAIL, receiver, text)
        logger.info(f"Email successfully sent to {receiver}")
    except Exception as e:
        logger.error(f"Failed to send email to {receiver}. Error: {e}")
