# backend/auth/routes.py
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import sqlite3
import uuid # For mock token generation
from ..database import get_db
from ..utils import is_valid_email

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST']) # This is for B2C users
def register_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    nom = data.get('nom', '')
    prenom = data.get('prenom', '')

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400
    if not password or len(password) < 8:
        return jsonify({"success": False, "message": "Le mot de passe doit contenir au moins 8 caractères."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, nom, prenom, is_admin, user_type) VALUES (?, ?, ?, ?, ?, ?)",
            (email, hashed_password, nom, prenom, False, 'b2c') # user_type is 'b2c'
        )
        db.commit()
        user_id = cursor.lastrowid
        user_info = {"id": user_id, "email": email, "nom": nom, "prenom": prenom, "is_admin": False, "user_type": "b2c"}
        current_app.logger.info(f"Utilisateur B2C enregistré : {email}")
        return jsonify({
            "success": True,
            "message": "Compte créé avec succès ! Vous pouvez maintenant vous connecter.",
            "user": user_info
        }), 201
    except sqlite3.IntegrityError:
        if db: db.rollback()
        return jsonify({"success": False, "message": "Un compte existe déjà avec cette adresse e-mail."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur d'inscription B2C pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne lors de l'inscription."}), 500
    finally:
        if db: db.close()


@auth_bp.route('/register-professional', methods=['POST']) # NEW endpoint for B2B
def register_professional_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    company_name = data.get('company_name')
    contact_nom = data.get('nom') # nom of the contact person
    contact_prenom = data.get('prenom') # prenom of the contact person
    phone_number = data.get('phone_number', None)

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400
    if not password or len(password) < 8:
        return jsonify({"success": False, "message": "Le mot de passe doit contenir au moins 8 caractères."}), 400
    if not company_name or not company_name.strip():
        return jsonify({"success": False, "message": "Le nom de l'entreprise est requis."}), 400
    if not contact_nom or not contact_prenom:
        return jsonify({"success": False, "message": "Nom et prénom du contact requis."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, nom, prenom, company_name, phone_number, is_admin, user_type, is_approved, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (email, hashed_password, contact_nom, contact_prenom, company_name, phone_number, False, 'b2b', False, 'pending_approval') # is_approved = False, status = 'pending_approval' for B2B
        )
        db.commit()
        user_id = cursor.lastrowid
        user_info = {
            "id": user_id, "email": email,
            "nom": contact_nom, "prenom": contact_prenom,
            "company_name": company_name, "phone_number": phone_number,
            "is_admin": False, "user_type": "b2b"
        }
        current_app.logger.info(f"Utilisateur B2B (professionnel) enregistré : {email} pour {company_name}")
        # TODO: Potentially send admin notification for B2B registration approval
        return jsonify({
            "success": True,
            "message": "Un administrateur doit valider votre compte.", # Updated text
            "user": user_info
        }), 201
    except sqlite3.IntegrityError:
        if db: db.rollback()
        return jsonify({"success": False, "message": "Un compte existe déjà avec cette adresse e-mail."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur d'inscription B2B pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne lors de l'inscription professionnelle."}), 500
    finally:
        if db: db.close()


@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "E-mail et mot de passe requis."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Fetch user_type along with other details
        cursor.execute("SELECT id, email, password_hash, nom, prenom, is_admin, user_type, company_name, phone_number FROM users WHERE email = ?", (email,))
        user_row = cursor.fetchone()
    except Exception as e:
        current_app.logger.error(f"Erreur DB lors de la connexion pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur de base de données."}), 500
    finally:
        if db: db.close()

    if user_row and check_password_hash(user_row['password_hash'], password):
        user_data = {
            "id": user_row['id'],
            "email": user_row['email'],
            "nom": user_row['nom'],
            "prenom": user_row['prenom'],
            "is_admin": bool(user_row['is_admin']),
            "user_type": user_row['user_type'], # Include user_type
            "company_name": user_row['company_name'], # Include company_name
            "phone_number": user_row['phone_number']
        }

        try:
            token_payload = {
                'user_id': user_data['id'],
                'email': user_data['email'],
                'is_admin': user_data['is_admin'],
                'user_type': user_data['user_type'], # Add user_type to JWT
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24))
            }
            token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')

            current_app.logger.info(f"Connexion réussie pour : {email} (Admin: {user_data['is_admin']}, Type: {user_data['user_type']})")
            return jsonify({
                "success": True,
                "message": "Connexion réussie !",
                "user": user_data,
                "token": token
            }), 200
        except Exception as e:
            current_app.logger.error(f"Erreur génération JWT pour {email}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Erreur d'authentification interne."}), 500
    else:
        current_app.logger.warning(f"Tentative de connexion échouée pour : {email}")
        return jsonify({"success": False, "message": "E-mail ou mot de passe incorrect."}), 401

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password_route(): # Renamed to avoid conflict
    data = request.get_json()
    email = data.get('email')

    if not email or not is_valid_email(email):
        return jsonify({"success": False, "message": "Veuillez fournir une adresse e-mail valide."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, user_type FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            user_id = user['id']
            # In a real app: Generate a secure, time-limited token, store it (or hash), and email the link.
            # For this mock, we'll just log it.
            mock_reset_token = str(uuid.uuid4()) # Generate a mock token
            
            # Construct the reset URL based on frontend structure
            # Example: http://127.0.0.1:5500/website/reset-password.html?token=YOUR_TOKEN&email=USER_EMAIL
            base_url = current_app.config.get('SITE_BASE_URL', 'http://127.0.0.1:5500/website')
            reset_url = f"{base_url.rstrip('/')}/reset-password.html?token={mock_reset_token}&email={email}"
            
            current_app.logger.info(f"Demande de réinitialisation de mot de passe pour {email} (User ID: {user_id}).")
            current_app.logger.info(f"MOCK EMAIL: Lien de réinitialisation (normalement envoyé par email): {reset_url}")
            # Here you would call a function to send an actual email:
            # send_password_reset_email(email, reset_url)

        # IMPORTANT: Always return a generic success message to prevent email enumeration attacks
        return jsonify({"success": True, "message": "Si un compte existe pour cet e-mail, un lien de réinitialisation des instructions a été envoyé."}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur 'mot de passe oublié' pour {email}: {e}", exc_info=True)
        # Still return a generic message to the client for security
        return jsonify({"success": True, "message": "Si un compte existe pour cet e-mail, des instructions de réinitialisation ont été envoyées."}), 200
    finally:
        if db: db.close()

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password_route(): # Renamed to avoid conflict
    data = request.get_json()
    token = data.get('token')
    email = data.get('email') # Get email from request body as well
    new_password = data.get('new_password')

    if not token or not new_password or not email:
        return jsonify({"success": False, "message": "Token, email et nouveau mot de passe sont requis."}), 400
    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Le nouveau mot de passe doit faire au moins 8 caractères."}), 400
    if not is_valid_email(email):
         return jsonify({"success": False, "message": "Format d'email invalide fourni pour la réinitialisation."}), 400

    db = None
    try:
        # In a real app:
        # 1. Validate the token (check against DB if stored, check expiry, check if used)
        # 2. If token is valid, get the user_id associated with it.
        # For this mock: We use the email to find the user, assuming token validity is checked on frontend or is implicit
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            # This implies the email (and thus the "token" if it were real) is invalid or user doesn't exist.
            return jsonify({"success": False, "message": "Lien de réinitialisation invalide ou expiré."}), 400 # Or 404

        user_id = user['id']
        hashed_password = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
        
        # In a real app, you would invalidate the used token here (e.g., mark as used in DB).
        
        db.commit()
        current_app.logger.info(f"Mot de passe réinitialisé pour l'utilisateur ID {user_id} (Email: {email}).")
        return jsonify({"success": True, "message": "Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter."}), 200

    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur lors de la réinitialisation du mot de passe pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la réinitialisation du mot de passe."}), 500
    finally:
        if db: db.close()


# Decorator for routes requiring professional user (B2B)
from functools import wraps
def professional_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]

        if not token: return jsonify({"success": False, "message": "Token manquant."}), 401
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            g.current_user_id = payload.get('user_id')
            g.user_type = payload.get('user_type')
            if g.user_type != 'b2b':
                return jsonify({"success": False, "message": "Accès professionnel requis."}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token expiré."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token invalide."}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_admin_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(" ")[1]
        if not token: return jsonify({"success": False, "message": "Token administrateur manquant."}), 401
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            g.current_user_id = payload.get('user_id') 
            g.is_admin = payload.get('is_admin', False)
            if not g.is_admin:
                return jsonify({"success": False, "message": "Accès administrateur requis."}), 403
            g.admin_user_id = g.current_user_id 
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token administrateur expiré."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token administrateur invalide."}), 401
        return f(*args, **kwargs)
    return decorated_admin_function
