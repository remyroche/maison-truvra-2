# backend/admin_api/routes.py
from flask import Blueprint, request, jsonify, current_app, url_for, g
from ..database import get_db, record_stock_movement
from ..auth.routes import admin_required 
import sqlite3
import json
import os
import datetime # Make sure datetime is imported

# Import asset generation functions from the new service layer
from ..services.asset_service import (
    generate_product_passport_html_content, 
    save_product_passport_html,
    generate_qr_code_for_passport, 
    generate_product_label_image
)

admin_api_bp = Blueprint('admin_api_bp_routes', __name__) # Blueprint name should be unique if used elsewhere

# --- Product Management ---
@admin_api_bp.route('/products', methods=['POST'])
@admin_required
def create_product():
    data = request.get_json()
    required_fields = ['id', 'name', 'category', 'short_description', 'image_url_main']
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": "Champs requis manquants pour la création du produit."}), 400

    # Extract all product data from request
    product_id = data['id']
    name = data['name']
    category = data['category']
    short_description = data['short_description']
    long_description = data.get('long_description', '')
    image_url_main = data['image_url_main']
    image_urls_thumb_list = data.get('image_urls_thumb', [])
    image_urls_thumb_json = json.dumps(image_urls_thumb_list) if isinstance(image_urls_thumb_list, list) else '[]'
    species = data.get('species')
    origin = data.get('origin')
    seasonality = data.get('seasonality')
    ideal_uses = data.get('ideal_uses')
    sensory_description = data.get('sensory_description')
    pairing_suggestions = data.get('pairing_suggestions')
    base_price = data.get('base_price') 
    initial_stock_quantity = int(data.get('initial_stock_quantity', 0)) 
    is_published = bool(data.get('is_published', True))
    weight_options = data.get('weight_options', []) 

    # Data for assets - these might need to be more dynamic or part of product creation form
    numero_lot_manuel = data.get('numero_lot_manuel', f"LOT-{product_id}-{datetime.date.today().strftime('%Y%m%d')}")
    date_conditionnement = data.get('date_conditionnement', datetime.date.today().isoformat())
    default_ddm = (datetime.date.today() + datetime.timedelta(days=365*2)).isoformat() # Default DDM: 2 years
    ddm = data.get('ddm', default_ddm)
    
    # Data for label/passport generation
    asset_product_data = {
        "id": product_id, "name": name, "species": species,
        "numero_lot_manuel": numero_lot_manuel,
        "date_conditionnement": date_conditionnement, "ddm": ddm,
        "poids_net_final_g": "Voir emballage" if weight_options else (data.get('specific_weight_for_label') or "N/A"),
        "ingredients_affichage": data.get('ingredients_for_label', "Consultez l'emballage du produit."),
        "logo_url": url_for('static', filename=current_app.config.get('LABEL_LOGO_PATH_STATIC_RELATIVE', 'images/image_6be700.png'), _external=True)
        # Add any other fields your asset generators require
    }

    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        admin_user_id = getattr(g, 'admin_user_id', None) # Get admin_user_id from global context

        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": f"L'ID produit '{product_id}' existe déjà."}), 409

        # Initialize asset paths to None
        passport_public_url = None
        qr_code_relative_path = None # Relative to static folder
        label_relative_path = None   # Relative to static folder

        # Generate assets first (optional: can be done after DB commit if preferred)
        passport_html_content = generate_product_passport_html_content(asset_product_data)
        passport_file_rel_path = save_product_passport_html(passport_html_content, product_id)

        if passport_file_rel_path:
            # Construct public URL for the passport
            # Assumes PASSPORT_BASE_URL ends with '/' or is the site root for static files
            # If PASSPORTS_SUBDIR is 'passports', then url_for('static', filename='passports/filename.html')
            # Or, if you have a dedicated route: url_for('serve_passport_route', filename=os.path.basename(passport_file_rel_path))
            # For simplicity, using PASSPORT_BASE_URL from config which should point to the dir where passports are served.
            passport_public_url = f"{current_app.config['PASSPORT_BASE_URL'].rstrip('/')}/{os.path.basename(passport_file_rel_path)}"
            qr_code_relative_path = generate_qr_code_for_passport(passport_public_url, product_id)
            if qr_code_relative_path:
                label_relative_path = generate_product_label_image(asset_product_data, qr_code_relative_path)
        
        cursor.execute("""
            INSERT INTO products (id, name, category, short_description, long_description, image_url_main, image_urls_thumb,
                                  species, origin, seasonality, ideal_uses, sensory_description, pairing_suggestions,
                                  base_price, stock_quantity, is_published, 
                                  passport_url, qr_code_path, label_path, 
                                  created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (product_id, name, category, short_description, long_description, image_url_main, image_urls_thumb_json,
              species, origin, seasonality, ideal_uses, sensory_description, pairing_suggestions,
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
                """, (product_id, int(option['weight_grams']), float(option['price']), 0 )) # Initial stock 0, then record movement
                variant_option_id = cursor.lastrowid
                if opt_stock > 0:
                    record_stock_movement(cursor, product_id, opt_stock, 'initial_stock',
                                          variant_option_id=variant_option_id, 
                                          notes=f"Stock initial pour variante {option['weight_grams']}g de {product_id}",
                                          user_id=admin_user_id)
                    # Update the stock_quantity for the variant after recording movement
                    cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE option_id = ?", (opt_stock, variant_option_id))

                total_variant_stock += opt_stock
            # Update main product's stock_quantity to sum of variants if it's variant-based
            cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (total_variant_stock, product_id))
        
        db.commit()
        current_app.logger.info(f"Produit '{product_id}' créé par admin {admin_user_id or 'System'}. Actifs générés.")
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        created_product_dict = dict(cursor.fetchone())
        if weight_options: # Fetch newly created options for the response
             cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_id,))
             created_product_dict['weight_options'] = [dict(row) for row in cursor.fetchall()]
        
        # Include asset paths in the response
        created_product_dict['assets'] = {
            "passport_url": passport_public_url,
            "qr_code_file_path": qr_code_relative_path, # Relative path from static folder
            "label_file_path": label_relative_path    # Relative path from static folder
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
        
        # Define allowed fields for direct update on 'products' table
        allowed_product_fields = [
            'name', 'category', 'short_description', 'long_description', 
            'image_url_main', 'species', 'origin', 'seasonality', 
            'ideal_uses', 'sensory_description', 'pairing_suggestions', 
            'base_price', 'is_published'
            # 'stock_quantity' for simple products can be updated here if not managed by variants
        ]

        for field in allowed_product_fields:
            if field in data:
                update_fields_sql_parts.append(f"{field} = ?")
                update_values.append(data[field])
        
        if 'image_urls_thumb' in data:
            if isinstance(data['image_urls_thumb'], list):
                update_fields_sql_parts.append("image_urls_thumb = ?")
                update_values.append(json.dumps(data['image_urls_thumb']))
            elif data['image_urls_thumb'] is None: # Allow clearing thumbnails
                update_fields_sql_parts.append("image_urls_thumb = ?")
                update_values.append('[]')


        # If there are fields to update for the main product table
        if update_fields_sql_parts:
            update_fields_sql_parts.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(product_id_to_update) # For the WHERE clause
            sql_update_product = f"UPDATE products SET {', '.join(update_fields_sql_parts)} WHERE id = ?"
            cursor.execute(sql_update_product, tuple(update_values))

        # Handle weight options (more robust update)
        if 'weight_options' in data:
            options_from_payload = data.get('weight_options', [])
            
            # Get current options from DB for comparison
            cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_id_to_update,))
            existing_options_db_list = [dict(row) for row in cursor.fetchall()]
            existing_options_db_map = {str(opt['option_id']): opt for opt in existing_options_db_list}

            processed_option_ids_from_payload = set()

            for opt_payload in options_from_payload:
                opt_id_payload_str = str(opt_payload.get('option_id')) if opt_payload.get('option_id') else None
                weight_grams = int(opt_payload['weight_grams'])
                price = float(opt_payload['price'])
                # Stock for variants is managed by record_stock_movement.
                # If 'initial_stock' is provided for an *existing* variant, it implies a correction.
                # If for a *new* variant, it's initial stock.
                stock_payload = int(opt_payload.get('initial_stock', 0))


                if opt_id_payload_str and opt_id_payload_str in existing_options_db_map: # Update existing option
                    existing_opt_data = existing_options_db_map[opt_id_payload_str]
                    cursor.execute("UPDATE product_weight_options SET weight_grams = ?, price = ? WHERE option_id = ?",
                                   (weight_grams, price, int(opt_id_payload_str)))
                    
                    # If stock is different, record an adjustment
                    if stock_payload != existing_opt_data['stock_quantity']:
                        quantity_diff = stock_payload - existing_opt_data['stock_quantity']
                        record_stock_movement(cursor, product_id_to_update, quantity_diff, 'correction',
                                              variant_option_id=int(opt_id_payload_str),
                                              notes=f"Correction stock variante lors MAJ produit (Admin: {admin_user_id or 'System'})",
                                              user_id=admin_user_id)
                        # The record_stock_movement already updates the stock in product_weight_options
                    processed_option_ids_from_payload.add(opt_id_payload_str)
                else: # Add new option
                    cursor.execute("INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity) VALUES (?, ?, ?, ?)",
                                   (product_id_to_update, weight_grams, price, 0)) # Initial stock 0
                    new_variant_id = cursor.lastrowid
                    if stock_payload > 0: # If initial stock provided for new variant
                        record_stock_movement(cursor, product_id_to_update, stock_payload, 'initial_stock',
                                              variant_option_id=new_variant_id, 
                                              notes=f"Stock initial pour nouvelle variante lors MAJ produit (Admin: {admin_user_id or 'System'})",
                                              user_id=admin_user_id)
                        # record_stock_movement updates the stock
                    processed_option_ids_from_payload.add(str(new_variant_id))
            
            # Delete options that were in DB but not in payload (unless they have stock and we want to prevent that)
            for opt_id_db_str, opt_data_db in existing_options_db_map.items():
                if opt_id_db_str not in processed_option_ids_from_payload:
                    # Optional: Check if stock > 0 and prevent deletion or log it
                    if opt_data_db['stock_quantity'] > 0:
                        current_app.logger.warning(f"Variante {opt_id_db_str} du produit {product_id_to_update} supprimée alors qu'elle avait {opt_data_db['stock_quantity']} en stock.")
                        # Optionally, record a 'perte' movement for the remaining stock
                        record_stock_movement(cursor, product_id_to_update, -opt_data_db['stock_quantity'], 'perte',
                                              variant_option_id=int(opt_id_db_str),
                                              notes=f"Stock perdu suite à suppression variante (Admin: {admin_user_id or 'System'})",
                                              user_id=admin_user_id)
                    cursor.execute("DELETE FROM product_weight_options WHERE option_id = ?", (int(opt_id_db_str),))

            # After all variant changes, update the main product's stock_quantity and base_price
            cursor.execute("SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = ?", (product_id_to_update,))
            sum_stock_row = cursor.fetchone()
            current_total_variant_stock = sum_stock_row[0] if sum_stock_row and sum_stock_row[0] is not None else 0
            
            # If variants exist, base_price on product table should be NULL.
            # If all variants were removed, base_price must be set from payload.
            num_remaining_variants = len(processed_option_ids_from_payload) + \
                                     sum(1 for opt_id in existing_options_db_map if opt_id not in processed_option_ids_from_payload and str(opt_payload.get("option_id")) == opt_id)


            if num_remaining_variants > 0 : # Variants still exist or were added
                 cursor.execute("UPDATE products SET stock_quantity = ?, base_price = NULL WHERE id = ?", 
                               (current_total_variant_stock, product_id_to_update))
            else: # No variants left, product becomes simple
                if 'base_price' not in data or data['base_price'] is None:
                    db.rollback()
                    return jsonify({"success": False, "message": "Si toutes les variantes sont supprimées, un prix de base doit être fourni."}), 400
                # Stock for simple product should be from payload or default to 0
                simple_product_stock = int(data.get('stock_quantity', 0)) if 'stock_quantity' in data else 0
                cursor.execute("UPDATE products SET stock_quantity = ?, base_price = ? WHERE id = ?", 
                               (simple_product_stock, data['base_price'], product_id_to_update))


        db.commit()
        current_app.logger.info(f"Produit '{product_id_to_update}' mis à jour par admin {admin_user_id or 'System'}.")
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id_to_update,))
        updated_product_dict = dict(cursor.fetchone())
        cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_id_to_update,))
        updated_product_dict['weight_options'] = [dict(row) for row in cursor.fetchall()]

        return jsonify({"success": True, "message": "Produit mis à jour avec succès.", "product": updated_product_dict})

    except ValueError as ve:
        if db: db.rollback()
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        if db: db.rollback()
        current_app.logger.error(f"Erreur serveur MAJ produit {product_id_to_update}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur interne."}), 500
    finally:
        if db: db.close()


@admin_api_bp.route('/products', methods=['GET'])
@admin_required
def list_admin_products():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Get variant_count and sum of variant stocks if applicable
        cursor.execute("""
            SELECT p.*, 
                   (SELECT COUNT(*) FROM product_weight_options WHERE product_id = p.id) as variant_count,
                   (SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = p.id) as total_variant_stock
            FROM products p 
            ORDER BY p.updated_at DESC
        """)
        products_rows = cursor.fetchall()
        products_list = []
        for row_data in products_rows:
            prod_dict = dict(row_data)
            # If it's a product managed by variants (base_price is NULL), its stock_quantity should reflect sum of variants
            if prod_dict['base_price'] is None and prod_dict['variant_count'] > 0:
                 prod_dict['stock_quantity'] = prod_dict['total_variant_stock'] if prod_dict['total_variant_stock'] is not None else 0
            # Remove helper columns if not needed in final JSON
            prod_dict.pop('total_variant_stock', None)
            products_list.append(prod_dict)
            
        return jsonify(products_list)
    except Exception as e:
        current_app.logger.error(f"Erreur listage produits admin: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500
    finally:
        if db: db.close()


# Inside backend/admin_api/routes.py

@admin_api_bp.route('/products/<string:product_id_param>', methods=['GET'])
@admin_required
def get_admin_product_details(product_id_param):
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        # Ensure you select the asset path columns
        cursor.execute("SELECT *, passport_url, qr_code_path, label_path FROM products WHERE id = ?", (product_id_param,)) # Added asset columns
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

        # Construct the 'assets' object for the response, similar to create/update
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


# --- Inventory Management ---
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
        
        # Basic validation for movement type vs quantity sign
        if quantity_change > 0 and movement_type in ['perte', 'vente']: # Vente should always be negative
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
    # This is the same as the public one for now, but could be enhanced for admin
    # For example, showing more detailed logs or cost prices.
    # Reusing the existing public inventory route logic from inventory_bp for now.
    # A more distinct admin version might be needed if requirements diverge.
    from ..inventory.routes import get_product_inventory_details # Relative import
    return get_product_inventory_details(product_id_param)


# --- User Management ---
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

# --- Order Management (Admin) ---
@admin_api_bp.route('/orders', methods=['GET'])
@admin_required
def list_admin_orders():
    db = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Basic query, can be expanded with filters from request.args
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '') # Expected YYYY-MM-DD

        query = "SELECT order_id, user_id, customer_email, customer_name, total_amount, order_date, status FROM orders"
        conditions = []
        params = []

        if search_query:
            conditions.append("(order_id LIKE ? OR customer_email LIKE ? OR customer_name LIKE ?)")
            like_search = f"%{search_query}%"
            params.extend([like_search, like_search, like_search])
        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        if date_filter: # Filter for orders on a specific date
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

@admin_api_bp.route('/orders/<string:order_id_param>', methods=['GET']) # order_id can be TRUVRAXXXXX
@admin_required
def get_admin_order_details(order_id_param):
    db = None
    # Extract numeric part if order_id_param is like "TRUVRA00123"
    actual_order_id = order_id_param
    if isinstance(order_id_param, str) and order_id_param.upper().startswith("TRUVRA"):
        try:
            actual_order_id = int(order_id_param[len("TRUVRA"):])
        except ValueError:
            return jsonify({"success": False, "message": "Format ID de commande invalide."}), 400
    else: # If it's already potentially numeric
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
        
        cursor.execute("""
            SELECT oi.item_id, oi.product_id, oi.product_name, oi.quantity, oi.price_at_purchase, oi.variant, pwo.weight_grams
            FROM order_items oi
            LEFT JOIN product_weight_options pwo ON oi.variant_option_id = pwo.option_id
            WHERE oi.order_id = ?
        """, (actual_order_id,))
        order_dict['items'] = [dict(row) for row in cursor.fetchall()]
        
        # Fetch notes for the order
        cursor.execute("SELECT note_id, content, created_at, admin_user_id FROM order_notes WHERE order_id = ? ORDER BY created_at ASC", (actual_order_id,))
        notes_raw = cursor.fetchall()
        order_dict['notes'] = []
        for note_row in notes_raw:
            note_dict = dict(note_row)
            # Optionally fetch admin user email/name if admin_user_id is stored
            # For now, just using the ID or 'Système'
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
        
        # Log this change as a note
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
    admin_user_id = getattr(g, 'admin_user_id', None) # Get admin_user_id from global context

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

