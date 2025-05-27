# backend/auth/routes.py
from flask import Blueprint, request, jsonify, current_app, g, session
from werkzeug.security import generate_password_hash, check_password_hash
import jwt # PyJWT
import datetime
import re # For password complexity
from ..database import get_db
from ..utils import is_valid_email, log_error # Assuming you have log_error in utils
# New imports
from ..email_utils import send_admin_b2b_registration_notification # Placeholder for email sending
from ..services.audit_service import AuditLogService # Placeholder for audit logging

auth_bp = Blueprint('auth_bp', __name__)

# --- Password Policy Configuration ---
# These could also be in current_app.config
PASSWORD_MIN_LENGTH = 10
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True

# --- Helper for Password Validation ---
def is_password_strong(password):
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères."
    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une majuscule."
    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        return False, "Le mot de passe doit contenir au moins une minuscule."
    if PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        return False, "Le mot de passe doit contenir au moins un chiffre."
    if PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): # Add more special chars if needed
        return False, "Le mot de passe doit contenir au moins un caractère spécial."
    return True, ""

# --- Decorators (modified for clarity and audit logging) ---
def token_required(f):
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            AuditLogService.log_event(action="TOKEN_MISSING_FOR_PROTECTED_ROUTE", success=False, details={"route": request.path})
            return jsonify({"success": False, "message": "Token manquant."}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            g.current_user_id = data['user_id']
            g.current_user_email = data.get('email') # Store email if present in token
            g.current_user_type = data.get('user_type')
            g.current_user_is_admin = data.get('is_admin', False)
        except jwt.ExpiredSignatureError:
            AuditLogService.log_event(action="TOKEN_EXPIRED", success=False, details={"token": token})
            return jsonify({"success": False, "message": "Le token a expiré."}), 401
        except jwt.InvalidTokenError:
            AuditLogService.log_event(action="TOKEN_INVALID", success=False, details={"token": token})
            return jsonify({"success": False, "message": "Token invalide."}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__ # Preserve original function name for Flask
    return decorated

def admin_required(f):
    @token_required
    def decorated(*args, **kwargs):
        if not g.current_user_is_admin:
            AuditLogService.log_event(action="ADMIN_ACCESS_DENIED", target_type="ROUTE", target_id=request.path, success=False)
            return jsonify({"success": False, "message": "Accès administrateur requis."}), 403
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

def professional_required(f):
    @token_required
    def decorated(*args, **kwargs):
        if g.current_user_type != 'b2b':
            AuditLogService.log_event(action="B2B_ACCESS_DENIED", target_type="ROUTE", target_id=request.path, success=False)
            return jsonify({"success": False, "message": "Accès professionnel (B2B) requis."}), 403
        # Additionally, check if the B2B account is active/approved
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("SELECT status FROM users WHERE id = ? AND user_type = 'b2b'", (g.current_user_id,))
            user_status_row = cursor.fetchone()
            if not user_status_row or user_status_row['status'] != 'active':
                AuditLogService.log_event(action="B2B_ACCOUNT_NOT_ACTIVE", target_type="USER", target_id=g.current_user_id, success=False)
                return jsonify({"success": False, "message": "Votre compte professionnel n'est pas actif ou en attente d'approbation."}), 403
        except Exception as e:
            log_error(f"Error checking B2B user status for user_id {g.current_user_id}: {e}")
            return jsonify({"success": False, "message": "Erreur serveur lors de la vérification du statut du compte."}), 500
        finally:
            if db: db.close()

        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated


@auth_bp.route('/register', methods=['POST'])
def register_b2c():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Aucune donnée reçue."}), 400

    email = data.get('email')
    password = data.get('password')
    nom = data.get('nom')
    prenom = data.get('prenom')

    # --- Server-side Validation ---
    if not all([email, password, nom, prenom]):
        missing_fields = [field for field, value in {"email": email, "password": password, "nom": nom, "prenom": prenom}.items() if not value]
        return jsonify({"success": False, "message": f"Champs manquants: {', '.join(missing_fields)}."}), 400
    if not is_valid_email(email): # from utils.py
        return jsonify({"success": False, "message": "Format d'email invalide."}), 400

    password_is_strong, strength_message = is_password_strong(password)
    if not password_is_strong:
        return jsonify({"success": False, "message": strength_message}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "Cet email est déjà utilisé."}), 409 # 409 Conflict

        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, nom, prenom, user_type, status) VALUES (?, ?, ?, ?, 'b2c', 'active')",
            (email, hashed_password, nom, prenom)
        )
        user_id = cursor.lastrowid
        db.commit()
        AuditLogService.log_event(action="B2C_USER_REGISTERED", target_type="USER", target_id=user_id, details={"email": email})
        return jsonify({"success": True, "message": "Compte client créé avec succès."}), 201
    except Exception as e:
        if db: db.rollback()
        log_error(f"Erreur lors de l'enregistrement B2C: {e}")
        return jsonify({"success": False, "message": "Erreur serveur lors de la création du compte."}), 500
    finally:
        if db: db.close()

@auth_bp.route('/register-professional', methods=['POST'])
def register_b2b():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Aucune donnée reçue."}), 400

    email = data.get('email')
    password = data.get('password')
    company_name = data.get('company_name')
    nom = data.get('nom') # Contact person last name
    prenom = data.get('prenom') # Contact person first name
    phone_number = data.get('phone_number')

    # --- Server-side Validation ---
    if not all([email, password, company_name, nom, prenom]):
        missing_fields = [
            field for field, value in {
                "email": email, "password": password, "company_name": company_name,
                "nom": nom, "prenom": prenom
            }.items() if not value
        ]
        return jsonify({"success": False, "message": f"Champs manquants: {', '.join(missing_fields)}."}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Format d'email invalide."}), 400

    password_is_strong, strength_message = is_password_strong(password)
    if not password_is_strong:
        return jsonify({"success": False, "message": strength_message}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "Cet email est déjà utilisé pour un autre compte."}), 409

        hashed_password = generate_password_hash(password)
        cursor.execute(
            """INSERT INTO users (email, password_hash, nom, prenom, company_name, phone_number, user_type, status, is_admin)
               VALUES (?, ?, ?, ?, ?, ?, 'b2b', 'pending_approval', 0)""",
            (email, hashed_password, nom, prenom, company_name, phone_number)
        )
        user_id = cursor.lastrowid
        db.commit()

        AuditLogService.log_event(action="B2B_USER_REGISTERED_PENDING_APPROVAL", target_type="USER", target_id=user_id, details={"email": email, "company": company_name})

        # --- Notify Admin ---
        admin_notification_email = current_app.config.get('ADMIN_EMAIL_NOTIFICATIONS')
        if admin_notification_email:
            send_admin_b2b_registration_notification(admin_notification_email, email, company_name)
        else:
            current_app.logger.warning("ADMIN_EMAIL_NOTIFICATIONS not set. Cannot send B2B registration alert.")

        return jsonify({"success": True, "message": "Compte professionnel créé. Il est en attente d'approbation par un administrateur."}), 201
    except Exception as e:
        if db: db.rollback()
        log_error(f"Erreur lors de l'enregistrement B2B: {e}")
        return jsonify({"success": False, "message": "Erreur serveur lors de la création du compte professionnel."}), 500
    finally:
        if db: db.close()


@auth_bp.route('/login', methods=['POST'])
# @limiter.limit("10 per minute") # Example of applying rate limit
def login():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Aucune donnée reçue."}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "Email et mot de passe requis."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, password_hash, user_type, nom, prenom, company_name, phone_number, status, is_admin FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            AuditLogService.log_event(action="LOGIN_FAILED_USER_NOT_FOUND", details={"email": email}, success=False)
            return jsonify({"success": False, "message": "Email ou mot de passe incorrect."}), 401 # Generic message

        if not check_password_hash(user['password_hash'], password):
            AuditLogService.log_event(action="LOGIN_FAILED_INVALID_PASSWORD", target_type="USER", target_id=user['id'], details={"email": email}, success=False)
            return jsonify({"success": False, "message": "Email ou mot de passe incorrect."}), 401 # Generic message

        if user['user_type'] == 'b2b' and user['status'] == 'pending_approval':
            AuditLogService.log_event(action="LOGIN_FAILED_B2B_PENDING_APPROVAL", target_type="USER", target_id=user['id'], details={"email": email}, success=False)
            return jsonify({"success": False, "message": "Votre compte professionnel est en attente d'approbation."}), 403
        
        if user['user_type'] == 'b2b' and user['status'] == 'suspended':
            AuditLogService.log_event(action="LOGIN_FAILED_B2B_SUSPENDED", target_type="USER", target_id=user['id'], details={"email": email}, success=False)
            return jsonify({"success": False, "message": "Votre compte professionnel a été suspendu."}), 403

        # --- Generate JWT Token ---
        token_payload = {
            'user_id': user['id'],
            'email': user['email'],
            'user_type': user['user_type'],
            'is_admin': bool(user['is_admin']),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24))
        }
        token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm="HS256")

        user_data_to_return = dict(user)
        del user_data_to_return['password_hash'] # Don't send hash to client

        AuditLogService.log_event(action="LOGIN_SUCCESS", target_type="USER", target_id=user['id'], details={"email": email, "user_type": user['user_type']})
        return jsonify({
            "success": True,
            "message": "Connexion réussie.",
            "token": token,
            "user": user_data_to_return
        }), 200

    except Exception as e:
        log_error(f"Erreur lors de la connexion: {e}")
        AuditLogService.log_event(action="LOGIN_FAILED_SERVER_ERROR", details={"email": email, "error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors de la connexion."}), 500
    finally:
        if db: db.close()


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({"success": False, "message": "Email requis."}), 400

    email = data.get('email')
    if not is_valid_email(email):
        return jsonify({"success": False, "message": "Format d'email invalide."}), 400

    # --- IMPORTANT ---
    # To prevent email enumeration, this endpoint should always return a success-like message.
    # The actual logic for token generation and email sending happens if the user exists.
    # You will need a proper email sending service.

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, nom, prenom FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            # 1. Generate a unique, short-lived reset token (e.g., using itsdangerous or another JWT)
            reset_token_payload = {
                'user_id': user['id'],
                'email': email,
                'purpose': 'password_reset',
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=current_app.config.get('PASSWORD_RESET_TOKEN_EXPIRY_MINUTES', 30))
            }
            reset_token = jwt.encode(reset_token_payload, current_app.config['SECRET_KEY'] + "_reset", algorithm="HS256") # Use a slightly different secret or context

            # 2. Send email to user with a link like /reset-password?token=<token>
            # This requires MAIL_SERVER, MAIL_PORT etc. configured in app.config and email sending utility
            # from ..email_utils import send_password_reset_email
            # reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:xxxx')}/reset-password.html?token={reset_token}"
            # email_sent = send_password_reset_email(email, user['prenom'] or user['nom'], reset_url)
            # if email_sent:
            #     AuditLogService.log_event(action="PASSWORD_RESET_EMAIL_SENT", target_type="USER", target_id=user['id'], details={"email": email})
            # else:
            #     AuditLogService.log_event(action="PASSWORD_RESET_EMAIL_FAILED", target_type="USER", target_id=user['id'], details={"email": email}, success=False)
            #     # Still return a generic success to the client
            current_app.logger.info(f"Simulating password reset email for {email}. Token: {reset_token}") # Placeholder
        else:
            # User not found, but don't reveal this.
            AuditLogService.log_event(action="PASSWORD_RESET_ATTEMPT_USER_NOT_FOUND", details={"email": email}, success=False)
            current_app.logger.info(f"Password reset attempt for non-existent email: {email}")


        return jsonify({"success": True, "message": "Si un compte existe pour cet email, un lien de réinitialisation (théorique) a été envoyé."}), 200

    except Exception as e:
        log_error(f"Erreur lors de la demande de réinitialisation de mot de passe: {e}")
        AuditLogService.log_event(action="PASSWORD_RESET_REQUEST_ERROR", details={"email": email, "error": str(e)}, success=False)
        # Even on server error, might be best to return generic success to prevent info leak.
        return jsonify({"success": True, "message": "Si un compte existe pour cet email, un lien de réinitialisation (théorique) a été envoyé."}), 200
    finally:
        if db: db.close()


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password_with_token():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Aucune donnée reçue."}), 400

    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({"success": False, "message": "Token et nouveau mot de passe requis."}), 400

    password_is_strong, strength_message = is_password_strong(new_password)
    if not password_is_strong:
        return jsonify({"success": False, "message": strength_message}), 400

    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'] + "_reset", algorithms=["HS256"])
        if payload.get('purpose') != 'password_reset':
            raise jwt.InvalidTokenError("Token not for password reset.")
        user_id = payload['user_id']
        email_from_token = payload['email']

    except jwt.ExpiredSignatureError:
        AuditLogService.log_event(action="PASSWORD_RESET_TOKEN_EXPIRED", details={"token_prefix": token[:10]}, success=False)
        return jsonify({"success": False, "message": "Le lien de réinitialisation a expiré."}), 401
    except jwt.InvalidTokenError as e:
        AuditLogService.log_event(action="PASSWORD_RESET_TOKEN_INVALID", details={"token_prefix": token[:10], "error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Le lien de réinitialisation est invalide ou a déjà été utilisé."}), 401

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Verify user still exists and matches token
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        user_db_check = cursor.fetchone()
        if not user_db_check or user_db_check['email'] != email_from_token:
            AuditLogService.log_event(action="PASSWORD_RESET_USER_MISMATCH", target_type="USER", target_id=user_id, details={"token_email": email_from_token}, success=False)
            return jsonify({"success": False, "message": "Erreur lors de la réinitialisation du mot de passe (utilisateur non trouvé)."}), 404


        hashed_password = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash = ?, password_last_changed = ? WHERE id = ?", (hashed_password, datetime.datetime.utcnow(), user_id))
        db.commit()

        if cursor.rowcount == 0:
            AuditLogService.log_event(action="PASSWORD_RESET_FAILED_NO_UPDATE", target_type="USER", target_id=user_id, success=False)
            return jsonify({"success": False, "message": "Échec de la mise à jour du mot de passe."}), 500

        AuditLogService.log_event(action="PASSWORD_RESET_SUCCESS", target_type="USER", target_id=user_id, details={"email": email_from_token})
        # Optionally, invalidate the token here if it's stored or stateful. JWTs are stateless.
        return jsonify({"success": True, "message": "Mot de passe réinitialisé avec succès."}), 200

    except Exception as e:
        if db: db.rollback()
        log_error(f"Erreur lors de la réinitialisation du mot de passe pour user_id {user_id}: {e}")
        AuditLogService.log_event(action="PASSWORD_RESET_SERVER_ERROR", target_type="USER", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors de la réinitialisation du mot de passe."}), 500
    finally:
        if db: db.close()

@auth_bp.route('/check-token', methods=['GET'])
@token_required
def check_token():
    # If @token_required passes, the token is valid.
    # Fetch fresh user data to ensure it's up-to-date (e.g., if user_type changed)
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, user_type, nom, prenom, company_name, phone_number, status, is_admin FROM users WHERE id = ?", (g.current_user_id,))
        user = cursor.fetchone()
        if not user:
             return jsonify({"success": False, "message": "Utilisateur non trouvé."}), 404 # Should not happen if token was valid for this user_id

        user_data_to_return = dict(user)
        return jsonify({"success": True, "user": user_data_to_return}), 200
    except Exception as e:
        log_error(f"Erreur lors de la vérification du token pour user {g.current_user_id}: {e}")
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

