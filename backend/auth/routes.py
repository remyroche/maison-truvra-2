from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re # For email and password validation
from datetime import datetime, timedelta
import secrets # For token generation
import json # For address objects

from backend.database import get_db_connection # Use the centralized get_db_connection
# AuditLogService is accessed via current_app.audit_log_service

auth_bp = Blueprint('auth_bp', __name__)

# --- Helper Functions ---
def is_valid_email(email):
    if not email: return False
    # Basic regex, consider a more robust library for production
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def is_strong_password(password):
    if not password or len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False # Uppercase
    if not re.search(r"[a-z]", password): return False # Lowercase
    if not re.search(r"[0-9]", password): return False # Number
    # Optional: if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False # Special character
    return True

# --- Registration (B2C) ---
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify(message="Invalid JSON data"), 400

    email = data.get('email')
    password = data.get('password')
    first_name = data.get('firstName') # Ensure frontend sends these exact keys
    last_name = data.get('lastName')

    if not all([email, password, first_name, last_name]):
        return jsonify(message="Missing required fields (email, password, firstName, lastName)"), 400
    if not is_valid_email(email):
        current_app.audit_log_service.log_action(action='user_register_attempt_failed', username=email, details={'reason': 'invalid_email_format'}, success=False)
        return jsonify(message="Invalid email format"), 400
    if not is_strong_password(password):
        current_app.audit_log_service.log_action(action='user_register_attempt_failed', username=email, details={'reason': 'weak_password'}, success=False)
        return jsonify(message="Password is not strong enough. Min 8 chars, with uppercase, lowercase, and number."), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            current_app.audit_log_service.log_action(
                action='user_register_attempt_failed', username=email,
                details={'reason': 'email_exists'}, success=False)
            return jsonify(message="Email already registered"), 409

        password_hash_val = generate_password_hash(password)
        verification_token = secrets.token_urlsafe(32) # For email verification

        cursor.execute('''
            INSERT INTO users (email, password_hash, first_name, last_name, is_professional, professional_status, verification_token, is_verified, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (email, password_hash_val, first_name, last_name, False, 'not_applicable', verification_token, False, datetime.utcnow()))
        user_id = cursor.lastrowid
        db.commit()

        current_app.audit_log_service.log_action(
            action='user_registered', user_id=user_id, username=email,
            target_type='user', target_id=user_id,
            details={'first_name': first_name, 'last_name': last_name, 'type': 'b2c'}, success=True)
        
        # TODO: Send verification email with verification_token
        # verification_link = f"{current_app.config.get('FRONTEND_URL', '')}/verify-email.html?token={verification_token}"
        # send_verification_email(email, verification_link) # Implement this
        current_app.logger.info(f"Verification token for {email}: {verification_token}") # Log for dev

        return jsonify(message="User registered successfully. Please check your email to verify your account.", userId=user_id), 201

    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Database error during B2C registration: {e}")
        current_app.audit_log_service.log_action(action='user_register_failed_db_error', username=email, details={'error': str(e)}, success=False)
        return jsonify(message=f"Database error: {str(e)}"), 500
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Unexpected error during B2C registration: {e}")
        current_app.audit_log_service.log_action(action='user_register_failed_unexpected', username=email, details={'error': str(e)}, success=False)
        return jsonify(message=f"An unexpected error occurred: {str(e)}"), 500

# --- Login ---
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify(message="Invalid JSON data"), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify(message="Email and password are required"), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            user_dict = dict(user) # Convert to dict for easier access
            if not user_dict['is_verified'] and not user_dict['is_admin']:
                 current_app.audit_log_service.log_action(
                    action='user_login_attempt_failed', user_id=user_dict['id'], username=email,
                    details={'reason': 'not_verified'}, success=False)
                 return jsonify(message="Account not verified. Please check your email."), 403
            
            if user_dict['is_professional'] and user_dict['professional_status'] != 'approved' and not user_dict['is_admin']:
                current_app.audit_log_service.log_action(
                    action='user_login_attempt_failed', user_id=user_dict['id'], username=email,
                    details={'reason': f"professional_status_{user_dict['professional_status']}"}, success=False)
                return jsonify(message=f"Professional account status: {user_dict['professional_status']}. Contact support if approved."), 403

            cursor.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (datetime.utcnow(), datetime.utcnow(), user_dict['id']))
            db.commit()

            # IMPORTANT: Replace this with actual JWT generation
            # token = generate_jwt_token(user_dict['id'], is_admin=user_dict['is_admin'])
            token = f"mock_auth_token_for_user_{user_dict['id']}"
            if user_dict['is_admin']:
                # Use a specific, identifiable token for admin during placeholder phase
                token = current_app.config.get('ADMIN_BEARER_TOKEN_PLACEHOLDER', 'admin_token_placeholder')


            current_app.audit_log_service.log_action(
                action='user_login_success', user_id=user_dict['id'], username=email,
                target_type='user', target_id=user_dict['id'],
                details={'is_admin': user_dict['is_admin'], 'is_professional': user_dict['is_professional']}, success=True)
            
            # Prepare user data to return to frontend
            user_data_to_return = {
                'userId': user_dict['id'], 'email': user_dict['email'],
                'firstName': user_dict['first_name'], 'lastName': user_dict['last_name'],
                'isAdmin': user_dict['is_admin'], 'isProfessional': user_dict['is_professional'],
                'professionalStatus': user_dict.get('professional_status'),
                'companyName': user_dict.get('company_name') if user_dict['is_professional'] else None,
                'preferredLanguage': user_dict.get('preferred_language', 'fr'),
                # Add other fields as needed by the frontend, e.g., addresses
                'billingAddress': json.loads(user_dict.get('billing_address') or '{}'),
                'shippingAddress': json.loads(user_dict.get('shipping_address') or '{}'),
            }
            return jsonify(message="Login successful", token=token, user=user_data_to_return), 200
        else:
            current_app.audit_log_service.log_action(
                action='user_login_attempt_failed', username=email,
                details={'reason': 'invalid_credentials'}, success=False)
            return jsonify(message="Invalid email or password"), 401

    except sqlite3.Error as e:
        current_app.logger.error(f"Database error during login: {e}")
        current_app.audit_log_service.log_action(action='user_login_failed_db_error', username=email, details={'error': str(e)}, success=False)
        return jsonify(message=f"Database error: {str(e)}"), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error during login: {e}")
        current_app.audit_log_service.log_action(action='user_login_failed_unexpected', username=email, details={'error': str(e)}, success=False)
        return jsonify(message=f"An unexpected error occurred: {str(e)}"), 500

# --- Professional Registration (B2B) ---
@auth_bp.route('/register/professional', methods=['POST'])
def register_professional():
    data = request.get_json()
    if not data:
        return jsonify(message="Invalid JSON data"), 400

    email = data.get('email')
    password = data.get('password')
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    phone_number = data.get('phoneNumber')
    company_name = data.get('companyName')
    vat_number = data.get('vatNumber')
    siret_number = data.get('siretNumber')
    billing_address_data = data.get('billingAddress', {}) # Expects an object: {street, city, postalCode, country}
    shipping_address_data = data.get('shippingAddress', {})

    required_prof_fields = [email, password, first_name, last_name, company_name, vat_number, siret_number, 
                            billing_address_data.get('street'), billing_address_data.get('city'), 
                            billing_address_data.get('postalCode'), billing_address_data.get('country')]
    if not all(required_prof_fields):
        return jsonify(message="Missing required fields for professional registration. Ensure all address fields are provided."), 400
    if not is_valid_email(email):
        current_app.audit_log_service.log_action(action='prof_register_attempt_failed', username=email, details={'reason': 'invalid_email_format', 'company': company_name}, success=False)
        return jsonify(message="Invalid email format"), 400
    if not is_strong_password(password):
        current_app.audit_log_service.log_action(action='prof_register_attempt_failed', username=email, details={'reason': 'weak_password', 'company': company_name}, success=False)
        return jsonify(message="Password is not strong enough."), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            current_app.audit_log_service.log_action(action='prof_register_attempt_failed', username=email, details={'reason': 'email_exists', 'company': company_name}, success=False)
            return jsonify(message="Email already registered"), 409
        
        # Optional: Check for unique VAT/SIRET if strictly needed and not handled by other processes
        # cursor.execute("SELECT id FROM users WHERE vat_number = ? OR siret_number = ?", (vat_number, siret_number))
        # if cursor.fetchone():
        #     current_app.audit_log_service.log_action(action='prof_register_attempt_failed', username=email, details={'reason': 'vat_or_siret_exists', 'company': company_name}, success=False)
        #     return jsonify(message="VAT number or SIRET number already registered."), 409

        password_hash_val = generate_password_hash(password)
        billing_address_json = json.dumps(billing_address_data)
        shipping_address_json = json.dumps(shipping_address_data if shipping_address_data else billing_address_data) # Default shipping to billing if not provided
        
        professional_status = 'pending' if current_app.config.get('B2B_APPROVAL_REQUIRED', True) else 'approved'
        # Professional accounts are typically verified upon approval by admin, or if no approval is needed.
        is_verified_on_reg = not current_app.config.get('B2B_APPROVAL_REQUIRED', True)
        verification_token_prof = secrets.token_urlsafe(32) if not is_verified_on_reg else None


        cursor.execute('''
            INSERT INTO users (email, password_hash, first_name, last_name, phone_number,
                               is_professional, professional_status, company_name, vat_number, siret_number,
                               billing_address, shipping_address, is_verified, verification_token, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (email, password_hash_val, first_name, last_name, phone_number,
              True, professional_status, company_name, vat_number, siret_number,
              billing_address_json, shipping_address_json, is_verified_on_reg, verification_token_prof, datetime.utcnow()))
        user_id = cursor.lastrowid
        db.commit()

        current_app.audit_log_service.log_action(
            action='prof_user_registered', user_id=user_id, username=email,
            target_type='user', target_id=user_id,
            details={'company_name': company_name, 'vat_number': vat_number, 'status': professional_status}, success=True)
        
        # TODO: Send email to admin for approval if B2B_APPROVAL_REQUIRED and status is 'pending'
        # send_admin_b2b_approval_request_email(admin_email, user_details)
        # TODO: Send confirmation email to professional user (mentioning approval process if applicable)
        # send_professional_registration_confirmation_email(email, user_details)
        
        message_response = "Professional account registered successfully."
        if professional_status == 'pending':
            message_response += " Your account is pending review and approval by our team."
        elif is_verified_on_reg:
             message_response += " Your account has been automatically approved."


        return jsonify(message=message_response, userId=user_id, professionalStatus=professional_status), 201

    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Database error during professional registration: {e}")
        current_app.audit_log_service.log_action(action='prof_register_failed_db_error', username=email, details={'error': str(e), 'company': company_name}, success=False)
        return jsonify(message=f"Database error: {str(e)}"), 500
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Unexpected error during professional registration: {e}")
        current_app.audit_log_service.log_action(action='prof_register_failed_unexpected', username=email, details={'error': str(e), 'company': company_name}, success=False)
        return jsonify(message=f"An unexpected error occurred: {str(e)}"), 500

# --- Email Verification ---
@auth_bp.route('/verify-email', methods=['POST']) # Or GET if token is in query param
def verify_email():
    token = request.args.get('token') # If GET
    if not token:
        data = request.get_json()
        token = data.get('token') if data else None # If POST

    if not token:
        return jsonify(message="Verification token is required"), 400

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE verification_token = ?", (token,))
        user = cursor.fetchone()

        if not user:
            current_app.audit_log_service.log_action(action='email_verify_failed_invalid_token', details={'token': token}, success=False)
            return jsonify(message="Invalid or expired verification token."), 400
        
        user_dict = dict(user)
        if user_dict['is_verified']:
            current_app.audit_log_service.log_action(action='email_verify_already_verified', user_id=user_dict['id'], username=user_dict['email'], success=True)
            return jsonify(message="Email already verified."), 200


        cursor.execute("UPDATE users SET is_verified = TRUE, verification_token = NULL, updated_at = ? WHERE id = ?", 
                       (datetime.utcnow(), user_dict['id']))
        db.commit()

        current_app.audit_log_service.log_action(
            action='email_verified_success', user_id=user_dict['id'], username=user_dict['email'],
            target_type='user', target_id=user_dict['id'], success=True)
        return jsonify(message="Email verified successfully. You can now log in."), 200

    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error during email verification: {e}")
        current_app.audit_log_service.log_action(action='email_verify_failed_error', details={'token': token, 'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred during email verification: {str(e)}"), 500


# --- Password Reset ---
@auth_bp.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify(message="Email is required"), 400
    email = data['email']

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT id, email, is_verified FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if user:
        user_dict = dict(user)
        # Optionally, only allow password reset for verified accounts
        # if not user_dict['is_verified']:
        #     current_app.audit_log_service.log_action(action='password_reset_request_unverified_email', username=email, success=False)
        #     return jsonify(message="Please verify your email before resetting password."), 403 # Or same success message

        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=current_app.config.get('PASSWORD_RESET_TOKEN_EXPIRES_HOURS', 1))
        cursor.execute("UPDATE users SET reset_token = ?, reset_token_expires = ?, updated_at = ? WHERE id = ?",
                       (reset_token, expires_at, datetime.utcnow(), user_dict['id']))
        db.commit()
        
        # TODO: Send email with reset_token
        # reset_link = f"{current_app.config.get('FRONTEND_URL', '')}/reset-password.html?token={reset_token}" # Ensure this matches frontend
        # send_password_reset_email(email, reset_link) # Implement this email sending function
        current_app.logger.info(f"Password reset token for {email}: {reset_token}") # Log for development
        current_app.audit_log_service.log_action(
            action='password_reset_requested', user_id=user_dict['id'], username=email,
            target_type='user', target_id=user_dict['id'], success=True)
    else: 
        # User not found, still return a generic success message to prevent email enumeration
        current_app.audit_log_service.log_action(action='password_reset_request_unknown_email', username=email, success=False)

    return jsonify(message="If your email is registered with us, you will receive a password reset link shortly."), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    if not data: return jsonify(message="Invalid JSON data"), 400

    token = data.get('token')
    new_password = data.get('newPassword')

    if not token or not new_password:
        return jsonify(message="Token and new password are required"), 400
    if not is_strong_password(new_password):
        current_app.audit_log_service.log_action(action='password_reset_failed_weak_password', details={'token_prefix': token[:6] if token else None}, success=False)
        return jsonify(message="New password is not strong enough."), 400

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE reset_token = ? AND reset_token_expires > ?",
                   (token, datetime.utcnow()))
    user = cursor.fetchone()

    if not user:
        current_app.audit_log_service.log_action(action='password_reset_failed_invalid_token', details={'token_prefix': token[:6] if token else None}, success=False)
        return jsonify(message="Invalid or expired password reset token."), 400
    
    user_dict = dict(user)
    new_password_hash_val = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires = NULL, updated_at = ?, is_verified = TRUE WHERE id = ?", # Also mark as verified
                   (new_password_hash_val, datetime.utcnow(), user_dict['id']))
    db.commit()

    current_app.audit_log_service.log_action(
        action='password_reset_success', user_id=user_dict['id'], username=user_dict['email'],
        target_type='user', target_id=user_dict['id'], success=True)
    
    # TODO: Send password change confirmation email
    # send_password_changed_confirmation_email(user_dict['email'])
    return jsonify(message="Your password has been reset successfully."), 200

# --- Get Current User Info (Example, needs proper auth) ---
@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    # This endpoint requires authentication (e.g., a valid JWT token)
    # For now, it's a placeholder.
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify(message="Authentication required"), 401
    
    token = auth_header.split(" ")[1]

    # Placeholder: In a real app, decode JWT and get user ID
    # For mock, if token is admin token, return admin user, else a mock user
    db = get_db_connection()
    cursor = db.cursor()
    user_id_from_token = None

    if token == current_app.config.get('ADMIN_BEARER_TOKEN_PLACEHOLDER', 'admin_token_placeholder'):
        admin_cursor = db.execute("SELECT id FROM users WHERE is_admin = TRUE ORDER BY id ASC LIMIT 1")
        admin_user_row = admin_cursor.fetchone()
        if admin_user_row: user_id_from_token = admin_user_row['id']
    elif token.startswith("mock_auth_token_for_user_"):
        try:
            user_id_from_token = int(token.split("_")[-1])
        except ValueError:
            return jsonify(message="Invalid mock token format"), 401
    else: # Actual JWT decoding would go here
        # try:
        #   payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        #   user_id_from_token = payload['sub'] # 'sub' is standard for subject (user_id)
        # except jwt.ExpiredSignatureError:
        #   return jsonify(message="Token has expired"), 401
        # except jwt.InvalidTokenError:
        #   return jsonify(message="Invalid token"), 401
        return jsonify(message="Invalid or unhandled token type for /me endpoint"), 401


    if not user_id_from_token:
        return jsonify(message="User not identified from token"), 401

    cursor.execute("SELECT id, email, first_name, last_name, is_admin, is_professional, professional_status, company_name, phone_number, billing_address, shipping_address, preferred_language FROM users WHERE id = ?", (user_id_from_token,))
    user = cursor.fetchone()

    if not user:
        return jsonify(message="User not found"), 404
    
    user_data = dict(user)
    try:
        user_data['billing_address'] = json.loads(user_data.get('billing_address') or '{}')
        user_data['shipping_address'] = json.loads(user_data.get('shipping_address') or '{}')
    except json.JSONDecodeError:
        user_data['billing_address'] = {}
        user_data['shipping_address'] = {}

    return jsonify(user_data), 200

# --- Update User Profile (Example) ---
@auth_bp.route('/me/update', methods=['PUT'])
def update_current_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify(message="Authentication required"), 401
    token = auth_header.split(" ")[1]
    
    # Placeholder for user ID extraction from token (same logic as /me)
    user_id_from_token = None
    db = get_db_connection() # Get DB connection early
    if token == current_app.config.get('ADMIN_BEARER_TOKEN_PLACEHOLDER', 'admin_token_placeholder'):
        admin_cursor = db.execute("SELECT id FROM users WHERE is_admin = TRUE ORDER BY id ASC LIMIT 1")
        admin_user_row = admin_cursor.fetchone()
        if admin_user_row: user_id_from_token = admin_user_row['id']
    elif token.startswith("mock_auth_token_for_user_"):
        try: user_id_from_token = int(token.split("_")[-1])
        except ValueError: return jsonify(message="Invalid mock token format"), 401
    else: return jsonify(message="Invalid or unhandled token type for /me/update endpoint"), 401 # JWT logic here

    if not user_id_from_token: return jsonify(message="User not identified from token"), 401

    data = request.get_json()
    if not data: return jsonify(message="Invalid JSON data"), 400

    allowed_fields = ['first_name', 'last_name', 'phone_number', 'billing_address', 'shipping_address', 'preferred_language']
    update_fields_sql = []
    update_values_sql = []

    for field in allowed_fields:
        if field in data:
            update_fields_sql.append(f"{field} = ?")
            value = data[field]
            if field in ['billing_address', 'shipping_address']:
                value = json.dumps(value if isinstance(value, dict) else {})
            update_values_sql.append(value)

    if not update_fields_sql:
        return jsonify(message="No updatable fields provided"), 400

    update_fields_sql.append("updated_at = ?")
    update_values_sql.append(datetime.utcnow())
    update_values_sql.append(user_id_from_token)

    sql_query = f"UPDATE users SET {', '.join(update_fields_sql)} WHERE id = ?"
    
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id_from_token,))
        user = cursor.fetchone()
        if not user: return jsonify(message="User not found"), 404

        cursor.execute(sql_query, tuple(update_values_sql))
        db.commit()

        current_app.audit_log_service.log_action(
            action='user_profile_updated', user_id=user_id_from_token, username=user['email'],
            target_type='user', target_id=user_id_from_token,
            details={'updated_fields': [f.split(' = ?')[0] for f in update_fields_sql if 'updated_at' not in f]}, success=True)
        
        # Fetch updated user data to return
        cursor.execute("SELECT id, email, first_name, last_name, is_admin, is_professional, professional_status, company_name, phone_number, billing_address, shipping_address, preferred_language FROM users WHERE id = ?", (user_id_from_token,))
        updated_user_data = dict(cursor.fetchone())
        try:
            updated_user_data['billing_address'] = json.loads(updated_user_data.get('billing_address') or '{}')
            updated_user_data['shipping_address'] = json.loads(updated_user_data.get('shipping_address') or '{}')
        except json.JSONDecodeError:
            updated_user_data['billing_address'] = {}
            updated_user_data['shipping_address'] = {}

        return jsonify(message="Profile updated successfully", user=updated_user_data), 200
    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Database error updating profile for user {user_id_from_token}: {e}")
        current_app.audit_log_service.log_action(action='user_profile_update_failed_db', user_id=user_id_from_token, details={'error': str(e)}, success=False)
        return jsonify(message=f"Database error: {str(e)}"), 500
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating profile for user {user_id_from_token}: {e}")
        current_app.audit_log_service.log_action(action='user_profile_update_failed', user_id=user_id_from_token, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500
