# backend/auth/routes.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import sqlite3 

from ..database import get_db
from ..utils import is_valid_email

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
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
        # New users are not admin by default
        cursor.execute(
            "INSERT INTO users (email, password_hash, nom, prenom, is_admin) VALUES (?, ?, ?, ?, ?)",
            (email, hashed_password, nom, prenom, False) # is_admin defaults to False
        )
        db.commit()
        user_id = cursor.lastrowid
        user_info = {"id": user_id, "email": email, "nom": nom, "prenom": prenom, "is_admin": False}
        current_app.logger.info(f"Utilisateur enregistré : {email}")
        return jsonify({
            "success": True, 
            "message": "Compte créé avec succès ! Vous pouvez maintenant vous connecter.",
            "user": user_info 
        }), 201
    except sqlite3.IntegrityError:
        if db: db.rollback()
        current_app.logger.warning(f"Tentative d'enregistrement avec un email existant : {email}")
        return jsonify({"success": False, "message": "Un compte existe déjà avec cette adresse e-mail."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur d'inscription pour {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Une erreur interne s'est produite lors de l'inscription."}), 500
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
        # Fetch is_admin along with other user details
        cursor.execute("SELECT id, email, password_hash, nom, prenom, is_admin FROM users WHERE email = ?", (email,))
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
            "is_admin": bool(user_row['is_admin']) # Ensure boolean
        }
        
        try:
            token_payload = {
                'user_id': user_data['id'],
                'email': user_data['email'],
                'is_admin': user_data['is_admin'], # Include admin status in JWT
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24))
            }
            token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
            
            current_app.logger.info(f"Connexion réussie pour : {email} (Admin: {user_data['is_admin']})")
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

# Helper decorator for admin routes (to be created and used in admin_api/routes.py)
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"success": False, "message": "Token mal formaté."}), 401

        if not token:
            return jsonify({"success": False, "message": "Token manquant."}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            if not data.get('is_admin'):
                return jsonify({"success": False, "message": "Accès administrateur requis."}), 403
            # Pass current admin user_id to the route if needed
            # g.current_admin_id = data.get('user_id') 
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token expiré."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token invalide."}), 401
        
        # Store admin user_id in flask.g for access in the route if needed
        # from flask import g
        # g.admin_user_id = data.get('user_id')

        return f(*args, **kwargs)
    return decorated_function

