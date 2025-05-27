# backend/auth/routes.py
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import sqlite3
import re # For email validation

# Assuming AuditLogService is in services.audit_service
# from ..services.audit_service import AuditLogService
# For now, let's create a placeholder if it's not ready
try:
    from ..services.audit_service import AuditLogService
except ImportError:
    class AuditLogService:
        def log_action(self, user_id, action, details=None, success=True, ip_address=None, role=None):
            print(f"AUDIT_LOG_PLACEHOLDER: User {user_id} ({role}) action: {action}, Success: {success}, Details: {details}, IP: {ip_address}")
    print("Warning: AuditLogService not found, using placeholder.")


auth_bp = Blueprint('auth_bp', __name__)

# --- Database Helper ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            g.current_user_id = data['user_id']
            g.current_user_role = data.get('role', 'b2c') # Default to b2c if role not in token
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        # Store user details in g for easier access
        user = get_user_by_id(g.current_user_id, g.current_user_role)
        if not user:
            return jsonify({'message': 'User not found!'}), 401
        g.current_user = user

        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    @login_required # Ensures user is logged in first
    def decorated_function(*args, **kwargs):
        if g.current_user_role != 'admin':
            AuditLogService().log_action(g.current_user_id, 'ADMIN_ACCESS_DENIED', f"Attempt to access {request.path}", success=False, ip_address=request.remote_addr, role=g.current_user_role)
            return jsonify({'message': 'Admin access required!'}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Utility Functions ---
def get_user_by_email(email, role='b2c'):
    db = get_db()
    table = 'users_b2c' if role == 'b2c' else 'users_b2b'
    user = db.execute(f'SELECT * FROM {table} WHERE email = ?', (email,)).fetchone()
    return user

def get_user_by_id(user_id, role='b2c'):
    db = get_db()
    table = 'users_b2c' if role == 'b2c' else 'users_b2b'
    user = db.execute(f'SELECT * FROM {table} WHERE id = ?', (user_id,)).fetchone()
    return user

def is_valid_email(email):
    # Basic email validation regex
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email)

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password): # At least one uppercase
        return False
    if not re.search(r"[a-z]", password): # At least one lowercase
        return False
    if not re.search(r"[0-9]", password): # At least one digit
        return False
    # if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): # At least one special character (optional)
    #     return False
    return True


# --- Routes ---
@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name') # For B2C
    role = data.get('role', 'b2c') # Default to B2C

    # Common validation
    if not email or not password or not name: # Name is required for B2C
        AuditLogService().log_action(None, 'REGISTER_ATTEMPT_FAIL', f"Missing fields for role {role}", success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'Missing required fields'}), 400
    if not is_valid_email(email):
        AuditLogService().log_action(None, 'REGISTER_ATTEMPT_FAIL', f"Invalid email format: {email}", success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'Invalid email format'}), 400
    if not is_strong_password(password):
        AuditLogService().log_action(None, 'REGISTER_ATTEMPT_FAIL', f"Password not strong enough for email: {email}", success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'Password is not strong enough. Min 8 chars, upper, lower, digit.'}), 400

    db = get_db()
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    if role == 'b2c':
        if get_user_by_email(email, 'b2c'):
            AuditLogService().log_action(None, 'REGISTER_B2C_FAIL', f"Email already exists: {email}", success=False, ip_address=request.remote_addr)
            return jsonify({'message': 'B2C user with this email already exists'}), 409
        
        address_shipping = data.get('address_shipping', '')
        address_billing = data.get('address_billing', '')
        phone = data.get('phone', '')
        
        try:
            cursor = db.execute('INSERT INTO users_b2c (name, email, password_hash, address_shipping, address_billing, phone) VALUES (?, ?, ?, ?, ?, ?)',
                                (name, email, hashed_password, address_shipping, address_billing, phone))
            db.commit()
            user_id = cursor.lastrowid
            AuditLogService().log_action(user_id, 'REGISTER_B2C_SUCCESS', f"Email: {email}", success=True, ip_address=request.remote_addr, role='b2c')
            return jsonify({'message': 'B2C user registered successfully', 'userId': user_id}), 201
        except sqlite3.IntegrityError:
            AuditLogService().log_action(None, 'REGISTER_B2C_FAIL', f"DB IntegrityError, likely email exists: {email}", success=False, ip_address=request.remote_addr)
            return jsonify({'message': 'B2C user with this email already exists (DB constraint)'}), 409
        except Exception as e:
            current_app.logger.error(f"B2C Registration error: {e}")
            AuditLogService().log_action(None, 'REGISTER_B2C_FAIL', f"Server error: {str(e)}", success=False, ip_address=request.remote_addr)
            return jsonify({'message': 'Could not register B2C user, server error.'}), 500

    elif role == 'b2b':
        company_name = data.get('company_name')
        siret = data.get('siret') # SIRET number for French companies
        vat_number = data.get('vat_number') # VAT number
        contact_name = name # Use 'name' as contact_name for B2B
        phone = data.get('phone')
        billing_address = data.get('billing_address')
        shipping_address = data.get('shipping_address')

        if not company_name or not siret or not contact_name or not phone or not billing_address:
            AuditLogService().log_action(None, 'REGISTER_B2B_FAIL', "Missing B2B specific fields", success=False, ip_address=request.remote_addr)
            return jsonify({'message': 'Missing B2B required fields (company_name, siret, contact_name, phone, billing_address)'}), 400

        if get_user_by_email(email, 'b2b'):
            AuditLogService().log_action(None, 'REGISTER_B2B_FAIL', f"B2B Email already exists: {email}", success=False, ip_address=request.remote_addr)
            return jsonify({'message': 'B2B user with this email already exists'}), 409
        
        try:
            cursor = db.execute('''
                INSERT INTO users_b2b (company_name, siret, vat_number, contact_name, email, password_hash, phone, billing_address, shipping_address, is_approved, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (company_name, siret, vat_number, contact_name, email, hashed_password, phone, billing_address, shipping_address, False, 'pending_approval'))
            db.commit()
            user_id = cursor.lastrowid
            # TODO: Send notification email to admin for B2B registration
            AuditLogService().log_action(user_id, 'REGISTER_B2B_PENDING', f"Company: {company_name}, Email: {email}", success=True, ip_address=request.remote_addr, role='b2b')
            return jsonify({'message': 'B2B registration request submitted. Awaiting approval.', 'userId': user_id}), 201
        except sqlite3.IntegrityError:
            AuditLogService().log_action(None, 'REGISTER_B2B_FAIL', f"DB IntegrityError, likely email/siret exists: {email}", success=False, ip_address=request.remote_addr)
            return jsonify({'message': 'B2B user with this email or SIRET already exists (DB constraint)'}), 409
        except Exception as e:
            current_app.logger.error(f"B2B Registration error: {e}")
            AuditLogService().log_action(None, 'REGISTER_B2B_FAIL', f"Server error: {str(e)}", success=False, ip_address=request.remote_addr)
            return jsonify({'message': 'Could not register B2B user, server error.'}), 500
    else:
        AuditLogService().log_action(None, 'REGISTER_ATTEMPT_FAIL', f"Invalid role specified: {role}", success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'Invalid role specified'}), 400


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'b2c') # Default to B2C if not specified

    if not email or not password:
        AuditLogService().log_action(None, 'LOGIN_ATTEMPT_FAIL', f"Missing email or password for role {role}", success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'Missing email or password'}), 400

    user = get_user_by_email(email, role)

    if not user:
        AuditLogService().log_action(None, 'LOGIN_FAIL', f"User not found: {email}, role: {role}", success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'User not found or invalid role'}), 401 # Generic message for security

    if not check_password_hash(user['password_hash'], password):
        AuditLogService().log_action(user['id'], 'LOGIN_FAIL', "Incorrect password", success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Incorrect password'}), 401

    if role == 'b2b' and not user['is_approved']:
        AuditLogService().log_action(user['id'], 'LOGIN_B2B_FAIL_NOT_APPROVED', "Account not approved", success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'B2B account not yet approved'}), 403
    
    if role == 'b2b' and user['status'] == 'suspended':
        AuditLogService().log_action(user['id'], 'LOGIN_B2B_FAIL_SUSPENDED', "Account suspended", success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'B2B account is suspended'}), 403


    token_payload = {
        'user_id': user['id'],
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24))
    }
    if role == 'admin': # Admins are a special type of B2C user for simplicity here, or could be separate
        token_payload['is_admin'] = True # Or check against a dedicated admin table/flag

    token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm="HS256")
    
    user_info = {
        'userId': user['id'],
        'email': user['email'],
        'role': role
    }
    if role == 'b2c':
        user_info['name'] = user['name']
    elif role == 'b2b':
        user_info['company_name'] = user['company_name']
        user_info['contact_name'] = user['contact_name']
        user_info['siret'] = user['siret']


    AuditLogService().log_action(user['id'], 'LOGIN_SUCCESS', f"Role: {role}", success=True, ip_address=request.remote_addr, role=role)
    return jsonify({'message': 'Login successful', 'token': token, 'user': user_info}), 200


@auth_bp.route('/api/user/profile', methods=['GET'])
@login_required # This decorator sets g.current_user_id and g.current_user_role
def get_user_profile():
    user_id = g.current_user_id
    role = g.current_user_role
    db = get_db()

    if role == 'b2c':
        user = db.execute('SELECT id, name, email, address_shipping, address_billing, phone, created_at FROM users_b2c WHERE id = ?', (user_id,)).fetchone()
    elif role == 'b2b':
        user = db.execute('SELECT id, company_name, siret, vat_number, contact_name, email, phone, billing_address, shipping_address, is_approved, status, created_at FROM users_b2b WHERE id = ?', (user_id,)).fetchone()
    else: # Should not happen if login_required works
        AuditLogService().log_action(user_id, 'GET_PROFILE_FAIL', 'Invalid role in token', success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Invalid user role specified in token'}), 400

    if not user:
        AuditLogService().log_action(user_id, 'GET_PROFILE_FAIL', 'User not found', success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'User not found'}), 404

    # Convert sqlite3.Row to dict for JSON serialization
    profile_data = dict(user)
    # Remove password hash for security
    if 'password_hash' in profile_data:
        del profile_data['password_hash']
    
    AuditLogService().log_action(user_id, 'GET_PROFILE_SUCCESS', '', success=True, ip_address=request.remote_addr, role=role)
    return jsonify(profile_data), 200


@auth_bp.route('/api/user/profile', methods=['PUT'])
@login_required
def update_user_profile():
    user_id = g.current_user_id
    role = g.current_user_role
    db = get_db()
    data = request.get_json()

    if not data:
        AuditLogService().log_action(user_id, 'UPDATE_PROFILE_FAIL', 'No data provided', success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'No data provided for update'}), 400

    if role == 'b2c':
        name = data.get('name')
        email = data.get('email') # Consider if email change needs verification
        address_shipping = data.get('address_shipping')
        address_billing = data.get('address_billing')
        phone = data.get('phone')
        
        # Validate email if changed
        current_user = db.execute('SELECT email FROM users_b2c WHERE id = ?', (user_id,)).fetchone()
        if email and email != current_user['email']:
            if not is_valid_email(email):
                AuditLogService().log_action(user_id, 'UPDATE_PROFILE_B2C_FAIL', f"Invalid new email format: {email}", success=False, ip_address=request.remote_addr, role=role)
                return jsonify({'message': 'Invalid new email format'}), 400
            existing_user = db.execute('SELECT id FROM users_b2c WHERE email = ? AND id != ?', (email, user_id)).fetchone()
            if existing_user:
                AuditLogService().log_action(user_id, 'UPDATE_PROFILE_B2C_FAIL', f"New email already in use: {email}", success=False, ip_address=request.remote_addr, role=role)
                return jsonify({'message': 'This email address is already in use by another account.'}), 409
        
        fields_to_update = {}
        if name is not None: fields_to_update['name'] = name
        if email is not None and email != current_user['email']: fields_to_update['email'] = email # Only update if changed
        if address_shipping is not None: fields_to_update['address_shipping'] = address_shipping
        if address_billing is not None: fields_to_update['address_billing'] = address_billing
        if phone is not None: fields_to_update['phone'] = phone

        if not fields_to_update:
            return jsonify({'message': 'No updatable fields provided or values are the same.'}), 200


        set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
        values = list(fields_to_update.values())
        values.append(user_id)

        try:
            db.execute(f'UPDATE users_b2c SET {set_clause} WHERE id = ?', tuple(values))
            db.commit()
            AuditLogService().log_action(user_id, 'UPDATE_PROFILE_B2C_SUCCESS', f"Fields updated: {list(fields_to_update.keys())}", success=True, ip_address=request.remote_addr, role=role)
            updated_user = dict(db.execute('SELECT id, name, email, address_shipping, address_billing, phone FROM users_b2c WHERE id = ?', (user_id,)).fetchone())
            return jsonify({'message': 'B2C profile updated successfully', 'user': updated_user}), 200
        except Exception as e:
            current_app.logger.error(f"B2C Profile update error: {e}")
            AuditLogService().log_action(user_id, 'UPDATE_PROFILE_B2C_FAIL', f"Server error: {str(e)}", success=False, ip_address=request.remote_addr, role=role)
            return jsonify({'message': 'Could not update B2C profile, server error.'}), 500

    elif role == 'b2b':
        # B2B users might have more restricted updates or require re-approval for some changes.
        # For now, allow updating contact_name, phone, shipping_address.
        # Company name, SIRET, VAT, billing_address changes might need admin intervention.
        contact_name = data.get('contact_name')
        phone = data.get('phone')
        shipping_address = data.get('shipping_address')
        # email = data.get('email') # Email change for B2B might be complex due to approval status

        fields_to_update = {}
        if contact_name is not None: fields_to_update['contact_name'] = contact_name
        if phone is not None: fields_to_update['phone'] = phone
        if shipping_address is not None: fields_to_update['shipping_address'] = shipping_address
        
        # Example: if email is allowed to change
        # current_b2b_user = db.execute('SELECT email FROM users_b2b WHERE id = ?', (user_id,)).fetchone()
        # if email and email != current_b2b_user['email']:
        #     if not is_valid_email(email):
        #         return jsonify({'message': 'Invalid new email format'}), 400
        #     existing_user = db.execute('SELECT id FROM users_b2b WHERE email = ? AND id != ?', (email, user_id)).fetchone()
        #     if existing_user:
        #         return jsonify({'message': 'This email address is already in use by another B2B account.'}), 409
        #     fields_to_update['email'] = email

        if not fields_to_update:
            return jsonify({'message': 'No updatable fields provided or values are the same for B2B profile.'}), 200

        set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
        values = list(fields_to_update.values())
        values.append(user_id)
        
        try:
            db.execute(f'UPDATE users_b2b SET {set_clause} WHERE id = ?', tuple(values))
            db.commit()
            AuditLogService().log_action(user_id, 'UPDATE_PROFILE_B2B_SUCCESS', f"Fields updated: {list(fields_to_update.keys())}", success=True, ip_address=request.remote_addr, role=role)
            updated_user = dict(db.execute('SELECT id, company_name, contact_name, email, phone, shipping_address, billing_address FROM users_b2b WHERE id = ?', (user_id,)).fetchone())
            return jsonify({'message': 'B2B profile updated successfully', 'user': updated_user}), 200
        except Exception as e:
            current_app.logger.error(f"B2B Profile update error: {e}")
            AuditLogService().log_action(user_id, 'UPDATE_PROFILE_B2B_FAIL', f"Server error: {str(e)}", success=False, ip_address=request.remote_addr, role=role)
            return jsonify({'message': 'Could not update B2B profile, server error.'}), 500
    else:
        AuditLogService().log_action(user_id, 'UPDATE_PROFILE_FAIL', 'Invalid role for profile update', success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Invalid user role for profile update'}), 400


@auth_bp.route('/api/user/change-password', methods=['POST'])
@login_required
def change_password():
    user_id = g.current_user_id
    role = g.current_user_role
    db = get_db()
    data = request.get_json()

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        AuditLogService().log_action(user_id, 'CHANGE_PASSWORD_FAIL', 'Missing current or new password', success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Current password and new password are required'}), 400

    if not is_strong_password(new_password):
        AuditLogService().log_action(user_id, 'CHANGE_PASSWORD_FAIL', 'New password not strong enough', success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'New password is not strong enough. Min 8 chars, upper, lower, digit.'}), 400

    table_name = 'users_b2c' if role == 'b2c' else 'users_b2b'
    user = db.execute(f'SELECT password_hash FROM {table_name} WHERE id = ?', (user_id,)).fetchone()

    if not user or not check_password_hash(user['password_hash'], current_password):
        AuditLogService().log_action(user_id, 'CHANGE_PASSWORD_FAIL', 'Incorrect current password', success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Incorrect current password'}), 401
    
    new_hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
    try:
        db.execute(f'UPDATE {table_name} SET password_hash = ? WHERE id = ?', (new_hashed_password, user_id))
        db.commit()
        AuditLogService().log_action(user_id, 'CHANGE_PASSWORD_SUCCESS', '', success=True, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Password updated successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Change password error: {e}")
        AuditLogService().log_action(user_id, 'CHANGE_PASSWORD_FAIL', f"Server error: {str(e)}", success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Could not update password, server error.'}), 500


@auth_bp.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    role = data.get('role', 'b2c') # Assume B2C if not specified, or require it

    if not email:
        return jsonify({'message': 'Email is required'}), 400
    
    # For security, always return a success-like message to prevent email enumeration
    # Actual password reset logic (token generation, email sending) would go here.
    user = get_user_by_email(email, role)
    if user:
        # 1. Generate a unique, short-lived reset token
        reset_token_payload = {
            'user_id': user['id'],
            'role': role,
            'email': email, # include email for verification on reset
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=current_app.config.get('PASSWORD_RESET_EXPIRATION_HOURS', 1))
        }
        reset_token = jwt.encode(reset_token_payload, current_app.config['SECRET_KEY'] + "_reset", algorithm="HS256") # Use a different secret or append to it

        # 2. Store token or a hash of it with user ID and expiry (optional, if not relying solely on JWT expiry)
        # db = get_db()
        # db.execute('INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)', 
        #            (user['id'], generate_password_hash(reset_token), datetime.datetime.utcnow() + datetime.timedelta(hours=1)))
        # db.commit()
        
        # 3. Send email with reset link (e.g., /reset-password?token=<reset_token>)
        # This part needs an actual email sending utility
        reset_link = f"{request.host_url.rstrip('/')}/reset-password.html?token={reset_token}&role={role}"
        print(f"Simulating password reset email to {email} for role {role}. Link: {reset_link}")
        # send_password_reset_email(email, reset_link) # Placeholder for actual email sending
        AuditLogService().log_action(user['id'] if user else None, 'FORGOT_PASSWORD_REQUEST', f"Email: {email}, Role: {role}", success=True, ip_address=request.remote_addr, role=role)
    else:
        # Log attempt for non-existent email but still return generic success to user
        AuditLogService().log_action(None, 'FORGOT_PASSWORD_ATTEMPT_UNKNOWN_EMAIL', f"Email: {email}, Role: {role}", success=False, ip_address=request.remote_addr)
        print(f"Password reset attempted for non-existent email/role: {email}/{role}")

    return jsonify({'message': 'If your email is registered, you will receive a password reset link.'}), 200


@auth_bp.route('/api/reset-password', methods=['POST'])
def reset_password_with_token():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    # role = data.get('role') # Role might be embedded in token or passed if not

    if not token or not new_password:
        return jsonify({'message': 'Token and new password are required'}), 400

    if not is_strong_password(new_password):
        return jsonify({'message': 'New password is not strong enough. Min 8 chars, upper, lower, digit.'}), 400

    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'] + "_reset", algorithms=["HS256"])
        user_id = payload['user_id']
        role = payload['role'] # Get role from token
        # email_from_token = payload['email'] # Optional: verify against user's current email
    except jwt.ExpiredSignatureError:
        AuditLogService().log_action(None, 'RESET_PASSWORD_FAIL', 'Expired token', success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'Password reset token has expired.'}), 401
    except jwt.InvalidTokenError:
        AuditLogService().log_action(None, 'RESET_PASSWORD_FAIL', 'Invalid token', success=False, ip_address=request.remote_addr)
        return jsonify({'message': 'Invalid password reset token.'}), 401

    # Optional: Check if token has been used or invalidated in DB
    # db = get_db()
    # stored_token = db.execute('SELECT * FROM password_reset_tokens WHERE user_id = ? AND used = FALSE AND expires_at > ?', 
    #                           (user_id, datetime.datetime.utcnow())).fetchone() # This requires a more complex token storage
    # if not stored_token or not check_password_hash(stored_token['token_hash'], token): # If storing hash
    #     return jsonify({'message': 'Invalid or expired reset token.'}), 401


    table_name = 'users_b2c' if role == 'b2c' else 'users_b2b'
    new_hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')

    try:
        db = get_db()
        db.execute(f'UPDATE {table_name} SET password_hash = ? WHERE id = ?', (new_hashed_password, user_id))
        # Optional: Mark token as used
        # db.execute('UPDATE password_reset_tokens SET used = TRUE WHERE id = ?', (stored_token['id'],))
        db.commit()
        AuditLogService().log_action(user_id, 'RESET_PASSWORD_SUCCESS', '', success=True, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Password has been reset successfully.'}), 200
    except Exception as e:
        current_app.logger.error(f"Reset password error: {e}")
        AuditLogService().log_action(user_id, 'RESET_PASSWORD_FAIL', f"Server error: {str(e)}", success=False, ip_address=request.remote_addr, role=role)
        return jsonify({'message': 'Could not reset password, server error.'}), 500


@auth_bp.route('/api/check-auth', methods=['GET'])
@login_required
def check_auth_status():
    # If @login_required passes, the user is authenticated.
    # g.current_user is set by the decorator.
    user_info = {
        'userId': g.current_user['id'],
        'email': g.current_user['email'],
        'role': g.current_user_role
    }
    if g.current_user_role == 'b2c':
        user_info['name'] = g.current_user['name']
    elif g.current_user_role == 'b2b':
        user_info['company_name'] = g.current_user['company_name']
        user_info['contact_name'] = g.current_user['contact_name']
        user_info['is_approved'] = g.current_user['is_approved']
        user_info['status'] = g.current_user['status']
    
    return jsonify({'isAuthenticated': True, 'user': user_info}), 200

