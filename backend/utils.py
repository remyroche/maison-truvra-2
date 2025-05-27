# backend/utils.py
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
import sqlite3
from .database import get_db_connection # Assuming get_db_connection is in database.py

# Consolidated from root utils.py
def format_date_french(date_obj):
    """Formats a date object or ISO string into a French string: 'jour mois année'."""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except ValueError:
            return "Date invalide" # Or handle error as preferred

    if not isinstance(date_obj, (datetime.date, datetime.datetime)):
        return "Format de date non supporté"

    months_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    return f"{date_obj.day} {months_fr[date_obj.month - 1]} {date_obj.year}"

def is_valid_email(email):
    """Validate email format."""
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def send_email_alert(subject, body, recipient_email, html_body=None):
    """
    Sends an email.
    Note: This is a basic implementation. For production, consider using a robust
    library like Flask-Mail and an email service (SendGrid, Mailgun, AWS SES).
    """
    config = current_app.config
    sender_email = config['MAIL_DEFAULT_SENDER']
    password = config['MAIL_PASSWORD']
    
    if not config.get('MAIL_SERVER') or not sender_email or not password:
        current_app.logger.error("Mail server settings are not configured. Email not sent.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email

    # Attach plain text part
    message.attach(MIMEText(body, "plain"))

    # Attach HTML part if provided
    if html_body:
        message.attach(MIMEText(html_body, "html"))
    
    current_app.logger.info(f"Attempting to send email to {recipient_email} with subject: {subject}")
    current_app.logger.debug(f"Mail Server: {config['MAIL_SERVER']}:{config['MAIL_PORT']}, Use TLS: {config['MAIL_USE_TLS']}")
    current_app.logger.debug(f"Mail Username: {config['MAIL_USERNAME']}")


    try:
        context = ssl.create_default_context()
        if config['MAIL_USE_TLS']:
            with smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT']) as server:
                server.starttls(context=context)
                server.login(config['MAIL_USERNAME'] or sender_email, password)
                server.sendmail(sender_email, recipient_email, message.as_string())
        else: # For non-TLS (e.g. local debugging server on port 1025)
             with smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT']) as server:
                server.login(config['MAIL_USERNAME'] or sender_email, password) # Login might not be needed for local debug server
                server.sendmail(sender_email, recipient_email, message.as_string())
        current_app.logger.info(f"Email successfully sent to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        current_app.logger.error(f"SMTP Authentication Error sending email: {e}")
    except smtplib.SMTPServerDisconnected as e:
        current_app.logger.error(f"SMTP Server Disconnected: {e}")
    except smtplib.SMTPConnectError as e:
        current_app.logger.error(f"SMTP Connection Error: {e}")
    except ConnectionRefusedError as e:
        current_app.logger.error(f"Connection Refused Error sending email (is mail server running?): {e}")
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
    return False


# --- JWT Utilities ---
def create_access_token(data: dict):
    """Creates a new access token."""
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=current_app.config['JWT_ACCESS_TOKEN_EXPIRES_MINUTES'])
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")
    return encoded_jwt

# Placeholder for refresh token if you implement that system
# def create_refresh_token(data: dict):
#     """Creates a new refresh token."""
#     to_encode = data.copy()
#     expire = datetime.datetime.utcnow() + datetime.timedelta(days=current_app.config['JWT_REFRESH_TOKEN_EXPIRES_DAYS'])
#     to_encode.update({"exp": expire, "type": "refresh"})
#     encoded_jwt = jwt.encode(to_encode, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")
#     return encoded_jwt

def decode_token(token: str):
    """Decodes a JWT token."""
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        current_app.logger.warning("Token expired.")
        return None # Or raise specific exception
    except jwt.InvalidTokenError:
        current_app.logger.warning("Invalid token.")
        return None # Or raise specific exception

# --- Decorator for JWT protected routes ---
def jwt_required(f):
    """
    A decorator to protect routes with JWT.
    Expects the token to be in the 'Authorization' header as 'Bearer <token>'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]

        if not token:
            current_app.logger.warning("JWT token missing from request.")
            return jsonify({"message": "Token is missing!"}), 401

        payload = decode_token(token)
        if not payload:
            current_app.logger.warning("JWT token is invalid or expired.")
            return jsonify({"message": "Token is invalid or expired!"}), 401
        
        # Optionally, check token type if you use different tokens (access, refresh)
        # if payload.get("type") != "access":
        #     return jsonify({"message": "Invalid token type!"}), 401

        # Make user identity available to the route if needed
        # For example, by querying the database with user_id from payload
        # For now, we'll just pass the payload.
        # You might want to fetch the user object from DB here and attach it to `g` or pass to function
        
        # Example: Get current user from DB based on token
        user_id = payload.get('user_id')
        user_role = payload.get('role') # Assuming role is stored in token

        if not user_id:
            current_app.logger.error("User ID not found in JWT payload.")
            return jsonify({"message": "Invalid token payload (missing user_id)!"}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if it's an admin user based on the 'users' table structure
        # This assumes your 'users' table has an 'id' and 'role' column
        # And admin users have role 'admin'
        cursor.execute("SELECT id, email, role FROM users WHERE id = ? AND role = 'admin'", (user_id,))
        admin_user = cursor.fetchone()
        conn.close()

        if not admin_user:
            current_app.logger.warning(f"Admin access denied for user_id: {user_id}. User not found or not admin.")
            return jsonify({"message": "Admin access required!"}), 403
        
        # You can attach the admin_user object or just the id to the request context if needed
        # For example: g.admin_user = admin_user 
        # Or pass it to the decorated function: return f(admin_user_id=user_id, *args, **kwargs)

        return f(*args, **kwargs) # Pass payload or specific parts if needed by the route
    return decorated_function


def professional_jwt_required(f):
    """
    A decorator to protect routes with JWT for professional users.
    Expects the token to be in the 'Authorization' header as 'Bearer <token>'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"message": "Token is invalid or expired!"}), 401
        
        user_id = payload.get('user_id')
        user_role = payload.get('role')

        if not user_id or user_role not in ['professional', 'admin']: # Admins can also access professional routes
            return jsonify({"message": "Professional access required or invalid token payload!"}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_role == 'professional':
            cursor.execute("SELECT id, email, role FROM users WHERE id = ? AND role = 'professional' AND is_verified = 1 AND account_status = 'approved'", (user_id,))
        elif user_role == 'admin': # If admin, they are allowed
             cursor.execute("SELECT id, email, role FROM users WHERE id = ? AND role = 'admin'", (user_id,))
        
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({"message": "Professional account not found, not verified, not approved, or access denied."}), 403
        
        # Pass user_id to the decorated function
        return f(current_user_id=user_id, *args, **kwargs)
    return decorated_function

def user_jwt_required(f):
    """
    A decorator to protect routes with JWT for general users (B2C or authenticated B2B).
    Expects the token to be in the 'Authorization' header as 'Bearer <token>'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"message": "Token is invalid or expired!"}), 401
        
        user_id = payload.get('user_id')
        # user_role = payload.get('role') # Role check can be more specific if needed

        if not user_id:
            return jsonify({"message": "Invalid token payload (missing user_id)!"}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # General check for an active, verified user
        cursor.execute("SELECT id, email, role, is_verified FROM users WHERE id = ? AND ( (role = 'b2c' AND is_verified = 1) OR (role = 'professional' AND is_verified = 1 AND account_status = 'approved') OR role = 'admin' )", (user_id,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({"message": "User account not found, not verified, or access denied."}), 403
        
        # Pass user_id to the decorated function
        return f(current_user_id=user_id, current_user_role=user['role'], *args, **kwargs)
    return decorated_function
