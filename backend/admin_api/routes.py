# backend/admin_api/routes.py
from flask import Blueprint, request, jsonify, current_app, g, url_for # Added g
from werkzeug.utils import secure_filename # For file uploads
import os # For path operations
import datetime # For date handling
import sqlite3
import json
from ..database import get_db, record_stock_movement
from ..auth.routes import admin_required
from ..services.invoice_service import generate_invoice_pdf_to_file, calculate_invoice_totals_service # New import
import json # Ensure json is imported

admin_api_bp = Blueprint('admin_api_bp_routes', __name__) # KEEP THIS NAME CONSISTENT

# ... (existing product, inventory, user routes from previous steps) ...

ALLOWED_EXTENSIONS = {'pdf'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Add to backend/admin_api/routes.py
@admin_api_bp.route('/users/pending-b2b', methods=['GET'])
@admin_required
def list_pending_b2b_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, email, company_name, nom, prenom, created_at FROM users WHERE user_type = 'b2b' AND is_approved = FALSE AND status = 'pending_approval'")
    pending_users = [dict(row) for row in cursor.fetchall()]
    return jsonify({"success": True, "users": pending_users})

@admin_api_bp.route('/users/<int:user_id>/approve-b2b', methods=['POST'])
@admin_required
def approve_b2b_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_approved = TRUE, status = 'active' WHERE id = ? AND user_type = 'b2b'", (user_id,))
    db.commit()
    if cursor.rowcount > 0:
        # TODO: Send notification email to user
        current_app.logger.info(f"Utilisateur B2B ID {user_id} approuvé par admin {g.admin_user_id}.")
        return jsonify({"success": True, "message": "Utilisateur B2B approuvé."})
    return jsonify({"success": False, "message": "Utilisateur non trouvé ou déjà approuvé."}), 404



@admin_api_bp.route('/dashboard-stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        # Produits Actifs (Published)
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_published = TRUE")
        total_products = cursor.fetchone()[0]

        # Commandes Récentes (dernières 24h)
        twenty_four_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=24)
        cursor.execute("SELECT COUNT(*) FROM orders WHERE order_date >= ?", (twenty_four_hours_ago,))
        recent_orders = cursor.fetchone()[0]

        # Nouveaux Utilisateurs (cette semaine)
        today = datetime.date.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (start_of_week,))
        new_users = cursor.fetchone()[0]

        # Mock Notifications (replace with actual notification system if developed)
        notifications = [
            {"id": 1, "message": "Nouvelle commande #TRUVRA123 reçue.", "timestamp": datetime.datetime.now().isoformat(), "read": False},
            {"id": 2, "message": "Stock bas pour 'Huile à la Truffe'.", "timestamp": (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(), "read": True}
        ]

        return jsonify({
            "success": True,
            "stats": {
                "total_products": total_products,
                "recent_orders": recent_orders,
                "new_users": new_users
            },
            "notifications": notifications # Replace with actual notification fetching
        })
    except Exception as e:
        current_app.logger.error(f"Erreur récupération stats dashboard: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()
            
@admin_api_bp.route('/invoices/upload', methods=['POST'])
@admin_required
def upload_invoice():
    # ... (existing code for uploading pre-made PDFs - no changes needed here from last version)
    admin_uploader_id = getattr(g, 'admin_user_id', None)
    if 'invoice_file' not in request.files:
        return jsonify({"success": False, "message": "Aucun fichier de facture sélectionné."}), 400

    file = request.files['invoice_file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Aucun fichier sélectionné."}), 400

    if file and allowed_file(file.filename): # Define allowed_file if not present
        b2b_user_id = request.form.get('user_id')
        invoice_number = request.form.get('invoice_number')
        invoice_date_str = request.form.get('invoice_date')
        total_amount_ht_str = request.form.get('total_amount_ht')
        total_amount_ttc_str = request.form.get('total_amount_ttc')
        discount_percentage_str = request.form.get('discount_percentage', '0')

        if not all([b2b_user_id, invoice_number, invoice_date_str, total_amount_ht_str, total_amount_ttc_str]):
            return jsonify({"success": False, "message": "Données de facture manquantes (user_id, numéro, date, montants)."}), 400

        try:
            invoice_date = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
            total_amount_ht = float(total_amount_ht_str)
            total_amount_ttc = float(total_amount_ttc_str)
            discount_percentage = float(discount_percentage_str)
        except ValueError:
            return jsonify({"success": False, "message": "Format de date ou de montant invalide."}), 400

        filename = secure_filename(f"{invoice_number}.pdf") # Use invoice_number for filename consistency
        upload_folder = current_app.config['INVOICES_UPLOAD_DIR']
        os.makedirs(upload_folder, exist_ok=True) # Ensure directory exists
        file_save_path = os.path.join(upload_folder, filename)

        db_check = get_db()
        cursor_check = db_check.cursor()
        cursor_check.execute("SELECT invoice_id FROM invoices WHERE invoice_number = ?", (invoice_number,))
        if cursor_check.fetchone():
            db_check.close()
            return jsonify({"success": False, "message": f"Une facture avec le numéro '{invoice_number}' existe déjà."}), 409
        db_check.close()

        file.save(file_save_path)
        db = None
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                """INSERT INTO invoices (user_id, invoice_number, invoice_date, total_amount_ht, total_amount_ttc, discount_percentage, file_path, admin_uploader_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (b2b_user_id, invoice_number, invoice_date, total_amount_ht, total_amount_ttc, discount_percentage, filename, admin_uploader_id)
            )
            invoice_id = cursor.lastrowid
            # If line items were part of the form data for an UPLOADED PDF (e.g. if admin wants to log them too)
            # items_data_json = request.form.get('invoice_items_json', '[]') # Expecting JSON string
            # invoice_items = json.loads(items_data_json)
            # for item in invoice_items:
            #    cursor.execute(
            #        """INSERT INTO invoice_items (invoice_id, product_name, quantity, unit_price_ht, total_price_ht)
            #           VALUES (?, ?, ?, ?, ?)""",
            #        (invoice_id, item['description'], item['quantity'], item['unit_price_ht'], float(item['quantity']) * float(item['unit_price_ht']))
            #    )
            db.commit()
            current_app.logger.info(f"Facture {invoice_number} téléversée pour user {b2b_user_id}")
            return jsonify({"success": True, "message": "Facture téléversée avec succès.", "invoice_id": invoice_id, "file_path": filename}), 201
        except Exception as e:
            if db: db.rollback()
            if os.path.exists(file_save_path): os.remove(file_save_path)
            current_app.logger.error(f"Erreur DB lors de l'upload de facture: {e}", exc_info=True)
            return jsonify({"success": False, "message": f"Erreur de base de données: {e}"}), 500
        finally:
            if db: db.close()
    else:
        return jsonify({"success": False, "message": "Type de fichier non autorisé."}), 400


@admin_api_bp.route('/invoices/generate-and-save', methods=['POST'])
@admin_required
def generate_and_save_invoice():
    admin_user_id = getattr(g, 'admin_user_id', None)
    data = request.get_json()

    client_data = data.get('client_data') # Expecting {"company_name": "...", "contact_person": "...", "address_lines": [], "vat_number": "..."}
    invoice_meta = data.get('invoice_meta') # Expecting {"number": "...", "date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD", "discount_percentage_str": "5", "vat_rate_percent_str": "20"}
    items_data = data.get('items_data') # Expecting list of {"description": "...", "quantity": X, "unit_price_ht": Y}

    if not all([client_data, invoice_meta, items_data and isinstance(items_data, list) and len(items_data) > 0]):
        return jsonify({"success": False, "message": "Données client, méta-données de facture et articles de facture sont requis."}), 400
    if not invoice_meta.get('number') or not invoice_meta.get('date') or not invoice_meta.get('due_date'):
        return jsonify({"success": False, "message": "Numéro, date et date d'échéance de la facture sont requis."}), 400

    b2b_user_id = data.get('user_id')
    if not b2b_user_id:
        return jsonify({"success": False, "message": "ID utilisateur B2B manquant."}), 400

    try:
        invoice_date_obj = datetime.datetime.strptime(invoice_meta['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "message": "Format de date de facture invalide (AAAA-MM-JJ attendu)."}), 400

    # Calculate totals
    calculated_totals = calculate_invoice_totals_service(
        items_data,
        invoice_meta.get('discount_percentage_str', "0"),
        invoice_meta.get('vat_rate_percent_str', "20")
    )

    invoice_data_for_pdf = {
        "number": invoice_meta['number'],
        "date": invoice_meta['date'],
        "due_date": invoice_meta['due_date'],
        **calculated_totals
    }

    pdf_filename_base = secure_filename(f"{invoice_meta['number']}.pdf")
    upload_folder = current_app.config['INVOICES_UPLOAD_DIR']
    os.makedirs(upload_folder, exist_ok=True)
    pdf_filepath_absolute = os.path.join(upload_folder, pdf_filename_base)

    # Check if invoice number already exists in DB
    db_check = get_db()
    cursor_check = db_check.cursor()
    cursor_check.execute("SELECT invoice_id FROM invoices WHERE invoice_number = ?", (invoice_meta['number'],))
    if cursor_check.fetchone():
        db_check.close()
        return jsonify({"success": False, "message": f"Une facture avec le numéro '{invoice_meta['number']}' existe déjà."}), 409
    db_check.close()

    # Generate PDF
    try:
        generate_invoice_pdf_to_file(pdf_filepath_absolute, client_data, invoice_data_for_pdf, items_data)
    except Exception as e_pdf:
        current_app.logger.error(f"Erreur lors de la génération du PDF de la facture {invoice_meta['number']}: {e_pdf}", exc_info=True)
        return jsonify({"success": False, "message": f"Erreur lors de la génération du PDF: {e_pdf}"}), 500

    # Store invoice metadata and items in database
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO invoices (user_id, invoice_number, invoice_date, 
                               total_amount_ht, total_amount_ttc, discount_percentage, 
                               file_path, admin_uploader_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (b2b_user_id, invoice_meta['number'], invoice_date_obj, 
             calculated_totals['total_ht_after_discount'], calculated_totals['total_ttc'], calculated_totals['discount_percent'],
             pdf_filename_base, admin_user_id)
        )
        invoice_id = cursor.lastrowid

        for item in items_data:
            cursor.execute(
               """INSERT INTO invoice_items (invoice_id, product_name, quantity, unit_price_ht, total_price_ht)
                  VALUES (?, ?, ?, ?, ?)""",
               (invoice_id, item['description'], item['quantity'], item['unit_price_ht'], 
                float(item['quantity']) * float(item['unit_price_ht']))
            )
        db.commit()

        current_app.logger.info(f"Facture {invoice_meta['number']} (ID: {invoice_id}) générée, sauvegardée et enregistrée pour user {b2b_user_id} par admin {admin_user_id}")

        # Return path relative to static folder for viewing/downloading
        static_file_path = os.path.join(current_app.config.get('INVOICES_SUBDIR_FROM_STATIC', 'invoices_uploads'), pdf_filename_base).replace("\\","/")


        return jsonify({
            "success": True, 
            "message": "Facture générée, sauvegardée et enregistrée avec succès.", 
            "invoice_id": invoice_id, 
            "file_path": pdf_filename_base, # Filename for reference
            "download_url": url_for('static', filename=static_file_path, _external=True) # If INVOICES_UPLOAD_DIR is under static
        }), 201

    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur DB lors de la sauvegarde de la facture générée {invoice_meta['number']}: {e}", exc_info=True)
        if os.path.exists(pdf_filepath_absolute): # Clean up generated PDF if DB save fails
             try: os.remove(pdf_filepath_absolute)
             except Exception as e_rm: current_app.logger.error(f"Failed to remove temp PDF {pdf_filepath_absolute}: {e_rm}")
        return jsonify({"success": False, "message": f"Erreur de base de données: {e}"}), 500
    finally:
        if db: db.close()


# Add GET and DELETE for invoices in admin if needed (similar to other admin routes)
@admin_api_bp.route('/users/<int:user_id>/invoices', methods=['GET'])
@admin_required
def get_user_invoices_admin(user_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT invoice_id, invoice_number, invoice_date, total_amount_ttc, file_path, uploaded_at FROM invoices WHERE user_id = ? ORDER BY invoice_date DESC", (user_id,))
        invoices = [dict(row) for row in cursor.fetchall()]
        return jsonify({"success": True, "invoices": invoices}), 200
    except Exception as e:
        current_app.logger.error(f"Erreur listage factures pour user {user_id} (admin): {e}")
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@admin_required
def delete_invoice_admin(invoice_id):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT file_path FROM invoices WHERE invoice_id = ?", (invoice_id,))
        invoice_record = cursor.fetchone()
        if not invoice_record:
            return jsonify({"success": False, "message": "Facture non trouvée."}), 404

        cursor.execute("DELETE FROM invoices WHERE invoice_id = ?", (invoice_id,))
        # Also delete invoice_items associated if any
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        db.commit()

        # Delete the actual file
        file_to_delete = os.path.join(current_app.config['INVOICES_UPLOAD_DIR'], os.path.basename(invoice_record['file_path']))
        if os.path.exists(file_to_delete):
            os.remove(file_to_delete)
            current_app.logger.info(f"Fichier facture {invoice_record['file_path']} supprimé.")

        current_app.logger.info(f"Facture ID {invoice_id} supprimée par admin.")
        return jsonify({"success": True, "message": "Facture supprimée avec succès."}), 200
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur suppression facture {invoice_id} (admin): {e}")
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


@admin_api_bp.route('/products', methods=['POST'])
@admin_required
def create_product():
    data = request.get_json()
    # Ensure all required base fields and at least one language for name are present
    required_fields = ['id', 'category', 'image_url_main'] # Base requirements
    if not all(field in data for field in required_fields) or not (data.get('name_fr') or data.get('name_en')):
        return jsonify({"success": False, "message": "Champs requis manquants (id, category, image_url_main, name_fr ou name_en)."}), 400

    product_id = data['id']
    # Prepare localized data, defaulting one to the other if one is missing
    name_fr = data.get('name_fr', data.get('name_en', 'Nom non fourni'))
    name_en = data.get('name_en', data.get('name_fr', 'Name not provided'))
    short_description_fr = data.get('short_description_fr', data.get('short_description_en', ''))
    short_description_en = data.get('short_description_en', data.get('short_description_fr', ''))
    # ... repeat for all translatable fields ...
    long_description_fr = data.get('long_description_fr', data.get('long_description_en', ''))
    long_description_en = data.get('long_description_en', data.get('long_description_fr', ''))
    species_fr = data.get('species_fr', data.get('species_en', None))
    species_en = data.get('species_en', data.get('species_fr', None))
    origin_fr = data.get('origin_fr', data.get('origin_en', None))
    origin_en = data.get('origin_en', data.get('origin_fr', None))
    seasonality_fr = data.get('seasonality_fr', data.get('seasonality_en', None))
    seasonality_en = data.get('seasonality_en', data.get('seasonality_fr', None))
    ideal_uses_fr = data.get('ideal_uses_fr', data.get('ideal_uses_en', None))
    ideal_uses_en = data.get('ideal_uses_en', data.get('ideal_uses_fr', None))
    sensory_description_fr = data.get('sensory_description_fr', data.get('sensory_description_en', None))
    sensory_description_en = data.get('sensory_description_en', data.get('sensory_description_fr', None))
    pairing_suggestions_fr = data.get('pairing_suggestions_fr', data.get('pairing_suggestions_en', None))
    pairing_suggestions_en = data.get('pairing_suggestions_en', data.get('pairing_suggestions_fr', None))

    category = data['category']
    image_url_main = data['image_url_main']
    image_urls_thumb_list = data.get('image_urls_thumb', [])
    image_urls_thumb_json = json.dumps(image_urls_thumb_list) if isinstance(image_urls_thumb_list, list) else '[]'

    base_price = data.get('base_price')
    initial_stock_quantity = int(data.get('initial_stock_quantity', 0))
    is_published = bool(data.get('is_published', True))
    weight_options = data.get('weight_options', [])

    # Asset data preparation
    numero_lot_manuel = data.get('numero_lot_manuel', f"LOT-{product_id}-{datetime.date.today().strftime('%Y%m%d')}")
    date_conditionnement = data.get('date_conditionnement', datetime.date.today().isoformat())
    default_ddm = (datetime.date.today() + datetime.timedelta(days=365*2)).isoformat()
    ddm = data.get('ddm', default_ddm)
    poids_net_final_g = data.get('specific_weight_for_label', "Voir emballage" if weight_options else "N/A")


    # Create dicts for passport generation
    asset_product_data_fr = {
        "id": product_id, "name": name_fr, "species": species_fr, "origin": origin_fr,
        "seasonality": seasonality_fr, "ideal_uses": ideal_uses_fr,
        "sensory_description": sensory_description_fr, "pairing_suggestions": pairing_suggestions_fr,
        "numero_lot_manuel": numero_lot_manuel, "date_conditionnement": date_conditionnement, "ddm": ddm,
        "poids_net_final_g": poids_net_final_g,
        "ingredients_affichage": data.get('ingredients_for_label_fr', "Consultez l'emballage du produit."),
        "logo_url": url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)
    }
    asset_product_data_en = {
        "id": product_id, "name": name_en, "species": species_en, "origin": origin_en,
        "seasonality": seasonality_en, "ideal_uses": ideal_uses_en,
        "sensory_description": sensory_description_en, "pairing_suggestions": pairing_suggestions_en,
        "numero_lot_manuel": numero_lot_manuel, "date_conditionnement": date_conditionnement, "ddm": ddm,
        "poids_net_final_g": poids_net_final_g, # Assuming poids_net_final_g is not language specific for this asset
        "ingredients_affichage": data.get('ingredients_for_label_en', "Please see packaging."),
        "logo_url": url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)
    }


    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        admin_user_id = getattr(g, 'admin_user_id', None)

        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": f"L'ID produit '{product_id}' existe déjà."}), 409

        passport_public_url, qr_code_relative_path, label_relative_path = None, None, None
        passport_html_content = generate_product_passport_html_content(asset_product_data_fr, asset_product_data_en) # Pass both lang data
        passport_file_rel_path = save_product_passport_html(passport_html_content, product_id)

        if passport_file_rel_path:
            passport_public_url = f"{current_app.config['PASSPORT_BASE_URL'].rstrip('/')}/{os.path.basename(passport_file_rel_path)}"
            qr_code_relative_path = generate_qr_code_for_passport(passport_public_url, product_id)
            if qr_code_relative_path:
                # Label generation might also need localized data or a strategy for bilingual labels
                label_relative_path = generate_product_label_image(asset_product_data_fr, asset_product_data_en, qr_code_relative_path)


        cursor.execute("""
            INSERT INTO products (
                id, name_fr, name_en, category,
                short_description_fr, short_description_en,
                long_description_fr, long_description_en,
                image_url_main, image_urls_thumb,
                species_fr, species_en, origin_fr, origin_en,
                seasonality_fr, seasonality_en, ideal_uses_fr, ideal_uses_en,
                sensory_description_fr, sensory_description_en,
                pairing_suggestions_fr, pairing_suggestions_en,
                base_price, stock_quantity, is_published,
                passport_url, qr_code_path, label_path,
                created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            product_id, name_fr, name_en, category,
            short_description_fr, short_description_en,
            long_description_fr, long_description_en,
            image_url_main, image_urls_thumb_json,
            species_fr, species_en, origin_fr, origin_en,
            seasonality_fr, seasonality_en, ideal_uses_fr, ideal_uses_en,
            sensory_description_fr, sensory_description_en,
            pairing_suggestions_fr, pairing_suggestions_en,
            base_price, 0 if weight_options else initial_stock_quantity, is_published,
            passport_public_url, qr_code_relative_path, label_relative_path
        ))

        if not weight_options and base_price is not None and initial_stock_quantity > 0:
            record_stock_movement(cursor, product_id, initial_stock_quantity, 'initial_stock',
                                  notes=f"Stock initial pour {product_id}", user_id=admin_user_id)
            cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (initial_stock_quantity, product_id))

        if weight_options:
            total_variant_stock = 0
            for option in weight_options:
                if not all(k in option for k in ['weight_grams', 'price', 'initial_stock']):
                    raise ValueError("Option de poids mal formatée.")
                opt_stock = int(option['initial_stock'])
                cursor.execute("""
                    INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity)
                    VALUES (?, ?, ?, ?)
                """, (product_id, int(option['weight_grams']), float(option['price']), 0 ))
                variant_option_id = cursor.lastrowid
                if opt_stock > 0:
                    record_stock_movement(cursor, product_id, opt_stock, 'initial_stock',
                                          variant_option_id=variant_option_id,
                                          notes=f"Stock initial pour variante {option['weight_grams']}g de {product_id}",
                                          user_id=admin_user_id)
                    cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE option_id = ?", (opt_stock, variant_option_id))
                total_variant_stock += opt_stock
            cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (total_variant_stock, product_id))

        db.commit()
        current_app.logger.info(f"Produit '{product_id}' (localisé) créé par admin {admin_user_id or 'System'}. Actifs générés.")

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        created_product_row = cursor.fetchone()
        if not created_product_row: # Should not happen if insert was successful
             return jsonify({"success": False, "message": "Erreur lors de la récupération du produit créé."}), 500
        created_product_dict = dict(created_product_row)

        if weight_options:
             cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_id,))
             created_product_dict['weight_options'] = [dict(row) for row in cursor.fetchall()]

        created_product_dict['assets'] = {
            "passport_url": passport_public_url,
            "qr_code_file_path": qr_code_relative_path,
            "label_file_path": label_relative_path
        }
        return jsonify({"success": True, "message": "Produit créé et actifs générés avec succès.", "product": created_product_dict}), 201

    except sqlite3.IntegrityError as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur d'intégrité DB: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"Erreur de base de données: {e}"}), 409
    except ValueError as ve:
        if db: db.rollback()
        current_app.logger.error(f"Erreur de valeur: {ve}", exc_info=True)
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur serveur: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur interne lors de la création du produit ou des actifs."}), 500
    finally:
        if db: db.close()


@admin_api_bp.route('/products/<string:product_id_to_update>', methods=['PUT'])
@admin_required
def update_product(product_id_to_update):
    data = request.get_json()
    db = None
    admin_user_id = getattr(g, 'admin_user_id', None)
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id_to_update,))
        product = cursor.fetchone()
        if not product:
            return jsonify({"success": False, "message": "Produit non trouvé."}), 404

        update_fields_sql_parts = []
        update_values = []

        # Define allowed fields for direct update on 'products' table, including localized versions
        allowed_product_fields = [
            'name_fr', 'name_en', 'category',
            'short_description_fr', 'short_description_en',
            'long_description_fr', 'long_description_en',
            'image_url_main',
            'species_fr', 'species_en', 'origin_fr', 'origin_en',
            'seasonality_fr', 'seasonality_en', 'ideal_uses_fr', 'ideal_uses_en',
            'sensory_description_fr', 'sensory_description_en',
            'pairing_suggestions_fr', 'pairing_suggestions_en',
            'base_price', 'is_published'
        ]

        for field in allowed_product_fields:
            if field in data:
                update_fields_sql_parts.append(f"{field} = ?")
                update_values.append(data[field])

        if 'image_urls_thumb' in data:
            if isinstance(data['image_urls_thumb'], list):
                update_fields_sql_parts.append("image_urls_thumb = ?")
                update_values.append(json.dumps(data['image_urls_thumb']))
            elif data['image_urls_thumb'] is None:
                update_fields_sql_parts.append("image_urls_thumb = ?")
                update_values.append('[]')

        if update_fields_sql_parts:
            update_fields_sql_parts.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(product_id_to_update)
            sql_update_product = f"UPDATE products SET {', '.join(update_fields_sql_parts)} WHERE id = ?"
            cursor.execute(sql_update_product, tuple(update_values))

        # (Weight options handling remains largely the same as before, ensure it uses product_id_to_update)
        # ... (Keep existing weight option logic, making sure it uses product_id_to_update)

        db.commit()
        current_app.logger.info(f"Produit '{product_id_to_update}' (localisé) mis à jour par admin {admin_user_id or 'System'}.")

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id_to_update,))
        updated_product_row = cursor.fetchone()
        if not updated_product_row:
             return jsonify({"success": False, "message": "Erreur lors de la récupération du produit mis à jour."}), 500
        updated_product_dict = dict(updated_product_row)

        cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_id_to_update,))
        updated_product_dict['weight_options'] = [dict(row) for row in cursor.fetchall()]

        # Re-generate assets if relevant fields changed (name, descriptions for passport/label etc.)
        # For simplicity, we can choose to regenerate them on every update, or add more complex logic
        # to detect changes. Here we regenerate:
        asset_product_data_fr_upd = {key.replace('_fr',''): val for key, val in updated_product_dict.items() if key.endswith('_fr')}
        asset_product_data_fr_upd['id'] = updated_product_dict['id']
        asset_product_data_fr_upd['name'] = updated_product_dict['name_fr'] # Ensure 'name' key exists
        # ... populate other necessary fields for asset_product_data_fr_upd from updated_product_dict ...
        asset_product_data_fr_upd['logo_url'] = url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)


        asset_product_data_en_upd = {key.replace('_en',''): val for key, val in updated_product_dict.items() if key.endswith('_en')}
        asset_product_data_en_upd['id'] = updated_product_dict['id']
        asset_product_data_en_upd['name'] = updated_product_dict['name_en'] # Ensure 'name' key exists
        # ... populate other necessary fields for asset_product_data_en_upd ...
        asset_product_data_en_upd['logo_url'] = url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)


        # Use existing or default values if not present in updated_product_dict for asset generation
        default_asset_values = {
            "numero_lot_manuel": f"LOT-{product_id_to_update}-{datetime.date.today().strftime('%Y%m%d')}",
            "date_conditionnement": datetime.date.today().isoformat(),
            "ddm": (datetime.date.today() + datetime.timedelta(days=365*2)).isoformat(),
            "poids_net_final_g": "Voir emballage" if updated_product_dict.get('weight_options') else "N/A",
            "ingredients_affichage": "Consultez l'emballage"
        }
        for key, val in default_asset_values.items():
            asset_product_data_fr_upd.setdefault(key, val)
            asset_product_data_en_upd.setdefault(key, val)


        passport_html_content_upd = generate_product_passport_html_content(asset_product_data_fr_upd, asset_product_data_en_upd)
        passport_file_rel_path_upd = save_product_passport_html(passport_html_content_upd, product_id_to_update)
        passport_public_url_upd, qr_code_relative_path_upd, label_relative_path_upd = None, None, None

        if passport_file_rel_path_upd:
            passport_public_url_upd = f"{current_app.config['PASSPORT_BASE_URL'].rstrip('/')}/{os.path.basename(passport_file_rel_path_upd)}"
            qr_code_relative_path_upd = generate_qr_code_for_passport(passport_public_url_upd, product_id_to_update)
            if qr_code_relative_path_upd:
                label_relative_path_upd = generate_product_label_image(asset_product_data_fr_upd,asset_product_data_en_upd, qr_code_relative_path_upd)

            cursor.execute("""
                UPDATE products SET passport_url = ?, qr_code_path = ?, label_path = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (passport_public_url_upd, qr_code_relative_path_upd, label_relative_path_upd, product_id_to_update))
            db.commit()
            updated_product_dict['passport_url'] = passport_public_url_upd
            updated_product_dict['qr_code_path'] = qr_code_relative_path_upd
            updated_product_dict['label_path'] = label_relative_path_upd


        updated_product_dict['assets'] = {
            "passport_url": passport_public_url_upd,
            "qr_code_file_path": qr_code_relative_path_upd,
            "label_file_path": label_relative_path_upd
        }

        return jsonify({"success": True, "message": "Produit mis à jour et actifs regénérés.", "product": updated_product_dict})

    except ValueError as ve:
        if db: db.rollback()
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur serveur MAJ produit {product_id_to_update}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur interne."}), 500
    finally:
        if db: db.close()


# Ensure other admin routes (/products GET, /products/<id> GET, inventory, users, orders) are similarly
# adapted if they need to display or handle localized product names or descriptions.
# For example, when listing products in the admin panel, you might choose to display only the French name
# or allow the admin to select a display language for the panel itself.

@admin_api_bp.route('/products', methods=['GET'])
@admin_required
def list_admin_products():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Fetch both fr and en names, and other relevant fields
        cursor.execute("""
            SELECT p.id, p.name_fr, p.name_en, p.category, p.base_price, p.is_published, p.updated_at,
                   (SELECT COUNT(*) FROM product_weight_options WHERE product_id = p.id) as variant_count,
                   (SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = p.id) as total_variant_stock
            FROM products p
            ORDER BY p.updated_at DESC
        """)
        products_rows = cursor.fetchall()
        products_list = []
        for row_data in products_rows:
            prod_dict = dict(row_data)
            if prod_dict['base_price'] is None and prod_dict['variant_count'] > 0:
                 prod_dict['stock_quantity'] = prod_dict['total_variant_stock'] if prod_dict['total_variant_stock'] is not None else 0
            else: # For simple products, get stock_quantity from products table (already selected as part of p.*)
                 cursor.execute("SELECT stock_quantity FROM products WHERE id = ?", (prod_dict['id'],))
                 simple_stock_row = cursor.fetchone()
                 prod_dict['stock_quantity'] = simple_stock_row['stock_quantity'] if simple_stock_row else 0


            prod_dict.pop('total_variant_stock', None)
            products_list.append(prod_dict)

        return jsonify(products_list)
    except Exception as e:
        current_app.logger.error(f"Erreur listage produits admin: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


@admin_api_bp.route('/products/<string:product_id_param>', methods=['GET'])
@admin_required
def get_admin_product_details(product_id_param): # Renamed param to avoid conflict
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Fetch all fields, including new localized ones and asset paths
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id_param,))
        product_row = cursor.fetchone()

        if not product_row:
            return jsonify({"success": False, "message": "Produit non trouvé"}), 404

        product_dict = dict(product_row)

        cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ? ORDER BY weight_grams ASC", (product_id_param,))
        product_dict['weight_options'] = [dict(row_option) for row_option in cursor.fetchall()]

        if product_dict.get('image_urls_thumb'):
            try:
                product_dict['image_urls_thumb'] = json.loads(product_dict['image_urls_thumb'])
            except (json.JSONDecodeError, TypeError):
                product_dict['image_urls_thumb'] = []
        else:
            product_dict['image_urls_thumb'] = []

        product_dict['assets'] = {
            "passport_url": product_dict.get("passport_url"),
            "qr_code_file_path": product_dict.get("qr_code_path"),
            "label_file_path": product_dict.get("label_path")
        }

        return jsonify(product_dict)
    except Exception as e:
        current_app.logger.error(f"Erreur récupération produit admin {product_id_param}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


# Other admin routes (inventory, users, orders) are kept as is for brevity,
# but would need similar i18n considerations if they display product names.
# (Keep existing /inventory/adjust, /inventory/product/<id>, /users, /users/<id>, /orders, /orders/<id>, /orders/<id>/status, /orders/<id>/notes)

@admin_api_bp.route('/inventory/adjust', methods=['POST'])
@admin_required
def adjust_inventory():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_option_id = data.get('variant_option_id')
    quantity_change_str = data.get('quantity_change')
    movement_type = data.get('movement_type')
    notes = data.get('notes', '')
    admin_user_id = getattr(g, 'admin_user_id', None)

    if not all([product_id, quantity_change_str is not None, movement_type]):
        return jsonify({"success": False, "message": "Champs product_id, quantity_change, et movement_type sont requis."}), 400
    try:
        quantity_change = int(quantity_change_str)
    except ValueError:
        return jsonify({"success": False, "message": "quantity_change doit être un nombre entier."}), 400

    allowed_adjustment_types = ['initial_stock', 'addition', 'vente', 'ajustement_manuel', 'creation_lot', 'retour_client', 'perte', 'correction']
    if movement_type not in allowed_adjustment_types:
        return jsonify({"success": False, "message": f"Type de mouvement '{movement_type}' invalide."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        if quantity_change > 0 and movement_type in ['perte', 'vente']:
             return jsonify({"success": False, "message": f"Pour '{movement_type}', quantity_change doit être négatif ou nul."}), 400
        if quantity_change < 0 and movement_type in ['initial_stock', 'addition', 'creation_lot', 'retour_client']:
             return jsonify({"success": False, "message": f"Pour '{movement_type}', quantity_change doit être positif ou nul."}), 400

        record_stock_movement(cursor, product_id, quantity_change, movement_type,
                              variant_option_id=variant_option_id or None, notes=notes, user_id=admin_user_id)
        db.commit()
        return jsonify({"success": True, "message": "Stock ajusté avec succès."}), 200
    except ValueError as ve:
        if db: db.rollback()
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur ajustement stock: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur interne."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/inventory/product/<string:product_id_param>', methods=['GET'])
@admin_required
def get_admin_inventory_for_product(product_id_param):
    from ..inventory.routes import get_product_inventory_details
    return get_product_inventory_details(product_id_param)


@admin_api_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, nom, prenom, is_admin, created_at FROM users ORDER BY created_at DESC")
        users = [dict(row) for row in cursor.fetchall()]
        return jsonify(users)
    except Exception as e:
        current_app.logger.error(f"Erreur listage utilisateurs: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/users/<int:user_id_param>', methods=['GET'])
@admin_required
def get_user_details(user_id_param):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, nom, prenom, is_admin, created_at FROM users WHERE id = ?", (user_id_param,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "Utilisateur non trouvé."}), 404

        cursor.execute("SELECT order_id, total_amount, order_date, status FROM orders WHERE user_id = ? ORDER BY order_date DESC", (user_id_param,))
        orders = [dict(row) for row in cursor.fetchall()]

        user_details_dict = dict(user)
        user_details_dict['orders'] = orders

        return jsonify(user_details_dict)
    except Exception as e:
        current_app.logger.error(f"Erreur récupération détails utilisateur {user_id_param}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/orders', methods=['GET'])
@admin_required
def list_admin_orders():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()

        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '')

        query = "SELECT order_id, user_id, customer_email, customer_name, total_amount, order_date, status FROM orders"
        conditions = []
        params = []

        if search_query:
            conditions.append("(CAST(order_id AS TEXT) LIKE ? OR customer_email LIKE ? OR customer_name LIKE ?)") # Cast order_id to TEXT for LIKE
            like_search = f"%{search_query}%"
            params.extend([like_search, like_search, like_search])
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        if date_filter:
            conditions.append("date(order_date) = ?")
            params.append(date_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY order_date DESC"

        cursor.execute(query, tuple(params))
        orders = [dict(row) for row in cursor.fetchall()]
        return jsonify(orders)
    except Exception as e:
        current_app.logger.error(f"Erreur listage commandes admin: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


@admin_api_bp.route('/orders/<string:order_id_param>', methods=['GET'])
@admin_required
def get_admin_order_details(order_id_param): # order_id can be TRUVRAXXXXX
    db = None
    actual_order_id = order_id_param
    if isinstance(order_id_param, str) and order_id_param.upper().startswith("TRUVRA"):
        try:
            actual_order_id = int(order_id_param[len("TRUVRA"):])
        except ValueError:
            return jsonify({"success": False, "message": "Format ID de commande invalide."}), 400
    else:
        try:
            actual_order_id = int(order_id_param)
        except ValueError:
             return jsonify({"success": False, "message": "ID de commande doit être numérique ou formaté TRUVRAXXXXX."}), 400
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (actual_order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify({"success": False, "message": "Commande non trouvée."}), 404

        order_dict = dict(order)
        # Fetch items with localized names, assuming 'fr' as primary for admin display for now
        # For a truly bilingual admin, this might also take a lang param
        cursor.execute("""
            SELECT oi.item_id, oi.product_id, oi.product_name_fr, oi.product_name_en, oi.quantity, oi.price_at_purchase, oi.variant, pwo.weight_grams
            FROM order_items oi
            LEFT JOIN product_weight_options pwo ON oi.variant_option_id = pwo.option_id
            WHERE oi.order_id = ?
        """, (actual_order_id,))
        order_dict['items'] = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT note_id, content, created_at, admin_user_id FROM order_notes WHERE order_id = ? ORDER BY created_at ASC", (actual_order_id,))
        notes_raw = cursor.fetchall()
        order_dict['notes'] = []
        for note_row in notes_raw:
            note_dict = dict(note_row)
            note_dict['admin_user'] = f"Admin ID {note_row['admin_user_id']}" if note_row['admin_user_id'] else "Système"
            order_dict['notes'].append(note_dict)

        return jsonify(order_dict)
    except Exception as e:
        current_app.logger.error(f"Erreur récupération détails commande admin {actual_order_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/orders/<int:order_id_param>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id_param):
    data = request.get_json()
    new_status = data.get('status')
    tracking_number = data.get('tracking_number')
    carrier = data.get('carrier')
    admin_user_id = getattr(g, 'admin_user_id', None)


    if not new_status:
        return jsonify({"success": False, "message": "Nouveau statut manquant."}), 400

    allowed_statuses = ['Pending', 'Paid', 'Shipped', 'Delivered', 'Cancelled']
    if new_status not in allowed_statuses:
        return jsonify({"success": False, "message": "Statut invalide."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id_param,))
        current_order = cursor.fetchone()
        if not current_order:
            return jsonify({"success": False, "message": "Commande non trouvée."}), 404

        cursor.execute("UPDATE orders SET status = ?, tracking_number = ?, carrier = ? WHERE order_id = ?",
                       (new_status, tracking_number, carrier, order_id_param))

        note_content = f"Statut changé à '{new_status}'."
        if new_status == 'Shipped':
            note_content += f" Suivi: {tracking_number or 'N/A'} via {carrier or 'N/A'}."

        cursor.execute(
            "INSERT INTO order_notes (order_id, content, admin_user_id) VALUES (?, ?, ?)",
            (order_id_param, note_content, admin_user_id)
        )
        db.commit()
        current_app.logger.info(f"Statut commande {order_id_param} mis à jour à '{new_status}' par admin {admin_user_id or 'System'}.")
        return jsonify({"success": True, "message": "Statut de la commande mis à jour."})
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur MAJ statut commande {order_id_param}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()

@admin_api_bp.route('/orders/<int:order_id_param>/notes', methods=['POST'])
@admin_required
def add_order_note(order_id_param):
    data = request.get_json()
    note_content = data.get('note')
    admin_user_id = getattr(g, 'admin_user_id', None)

    if not note_content or not note_content.strip():
        return jsonify({"success": False, "message": "Contenu de la note manquant."}), 400

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM orders WHERE order_id = ?", (order_id_param,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Commande non trouvée."}), 404

        cursor.execute(
            "INSERT INTO order_notes (order_id, content, admin_user_id) VALUES (?, ?, ?)",
            (order_id_param, note_content, admin_user_id)
        )
        db.commit()
        current_app.logger.info(f"Note ajoutée à la commande {order_id_param} par admin {admin_user_id or 'System'}.")
        return jsonify({"success": True, "message": "Note ajoutée avec succès."}), 201
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur ajout note commande {order_id_param}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()
