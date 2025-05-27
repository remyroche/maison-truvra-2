# backend/auth/routes.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import uuid
import datetime
from ..database import get_db_connection, init_db_command # Assuming these are in backend/database.py
from ..utils import is_valid_email, send_email_alert, create_access_token, decode_token, user_jwt_required, professional_jwt_required
from ..audit_log_service import AuditLogService # Assuming this is correctly set up

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
audit_logger = AuditLogService()

# --- Admin Login (Moved here for clarity, or could be in admin_api/routes.py) ---
@auth_bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, role FROM users WHERE email = ? AND role = 'admin'", (email,))
    admin_user = cursor.fetchone()
    conn.close()

    if admin_user and check_password_hash(admin_user['password_hash'], password):
        access_token = create_access_token(data={"user_id": admin_user['id'], "role": "admin"})
        audit_logger.log_event('admin_login_success', user_id=admin_user['id'], details={'email': email})
        return jsonify({"message": "Admin login successful", "access_token": access_token, "user": {"email": email, "role": "admin"}}), 200
    else:
        audit_logger.log_event('admin_login_failed', details={'email': email, 'reason': 'Invalid credentials'})
        return jsonify({"message": "Invalid admin credentials"}), 401

# --- B2C User Registration ---
@auth_bp.route('/register', methods=['POST'])
def register_b2c():
    data = request.get_json()
    required_fields = ['firstName', 'lastName', 'email', 'password', 'addressLine1', 'city', 'postalCode', 'country', 'phone']
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

    if not is_valid_email(data['email']):
        return jsonify({"message": "Invalid email format"}), 400
    
    if len(data['password']) < 8: # Basic password strength
        return jsonify({"message": "Password must be at least 8 characters long"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (data['email'],))
    if cursor.fetchone():
        conn.close()
        return jsonify({"message": "Email already registered"}), 409

    hashed_password = generate_password_hash(data['password'])
    verification_token = str(uuid.uuid4())
    
    try:
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, password_hash, phone_number, role, is_verified, verification_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'b2c', 0, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (data['firstName'], data['lastName'], data['email'], hashed_password, data['phone'], verification_token))
        user_id = cursor.lastrowid

        # Insert address
        cursor.execute("""
            INSERT INTO addresses (user_id, address_line1, address_line2, city, postal_code, country, is_default_shipping, is_default_billing)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1)
        """, (user_id, data['addressLine1'], data.get('addressLine2'), data['city'], data['postalCode'], data['country']))
        
        conn.commit()
        
        # Send verification email
        verification_link = f"{current_app.config['FRONTEND_URL']}/verify-email?token={verification_token}"
        email_subject = "Vérifiez votre adresse e-mail - Maison Trüvra"
        email_body = f"""Bonjour {data['firstName']},

Merci de vous être inscrit sur Maison Trüvra.
Veuillez cliquer sur le lien suivant pour vérifier votre adresse e-mail :
{verification_link}

Si vous n'avez pas créé de compte, veuillez ignorer cet e-mail.

Cordialement,
L'équipe Maison Trüvra
"""
        email_html_body = f"""
        <p>Bonjour {data['firstName']},</p>
        <p>Merci de vous être inscrit sur Maison Trüvra.</p>
        <p>Veuillez cliquer sur le lien suivant pour vérifier votre adresse e-mail :</p>
        <p><a href="{verification_link}">Vérifier mon e-mail</a></p>
        <p>Si vous n'avez pas créé de compte, veuillez ignorer cet e-mail.</p>
        <p>Cordialement,<br>L'équipe Maison Trüvra</p>
        """
        if send_email_alert(email_subject, email_body, data['email'], html_body=email_html_body):
            audit_logger.log_event('b2c_registration_success', user_id=user_id, details={'email': data['email'], 'verification_email_sent': True})
            return jsonify({"message": "Registration successful. Please check your email to verify your account.", "user_id": user_id}), 201
        else:
            audit_logger.log_event('b2c_registration_email_failed', user_id=user_id, details={'email': data['email']})
            # User is created, but email failed. Frontend should inform user to possibly request resend or contact support.
            return jsonify({"message": "Registration successful, but verification email could not be sent. Please contact support.", "user_id": user_id}), 201

    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error during B2C registration: {e}")
        audit_logger.log_event('b2c_registration_failed_db', details={'email': data['email'], 'error': str(e)})
        return jsonify({"message": "Registration failed due to a database error"}), 500
    finally:
        conn.close()


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({"message": "Verification token is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, is_verified FROM users WHERE verification_token = ?", (token,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"message": "Invalid or expired verification token"}), 400
    
    if user['is_verified']:
        conn.close()
        return jsonify({"message": "Email already verified"}), 200

    try:
        cursor.execute("UPDATE users SET is_verified = 1, verification_token = NULL, email_verified_at = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
        conn.commit()
        audit_logger.log_event('email_verification_success', user_id=user['id'])
        return jsonify({"message": "Email verified successfully. You can now log in."}), 200
    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error during email verification: {e}")
        audit_logger.log_event('email_verification_failed_db', user_id=user['id'], details={'error': str(e)})
        return jsonify({"message": "Email verification failed due to a database error"}), 500
    finally:
        conn.close()

# --- B2C User Login ---
@auth_bp.route('/login', methods=['POST'])
def login_b2c():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    # Ensure only B2C users or verified B2B users can log in via this route
    cursor.execute("SELECT id, password_hash, role, is_verified, account_status FROM users WHERE email = ? AND (role = 'b2c' OR role = 'professional')", (email,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        audit_logger.log_event('login_failed', details={'email': email, 'reason': 'User not found'})
        return jsonify({"message": "Invalid credentials or user not found"}), 401

    if not user['is_verified']:
        conn.close()
        audit_logger.log_event('login_failed_unverified', user_id=user['id'], details={'email': email})
        return jsonify({"message": "Account not verified. Please check your email."}), 403
    
    if user['role'] == 'professional' and user['account_status'] != 'approved':
        conn.close()
        audit_logger.log_event('login_failed_b2b_not_approved', user_id=user['id'], details={'email': email, 'status': user['account_status']})
        return jsonify({"message": f"Professional account is {user['account_status']}. Please wait for approval or contact support."}), 403

    if check_password_hash(user['password_hash'], password):
        access_token = create_access_token(data={"user_id": user['id'], "role": user['role']})
        conn.close()
        audit_logger.log_event('login_success', user_id=user['id'], details={'email': email, 'role': user['role']})
        # Return more user info if needed by frontend
        user_info = {"id": user['id'], "email": email, "role": user['role']} 
        return jsonify({"message": "Login successful", "access_token": access_token, "user": user_info}), 200
    else:
        conn.close()
        audit_logger.log_event('login_failed', user_id=user['id'] if user else None, details={'email': email, 'reason': 'Invalid password'})
        return jsonify({"message": "Invalid credentials"}), 401


# --- Get Current User Info (Protected Route) ---
@auth_bp.route('/me', methods=['GET'])
@user_jwt_required # This decorator handles token validation and gets user_id
def get_current_user(current_user_id, current_user_role): # Decorated function receives user_id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch more comprehensive user details
    if current_user_role == 'b2c':
        cursor.execute("""
            SELECT u.id, u.first_name, u.last_name, u.email, u.phone_number, u.role, u.created_at,
                   a.address_line1, a.address_line2, a.city, a.postal_code, a.country
            FROM users u
            LEFT JOIN addresses a ON u.id = a.user_id AND a.is_default_shipping = 1
            WHERE u.id = ?
        """, (current_user_id,))
    elif current_user_role == 'professional':
         cursor.execute("""
            SELECT u.id, u.first_name, u.last_name, u.email, u.phone_number, u.role, u.company_name, 
                   u.vat_number, u.siret_number, u.kbis_path, u.account_status, u.created_at,
                   a_ship.address_line1 as shipping_address_line1, a_ship.address_line2 as shipping_address_line2, 
                   a_ship.city as shipping_city, a_ship.postal_code as shipping_postal_code, a_ship.country as shipping_country,
                   a_bill.address_line1 as billing_address_line1, a_bill.address_line2 as billing_address_line2, 
                   a_bill.city as billing_city, a_bill.postal_code as billing_postal_code, a_bill.country as billing_country
            FROM users u
            LEFT JOIN addresses a_ship ON u.id = a_ship.user_id AND a_ship.is_default_shipping = 1
            LEFT JOIN addresses a_bill ON u.id = a_bill.user_id AND a_bill.is_default_billing = 1
            WHERE u.id = ?
        """, (current_user_id,))
    elif current_user_role == 'admin':
        cursor.execute("SELECT id, first_name, last_name, email, role, created_at FROM users WHERE id = ?", (current_user_id,))
    else: # Should not happen due to decorator
        conn.close()
        return jsonify({"message": "Invalid user role"}), 500

    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        # Convert row to dict
        user_dict = dict(user_data)
        # Format dates if necessary, e.g., user_dict['created_at'] = format_date_french(user_dict['created_at'])
        return jsonify(user_dict), 200
    else:
        # This case should ideally be caught by the decorator if user is deleted after token issuance
        return jsonify({"message": "User not found"}), 404

# --- Password Reset Request ---
@auth_bp.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    email = data.get('email')
    if not email or not is_valid_email(email):
        return jsonify({"message": "Valid email is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, role, is_verified FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if user and user['is_verified']: # Only allow for verified users
        reset_token = str(uuid.uuid4())
        # Store token and expiry (e.g., 1 hour)
        # For simplicity, storing in users table. A separate table might be better.
        # Ensure you have 'reset_token' and 'reset_token_expires_at' columns in 'users' table.
        # ALTER TABLE users ADD COLUMN reset_token TEXT;
        # ALTER TABLE users ADD COLUMN reset_token_expires_at TIMESTAMP;
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        
        try:
            cursor.execute("UPDATE users SET reset_token = ?, reset_token_expires_at = ? WHERE id = ?", 
                           (reset_token, expires_at, user['id']))
            conn.commit()

            reset_link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={reset_token}" # Path on frontend
            email_subject = "Réinitialisation de votre mot de passe - Maison Trüvra"
            email_body = f"""Bonjour {user['first_name']},

Vous avez demandé une réinitialisation de mot de passe pour votre compte Maison Trüvra.
Veuillez cliquer sur le lien suivant pour choisir un nouveau mot de passe. Ce lien expirera dans une heure :
{reset_link}

Si vous n'avez pas demandé cette réinitialisation, veuillez ignorer cet e-mail.

Cordialement,
L'équipe Maison Trüvra
"""
            email_html_body = f"""
            <p>Bonjour {user['first_name']},</p>
            <p>Vous avez demandé une réinitialisation de mot de passe pour votre compte Maison Trüvra.</p>
            <p>Veuillez cliquer sur le lien suivant pour choisir un nouveau mot de passe. Ce lien expirera dans une heure :</p>
            <p><a href="{reset_link}">Réinitialiser mon mot de passe</a></p>
            <p>Si vous n'avez pas demandé cette réinitialisation, veuillez ignorer cet e-mail.</p>
            <p>Cordialement,<br>L'équipe Maison Trüvra</p>
            """
            if send_email_alert(email_subject, email_body, email, html_body=email_html_body):
                audit_logger.log_event('password_reset_request_success', user_id=user['id'], details={'email': email})
            else:
                # Log email failure but still give generic success to user for security
                audit_logger.log_event('password_reset_email_failed', user_id=user['id'], details={'email': email})
            
            # Always return a generic message to prevent email enumeration
            return jsonify({"message": "If your email is registered and verified, you will receive a password reset link."}), 200

        except sqlite3.Error as e:
            conn.rollback()
            current_app.logger.error(f"Database error during password reset request: {e}")
            audit_logger.log_event('password_reset_request_failed_db', details={'email': email, 'error': str(e)})
            return jsonify({"message": "Failed to process password reset request due to a database error."}), 500
        finally:
            conn.close()
    else:
        conn.close()
        # Generic message even if user not found or not verified
        audit_logger.log_event('password_reset_request_ignored', details={'email': email, 'reason': 'User not found or not verified'})
        return jsonify({"message": "If your email is registered and verified, you will receive a password reset link."}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('newPassword')

    if not token or not new_password:
        return jsonify({"message": "Token and new password are required"}), 400
    
    if len(new_password) < 8:
        return jsonify({"message": "Password must be at least 8 characters long"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, reset_token_expires_at FROM users WHERE reset_token = ?", (token,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"message": "Invalid or expired password reset token"}), 400

    # Check token expiry
    # Ensure reset_token_expires_at is stored as UTC and compared with UTC now
    # For SQLite, it's often stored as text; ensure consistent formatting.
    # Assuming expires_at was stored via datetime.datetime.utcnow()
    expires_at_str = user['reset_token_expires_at']
    try:
        # Try parsing with timezone info if stored like 'YYYY-MM-DD HH:MM:SS.ffffff+00:00'
        # Or without if stored as naive UTC timestamp string 'YYYY-MM-DD HH:MM:SS.ffffff'
        # Assuming it's stored as a string that fromisoformat can handle or direct datetime object if DB supports
        if isinstance(expires_at_str, str):
            # Python's fromisoformat expects 'YYYY-MM-DD HH:MM:SS[.ffffff][+/-HH:MM[:SS[.ffffff]]]'
            # SQLite might store it as 'YYYY-MM-DD HH:MM:SS' if not careful
            # Let's assume it's stored in a compatible ISO format or a format strptime can parse
            try:
                expires_at_dt = datetime.datetime.fromisoformat(expires_at_str)
            except ValueError: # Fallback for simpler 'YYYY-MM-DD HH:MM:SS'
                expires_at_dt = datetime.datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S.%f') # Or without .%f if not stored
            
            # If expires_at_dt is naive, assume it's UTC
            if expires_at_dt.tzinfo is None:
                 expires_at_dt = expires_at_dt.replace(tzinfo=datetime.timezone.utc)

        elif isinstance(expires_at_str, datetime.datetime): # If DB driver returns datetime object
            expires_at_dt = expires_at_str
            if expires_at_dt.tzinfo is None: # Ensure timezone aware for comparison
                 expires_at_dt = expires_at_dt.replace(tzinfo=datetime.timezone.utc)
        else:
            raise ValueError("Unsupported type for reset_token_expires_at")

        if datetime.datetime.now(datetime.timezone.utc) > expires_at_dt:
            conn.close()
            return jsonify({"message": "Password reset token has expired"}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error parsing reset_token_expires_at ('{expires_at_str}'): {e}")
        conn.close()
        return jsonify({"message": "Error processing token expiry. Please try again."}), 500


    hashed_password = generate_password_hash(new_password)
    try:
        cursor.execute("UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?", 
                       (hashed_password, user['id']))
        conn.commit()
        audit_logger.log_event('password_reset_success', user_id=user['id'])
        return jsonify({"message": "Password has been reset successfully."}), 200
    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error during password reset: {e}")
        audit_logger.log_event('password_reset_failed_db', user_id=user['id'], details={'error': str(e)})
        return jsonify({"message": "Failed to reset password due to a database error"}), 500
    finally:
        conn.close()

# Placeholder for logout if using server-side token blocklist
# @auth_bp.route('/logout', methods=['POST'])
# @user_jwt_required
# def logout(current_user_id):
#     # If implementing a token blocklist, add the token here
#     audit_logger.log_event('logout', user_id=current_user_id)
#     return jsonify({"message": "Logout successful"}), 200

