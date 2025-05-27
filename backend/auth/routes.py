# backend/auth/routes.py
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature


from ..database import db, User
from ..utils import is_valid_email # Assuming utils.py is in the same directory level or adjust import

auth_bp = Blueprint('auth', __name__)

# --- Decorators ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers and request.headers['Authorization'].startswith('Bearer '):
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing!'}), 401
        
        try:
            # g.current_user_id, g.user_type, g.is_admin should be set by before_request_func in __init__.py
            if not g.get('current_user_id'): # Check if user was actually loaded from token
                 # This case might happen if before_request_func failed silently or token was invalid but not caught there
                payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
                g.current_user_id = payload.get('user_id')
                g.user_type = payload.get('user_type')
                g.is_admin = payload.get('is_admin', False)

            if not g.current_user_id: # Still no user_id
                 return jsonify({'success': False, 'message': 'Invalid token or user not found.'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Token is invalid!'}), 401
        except Exception as e:
            current_app.logger.error(f"Error in token_required decorator: {e}", exc_info=True)
            return jsonify({'success': False, 'message': 'Token processing error.'}), 401
            
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @token_required # Ensures token is valid and g.is_admin is populated
    def decorated(*args, **kwargs):
        if not g.get('is_admin'):
            return jsonify({'success': False, 'message': 'Admin access required.'}), 403
        return f(*args, **kwargs)
    return decorated

def professional_required(f):
    @wraps(f)
    @token_required # Ensures token is valid and g.user_type is populated
    def decorated(*args, **kwargs):
        if g.get('user_type') != 'professional':
            return jsonify({'success': False, 'message': 'Professional account access required.'}), 403
        
        user = User.query.get(g.current_user_id) # Check approval status from DB directly
        if not user or not user.is_approved or user.status != 'active':
             return jsonify({'success': False, 'message': 'Professional account not approved or inactive.'}), 403
        return f(*args, **kwargs)
    return decorated


# --- Routes ---
@auth_bp.route('/register', methods=['POST'])
def register_b2c():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided.'}), 400

    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')

    if not all([email, password, first_name, last_name]):
        return jsonify({'success': False, 'message': 'Missing required fields.'}), 400

    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format.'}), 400
    
    if len(password) < 8: # Basic password length check
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters long.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered.'}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(
        email=email, 
        password_hash=hashed_password, 
        first_name=first_name, 
        last_name=last_name,
        user_type='b2c', # Default B2C user
        is_approved=True, # B2C users are auto-approved
        status='active'
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        # TODO: Send welcome email
        return jsonify({'success': True, 'message': 'B2C user registered successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error registering B2C user: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@auth_bp.route('/register-professional', methods=['POST'])
def register_professional():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided.'}), 400

    email = data.get('email')
    password = data.get('password')
    company_name = data.get('company_name')
    vat_number = data.get('vat_number') # Optional, but good for B2B
    # Add other B2B specific fields: address, phone, etc.

    if not all([email, password, company_name]): # Basic check
        return jsonify({'success': False, 'message': 'Missing required fields: email, password, company_name.'}), 400

    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format.'}), 400
    
    if len(password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters long.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered.'}), 409
    
    if vat_number and User.query.filter_by(vat_number=vat_number).first(): # Check for unique VAT if provided and required to be unique
        return jsonify({'success': False, 'message': 'VAT number already registered.'}), 409


    hashed_password = generate_password_hash(password)
    new_user = User(
        email=email,
        password_hash=hashed_password,
        company_name=company_name,
        vat_number=vat_number,
        user_type='professional',
        is_approved=False, # Professionals require admin approval
        status='pending_approval'
        # Populate other fields from data
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        # TODO: Send email to admin for approval & to user about pending approval
        return jsonify({'success': True, 'message': 'Professional registration submitted. Awaiting admin approval.'}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error registering professional user: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided.'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

    if user.status == 'inactive' or user.status == 'suspended' or user.status == 'rejected':
        return jsonify({'success': False, 'message': f'Account is {user.status}. Please contact support.'}), 403
    
    if user.user_type == 'professional' and (not user.is_approved or user.status == 'pending_approval'):
        return jsonify({'success': False, 'message': 'Professional account not yet approved or pending approval.'}), 403
    
    # Determine token expiration based on user type
    if user.user_type == 'admin': # Assuming admin users have user_type 'admin'
        expires_delta = timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES_ADMIN'])
    elif user.user_type == 'professional':
        expires_delta = timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES_PROFESSIONAL'])
    else: # b2c and others
        expires_delta = timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES_DEFAULT'])
        
    token_payload = {
        'user_id': user.id,
        'email': user.email,
        'user_type': user.user_type,
        'is_admin': user.user_type == 'admin', # Set is_admin flag in token if user_type is 'admin'
        'exp': datetime.now(timezone.utc) + expires_delta
    }
    token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({
        'success': True, 
        'message': 'Login successful.', 
        'token': token,
        'user': user.to_dict() # Send non-sensitive user data
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password_route():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': 'Email is required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Still return success to prevent email enumeration, but log it
        current_app.logger.info(f"Password reset requested for non-existent email: {email}")
        return jsonify({'success': True, 'message': 'If your email is registered, you will receive a password reset link.'})

    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['PASSWORD_RESET_SALT'])
        reset_token = s.dumps({'user_id': user.id, 'email': user.email})
        
        # TODO: Implement actual email sending logic here
        # reset_url = url_for('auth.reset_password_route', token=reset_token, _external=True) # If reset page is part of this app
        reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:8080')}/reset-password?token={reset_token}" # Adjust to your frontend URL
        
        mail_subject = "Password Reset Request - Maison Trüvra"
        mail_body = f"""
        <p>Hello {user.first_name or user.company_name or user.email},</p>
        <p>You requested a password reset. Click the link below to reset your password:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>This link is valid for 1 hour.</p>
        <p>If you did not request this, please ignore this email.</p>
        <p>Thanks,<br>The Maison Trüvra Team</p>
        """
        # from ..utils import send_email # Assuming you have an email utility
        # send_email(to_email=user.email, subject=mail_subject, body_html=mail_body)
        current_app.logger.info(f"Password reset token generated for {email}. Reset URL (for dev): {reset_url}")
        # For now, just log it:
        print(f"DEBUG: Password Reset URL for {user.email}: {reset_url}")


        return jsonify({'success': True, 'message': 'If your email is registered, you will receive a password reset link.'})
    except Exception as e:
        current_app.logger.error(f"Error in forgot password for {email}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error processing password reset request.'}), 500


@auth_bp.route('/reset-password/<token>', methods=['POST']) # Or just /reset-password and token from body
def reset_password_with_token(token): # If token in URL
# def reset_password_route(): # If token in body
    data = request.get_json()
    # token = data.get('token') # If token in body
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({'success': False, 'message': 'Token and new password are required.'}), 400
    
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'New password must be at least 8 characters long.'}), 400

    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=current_app.config['PASSWORD_RESET_SALT'])
    try:
        token_data = s.loads(token, max_age=3600) # Token valid for 1 hour
        user_id = token_data.get('user_id')
        email_from_token = token_data.get('email') # For extra verification if needed

        user = User.query.get(user_id)
        if not user or user.email != email_from_token: # Basic check
            return jsonify({'success': False, 'message': 'Invalid or expired reset link (user mismatch).'}), 400

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        # TODO: Send password change confirmation email
        return jsonify({'success': True, 'message': 'Password has been reset successfully.'})

    except SignatureExpired:
        return jsonify({'success': False, 'message': 'Password reset link has expired.'}), 400
    except BadTimeSignature:
        return jsonify({'success': False, 'message': 'Invalid password reset link (bad signature).'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting password with token: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error resetting password.'}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    user_id = g.current_user_id
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
    return jsonify({'success': True, 'user': user.to_dict()})

@auth_bp.route('/logout', methods=['POST'])
@token_required # Optional: could just be a client-side token removal
def logout():
    # Server-side logout for JWT is typically about managing token blocklists if you need immediate invalidation.
    # For simplicity, client should just discard the token.
    # If you implement a blocklist, add token to it here.
    g.current_user_id = None
    g.user_type = None
    g.is_admin = False
    return jsonify({'success': True, 'message': 'Successfully logged out.'})
