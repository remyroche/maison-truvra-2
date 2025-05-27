# backend/professional/routes.py
from flask import Blueprint, request, jsonify, current_app, g, send_from_directory
from werkzeug.security import generate_password_hash
import os
import sqlite3
from ..database import get_db
from ..auth.routes import professional_required # Decorator to ensure user is B2B
from ..utils import is_valid_email


professional_bp = Blueprint('professional_bp_routes', __name__) # Renamed to avoid conflict if registered elsewhere

@professional_bp.route('/account', methods=['GET'])
@professional_required # Ensures only logged-in B2B users can access
def get_professional_account_details():
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number FROM users WHERE id = ? AND user_type = 'b2b'", (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            return jsonify({"success": False, "message": "Compte professionnel non trouvé."}), 404
        return jsonify({"success": True, "user": dict(user_data)}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur récupération compte pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@professional_bp.route('/account', methods=['PUT'])
@professional_required
def update_professional_account_details():
    user_id = g.current_user_id
    data = request.get_json()

    fields_to_update = {}
    if 'email' in data:
        if not is_valid_email(data['email']):
            return jsonify({"success": False, "message": "Format d'email invalide."}), 400
        fields_to_update['email'] = data['email']
    if 'nom' in data: fields_to_update['nom'] = data['nom']
    if 'prenom' in data: fields_to_update['prenom'] = data['prenom']
    if 'company_name' in data: fields_to_update['company_name'] = data['company_name']
    if 'phone_number' in data: fields_to_update['phone_number'] = data['phone_number'] # Add validation if needed

    if 'password' in data:
        if not data['password'] or len(data['password']) < 8:
            return jsonify({"success": False, "message": "Le nouveau mot de passe doit faire au moins 8 caractères."}), 400
        fields_to_update['password_hash'] = generate_password_hash(data['password'])

    if not fields_to_update:
        return jsonify({"success": False, "message": "Aucun champ à mettre à jour fourni."}), 400

    set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
    values = list(fields_to_update.values())
    values.append(user_id)

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ? AND user_type = 'b2b'", tuple(values))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Compte professionnel non trouvé ou aucune modification."}), 404

        # Fetch updated user data to return (excluding password_hash)
        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number, user_type FROM users WHERE id = ?", (user_id,))
        updated_user = dict(cursor.fetchone())

        return jsonify({"success": True, "message": "Informations du compte mises à jour.", "user": updated_user}), 200
    except sqlite3.IntegrityError as e: # Handles unique email constraint
        if db: db.rollback()
        current_app.logger.warning(f"Erreur MAJ compte pro (email existant?) {user_id}: {e}")
        return jsonify({"success": False, "message": "L'adresse e-mail est peut-être déjà utilisée."}), 409
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur MAJ compte pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors de la mise à jour."}), 500
    finally:
        if db: db.close()


@professional_bp.route('/invoices', methods=['GET'])
@professional_required
def list_professional_invoices():
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT invoice_id, invoice_number, invoice_date, total_amount_ttc, file_path FROM invoices WHERE user_id = ? ORDER BY invoice_date DESC",
            (user_id,)
        )
        invoices = [dict(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "invoices": invoices}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur listage factures pro {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


@professional_bp.route('/invoices/<int:invoice_id>/download', methods=['GET'])
@professional_required
def download_professional_invoice(invoice_id):
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT file_path FROM invoices WHERE invoice_id = ? AND user_id = ?", (invoice_id, user_id))
        invoice_record = cursor.fetchone()

        if not invoice_record or not invoice_record['file_path']:
            return jsonify({"success": False, "message": "Facture non trouvée ou accès non autorisé."}), 404

        # INVOICES_UPLOAD_DIR should be an absolute path to the directory where invoice PDFs are stored
        # It should be configured in your Flask app config (e.g., instance folder or a dedicated media root)
        # For example: app.config['INVOICES_UPLOAD_DIR'] = '/path/to/your/invoices_folder'
        invoices_dir = current_app.config.get('INVOICES_UPLOAD_DIR')
        if not invoices_dir:
            current_app.logger.error("INVOICES_UPLOAD_DIR n'est pas configuré dans l'application.")
            return jsonify({"success": False, "message": "Configuration serveur incorrecte."}), 500
        
        file_path = invoice_record['file_path'] # This should be the filename or relative path within invoices_dir
        
        # Ensure the path is safe and does not allow directory traversal
        safe_filename = os.path.basename(file_path)
        
        current_app.logger.info(f"Tentative de téléchargement de la facture : {safe_filename} depuis le répertoire : {invoices_dir} pour l'utilisateur {user_id}")

        # Use send_from_directory for safer file serving
        return send_from_directory(invoices_dir, safe_filename, as_attachment=True)

    except Exception as e:
        current_app.logger.error(f"Erreur téléchargement facture {invoice_id} pour utilisateur {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors du téléchargement de la facture."}), 500
    finally:
        if db: db.close()

# Conceptual: Forgot Password (would require email sending setup)
# @auth_bp.route('/forgot-password', methods=['POST'])
# def forgot_password():
#     # 1. Get email from request
#     # 2. Check if user exists (B2B or B2C, this route could be shared)
#     # 3. Generate a unique, short-lived reset token (e.g., using itsdangerous library or another JWT)
#     # 4. Store token hash in DB associated with user, or use a stateless JWT with expiry
#     # 5. Send email to user with a link like /reset-password?token=<token>
#     # (Requires MAIL_SERVER, MAIL_PORT etc. configured in app.config and email sending utility)
#     return jsonify({"success": True, "message": "Si un compte existe pour cet email, un lien de réinitialisation a été envoyé."})

# @auth_bp.route('/reset-password', methods=['POST'])
# def reset_password():
#     # 1. Get token and new_password from request
#     # 2. Validate token (check against DB or decode JWT, check expiry)
#     # 3. If valid, find user associated with token
#     # 4. Hash new_password and update user's password_hash in DB
#     #
