# backend/professional/routes.py
from flask import Blueprint, request, jsonify, current_app, g, send_from_directory, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
import datetime # Added for password_last_changed
from ..database import get_db
from ..auth.routes import professional_required, is_password_strong # Decorator and password strength check
from ..utils import is_valid_email, log_error
from ..services.audit_service import AuditLogService # Placeholder for audit logging

professional_bp = Blueprint('professional_bp_routes', __name__)

@professional_bp.route('/account', methods=['GET'])
@professional_required
def get_professional_account_details():
    user_id = g.current_user_id
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Ensure status is also selected if needed by frontend for display consistency
        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number, status FROM users WHERE id = ? AND user_type = 'b2b'", (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            AuditLogService.log_event(action="B2B_ACCOUNT_DETAILS_NOT_FOUND", target_type="USER", target_id=user_id, success=False)
            return jsonify({"success": False, "message": "Compte professionnel non trouvé."}), 404
        
        AuditLogService.log_event(action="B2B_ACCOUNT_DETAILS_VIEWED", target_type="USER", target_id=user_id)
        return jsonify({"success": True, "user": dict(user_data)}), 200
    except Exception as e:
        log_error(f"Erreur récupération compte pro {user_id}: {e}")
        AuditLogService.log_event(action="B2B_ACCOUNT_DETAILS_ERROR", target_type="USER", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération des informations."}), 500
    finally:
        if db: db.close()

@professional_bp.route('/account', methods=['PUT'])
@professional_required
def update_professional_account_details():
    user_id = g.current_user_id
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Aucune donnée reçue."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT email, password_hash FROM users WHERE id = ?", (user_id,))
        current_user_data = cursor.fetchone()
        if not current_user_data:
            AuditLogService.log_event(action="B2B_ACCOUNT_UPDATE_USER_NOT_FOUND", target_type="USER", target_id=user_id, success=False)
            return jsonify({"success": False, "message": "Utilisateur non trouvé."}), 404

        current_email = current_user_data['email']
        current_password_hash = current_user_data['password_hash']

        fields_to_update = {}
        original_values = {} # For audit logging

        if 'email' in data and data['email'] != current_email:
            new_email = data['email'].strip()
            if not is_valid_email(new_email):
                return jsonify({"success": False, "message": "Format d'email invalide."}), 400
            # Check if new email is already taken
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (new_email, user_id))
            if cursor.fetchone():
                return jsonify({"success": False, "message": "Cette adresse e-mail est déjà utilisée par un autre compte."}), 409
            fields_to_update['email'] = new_email
            original_values['email'] = current_email

        for field in ['nom', 'prenom', 'company_name', 'phone_number']:
            if field in data and data[field] != current_user_data.get(field): # Check if value changed
                fields_to_update[field] = data[field].strip() if isinstance(data[field], str) else data[field]
                original_values[field] = current_user_data.get(field)


        if 'new_password' in data and data['new_password']:
            new_password = data['new_password']
            current_password_form = data.get('current_password')

            if not current_password_form:
                return jsonify({"success": False, "message": "Le mot de passe actuel est requis pour changer le mot de passe."}), 400
            if not check_password_hash(current_password_hash, current_password_form):
                AuditLogService.log_event(action="B2B_PASSWORD_CHANGE_INVALID_CURRENT_PW", target_type="USER", target_id=user_id, success=False)
                return jsonify({"success": False, "message": "Mot de passe actuel incorrect."}), 403

            password_is_strong, strength_message = is_password_strong(new_password)
            if not password_is_strong:
                return jsonify({"success": False, "message": strength_message}), 400
            
            fields_to_update['password_hash'] = generate_password_hash(new_password)
            fields_to_update['password_last_changed'] = datetime.datetime.utcnow() # Track password change date
            original_values['password_hash'] = "********" # Don't log the hash

        if not fields_to_update:
            return jsonify({"success": False, "message": "Aucun champ à mettre à jour fourni ou les valeurs sont identiques."}), 400

        set_clause = ", ".join([f"{key} = ?" for key in fields_to_update.keys()])
        values = list(fields_to_update.values())
        values.append(user_id) # For WHERE clause

        cursor.execute(f"UPDATE users SET {set_clause} WHERE id = ? AND user_type = 'b2b'", tuple(values))
        db.commit()

        if cursor.rowcount == 0: # Should not happen if fields_to_update is not empty and user exists
             AuditLogService.log_event(action="B2B_ACCOUNT_UPDATE_NO_ROWS_AFFECTED", target_type="USER", target_id=user_id, details=fields_to_update, success=False)
             return jsonify({"success": False, "message": "Aucune modification n'a été enregistrée."}), 404 # Or 500

        cursor.execute("SELECT id, email, nom, prenom, company_name, phone_number, user_type, status FROM users WHERE id = ?", (user_id,))
        updated_user = dict(cursor.fetchone())

        AuditLogService.log_event(
            action="B2B_ACCOUNT_UPDATED",
            target_type="USER",
            target_id=user_id,
            details={"updated_fields": list(fields_to_update.keys()), "original_values": original_values}
        )
        return jsonify({"success": True, "message": "Informations du compte mises à jour avec succès.", "user": updated_user}), 200
    except sqlite3.IntegrityError as e: # Handles unique constraint violation for email
        if db: db.rollback()
        log_error(f"Erreur d'intégrité MAJ compte pro {user_id}: {e}")
        AuditLogService.log_event(action="B2B_ACCOUNT_UPDATE_INTEGRITY_ERROR", target_type="USER", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "L'adresse e-mail est peut-être déjà utilisée par un autre compte."}), 409
    except Exception as e:
        if db: db.rollback()
        log_error(f"Erreur MAJ compte pro {user_id}: {e}")
        AuditLogService.log_event(action="B2B_ACCOUNT_UPDATE_SERVER_ERROR", target_type="USER", target_id=user_id, details={"error": str(e)}, success=False)
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
        # Added status and paid_date to the SELECT query
        cursor.execute(
            """SELECT invoice_id, invoice_number, invoice_date, total_amount_ttc, file_path, status, paid_date
               FROM invoices 
               WHERE user_id = ? 
               ORDER BY invoice_date DESC""",
            (user_id,)
        )
        invoices_data = []
        for row in cursor.fetchall():
            invoice_dict = dict(row)
            # Ensure download_url is correctly formed if needed by frontend,
            # but frontend might construct it using API_BASE_URL and invoice_id.
            # invoice_dict['download_url'] = url_for('professional_bp_routes.download_professional_invoice', invoice_id=row['invoice_id'], _external=False) # Relative URL
            invoices_data.append(invoice_dict)
        
        AuditLogService.log_event(action="B2B_INVOICES_LISTED", target_type="USER", target_id=user_id)
        return jsonify({"success": True, "invoices": invoices_data}), 200
    except Exception as e:
        log_error(f"Erreur listage factures pro {user_id}: {e}")
        AuditLogService.log_event(action="B2B_INVOICES_LIST_ERROR", target_type="USER", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération des factures."}), 500
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
            AuditLogService.log_event(action="B2B_INVOICE_DOWNLOAD_NOT_FOUND", target_type="INVOICE", target_id=invoice_id, success=False)
            return jsonify({"success": False, "message": "Facture non trouvée ou accès non autorisé."}), 404

        invoices_dir = current_app.config.get('INVOICES_UPLOAD_DIR')
        if not invoices_dir or not os.path.isdir(invoices_dir): # Check if directory exists
            log_error("INVOICES_UPLOAD_DIR n'est pas configuré ou n'est pas un répertoire valide.")
            AuditLogService.log_event(action="B2B_INVOICE_DOWNLOAD_CONFIG_ERROR", target_type="INVOICE", target_id=invoice_id, success=False)
            return jsonify({"success": False, "message": "Configuration serveur incorrecte pour le téléchargement des factures."}), 500

        safe_filename = os.path.basename(invoice_record['file_path']) # Basic sanitization
        full_file_path = os.path.join(invoices_dir, safe_filename)

        if not os.path.isfile(full_file_path):
            log_error(f"Invoice file not found on disk: {full_file_path} for invoice_id {invoice_id}")
            AuditLogService.log_event(action="B2B_INVOICE_DOWNLOAD_FILE_MISSING_DISK", target_type="INVOICE", target_id=invoice_id, success=False)
            return jsonify({"success": False, "message": "Fichier facture non trouvé sur le serveur."}), 404

        current_app.logger.info(f"Attempting to download: {safe_filename} from {invoices_dir} for user {user_id}, invoice {invoice_id}")
        AuditLogService.log_event(action="B2B_INVOICE_DOWNLOADED", target_type="INVOICE", target_id=invoice_id, details={"filename": safe_filename})
        return send_from_directory(invoices_dir, safe_filename, as_attachment=True, download_name=f"{invoice_record['invoice_number']}.pdf")

    except Exception as e:
        log_error(f"Erreur téléchargement facture {invoice_id} user {user_id}: {e}")
        AuditLogService.log_event(action="B2B_INVOICE_DOWNLOAD_SERVER_ERROR", target_type="INVOICE", target_id=invoice_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors du téléchargement de la facture."}), 500
    finally:
        if db: db.close()
