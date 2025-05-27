# backend/utils.py
import re
import smtplib # For email sending, if used
from email.mime.text import MIMEText # For email sending
from email.mime.multipart import MIMEMultipart # For email sending
from flask import current_app # For accessing app config

def is_valid_email(email):
    """
    Validates an email address format.
    """
    if not email:
        return False
    # Regex for basic email validation
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def send_email_alert(subject, body, recipient_email=None):
    """
    Sends an email alert.
    Uses configuration from Flask app (current_app.config).
    """
    if not current_app.config.get('MAIL_SERVER'):
        current_app.logger.error("Mail server not configured. Cannot send email alert.")
        return False

    sender_email = current_app.config.get('MAIL_USERNAME')
    sender_password = current_app.config.get('MAIL_PASSWORD') # App Password for Gmail
    mail_recipient = recipient_email or current_app.config.get('ADMIN_ALERT_EMAIL')

    if not sender_email or not sender_password or not mail_recipient:
        current_app.logger.error("Mail credentials or recipient not fully configured. Cannot send email alert.")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = mail_recipient
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Ensure MAIL_USE_TLS and MAIL_USE_SSL are handled if defined in config
        mail_port = current_app.config.get('MAIL_PORT', 587)
        use_tls = current_app.config.get('MAIL_USE_TLS', True) # Default to TLS for port 587
        use_ssl = current_app.config.get('MAIL_USE_SSL', False)

        if use_ssl:
            server = smtplib.SMTP_SSL(current_app.config['MAIL_SERVER'], mail_port)
        else:
            server = smtplib.SMTP(current_app.config['MAIL_SERVER'], mail_port)
        
        if use_tls and not use_ssl: # starttls should not be called if SMTP_SSL is used
            server.starttls()
        
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, mail_recipient, text)
        server.quit()
        current_app.logger.info(f"Email alert '{subject}' sent successfully to {mail_recipient}.")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email alert '{subject}' to {mail_recipient}: {e}", exc_info=True)
        return False

# Add other general utility functions here if needed
