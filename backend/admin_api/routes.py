from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash # For potential admin user management
import sqlite3
import os
import json
from datetime import datetime, date # Added date
from functools import wraps

# Assuming database.py is in the same directory or accessible via backend.database
from backend.database import get_db_connection # Use the centralized get_db_connection
# Services are accessed via current_app:
# current_app.asset_service
# current_app.invoice_service
# current_app.audit_log_service

admin_api_bp = Blueprint('admin_api_bp', __name__)

# --- Decorators ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        admin_user_id_from_token = None

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify(message="Missing or invalid Authorization header"), 401
        
        token = auth_header.split(" ")[1]
        
        # In a real app, you'd verify a JWT token.
        # For this example, we'll use a placeholder token logic.
        # IMPORTANT: Replace this with actual JWT validation (e.g., using PyJWT)
        if token == current_app.config.get('ADMIN_BEARER_TOKEN_PLACEHOLDER', 'admin_token_placeholder'): # Use a config value
            # In a real JWT, the token itself would contain the user_id (sub claim)
            # For this placeholder, we might assume a default admin ID or fetch based on the token if it were unique.
            # Let's assume the placeholder token implies the first admin user.
            try:
                db_temp = get_db_connection() # Temporary connection to find an admin
                admin_check_cursor = db_temp.execute("SELECT id FROM users WHERE is_admin = TRUE ORDER BY id ASC LIMIT 1")
                first_admin = admin_check_cursor.fetchone()
                if first_admin:
                    admin_user_id_from_token = first_admin['id']
                else: # No admin user found, this is a problem for the placeholder logic
                    current_app.logger.error("Admin token placeholder used, but no admin user found in DB.")
                    return jsonify(message="Admin user configuration error."), 500
            except Exception as e_db_admin_check:
                current_app.logger.error(f"Error fetching admin for token placeholder: {e_db_admin_check}")
                return jsonify(message="Server error during admin check."), 500
        else:
            # Here you would decode and verify an actual JWT
            # try:
            #     decoded_token = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            #     admin_user_id_from_token = decoded_token.get('sub') # 'sub' is standard for subject (user_id)
            # except jwt.ExpiredSignatureError:
            #     return jsonify(message="Token has expired"), 401
            # except jwt.InvalidTokenError:
            #     return jsonify(message="Invalid token"), 401
            current_app.logger.warning(f"Invalid admin token received: {token}")
            return jsonify(message="Invalid or expired admin token."), 401


        if not admin_user_id_from_token:
            return jsonify(message="Admin user ID not found in token or token invalid."), 401

        db = get_db_connection()
        cursor = db.execute("SELECT * FROM users WHERE id = ? AND is_admin = TRUE", (admin_user_id_from_token,))
        admin_user = cursor.fetchone()

        if not admin_user:
            return jsonify(message="Admin privileges required or user not found."), 403
        
        g.admin_user = dict(admin_user) # Make admin user (as dict) available in request context
        return f(*args, **kwargs)
    return decorated_function

# --- Helper Functions ---
def get_json_or_abort(req):
    req_data = req.get_json(silent=True)
    if req_data is None:
        # Try to parse form data if JSON is not present, for file uploads mixed with data
        if req.form:
            return req.form.to_dict() # Convert ImmutableMultiDict to dict
        return None # Or raise an error: abort(400, description="Invalid JSON data in request")
    return req_data

# --- Product Management ---
@admin_api_bp.route('/products', methods=['POST'])
@admin_required
def create_product():
    # This endpoint might handle multipart/form-data if images are uploaded directly
    # For now, assuming JSON data and image URLs are provided.
    data = get_json_or_abort(request)
    if data is None:
        return jsonify(message="Invalid data in request. Expecting JSON or form-data."), 400

    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user

    try:
        required_fields = ['name_fr', 'name_en', 'category_id', 'sku', 'base_price', 'slug']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify(message=f"Missing required field: {field}"), 400

        cursor.execute("SELECT id FROM products WHERE sku = ?", (data['sku'],))
        if cursor.fetchone():
            return jsonify(message=f"Product with SKU {data['sku']} already exists."), 409
        cursor.execute("SELECT id FROM products WHERE slug = ?", (data['slug'],))
        if cursor.fetchone():
            return jsonify(message=f"Product with slug {data['slug']} already exists."), 409

        additional_image_urls_json = json.dumps(data.get('additional_image_urls', []))

        cursor.execute('''
            INSERT INTO products (name_fr, name_en, description_fr, description_en, category_id, sku, 
                                  base_price, currency, main_image_url, additional_image_urls, tags, 
                                  is_active, is_featured, meta_title_fr, meta_title_en, 
                                  meta_description_fr, meta_description_en, slug, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['name_fr'], data['name_en'], data.get('description_fr'), data.get('description_en'),
              data['category_id'], data['sku'], float(data['base_price']), data.get('currency', 'EUR'),
              data.get('main_image_url'), additional_image_urls_json, data.get('tags'),
              data.get('is_active', True) if isinstance(data.get('is_active'), bool) else (str(data.get('is_active')).lower() == 'true'), 
              data.get('is_featured', False) if isinstance(data.get('is_featured'), bool) else (str(data.get('is_featured')).lower() == 'true'),
              data.get('meta_title_fr'), data.get('meta_title_en'),
              data.get('meta_description_fr'), data.get('meta_description_en'), data['slug'], datetime.utcnow()))
        product_id = cursor.lastrowid

        variants_data = json.loads(data.get('variants', '[]')) if isinstance(data.get('variants'), str) else data.get('variants', [])
        created_variants_info = []

        for variant_data in variants_data:
            variant_sku = variant_data.get('sku')
            if not variant_sku: 
                variant_sku = f"{data['sku']}-V{len(created_variants_info)+1}"
            
            cursor.execute("SELECT id FROM product_variants WHERE sku = ?", (variant_sku,))
            if cursor.fetchone():
                current_app.logger.warning(f"Variant with SKU {variant_sku} already exists. Skipping for product {product_id}.")
                continue

            cursor.execute('''
                INSERT INTO product_variants (product_id, sku, name_fr, name_en, price_modifier, stock_quantity, weight_grams, dimensions, image_url, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, variant_sku, variant_data.get('name_fr'), variant_data.get('name_en'),
                  float(variant_data.get('price_modifier', 0)), int(variant_data.get('stock_quantity', 0)),
                  int(variant_data.get('weight_grams', 0)), json.dumps(variant_data.get('dimensions')), 
                  variant_data.get('image_url'), 
                  variant_data.get('is_active', True) if isinstance(variant_data.get('is_active'), bool) else (str(variant_data.get('is_active')).lower() == 'true'),
                  datetime.utcnow()))
            variant_id = cursor.lastrowid
            created_variants_info.append({'id': variant_id, 'sku': variant_sku, 'name_fr': variant_data.get('name_fr')})

            if int(variant_data.get('stock_quantity', 0)) > 0:
                 cursor.execute('''
                    INSERT INTO inventory_movements (product_variant_id, change_quantity, reason, notes)
                    VALUES (?, ?, ?, ?)
                 ''', (variant_id, int(variant_data.get('stock_quantity')), 'initial_stock', 'Product creation'))

        product_for_assets = {**data, "id": product_id} 
        qr_code_url, label_url, passport_url = None, None, None
        try:
            asset_service = current_app.asset_service
            qr_code_url = asset_service.generate_qr_code(product_id, data['slug'])
            
            primary_variant_for_assets_data = created_variants_info[0] if created_variants_info else None
            
            label_url = asset_service.generate_product_label(product_for_assets, primary_variant_for_assets_data)
            passport_url = asset_service.generate_product_passport(product_for_assets, primary_variant_for_assets_data)

            cursor.execute('''
                UPDATE products SET qr_code_url = ?, label_url = ?, product_passport_url = ?
                WHERE id = ?
            ''', (qr_code_url, label_url, passport_url, product_id))
        except Exception as e_asset:
            current_app.logger.error(f"Error generating assets for product {product_id}: {e_asset}")

        db.commit()
        current_app.audit_log_service.log_action(
            action='product_created', user_id=admin_user['id'], username=admin_user['email'],
            target_type='product', target_id=product_id,
            details={'name': data['name_fr'], 'sku': data['sku'], 'variants_count': len(created_variants_info)}, success=True)
        return jsonify(message="Product created successfully", product_id=product_id, 
                       qr_code_url=qr_code_url, label_url=label_url, product_passport_url=passport_url,
                       variants=created_variants_info), 201
    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"Database integrity error creating product: {e}")
        if "UNIQUE constraint failed: products.sku" in str(e): return jsonify(message=f"Product with SKU {data.get('sku')} already exists."), 409
        if "UNIQUE constraint failed: products.slug" in str(e): return jsonify(message=f"Product with slug {data.get('slug')} already exists."), 409
        return jsonify(message=f"Database integrity error: {e}"), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error creating product: {e}")
        current_app.audit_log_service.log_action(
            action='product_create_failed', user_id=admin_user['id'], username=admin_user['email'],
            details={'error': str(e), 'data': data if isinstance(data, dict) else str(data)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    data = get_json_or_abort(request)
    if data is None:
        return jsonify(message="Invalid data in request. Expecting JSON or form-data."), 400
        
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user

    try:
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return jsonify(message="Product not found"), 404
        product = dict(product) # Convert to dict for easier access

        if 'sku' in data and data['sku'] != product['sku']:
            cursor.execute("SELECT id FROM products WHERE sku = ? AND id != ?", (data['sku'], product_id))
            if cursor.fetchone(): return jsonify(message=f"Another product with SKU {data['sku']} already exists."), 409
        if 'slug' in data and data['slug'] != product['slug']:
            cursor.execute("SELECT id FROM products WHERE slug = ? AND id != ?", (data['slug'], product_id))
            if cursor.fetchone(): return jsonify(message=f"Another product with slug {data['slug']} already exists."), 409

        update_fields = []
        update_values = []
        allowed_fields = ['name_fr', 'name_en', 'description_fr', 'description_en', 'category_id', 'sku', 
                          'base_price', 'currency', 'main_image_url', 'tags', 'is_active', 'is_featured', 
                          'meta_title_fr', 'meta_title_en', 'meta_description_fr', 'meta_description_en', 'slug']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                value = data[field]
                if field in ['is_active', 'is_featured']:
                    value = value if isinstance(value, bool) else (str(value).lower() == 'true')
                elif field == 'base_price':
                    value = float(value)
                elif field == 'category_id':
                    value = int(value)
                update_values.append(value)
        
        if 'additional_image_urls' in data:
            update_fields.append("additional_image_urls = ?")
            update_values.append(json.dumps(data.get('additional_image_urls', [])))

        if update_fields:
            update_fields.append("updated_at = ?")
            update_values.append(datetime.utcnow())
            update_values.append(product_id)
            sql_update_product = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql_update_product, tuple(update_values))

        updated_variants_info = []
        raw_variants_data = data.get('variants')
        if raw_variants_data:
            variants_data_list = json.loads(raw_variants_data) if isinstance(raw_variants_data, str) else raw_variants_data

            cursor.execute("SELECT * FROM product_variants WHERE product_id = ?", (product_id,))
            existing_variants_db = {v['sku']: dict(v) for v in cursor.fetchall()}
            requested_variant_skus = set()

            for variant_data in variants_data_list:
                variant_sku = variant_data.get('sku')
                if not variant_sku: continue
                requested_variant_skus.add(variant_sku)

                variant_update_fields_list = []
                variant_update_values_list = []
                variant_allowed_fields = ['name_fr', 'name_en', 'price_modifier', 'stock_quantity', 
                                          'weight_grams', 'dimensions', 'image_url', 'is_active']

                for field in variant_allowed_fields:
                    if field in variant_data:
                        variant_update_fields_list.append(f"{field} = ?")
                        value = variant_data[field]
                        if field == 'dimensions': value = json.dumps(value)
                        elif field in ['price_modifier']: value = float(value)
                        elif field in ['stock_quantity', 'weight_grams']: value = int(value)
                        elif field == 'is_active': value = value if isinstance(value, bool) else (str(value).lower() == 'true')
                        variant_update_values_list.append(value)
                
                if variant_sku in existing_variants_db:
                    if variant_update_fields_list:
                        variant_update_fields_list.append("updated_at = ?")
                        variant_update_values_list.append(datetime.utcnow())
                        variant_update_values_list.append(existing_variants_db[variant_sku]['id'])
                        sql_update_variant = f"UPDATE product_variants SET {', '.join(variant_update_fields_list)} WHERE id = ?"
                        cursor.execute(sql_update_variant, tuple(variant_update_values_list))
                        updated_variants_info.append({'id': existing_variants_db[variant_sku]['id'], 'sku': variant_sku, 'status': 'updated'})
                else:
                    cursor.execute('''
                        INSERT INTO product_variants (product_id, sku, name_fr, name_en, price_modifier, stock_quantity, weight_grams, dimensions, image_url, is_active, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (product_id, variant_sku, variant_data.get('name_fr'), variant_data.get('name_en'),
                          float(variant_data.get('price_modifier', 0)), int(variant_data.get('stock_quantity', 0)),
                          int(variant_data.get('weight_grams',0)), json.dumps(variant_data.get('dimensions')),
                          variant_data.get('image_url'), 
                          variant_data.get('is_active', True) if isinstance(variant_data.get('is_active'), bool) else (str(variant_data.get('is_active')).lower() == 'true'),
                          datetime.utcnow()))
                    new_variant_id = cursor.lastrowid
                    updated_variants_info.append({'id': new_variant_id, 'sku': variant_sku, 'status': 'created'})
                
                if 'stock_quantity' in variant_data:
                    new_stock = int(variant_data['stock_quantity'])
                    variant_db_id = existing_variants_db[variant_sku]['id'] if variant_sku in existing_variants_db else new_variant_id
                    
                    # Get current stock for this variant to calculate change
                    stock_check_cursor = db.cursor()
                    stock_check_cursor.execute("SELECT stock_quantity FROM product_variants WHERE id = ?", (variant_db_id,))
                    current_variant_stock_row = stock_check_cursor.fetchone()
                    current_stock_val = current_variant_stock_row['stock_quantity'] if current_variant_stock_row else 0
                    
                    stock_change = new_stock - current_stock_val
                    if stock_change != 0:
                        cursor.execute('''
                            INSERT INTO inventory_movements (product_variant_id, change_quantity, reason, notes)
                            VALUES (?, ?, ?, ?)
                        ''', (variant_db_id, stock_change, 'admin_update', f'Stock changed from {current_stock_val} to {new_stock}'))
                    # The variant's stock_quantity is already updated by the main variant update logic if 'stock_quantity' was in variant_data

            variants_to_delete_skus = set(existing_variants_db.keys()) - requested_variant_skus
            for sku_to_delete in variants_to_delete_skus:
                variant_to_delete_id = existing_variants_db[sku_to_delete]['id']
                cursor.execute("DELETE FROM product_variants WHERE id = ?", (variant_to_delete_id,))
                cursor.execute("DELETE FROM inventory_movements WHERE product_variant_id = ?", (variant_to_delete_id,))
                updated_variants_info.append({'sku': sku_to_delete, 'status': 'deleted'})

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,)) # Re-fetch product for asset generation
        updated_product_data_for_assets = dict(cursor.fetchone())
        qr_code_url, label_url, passport_url = product['qr_code_url'], product['label_url'], product['product_passport_url']
        assets_changed = False

        if 'slug' in data and data['slug'] != product['slug']:
            try:
                qr_code_url = current_app.asset_service.generate_qr_code(product_id, data['slug'])
                assets_changed = True
            except Exception as e_asset: current_app.logger.error(f"Error re-generating QR for product {product_id}: {e_asset}")

        if ('name_fr' in data and data['name_fr'] != product['name_fr']) or not label_url or not passport_url : # Regenerate if name changes or assets missing
            try:
                cursor.execute("SELECT * FROM product_variants WHERE product_id = ? ORDER BY id ASC LIMIT 1", (product_id,))
                first_variant_after_update = cursor.fetchone()
                label_url = current_app.asset_service.generate_product_label(updated_product_data_for_assets, dict(first_variant_after_update) if first_variant_after_update else None)
                passport_url = current_app.asset_service.generate_product_passport(updated_product_data_for_assets, dict(first_variant_after_update) if first_variant_after_update else None)
                assets_changed = True
            except Exception as e_asset: current_app.logger.error(f"Error re-generating label/passport for product {product_id}: {e_asset}")
        
        if assets_changed:
            cursor.execute('''
                UPDATE products SET qr_code_url = ?, label_url = ?, product_passport_url = ?, updated_at = ?
                WHERE id = ?
            ''', (qr_code_url, label_url, passport_url, datetime.utcnow(), product_id))

        db.commit()
        current_app.audit_log_service.log_action(
            action='product_updated', user_id=admin_user['id'], username=admin_user['email'],
            target_type='product', target_id=product_id,
            details={'updated_fields': list(data.keys()), 'variants_status': updated_variants_info}, success=True)
        return jsonify(message="Product updated successfully", product_id=product_id, 
                       qr_code_url=qr_code_url, label_url=label_url, product_passport_url=passport_url,
                       variants_status=updated_variants_info), 200
    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"DB integrity error updating product {product_id}: {e}")
        return jsonify(message=f"Database integrity error: {e}"), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating product {product_id}: {e}")
        current_app.audit_log_service.log_action(
            action='product_update_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='product', target_id=product_id,
            details={'error': str(e), 'data': data if isinstance(data, dict) else str(data)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return jsonify(message="Product not found"), 404

        # Optionally, delete associated assets from filesystem (QR, label, passport)
        # asset_service = current_app.asset_service
        # if product['qr_code_url']: asset_service.delete_asset_file(product['qr_code_url'])
        # ... and so on for label and passport. AssetService would need a delete_asset_file method.

        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        # Variants and inventory movements should be deleted via CASCADE if set up in DB schema,
        # otherwise, delete them manually here.
        # Assuming CASCADE for product_variants -> inventory_movements
        # And products -> product_variants
        # If not, add:
        # cursor.execute("DELETE FROM product_variants WHERE product_id = ?", (product_id,))
        # cursor.execute("DELETE FROM inventory_movements WHERE product_variant_id IN (SELECT id FROM product_variants WHERE product_id = ?)", (product_id,))
        
        db.commit()
        current_app.audit_log_service.log_action(
            action='product_deleted', user_id=admin_user['id'], username=admin_user['email'],
            target_type='product', target_id=product_id,
            details={'name': product['name_fr'], 'sku': product['sku']}, success=True)
        return jsonify(message="Product deleted successfully"), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error deleting product {product_id}: {e}")
        current_app.audit_log_service.log_action(
            action='product_delete_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='product', target_id=product_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/products', methods=['GET'])
@admin_required
def get_all_products_admin():
    db = get_db_connection()
    cursor = db.execute("""
        SELECT p.*, c.name_fr as category_name_fr, c.name_en as category_name_en 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id 
        ORDER BY p.created_at DESC
    """)
    products = [dict(row) for row in cursor.fetchall()]
    
    for product in products:
        variant_cursor = db.execute("SELECT * FROM product_variants WHERE product_id = ? ORDER BY id ASC", (product['id'],))
        variants = [dict(v_row) for v_row in variant_cursor.fetchall()]
        product['variants'] = variants
        if product.get('additional_image_urls'):
            try: product['additional_image_urls'] = json.loads(product['additional_image_urls'])
            except json.JSONDecodeError: product['additional_image_urls'] = []
    return jsonify(products), 200

@admin_api_bp.route('/products/<int:product_id>', methods=['GET'])
@admin_required
def get_product_admin(product_id):
    db = get_db_connection()
    cursor = db.execute("""
        SELECT p.*, c.name_fr as category_name_fr, c.name_en as category_name_en 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id 
        WHERE p.id = ?
    """, (product_id,))
    product = cursor.fetchone()
    if not product:
        return jsonify(message="Product not found"), 404
    
    product_dict = dict(product)
    variant_cursor = db.execute("SELECT * FROM product_variants WHERE product_id = ? ORDER BY id ASC", (product_id,))
    variants = [dict(v_row) for v_row in variant_cursor.fetchall()]
    product_dict['variants'] = variants
    if product_dict.get('additional_image_urls'):
        try: product_dict['additional_image_urls'] = json.loads(product_dict['additional_image_urls'])
        except json.JSONDecodeError: product_dict['additional_image_urls'] = []
    return jsonify(product_dict), 200


# --- Category Management ---
@admin_api_bp.route('/categories', methods=['POST'])
@admin_required
def create_category():
    data = get_json_or_abort(request)
    if data is None: return jsonify(message="Invalid JSON data"), 400
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        required = ['name_fr', 'name_en', 'slug']
        if not all(f in data and data[f] for f in required):
            return jsonify(message=f"Missing required fields: {', '.join(required)}"), 400
        
        cursor.execute("SELECT id FROM categories WHERE slug = ?", (data['slug'],))
        if cursor.fetchone(): return jsonify(message=f"Category with slug {data['slug']} already exists."), 409

        cursor.execute('''
            INSERT INTO categories (name_fr, name_en, description_fr, description_en, slug, image_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['name_fr'], data['name_en'], data.get('description_fr'), data.get('description_en'), 
              data['slug'], data.get('image_url'), datetime.utcnow()))
        category_id = cursor.lastrowid
        db.commit()
        current_app.audit_log_service.log_action(
            action='category_created', user_id=admin_user['id'], username=admin_user['email'],
            target_type='category', target_id=category_id, details={'name': data['name_fr'], 'slug': data['slug']}, success=True)
        return jsonify(message="Category created successfully", category_id=category_id), 201
    except sqlite3.IntegrityError as e:
        db.rollback()
        return jsonify(message=f"Database integrity error: {e}"), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error creating category: {e}")
        current_app.audit_log_service.log_action(
            action='category_create_failed', user_id=admin_user['id'], username=admin_user['email'],
            details={'error': str(e), 'data': data}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@admin_required
def update_category(category_id):
    data = get_json_or_abort(request)
    if data is None: return jsonify(message="Invalid JSON data"), 400
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        if not category: return jsonify(message="Category not found"), 404

        if 'slug' in data and data['slug'] != category['slug']:
            cursor.execute("SELECT id FROM categories WHERE slug = ? AND id != ?", (data['slug'], category_id))
            if cursor.fetchone(): return jsonify(message=f"Another category with slug {data['slug']} already exists."), 409
        
        update_fields_cat = []
        update_values_cat = []
        allowed_cat_fields = ['name_fr', 'name_en', 'description_fr', 'description_en', 'slug', 'image_url']
        for field in allowed_cat_fields:
            if field in data:
                update_fields_cat.append(f"{field} = ?")
                update_values_cat.append(data[field])
        
        if not update_fields_cat: return jsonify(message="No fields provided for category update."), 400

        update_fields_cat.append("updated_at = ?")
        update_values_cat.append(datetime.utcnow())
        update_values_cat.append(category_id)
        sql_update_cat = f"UPDATE categories SET {', '.join(update_fields_cat)} WHERE id = ?"
        cursor.execute(sql_update_cat, tuple(update_values_cat))
        db.commit()
        current_app.audit_log_service.log_action(
            action='category_updated', user_id=admin_user['id'], username=admin_user['email'],
            target_type='category', target_id=category_id, details={'updated_fields': list(data.keys())}, success=True)
        return jsonify(message="Category updated successfully"), 200
    except sqlite3.IntegrityError as e:
        db.rollback()
        return jsonify(message=f"Database integrity error: {e}"), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating category {category_id}: {e}")
        current_app.audit_log_service.log_action(
            action='category_update_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='category', target_id=category_id, details={'error': str(e), 'data': data}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        if not category: return jsonify(message="Category not found"), 404

        # Check if any products are associated with this category
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE category_id = ?", (category_id,))
        if cursor.fetchone()['count'] > 0:
            return jsonify(message="Cannot delete category: products are associated with it. Reassign products first."), 409
            
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        db.commit()
        current_app.audit_log_service.log_action(
            action='category_deleted', user_id=admin_user['id'], username=admin_user['email'],
            target_type='category', target_id=category_id, details={'name': category['name_fr']}, success=True)
        return jsonify(message="Category deleted successfully"), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error deleting category {category_id}: {e}")
        current_app.audit_log_service.log_action(
            action='category_delete_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='category', target_id=category_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/categories', methods=['GET'])
@admin_required # Or make public if needed for frontend selectors
def get_all_categories_admin():
    db = get_db_connection()
    cursor = db.execute("SELECT * FROM categories ORDER BY name_fr ASC")
    categories = [dict(row) for row in cursor.fetchall()]
    return jsonify(categories), 200


# --- B2B Invoice Generation ---
@admin_api_bp.route('/invoices/professional/generate', methods=['POST'])
@admin_required
def generate_professional_invoice_admin():
    data = get_json_or_abort(request)
    if data is None: return jsonify({"message": "Invalid JSON data"}), 400
    admin_user = g.admin_user

    invoice_id_from_request = data.get("invoice_id_display") # e.g., "PROV-2024-001" - this is the human-readable ID
    professional_user_id = data.get("professional_user_id")

    if not invoice_id_from_request or not professional_user_id:
        return jsonify({"message": "Missing invoice_id_display or professional_user_id"}), 400

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE id = ? AND is_professional = TRUE", (professional_user_id,))
        prof_user = cursor.fetchone()
        if not prof_user: return jsonify({"message": "Professional user not found"}), 404
        prof_user = dict(prof_user)

        invoice_items_from_request = data.get("items", [])
        if not invoice_items_from_request: return jsonify({"message": "Invoice items are required"}), 400
        
        subtotal = sum(float(item.get('quantity', 0)) * float(item.get('unit_price', 0)) for item in invoice_items_from_request)
        vat_rate = float(data.get('vat_rate', 0.20))
        vat_amount = subtotal * vat_rate
        total_amount = subtotal + vat_amount

        billing_address_obj = json.loads(prof_user.get('billing_address') or '{}')
        billing_address_str = ", ".join(filter(None, [
            billing_address_obj.get('street'),
            billing_address_obj.get('city'),
            billing_address_obj.get('postal_code'),
            billing_address_obj.get('country')
        ])) or "N/A"


        invoice_data_for_service = {
            "invoice_id": invoice_id_from_request, 
            "professional_user_id": professional_user_id,
            "issue_date": data.get("issue_date", date.today().strftime('%Y-%m-%d')),
            "due_date": data.get("due_date"),
            "client_details": {
                "company_name": prof_user['company_name'],
                "vat_number": prof_user['vat_number'],
                "billing_address": billing_address_str,
                "email": prof_user['email'], # Added email
                "phone": prof_user.get('phone_number', 'N/A') # Added phone
            },
            "items": invoice_items_from_request,
            "subtotal": subtotal, "vat_rate": vat_rate, "vat_amount": vat_amount, "total_amount": total_amount,
            "notes": data.get("notes", "Merci pour votre commande."),
            "payment_terms": data.get("payment_terms", "Paiement à réception.")
        }
        
        pdf_filepath = current_app.invoice_service.create_professional_invoice_pdf(invoice_data_for_service)

        if pdf_filepath:
            cursor.execute("""
                INSERT INTO professional_invoices 
                (professional_user_id, invoice_number, issue_date, due_date, total_amount, vat_amount, status, pdf_url, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (professional_user_id, invoice_id_from_request, 
                  invoice_data_for_service['issue_date'], invoice_data_for_service.get('due_date'),
                  total_amount, vat_amount, data.get('status', 'sent'), pdf_filepath, invoice_data_for_service.get('notes'), datetime.utcnow()))
            prof_invoice_db_id = cursor.lastrowid
            
            for item in invoice_items_from_request:
                cursor.execute("""
                    INSERT INTO professional_invoice_items (invoice_id, description, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                """, (prof_invoice_db_id, item['description'], item['quantity'], item['unit_price'], float(item.get('quantity',0)) * float(item.get('unit_price',0)) ))
            db.commit()
            
            current_app.audit_log_service.log_action(
                action='b2b_invoice_generated', user_id=admin_user['id'], username=admin_user['email'],
                target_type='professional_invoice', target_id=prof_invoice_db_id,
                details={'invoice_number': invoice_id_from_request, 'client_id': professional_user_id, 'pdf_path': pdf_filepath}, success=True)
            return jsonify({"message": "Professional invoice generated successfully", "pdf_path": pdf_filepath, "invoice_db_id": prof_invoice_db_id}), 201
        else:
            current_app.audit_log_service.log_action(
                action='b2b_invoice_generation_failed', user_id=admin_user['id'], username=admin_user['email'],
                target_type='professional_invoice',
                details={'invoice_data': invoice_data_for_service, 'error': 'PDF generation returned None'}, success=False)
            return jsonify({"message": "Failed to generate professional invoice PDF"}), 500
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error generating B2B invoice: {e}", exc_info=True)
        current_app.audit_log_service.log_action(
            action='b2b_invoice_generation_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='professional_invoice',
            details={'invoice_data': data, 'error': str(e)}, success=False)
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@admin_api_bp.route('/invoices/professional', methods=['GET'])
@admin_required
def get_professional_invoices():
    db = get_db_connection()
    cursor = db.execute("""
        SELECT pi.*, u.company_name, u.email as user_email
        FROM professional_invoices pi
        JOIN users u ON pi.professional_user_id = u.id
        ORDER BY pi.issue_date DESC, pi.id DESC
    """)
    invoices = [dict(row) for row in cursor.fetchall()]
    return jsonify(invoices), 200

@admin_api_bp.route('/invoices/professional/<int:invoice_db_id>', methods=['PUT'])
@admin_required
def update_professional_invoice_status(invoice_db_id):
    data = get_json_or_abort(request)
    if data is None or 'status' not in data:
        return jsonify(message="Missing 'status' in request data"), 400
    
    new_status = data['status']
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM professional_invoices WHERE id = ?", (invoice_db_id,))
        invoice = cursor.fetchone()
        if not invoice:
            return jsonify(message="Invoice not found"), 404

        cursor.execute("UPDATE professional_invoices SET status = ?, updated_at = ? WHERE id = ?", 
                       (new_status, datetime.utcnow(), invoice_db_id))
        db.commit()

        current_app.audit_log_service.log_action(
            action='b2b_invoice_status_updated', user_id=admin_user['id'], username=admin_user['email'],
            target_type='professional_invoice', target_id=invoice_db_id,
            details={'invoice_number': invoice['invoice_number'], 'old_status': invoice['status'], 'new_status': new_status}, success=True)
        return jsonify(message=f"Invoice {invoice['invoice_number']} status updated to {new_status}."), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating B2B invoice {invoice_db_id} status: {e}")
        current_app.audit_log_service.log_action(
            action='b2b_invoice_status_update_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='professional_invoice', target_id=invoice_db_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500


# --- Dashboard Stats Endpoints ---
@admin_api_bp.route('/stats/total_users', methods=['GET'])
@admin_required
def get_stats_total_users():
    db = get_db_connection()
    count = db.execute("SELECT COUNT(*) as total_users FROM users").fetchone()['total_users']
    return jsonify(total_users=count)

@admin_api_bp.route('/stats/total_products', methods=['GET'])
@admin_required
def get_stats_total_products():
    db = get_db_connection()
    count = db.execute("SELECT COUNT(*) as total_products FROM products").fetchone()['total_products']
    return jsonify(total_products=count)

@admin_api_bp.route('/stats/total_orders', methods=['GET'])
@admin_required
def get_stats_total_orders():
    db = get_db_connection()
    count = db.execute("SELECT COUNT(*) as total_orders FROM orders WHERE status NOT IN ('pending', 'cancelled')").fetchone()['total_orders']
    return jsonify(total_orders=count)

@admin_api_bp.route('/stats/total_revenue', methods=['GET'])
@admin_required
def get_stats_total_revenue():
    db = get_db_connection()
    revenue = db.execute("SELECT SUM(total_amount) as total_revenue FROM orders WHERE payment_status = 'paid'").fetchone()['total_revenue'] or 0.0
    return jsonify(total_revenue=revenue)

# --- User Management ---
@admin_api_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users_admin():
    db = get_db_connection()
    users = [dict(row) for row in db.execute("SELECT id, email, first_name, last_name, is_admin, is_professional, professional_status, company_name, created_at, last_login_at, is_verified FROM users ORDER BY created_at DESC").fetchall()]
    return jsonify(users), 200

@admin_api_bp.route('/users/<int:user_id>/approve_professional', methods=['PUT'])
@admin_required
def approve_professional_user(user_id):
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM users WHERE id = ? AND is_professional = TRUE", (user_id,))
        user_to_approve = cursor.fetchone()
        if not user_to_approve:
            return jsonify(message="User not found or not a professional account."), 404
        if user_to_approve['professional_status'] == 'approved':
            return jsonify(message="User is already approved."), 200 # Or 400 if it's an invalid action

        cursor.execute("UPDATE users SET professional_status = 'approved', is_verified = TRUE, updated_at = ? WHERE id = ?", 
                       (datetime.utcnow(), user_id)) # Also mark as verified upon approval
        db.commit()
        # TODO: Send email notification to user
        current_app.audit_log_service.log_action(
            action='b2b_user_approved', user_id=admin_user['id'], username=admin_user['email'],
            target_type='user', target_id=user_id, details={'email': user_to_approve['email']}, success=True)
        return jsonify(message="Professional user approved successfully."), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error approving professional user {user_id}: {e}")
        current_app.audit_log_service.log_action(
            action='b2b_user_approve_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='user', target_id=user_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/users/<int:user_id>/professional_status', methods=['PUT'])
@admin_required
def update_professional_user_status(user_id):
    data = get_json_or_abort(request)
    if data is None or 'status' not in data:
        return jsonify(message="Missing 'status' in request data (e.g., 'approved', 'rejected', 'pending')"), 400
    
    new_status = data['status']
    valid_statuses = ['pending', 'approved', 'rejected', 'suspended'] # Define valid statuses
    if new_status not in valid_statuses:
        return jsonify(message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"), 400

    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM users WHERE id = ? AND is_professional = TRUE", (user_id,))
        user_to_update = cursor.fetchone()
        if not user_to_update:
            return jsonify(message="User not found or not a professional account."), 404

        cursor.execute("UPDATE users SET professional_status = ?, updated_at = ? WHERE id = ?", 
                       (new_status, datetime.utcnow(), user_id))
        db.commit()
        # TODO: Send email notification if status changes significantly (e.g., rejected, suspended)
        current_app.audit_log_service.log_action(
            action='b2b_user_status_changed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='user', target_id=user_id, 
            details={'email': user_to_update['email'], 'old_status': user_to_update['professional_status'], 'new_status': new_status}, success=True)
        return jsonify(message=f"Professional user status updated to '{new_status}' successfully."), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating professional user {user_id} status: {e}")
        current_app.audit_log_service.log_action(
            action='b2b_user_status_change_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='user', target_id=user_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

# --- Order Management (Basic Examples) ---
@admin_api_bp.route('/orders', methods=['GET'])
@admin_required
def get_all_orders_admin():
    db = get_db_connection()
    # Join with users table to get customer email/name
    orders_cursor = db.execute("""
        SELECT o.*, u.email as customer_email, u.first_name as customer_first_name, u.last_name as customer_last_name
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        ORDER BY o.order_date DESC
    """)
    orders = [dict(row) for row in orders_cursor.fetchall()]

    for order in orders:
        items_cursor = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
        order['items'] = [dict(item_row) for item_row in items_cursor.fetchall()]
        # Parse JSON address fields
        try:
            order['shipping_address'] = json.loads(order['shipping_address']) if order.get('shipping_address') else {}
            order['billing_address'] = json.loads(order['billing_address']) if order.get('billing_address') else {}
        except json.JSONDecodeError:
            current_app.logger.warning(f"Could not parse address for order {order['id']}")
            order['shipping_address'] = {}
            order['billing_address'] = {}


    return jsonify(orders), 200

@admin_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id):
    data = get_json_or_abort(request)
    if data is None or 'status' not in data:
        return jsonify(message="Missing 'status' in request data"), 400
    
    new_status = data['status']
    # Define valid order statuses if needed
    # valid_order_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
    # if new_status not in valid_order_statuses:
    #     return jsonify(message="Invalid order status"), 400

    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify(message="Order not found"), 404

        cursor.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", 
                       (new_status, datetime.utcnow(), order_id))
        db.commit()
        # TODO: Send email notification to customer about status change
        current_app.audit_log_service.log_action(
            action='order_status_updated', user_id=admin_user['id'], username=admin_user['email'],
            target_type='order', target_id=order_id, 
            details={'old_status': order['status'], 'new_status': new_status}, success=True)
        return jsonify(message=f"Order {order_id} status updated to {new_status}."), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating order {order_id} status: {e}")
        current_app.audit_log_service.log_action(
            action='order_status_update_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='order', target_id=order_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

# --- Review Management ---
@admin_api_bp.route('/reviews', methods=['GET'])
@admin_required
def get_all_reviews_admin():
    # Parameter for status (e.g., ?status=pending or ?status=approved)
    status_filter = request.args.get('status')
    query = """
        SELECT r.*, p.name_fr as product_name, u.email as user_email
        FROM reviews r
        JOIN products p ON r.product_id = p.id
        JOIN users u ON r.user_id = u.id
    """
    params = []
    if status_filter:
        query += " WHERE r.is_approved = ?"
        params.append(status_filter.lower() == 'approved' or status_filter == '1') # True for approved, False for pending
    
    query += " ORDER BY r.review_date DESC"

    db = get_db_connection()
    reviews_cursor = db.execute(query, tuple(params))
    reviews = [dict(row) for row in reviews_cursor.fetchall()]
    return jsonify(reviews), 200

@admin_api_bp.route('/reviews/<int:review_id>/approve', methods=['PUT'])
@admin_required
def approve_review(review_id):
    return _update_review_approval(review_id, True)

@admin_api_bp.route('/reviews/<int:review_id>/reject', methods=['PUT']) # Or use DELETE for outright removal
@admin_required
def reject_review(review_id):
    # Rejecting could mean setting is_approved to False, or deleting.
    # For now, let's make it set is_approved to False.
    return _update_review_approval(review_id, False, action_on_false='rejected')


def _update_review_approval(review_id, approval_status, action_on_false='rejected'):
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
        review = cursor.fetchone()
        if not review:
            return jsonify(message="Review not found"), 404

        cursor.execute("UPDATE reviews SET is_approved = ? WHERE id = ?", (approval_status, review_id))
        db.commit()
        
        action_verb = 'approved' if approval_status else action_on_false
        current_app.audit_log_service.log_action(
            action=f'review_{action_verb}', user_id=admin_user['id'], username=admin_user['email'],
            target_type='review', target_id=review_id, success=True)
        return jsonify(message=f"Review {review_id} has been {action_verb}."), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating review {review_id} approval: {e}")
        current_app.audit_log_service.log_action(
            action=f'review_{action_verb}_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='review', target_id=review_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@admin_required
def delete_review(review_id):
    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
        review = cursor.fetchone()
        if not review:
            return jsonify(message="Review not found"), 404
            
        cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        db.commit()
        current_app.audit_log_service.log_action(
            action='review_deleted', user_id=admin_user['id'], username=admin_user['email'],
            target_type='review', target_id=review_id, success=True)
        return jsonify(message="Review deleted successfully"), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error deleting review {review_id}: {e}")
        current_app.audit_log_service.log_action(
            action='review_delete_failed', user_id=admin_user['id'], username=admin_user['email'],
            target_type='review', target_id=review_id, details={'error': str(e)}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

# --- Inventory Management (Basic Examples) ---
@admin_api_bp.route('/inventory/movements', methods=['POST'])
@admin_required
def record_inventory_movement():
    data = get_json_or_abort(request)
    if data is None: return jsonify(message="Invalid JSON data"), 400
    
    required_fields_inv = ['product_variant_id', 'change_quantity', 'reason']
    if not all(f in data for f in required_fields_inv):
        return jsonify(message=f"Missing required fields: {', '.join(required_fields_inv)}"), 400

    product_variant_id = data['product_variant_id']
    change_quantity = int(data['change_quantity'])
    reason = data['reason']
    notes = data.get('notes')
    related_order_id = data.get('related_order_id')

    db = get_db_connection()
    cursor = db.cursor()
    admin_user = g.admin_user
    try:
        # Check if variant exists
        cursor.execute("SELECT stock_quantity FROM product_variants WHERE id = ?", (product_variant_id,))
        variant = cursor.fetchone()
        if not variant:
            return jsonify(message="Product variant not found"), 404
        
        new_stock_quantity = variant['stock_quantity'] + change_quantity
        if new_stock_quantity < 0: # Prevent negative stock unless explicitly allowed by business logic
             # For now, allow it but log a warning. Production might block this.
            current_app.logger.warning(f"Stock for variant {product_variant_id} going negative: {new_stock_quantity}")


        cursor.execute('''
            INSERT INTO inventory_movements (product_variant_id, change_quantity, reason, related_order_id, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_variant_id, change_quantity, reason, related_order_id, notes))
        movement_id = cursor.lastrowid

        # Update stock_quantity in product_variants table
        cursor.execute("UPDATE product_variants SET stock_quantity = ? WHERE id = ?", 
                       (new_stock_quantity, product_variant_id))
        db.commit()

        current_app.audit_log_service.log_action(
            action='inventory_movement_recorded', user_id=admin_user['id'], username=admin_user['email'],
            target_type='inventory_movement', target_id=movement_id, 
            details={'variant_id': product_variant_id, 'change': change_quantity, 'reason': reason, 'new_stock': new_stock_quantity}, success=True)
        return jsonify(message="Inventory movement recorded successfully", movement_id=movement_id, new_stock_quantity=new_stock_quantity), 201
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error recording inventory movement: {e}")
        current_app.audit_log_service.log_action(
            action='inventory_movement_failed', user_id=admin_user['id'], username=admin_user['email'],
            details={'error': str(e), 'data': data}, success=False)
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@admin_api_bp.route('/inventory/variants/<int:variant_id>', methods=['GET'])
@admin_required
def get_variant_inventory_details(variant_id):
    db = get_db_connection()
    variant_cursor = db.execute("""
        SELECT pv.*, p.name_fr as product_name 
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.id
        WHERE pv.id = ?
    """, (variant_id,))
    variant = variant_cursor.fetchone()
    if not variant:
        return jsonify(message="Product variant not found"), 404
    
    movements_cursor = db.execute("SELECT * FROM inventory_movements WHERE product_variant_id = ? ORDER BY movement_date DESC", (variant_id,))
    movements = [dict(row) for row in movements_cursor.fetchall()]
    
    return jsonify(variant=dict(variant), movements=movements), 200

