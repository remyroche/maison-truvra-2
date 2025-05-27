# backend/professional/routes.py
from flask import Blueprint, request, jsonify, current_app, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
from ..database import get_db
from ..auth.routes import professional_required # Decorator from auth_bp
from ..utils import is_valid_email # Assuming is_valid_email from backend/utils.py

professional_bp = Blueprint('professional_bp_routes', __name__) # Ensure this name is unique if used elsewhere

@professional_bp.route('/account', methods=['GET'])
@professional_required
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
    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        # Fetch current email to check if it's being changed
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        current_user_data = cursor.fetchone()
        if not current_user_data:
            return jsonify({"success": False, "message": "Utilisateur non trouvé."}), 404

        current_email = current_user_data['email']

        fields_to_update = {}
        if 'email' in data and data['email'] != current_email:
            if not is_valid_email(data['email']):
                return jsonify({"success": False, "message": "Format d'email invalide."}), 400
            fields_to_update['email'] = data['email']
        if 'nom' in data: fields_to_update['nom'] = data['nom']
        if 'prenom' in data: fields_to_update['prenom'] = data['prenom']
        if 'company_name' in data: fields_to_update['company_name'] = data['company_name']
        if 'phone_number' in data: fields_to_update['phone_number'] = data['phone_number']

        if 'new_password' in data:
            if not data['new_password'] or len(data['new_password']) < 8:
                return jsonify({"success": False, "message": "Le nouveau mot de passe doit faire au moins 8 caractères."}), 400
            # Optional: require current_password for security
            if 'current_password' in data:
                cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
                user_pwd_row = cursor.fetchone()
                if not user_pwd_row or not check_password_hash(user_pwd_row['password_hash'], data['current_password']):
                    return jsonify({"success": False, "message": "Mot de passe actuel incorrect."}), 403
            fields_to_update['password_hash'] = generate_password_hash(data['new_password'])

        if not fields_to_update:
            return jsonify({"success": False, "message": "Aucun champ à mettre à jour fourni."}), 400

        set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
        values = list(fields_to_update.values())
        values.append(user_id)

        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ? AND user_type = 'b2b'", tuple(values))
        db.commit()

        if cursor.rowcount == 0 and not fields_to_update.get('password_hash'): # Password update doesn't affect rowcount if other fields same
            return jsonify({"success": False, "message": "Aucune modification détectée ou utilisateur non trouvé."}), 404

        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number, user_type FROM users WHERE id = ?", (user_id,))
        updated_user = dict(cursor.fetchone())

        return jsonify({"success": True, "message": "Informations du compte mises à jour.", "user": updated_user}), 200
    except sqlite3.IntegrityError as e:
        if db: db.rollback()
        return jsonify({"success": False, "message": "L'adresse e-mail est peut-être déjà utilisée par un autre compte."}), 409
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
        invoices_data = []
        for row in cursor.fetchall():
            invoice_dict = dict(row)
            # Create a downloadable link (frontend will use this)
            invoice_dict['download_url'] = url_for('professional_bp_routes.download_professional_invoice', invoice_id=row['invoice_id'], _external=False)
            invoices_data.append(invoice_dict)
        return jsonify({"success": True, "invoices": invoices_data}), 200
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
        cursor.execute("SELECT file_path, invoice_number FROM invoices WHERE invoice_id = ? AND user_id = ?", (invoice_id, user_id))
        invoice_record = cursor.fetchone()

        if not invoice_record or not invoice_record['file_path']:
            return jsonify({"success": False, "message": "Facture non trouvée ou accès non autorisé."}), 404

        invoices_dir = current_app.config.get('INVOICES_UPLOAD_DIR') # Absolute path
        if not invoices_dir:
            current_app.logger.error("INVOICES_UPLOAD_DIR n'est pas configuré.")
            return jsonify({"success": False, "message": "Configuration serveur incorrecte."}), 500

        # file_path from DB is the filename (e.g., FACT2025-001.pdf)
        safe_filename = os.path.basename(invoice_record['file_path'])

        current_app.logger.info(f"Tentative de téléchargement : {safe_filename} depuis {invoices_dir} pour user {user_id}")
        return send_from_directory(invoices_dir, safe_filename, as_attachment=True, download_name=f"{invoice_record['invoice_number']}.pdf")
    except Exception as e:
        current_app.logger.error(f"Erreur téléchargement facture {invoice_id} user {user_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur lors du téléchargement."}), 500
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
