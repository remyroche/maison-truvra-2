# backend/admin_api/routes.py
from flask import Blueprint, request, jsonify, current_app, send_from_directory
import sqlite3
import os
import json
import datetime # Ensure datetime is imported
from werkzeug.utils import secure_filename
from ..database import get_db_connection, record_stock_movement
from ..utils import jwt_required, send_email_alert # send_email_alert for user status updates
from ..audit_log_service import AuditLogService
from ..services.asset_service import AssetService 
from ..services.invoice_service import InvoiceService # Assuming this service exists

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')
audit_logger = AuditLogService()
asset_service = AssetService() 
invoice_service = InvoiceService()

# Helper to convert row to dict
def row_to_dict(cursor, row):
    if row:
        return dict(zip([column[0] for column in cursor.description], row))
    return {} # Return empty dict if row is None to prevent errors on attribute access


# --- Dashboard ---
@admin_api_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required 
def get_dashboard_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'b2c' OR role = 'professional'")
        total_users_row = cursor.fetchone()
        total_users = total_users_row[0] if total_users_row else 0

        cursor.execute("SELECT COUNT(*) FROM products")
        total_products_row = cursor.fetchone()
        total_products = total_products_row[0] if total_products_row else 0
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE date(order_date) = date('now')")
        orders_today_row = cursor.fetchone()
        orders_today = orders_today_row[0] if orders_today_row else 0
        
        cursor.execute("SELECT SUM(total_amount) FROM orders WHERE date(order_date) = date('now')")
        revenue_today_row = cursor.fetchone()
        revenue_today = revenue_today_row[0] if revenue_today_row and revenue_today_row[0] is not None else 0.0
        
        cursor.execute("SELECT o.id, u.email as user_email, o.order_date, o.total_amount, o.status FROM orders o JOIN users u ON o.user_id = u.id ORDER BY o.order_date DESC LIMIT 5")
        recent_orders_rows = cursor.fetchall()
        recent_orders = [row_to_dict(cursor, r) for r in recent_orders_rows]

        cursor.execute("SELECT r.id, u.email as user_email, p.name_fr as product_name, r.rating, r.comment, r.is_approved, r.created_at FROM reviews r JOIN users u ON r.user_id = u.id JOIN products p ON r.product_id = p.id ORDER BY r.created_at DESC LIMIT 5")
        recent_reviews_rows = cursor.fetchall()
        recent_reviews = [row_to_dict(cursor, r) for r in recent_reviews_rows]
        
        conn.close()
        stats = {"totalUsers": total_users, "totalProducts": total_products, "ordersToday": orders_today, "revenueToday": revenue_today, "recentOrders": recent_orders, "recentReviews": recent_reviews}
        return jsonify(stats), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred while fetching dashboard stats", "error": str(e)}), 500

# --- Categories ---
@admin_api_bp.route('/categories', methods=['GET'])
@jwt_required
def get_categories():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_fr, name_en, description_fr, description_en, image_url FROM categories ORDER BY name_fr")
        categories_rows = cursor.fetchall()
        categories = [row_to_dict(cursor, r) for r in categories_rows]
        conn.close()
        return jsonify(categories), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"DB error fetching categories: {e}", exc_info=True)
        return jsonify({"message": "Failed to fetch categories", "error": str(e)}), 500

@admin_api_bp.route('/categories', methods=['POST'])
@jwt_required
def create_category():
    data = request.form.to_dict()
    image_file = request.files.get('image_file')
    if not all(field in data for field in ['name_fr', 'name_en']):
        return jsonify({"message": "Missing required fields (name_fr, name_en)"}), 400
    image_url = None
    if image_file:
        filename = secure_filename(f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
        image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'category_images', filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image_file.save(image_path)
        image_url = f"/assets_generated/category_images/{filename}" # Relative URL for serving
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name_fr, name_en, description_fr, description_en, image_url) VALUES (?, ?, ?, ?, ?)", 
                       (data['name_fr'], data['name_en'], data.get('description_fr'), data.get('description_en'), image_url))
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        audit_logger.log_event('category_created', details={'category_id': category_id, 'name_fr': data['name_fr']})
        return jsonify({"message": "Category created successfully", "category_id": category_id, "image_url": image_url}), 201
    except sqlite3.IntegrityError: # e.g. unique constraint on name
        return jsonify({"message": "Category name might already exist or other integrity constraint failed."}), 409
    except sqlite3.Error as e:
        current_app.logger.error(f"DB error creating category: {e}", exc_info=True)
        return jsonify({"message": "Failed to create category", "error": str(e)}), 500

@admin_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required
def update_category(category_id):
    data = request.form.to_dict()
    image_file = request.files.get('image_file')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image_url FROM categories WHERE id = ?", (category_id,))
    category_row = cursor.fetchone()
    if not category_row: conn.close(); return jsonify({"message": "Category not found"}), 404
    
    category = row_to_dict(cursor, category_row) 
    image_url = category.get('image_url') 

    if image_file:
        if image_url: 
            old_image_filename = os.path.basename(image_url)
            old_image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'category_images', old_image_filename)
            if os.path.exists(old_image_path):
                try: os.remove(old_image_path)
                except OSError as e: current_app.logger.error(f"Error deleting old category image {old_image_path}: {e}")
        
        filename = secure_filename(f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
        image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'category_images', filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image_file.save(image_path)
        image_url = f"/assets_generated/category_images/{filename}"
    try:
        cursor.execute("UPDATE categories SET name_fr = ?, name_en = ?, description_fr = ?, description_en = ?, image_url = ? WHERE id = ?", 
                       (data.get('name_fr'), data.get('name_en'), data.get('description_fr'), data.get('description_en'), image_url, category_id))
        conn.commit(); conn.close()
        audit_logger.log_event('category_updated', details={'category_id': category_id, 'name_fr': data.get('name_fr')})
        return jsonify({"message": "Category updated successfully", "image_url": image_url}), 200
    except sqlite3.Error as e:
        conn.close(); current_app.logger.error(f"DB error updating category {category_id}: {e}", exc_info=True); return jsonify({"message": "Failed to update category", "error": str(e)}), 500

@admin_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@jwt_required
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,))
    product_count_row = cursor.fetchone()
    if product_count_row and product_count_row[0] > 0: 
        conn.close()
        return jsonify({"message": f"Cannot delete category: it is associated with {product_count_row[0]} product(s)."}), 409
    
    cursor.execute("SELECT image_url FROM categories WHERE id = ?", (category_id,))
    category_row = cursor.fetchone()
    category = row_to_dict(cursor, category_row)

    try:
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,)); conn.commit()
        if category and category.get('image_url'):
            image_filename = os.path.basename(category['image_url'])
            image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'category_images', image_filename)
            if os.path.exists(image_path): 
                try: os.remove(image_path)
                except OSError as e: current_app.logger.error(f"Error deleting category image file {image_path}: {e}")
        conn.close()
        audit_logger.log_event('category_deleted', details={'category_id': category_id})
        return jsonify({"message": "Category deleted successfully"}), 200
    except sqlite3.Error as e:
        conn.close(); current_app.logger.error(f"DB error deleting category {category_id}: {e}", exc_info=True); return jsonify({"message": "Failed to delete category", "error": str(e)}), 500

# --- Products ---
@admin_api_bp.route('/products', methods=['GET'])
@jwt_required
def get_products():
    category_id_filter = request.args.get('category_id')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT p.*, c.name_fr as category_name_fr FROM products p LEFT JOIN categories c ON p.category_id = c.id"
        params = []
        if category_id_filter: query += " WHERE p.category_id = ?"; params.append(category_id_filter)
        query += " ORDER BY p.name_fr"
        cursor.execute(query, params)
        products_rows = cursor.fetchall()
        products = []
        for row_tuple in products_rows:
            product_dict = row_to_dict(cursor, row_tuple)
            if product_dict and product_dict.get('product_type') == 'variable':
                cursor.execute("SELECT * FROM product_weight_options WHERE product_id = ?", (product_dict['id'],))
                product_dict['variants'] = [row_to_dict(cursor, v_row) for v_row in cursor.fetchall()]
            if product_dict: products.append(product_dict) # Ensure product_dict is not empty
        conn.close()
        return jsonify(products), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"DB error fetching products: {e}", exc_info=True)
        return jsonify({"message": "Failed to fetch products", "error": str(e)}), 500

@admin_api_bp.route('/products', methods=['POST'])
@jwt_required
def create_product():
    try:
        product_data_json = request.form.get('product_data')
        if not product_data_json: return jsonify({"message": "Missing 'product_data' in form"}), 400
        data = json.loads(product_data_json)
        image_file = request.files.get('image_file')
        
        required_fields = ['name_fr', 'name_en', 'category_id', 'product_type']
        if not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in data]
            return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

        product_type = data['product_type']
        base_price = data.get('base_price') if product_type == 'simple' else None
        initial_stock_quantity_for_simple = int(data.get('initial_stock_quantity', 0)) if product_type == 'simple' else 0
        weight_options_data = data.get('weight_options', []) if product_type == 'variable' else []

        if product_type == 'simple' and base_price is None :
            return jsonify({"message": "Simple products require 'base_price'"}), 400
        if product_type == 'variable' and not weight_options_data:
            return jsonify({"message": "Variable products require 'weight_options'"}), 400
        
        image_url = None
        if image_file:
            filename = secure_filename(f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
            image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'product_images', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            image_url = f"/assets_generated/product_images/{filename}"

        conn = get_db_connection()
        conn.execute("BEGIN")
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name_fr, name_en, description_fr, description_en, category_id, 
                                      base_price, image_url, product_type, is_active, stock_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0) 
            """, (data['name_fr'], data['name_en'], data.get('description_fr'), data.get('description_en'),
                  data['category_id'], base_price, image_url, product_type, data.get('is_active', True)))
            product_id = cursor.lastrowid

            cat_cursor = conn.cursor() # Use a different cursor or ensure main one is not in use for this sub-query
            cat_cursor.execute("SELECT name_fr FROM categories WHERE id = ?", (data['category_id'],))
            cat_data_row = cat_cursor.fetchone()
            category_name_fr = row_to_dict(cat_cursor, cat_data_row).get('name_fr', 'N/A') if cat_data_row else 'N/A'

            generated_serialized_items_info = []

            if product_type == 'variable':
                total_variant_aggregate_stock = 0
                for option_idx, option in enumerate(weight_options_data):
                    if not all(k in option for k in ['weight_grams', 'price', 'stock_quantity']):
                        conn.rollback(); return jsonify({"message": "Each weight option requires 'weight_grams', 'price', and 'stock_quantity'."}), 400
                    
                    variant_initial_stock = int(option['stock_quantity'])
                    total_variant_aggregate_stock += variant_initial_stock

                    cursor.execute("""
                        INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity, sku)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_id, option['weight_grams'], option['price'], variant_initial_stock, option.get('sku')))
                    variant_id = cursor.lastrowid
                    
                    if variant_initial_stock > 0:
                        variant_details_for_assets = {
                            "product_id": product_id, "name_fr": data['name_fr'], "ingredients": data.get('description_fr'),
                            "category_id": data['category_id'], "weight_grams": option['weight_grams'], "price": option['price'],
                            "product_id_display": f"MT{product_id:05d}-V{variant_id}",
                            "truffle_species": category_name_fr,
                            "lot_number": data.get('lot_number_batch'), 
                            "date_conditionnement": data.get('date_conditionnement_batch'),
                            "ddm": data.get('ddm_batch'),
                        }
                        for _ in range(variant_initial_stock):
                            item_uid = asset_service.generate_item_uid()
                            item_passport_public_url = f"{current_app.config.get('FRONTEND_URL', 'http://127.0.0.1:8000')}/passport/{item_uid}"
                            qr_fs_path, qr_asset_url = asset_service.generate_item_qr_code(item_uid, item_passport_public_url)
                            if not qr_fs_path: conn.rollback(); return jsonify({"message": f"QR code generation failed for variant item of product {product_id}"}), 500
                            
                            passport_details_for_item = {**variant_details_for_assets, "item_uid": item_uid}
                            passport_asset_url = asset_service.generate_item_passport(passport_details_for_item)
                            if not passport_asset_url: conn.rollback(); return jsonify({"message": f"Passport generation failed for variant item UID {item_uid}"}), 500

                            cursor.execute("""
                                INSERT INTO serialized_inventory_items (item_uid, product_id, variant_id, status, 
                                                                        passport_html_url, qr_code_url, lot_number, date_conditionnement, ddm)
                                VALUES (?, ?, ?, 'in_stock', ?, ?, ?, ?, ?)
                            """, (item_uid, product_id, variant_id, item_passport_public_url, qr_asset_url,
                                  variant_details_for_assets.get('lot_number'), 
                                  variant_details_for_assets.get('date_conditionnement'),
                                  variant_details_for_assets.get('ddm')))
                            generated_serialized_items_info.append({"item_uid": item_uid, "variant_id": variant_id, "passport_url": item_passport_public_url})
                        
                        record_stock_movement(conn, product_id, variant_id, 'initial_stock_serialized', variant_initial_stock, 
                                              f"Initial serialized stock for variant {option['weight_grams']}g")
                cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (total_variant_aggregate_stock, product_id))

            elif product_type == 'simple' and initial_stock_quantity_for_simple > 0:
                simple_product_details_for_assets = {
                    "product_id": product_id, "name_fr": data['name_fr'], "ingredients": data.get('description_fr'),
                    "category_id": data['category_id'], "price": base_price,
                    "product_id_display": f"MT{product_id:05d}",
                    "truffle_species": category_name_fr,
                    "weight_grams": data.get('base_weight_grams'), 
                    "lot_number": data.get('lot_number_batch'), 
                    "date_conditionnement": data.get('date_conditionnement_batch'),
                    "ddm": data.get('ddm_batch'),
                }
                for _ in range(initial_stock_quantity_for_simple):
                    item_uid = asset_service.generate_item_uid()
                    item_passport_public_url = f"{current_app.config.get('FRONTEND_URL', 'http://127.0.0.1:8000')}/passport/{item_uid}"
                    qr_fs_path, qr_asset_url = asset_service.generate_item_qr_code(item_uid, item_passport_public_url)
                    if not qr_fs_path: conn.rollback(); return jsonify({"message": f"QR code generation failed for simple item of product {product_id}"}), 500

                    passport_details_for_item = {**simple_product_details_for_assets, "item_uid": item_uid}
                    passport_asset_url = asset_service.generate_item_passport(passport_details_for_item)
                    if not passport_asset_url: conn.rollback(); return jsonify({"message": f"Passport generation failed for simple item UID {item_uid}"}), 500

                    cursor.execute("""
                        INSERT INTO serialized_inventory_items (item_uid, product_id, variant_id, status, 
                                                                passport_html_url, qr_code_url, lot_number, date_conditionnement, ddm)
                        VALUES (?, ?, NULL, 'in_stock', ?, ?, ?, ?, ?) """, 
                        (item_uid, product_id, item_passport_public_url, qr_asset_url,
                         simple_product_details_for_assets.get('lot_number'),
                         simple_product_details_for_assets.get('date_conditionnement'),
                         simple_product_details_for_assets.get('ddm')))
                    generated_serialized_items_info.append({"item_uid": item_uid, "passport_url": item_passport_public_url})

                cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (initial_stock_quantity_for_simple, product_id))
                record_stock_movement(conn, product_id, None, 'initial_stock_serialized', initial_stock_quantity_for_simple, 
                                      "Initial serialized stock for simple product")

            conn.commit()
            audit_logger.log_event('product_created_with_serialized_stock', details={'product_id': product_id, 'name_fr': data['name_fr'], 'num_serialized_items': len(generated_serialized_items_info)})
            return jsonify({
                "message": "Product created successfully with initial serialized stock.", 
                "product_id": product_id, 
                "image_url": image_url,
                "serialized_items_info": generated_serialized_items_info
            }), 201

        except (sqlite3.Error, ValueError) as e_db_val:
            conn.rollback()
            current_app.logger.error(f"DB/Validation error creating product with stock: {e_db_val}", exc_info=True)
            return jsonify({"message": f"Failed to create product: {str(e_db_val)}"}), 500
        except Exception as e_asset: # Catch asset generation specific errors
            conn.rollback()
            current_app.logger.error(f"Asset generation error creating product: {e_asset}", exc_info=True)
            return jsonify({"message": f"Product data saved, but asset generation failed: {str(e_asset)}"}), 500 # Or 500 if critical
        finally:
            if conn: conn.close()

    except json.JSONDecodeError:
        return jsonify({"message": "Invalid JSON in 'product_data'"}), 400
    except Exception as e: # Catch any other unexpected error during initial processing
        current_app.logger.error(f"Unexpected error in create_product: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required
def update_product(product_id):
    # This route updates the PRODUCT DEFINITION. 
    # Serialized items and their individual passports are generally NOT updated here.
    # Aggregate stock counts in products/product_weight_options can be updated.
    # If product name/description changes, existing item passports might become "outdated" in content,
    # but their UIDs and URLs remain. This is a business decision how to handle.
    try:
        product_data_json = request.form.get('product_data')
        if not product_data_json: return jsonify({"message": "Missing 'product_data'"}), 400
        data = json.loads(product_data_json)
        image_file = request.files.get('image_file')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product_row = cursor.fetchone()
        if not product_row: conn.close(); return jsonify({"message": "Product not found"}), 404
        product = row_to_dict(cursor, product_row)

        new_image_url = product.get('image_url')
        if image_file:
            if product.get('image_url'):
                old_image_filename = os.path.basename(product['image_url'])
                old_image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'product_images', old_image_filename)
                if os.path.exists(old_image_path): 
                    try: os.remove(old_image_path)
                    except OSError as e: current_app.logger.error(f"Error deleting old product image {old_image_path}: {e}")
            
            filename = secure_filename(f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
            image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'product_images', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            new_image_url = f"/assets_generated/product_images/{filename}"
        
        conn.execute("BEGIN")
        try:
            # Update product definition
            cursor.execute("""
                UPDATE products SET name_fr = ?, name_en = ?, description_fr = ?, description_en = ?, 
                                   category_id = ?, base_price = ?, image_url = ?, is_active = ?
                WHERE id = ?
            """, (data.get('name_fr', product['name_fr']), data.get('name_en', product['name_en']), 
                  data.get('description_fr', product['description_fr']), data.get('description_en', product['description_en']),
                  data.get('category_id', product['category_id']), data.get('base_price', product['base_price']), 
                  new_image_url, data.get('is_active', product['is_active']), product_id))

            if product['product_type'] == 'variable':
                weight_options_data = data.get('weight_options', [])
                current_total_variant_aggregate_stock = 0
                
                # Get existing variant IDs from form to know which ones to keep/update
                form_variant_ids = {opt.get('id') for opt in weight_options_data if opt.get('id')}

                # Delete variants not present in the form submission (CAUTION with serialized items)
                # This is complex. If a variant type is removed, what about existing serialized items of that type?
                # For now, only updating existing or adding new. Deletion of variant types needs careful strategy.
                # cursor.execute("DELETE FROM product_weight_options WHERE product_id = ? AND id NOT IN ({})".format(','.join('?'*len(form_variant_ids))), (product_id, *form_variant_ids) if form_variant_ids else (product_id,))


                for option in weight_options_data:
                    option_id = option.get('id')
                    # This stock_quantity is the AGGREGATE for the variant type, not for individual UIDs.
                    variant_aggregate_stock = int(option.get('stock_quantity', 0)) 
                    current_total_variant_aggregate_stock += variant_aggregate_stock

                    if option_id: # Existing variant
                        cursor.execute("UPDATE product_weight_options SET weight_grams=?, price=?, stock_quantity=?, sku=? WHERE id=? AND product_id=?",
                                       (option['weight_grams'], option['price'], variant_aggregate_stock, option.get('sku'), option_id, product_id))
                    else: # New variant added to an existing product
                         cursor.execute("INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity, sku) VALUES (?,?,?,?,?)",
                                       (product_id, option['weight_grams'], option['price'], variant_aggregate_stock, option.get('sku')))
                         # If adding a new variant type with initial stock, those UIDs should be created via "Receive Serialized Stock"
                         # This PUT product route is primarily for definition and aggregate stock updates.
                
                # Update the parent product's aggregate stock_quantity based on sum of its variants' aggregate stocks
                cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (current_total_variant_aggregate_stock, product_id))
            
            elif product['product_type'] == 'simple':
                # This updates the AGGREGATE stock for a simple product.
                # Individual UIDs are managed via "Receive Serialized Stock" or sales.
                new_simple_aggregate_stock = data.get('initial_stock_quantity') # Field name from form, better as 'aggregate_stock_count'
                if new_simple_aggregate_stock is not None:
                    cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (int(new_simple_aggregate_stock), product_id))

            conn.commit()
            audit_logger.log_event('product_definition_updated', details={'product_id': product_id, 'name_fr': data.get('name_fr')})
            return jsonify({"message": "Product definition updated successfully"}), 200
        except (sqlite3.Error, ValueError) as e:
            conn.rollback(); current_app.logger.error(f"Error updating product {product_id}: {e}", exc_info=True); return jsonify({"message": "Failed to update product", "error": str(e)}), 500
        finally:
            if conn: conn.close()
    except json.JSONDecodeError: return jsonify({"message": "Invalid JSON in 'product_data'"}), 400
    except Exception as e: current_app.logger.error(f"Unexpected error in update_product {product_id}: {e}", exc_info=True); return jsonify({"message": "Unexpected error", "error": str(e)}), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required
def delete_product(product_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Check for active (in_stock, allocated) serialized items
        cursor.execute("SELECT COUNT(*) FROM serialized_inventory_items WHERE product_id = ? AND status IN ('in_stock', 'allocated')", (product_id,))
        active_item_count_row = cursor.fetchone()
        active_item_count = active_item_count_row[0] if active_item_count_row else 0
        if active_item_count > 0:
            conn.close()
            return jsonify({"message": f"Cannot delete product: {active_item_count} active serialized items exist. Please manage them first (e.g., mark as archived/damaged or reassign)."}), 409
        
        # Check for orders associated with this product (via order_items)
        # This check should ideally look at item_uids that trace back to this product_id.
        # For simplicity, checking direct product_id in order_items.
        cursor.execute("SELECT COUNT(*) FROM order_items WHERE product_id = ?", (product_id,))
        order_item_count_row = cursor.fetchone()
        order_item_count = order_item_count_row[0] if order_item_count_row else 0
        if order_item_count > 0:
            conn.close()
            return jsonify({"message": f"Cannot delete product: It is referenced in {order_item_count} order items. Consider archiving the product instead."}), 409

        conn.execute("BEGIN")
        product_info_row = cursor.execute("SELECT image_url FROM products WHERE id = ?", (product_id,)).fetchone()
        product_info = row_to_dict(cursor, product_info_row)

        if product_info and product_info.get('image_url'):
            img_filename = os.path.basename(product_info['image_url'])
            img_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'product_images', img_filename)
            if os.path.exists(img_path): 
                try: os.remove(img_path)
                except OSError as e: current_app.logger.error(f"Error deleting product image file {img_path}: {e}")
        
        # Delete related data. Order matters due to FK constraints if not using CASCADE.
        # inventory_movements for non-serialized items, or general product adjustments
        cursor.execute("DELETE FROM inventory_movements WHERE product_id = ? AND related_item_uid IS NULL", (product_id,))
        # reviews
        cursor.execute("DELETE FROM reviews WHERE product_id = ?", (product_id,))
        # product_weight_options (will fail if serialized_inventory_items has FK to it without ON DELETE CASCADE)
        # Ensure serialized_inventory_items with this product_id (and its variants) are handled first or FK allows SET NULL/CASCADE.
        # Assuming serialized_inventory_items are already confirmed non-active or managed.
        # If FK product_weight_options.product_id has ON DELETE CASCADE, this is fine.
        # If serialized_inventory_items.variant_id has ON DELETE RESTRICT, this will fail if items point to these variants.
        # It's safer to ensure no serialized_inventory_items reference variants of this product before deleting variants.
        # For now, we proceed assuming this check is implicitly covered by the "no active items" rule.
        cursor.execute("DELETE FROM product_weight_options WHERE product_id = ?", (product_id,))
        
        # Finally, delete the product itself
        delete_product_result = cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        
        if delete_product_result.rowcount == 0 :
             conn.rollback()
             return jsonify({"message": "Product not found or could not be deleted."}), 404

        conn.commit()
        audit_logger.log_event('product_definition_deleted', details={'product_id': product_id})
        return jsonify({"message": "Product definition deleted successfully"}), 200
    except sqlite3.IntegrityError as ie:
        conn.rollback()
        current_app.logger.error(f"DB integrity error deleting product {product_id}: {ie}", exc_info=True)
        return jsonify({"message": "Failed to delete product due to existing references (e.g., in historical orders or unmanaged serialized items). Please resolve these first or consider archiving.", "error": str(ie)}), 409
    except sqlite3.Error as e:
        conn.rollback(); current_app.logger.error(f"DB error deleting product {product_id}: {e}", exc_info=True); return jsonify({"message": "Failed to delete product", "error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- Users ---
@admin_api_bp.route('/users', methods=['GET'])
@jwt_required
def get_users():
    # Add pagination, filtering by role, status etc.
    filter_role = request.args.get('role')
    query = """
        SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.is_verified, u.account_status, 
               u.created_at, u.company_name, u.vat_number,
               a.address_line1, a.city, a.postal_code, a.country 
        FROM users u
        LEFT JOIN addresses a ON u.id = a.user_id AND (a.is_default_shipping = 1 OR a.is_default_billing = 1)
    """
    params = []
    if filter_role:
        query += " WHERE u.role = ?"
        params.append(filter_role)
    query += " ORDER BY u.created_at DESC"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        users_rows = cursor.fetchall()
        users = [row_to_dict(cursor, r) for r in users_rows]
        conn.close()
        return jsonify(users), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching users: {e}", exc_info=True)
        return jsonify({"message": "Failed to fetch users", "error": str(e)}), 500

@admin_api_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required
def update_user(user_id):
    data = request.get_json()
    allowed_updates = {}
    if 'role' in data and data['role'] in ['b2c', 'professional', 'admin']: allowed_updates['role'] = data['role']
    if 'is_verified' in data: allowed_updates['is_verified'] = 1 if data['is_verified'] else 0
    if 'account_status' in data and data['account_status'] in ['pending', 'approved', 'rejected', 'suspended']: allowed_updates['account_status'] = data['account_status']
    if 'first_name' in data: allowed_updates['first_name'] = data['first_name']
    if 'last_name' in data: allowed_updates['last_name'] = data['last_name']
    if 'company_name' in data: allowed_updates['company_name'] = data['company_name']
    # Add other fields an admin might edit (e.g. phone_number, siret_number, vat_number)

    if not allowed_updates: return jsonify({"message": "No valid fields provided for update"}), 400
    
    set_parts = [f"{key} = :{key}" for key in allowed_updates.keys()] # Use named placeholders
    set_clause = ", ".join(set_parts)
    
    # Add user_id to the dictionary for the WHERE clause
    update_values = {**allowed_updates, "user_id_to_update": user_id}


    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = :user_id_to_update", update_values)
        conn.commit()
        
        if cursor.rowcount == 0: 
            conn.close()
            return jsonify({"message": "User not found or no changes made"}), 404
        
        audit_logger.log_event('user_updated_by_admin', details={'target_user_id': user_id, 'changes': allowed_updates})
        
        # Send email notification for B2B account status changes
        if 'account_status' in allowed_updates and allowed_updates['account_status'] in ['approved', 'rejected']:
            user_info_row = cursor.execute("SELECT email, first_name, role FROM users WHERE id = ?", (user_id,)).fetchone()
            user_info = row_to_dict(cursor, user_info_row) # Convert to dict
            conn.close() # Close DB connection before potentially long operation like sending email

            if user_info and user_info.get('role') == 'professional' and user_info.get('email'):
                status_translation = {'approved': 'approuvé', 'rejected': 'rejeté'}
                email_subject = f"Mise à jour du statut de votre compte professionnel - Maison Trüvra"
                email_body = f"Bonjour {user_info.get('first_name', 'Professionnel')},\n\n"
                email_body += f"Le statut de votre compte professionnel Maison Trüvra a été mis à jour : {status_translation.get(allowed_updates['account_status'], allowed_updates['account_status'])}.\n"
                if allowed_updates['account_status'] == 'approved':
                    email_body += "Vous pouvez maintenant vous connecter et accéder à nos tarifs et services professionnels.\n"
                elif allowed_updates['account_status'] == 'rejected':
                     email_body += "Pour plus d'informations ou si vous pensez qu'il s'agit d'une erreur, veuillez contacter notre support.\n"
                email_body += "\nCordialement,\nL'équipe Maison Trüvra"
                
                if not send_email_alert(email_subject, email_body, user_info['email']): # Ensure send_email_alert is robust
                    current_app.logger.error(f"Failed to send account status update email to {user_info['email']}")
                    # Potentially return a partial success message if email fails but DB update was ok
            elif conn: # Ensure connection is closed if not closed above
                 conn.close()
        else: # If no email to send, ensure connection is closed
            if conn: conn.close()

        return jsonify({"message": "User updated successfully"}), 200
    except sqlite3.Error as e:
        if conn: conn.close() # Ensure connection is closed on error too
        current_app.logger.error(f"DB error updating user {user_id}: {e}", exc_info=True); return jsonify({"message": "Failed to update user", "error": str(e)}), 500


# --- Reviews ---
@admin_api_bp.route('/reviews', methods=['GET'])
@jwt_required
def get_reviews():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.product_id, p.name_fr as product_name, r.user_id, u.email as user_email, 
                   r.rating, r.comment, r.is_approved, r.created_at
            FROM reviews r
            JOIN products p ON r.product_id = p.id
            JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
        """)
        reviews_rows = cursor.fetchall()
        reviews = [row_to_dict(cursor, r) for r in reviews_rows]
        conn.close()
        return jsonify(reviews), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching reviews: {e}", exc_info=True)
        return jsonify({"message": "Failed to fetch reviews", "error": str(e)}), 500

@admin_api_bp.route('/reviews/<int:review_id>/approve', methods=['PUT'])
@jwt_required
def approve_review(review_id):
    data = request.get_json()
    is_approved_status = data.get('is_approved', 1) # Default to approving, allow 0 to unapprove
    
    if not isinstance(is_approved_status, bool) and is_approved_status not in [0,1]:
        return jsonify({"message": "Invalid 'is_approved' status. Must be boolean, 0, or 1."}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE reviews SET is_approved = ? WHERE id = ?", (1 if is_approved_status else 0, review_id))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Review not found"}), 404
        conn.close()
        audit_logger.log_event('review_approval_updated', details={'review_id': review_id, 'is_approved': is_approved_status})
        return jsonify({"message": f"Review status updated successfully (Approved: {bool(is_approved_status)})"}), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error updating review {review_id} approval: {e}", exc_info=True)
        return jsonify({"message": "Failed to update review approval status", "error": str(e)}), 500

@admin_api_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required
def delete_review(review_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Review not found"}), 404
        conn.close()
        audit_logger.log_event('review_deleted', details={'review_id': review_id})
        return jsonify({"message": "Review deleted successfully"}), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error deleting review {review_id}: {e}", exc_info=True)
        return jsonify({"message": "Failed to delete review", "error": str(e)}), 500

# --- Admin Order Management ---
@admin_api_bp.route('/orders', methods=['GET'])
@jwt_required
def get_admin_orders():
    # Add pagination and filtering (by status, user, date range)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id as order_id, u.email as user_email, u.first_name, u.last_name, 
                   o.order_date, o.total_amount, o.status
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.order_date DESC
        """)
        orders_rows = cursor.fetchall()
        orders_summary = [row_to_dict(cursor, r) for r in orders_rows]
        
        # Optionally, fetch items for each order if needed in summary view, or provide a separate detail endpoint
        # For performance, avoid fetching all items for all orders in a list view if not essential.
        # Example to add items (can be slow for many orders):
        # for order_summary in orders_summary:
        #     items_cursor = conn.cursor()
        #     items_cursor.execute("SELECT item_uid, name_fr_at_purchase, quantity, price_at_purchase FROM order_items WHERE order_id = ?", (order_summary['order_id'],))
        #     order_summary['items'] = [row_to_dict(items_cursor, i) for i in items_cursor.fetchall()]
            
        conn.close()
        return jsonify(orders_summary), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching orders for admin: {e}", exc_info=True)
        return jsonify({"message": "Failed to fetch orders", "error": str(e)}), 500

@admin_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')
    valid_statuses = ['pending_payment', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
    if not new_status or new_status not in valid_statuses:
        return jsonify({"message": f"Invalid or missing status. Must be one of: {', '.join(valid_statuses)}"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch order details to get user email for notification
        order_user_info_row = cursor.execute("SELECT u.email, u.first_name FROM orders o JOIN users u ON o.user_id = u.id WHERE o.id = ?", (order_id,)).fetchone()
        order_user_info = row_to_dict(cursor, order_user_info_row)

        cursor.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, order_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Order not found"}), 404
        
        conn.close() # Close before email

        if order_user_info and order_user_info.get('email'):
            email_subject = f"Mise à jour de votre commande #{order_id} - Maison Trüvra"
            email_body = f"Bonjour {order_user_info.get('first_name', 'Client')},\n\nLe statut de votre commande #{order_id} a été mis à jour : {new_status}.\n\nVous pouvez consulter les détails de votre commande sur votre compte.\n\nCordialement,\nL'équipe Maison Trüvra"
            if not send_email_alert(email_subject, email_body, order_user_info['email']):
                current_app.logger.error(f"Failed to send order status update email for order {order_id} to {order_user_info['email']}")
                # Don't fail the request if email fails, but log it.

        audit_logger.log_event('order_status_updated_by_admin', details={'order_id': order_id, 'new_status': new_status})
        return jsonify({"message": f"Order {order_id} status updated to {new_status}"}), 200
    except sqlite3.Error as e:
        if conn: conn.close()
        current_app.logger.error(f"Database error updating order status for {order_id}: {e}", exc_info=True)
        return jsonify({"message": "Failed to update order status", "error": str(e)}), 500

# --- Professional Invoices ---
@admin_api_bp.route('/invoices/professional', methods=['POST'])
@jwt_required
def generate_professional_invoice_admin():
    data_form = request.form 
    invoice_details_json = data_form.get('invoice_details')
    if not invoice_details_json:
        return jsonify({"message": "Missing 'invoice_details' in form data"}), 400
    
    try:
        invoice_data_dict = json.loads(invoice_details_json)
    except json.JSONDecodeError:
        return jsonify({"message": "Invalid JSON in 'invoice_details'"}), 400

    company_info_override = {k.replace('template_', ''): v for k, v in data_form.items() if k.startswith('template_')}

    required_invoice_fields = ['professional_user_id', 'items', 'invoice_id_display', 'issue_date', 'due_date', 'subtotal_ht', 'total_vat_amount', 'total_amount_ttc']
    if not all(k in invoice_data_dict for k in required_invoice_fields):
        missing_fields = [k for k in required_invoice_fields if k not in invoice_data_dict]
        return jsonify({"message": f"Missing required fields in invoice_details: {', '.join(missing_fields)}"}), 400

    try:
        # Assuming invoice_service.create_and_save_professional_invoice handles DB insertion and PDF generation
        pdf_fs_path, invoice_number_from_db = invoice_service.create_and_save_professional_invoice(
            invoice_data_dict, 
            company_info_override=company_info_override if company_info_override else None
        )
        
        pdf_filename = os.path.basename(pdf_fs_path)
        # Construct URL based on how assets are served.
        # INVOICE_PDF_PATH is like ".../assets_generated/invoices"
        # The URL should be "/assets_generated/invoices/filename.pdf" if ASSET_STORAGE_PATH is the root for /assets_generated
        # Or more directly:
        pdf_url = f"/{os.path.basename(current_app.config['INVOICE_PDF_PATH'])}/{pdf_filename}"
        
        audit_logger.log_event('professional_invoice_generated_admin', details={'invoice_number': invoice_number_from_db, 'professional_user_id': invoice_data_dict['professional_user_id']})
        return jsonify({"message": "Professional invoice generated successfully", "pdf_url": pdf_url, "invoice_number": invoice_number_from_db}), 201
    except ValueError as ve: 
        current_app.logger.warning(f"Validation error generating prof invoice: {ve}")
        return jsonify({"message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error generating professional invoice: {e}", exc_info=True)
        return jsonify({"message": "Failed to generate professional invoice", "error": str(e)}), 500

@admin_api_bp.route('/invoices', methods=['GET'])
@jwt_required
def get_all_invoices():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pi.id, pi.invoice_number, pi.professional_user_id, u.company_name, u.email as user_email,
                   pi.issue_date, pi.due_date, pi.total_amount_ttc, pi.status, pi.pdf_path
            FROM professional_invoices pi
            JOIN users u ON pi.professional_user_id = u.id
            ORDER BY pi.issue_date DESC
        """)
        prof_invoices_rows = cursor.fetchall()
        prof_invoices = []
        for row_tuple in prof_invoices_rows:
            inv_dict = row_to_dict(cursor, row_tuple)
            if inv_dict and inv_dict.get('pdf_path'): # pdf_path is filesystem path
                pdf_filename = os.path.basename(inv_dict['pdf_path'])
                inv_dict['pdf_url'] = f"/{os.path.basename(current_app.config['INVOICE_PDF_PATH'])}/{pdf_filename}"
            else:
                if inv_dict: inv_dict['pdf_url'] = None
            if inv_dict: prof_invoices.append(inv_dict)
        
        conn.close()
        return jsonify({"professional_invoices": prof_invoices, "b2c_invoices": []}), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching invoices: {e}", exc_info=True)
        return jsonify({"message": "Failed to fetch invoices", "error": str(e)}), 500

# --- Serve generated assets ---
# This route allows serving files from various subdirectories within ASSET_STORAGE_PATH
@admin_api_bp.route('/assets/<path:folder>/<path:filename>')
# @jwt_required # Consider if these assets need admin protection or are public once URL is known.
# For QR codes, labels, product images, they are often public. Invoices might be protected.
def serve_generated_asset(folder, filename):
    allowed_folders = ['product_labels', 'product_passports', 'product_qr_codes', 'invoices', 'product_images', 'category_images']
    if folder not in allowed_folders: 
        current_app.logger.warning(f"Access attempt to invalid asset folder: {folder}")
        return jsonify({"message": "Invalid asset folder"}), 403
    
    # ASSET_STORAGE_PATH is the root for all generated assets (e.g. /abs/path/to/project/assets_generated)
    # The 'folder' variable from the URL specifies the subdirectory within ASSET_STORAGE_PATH
    directory = os.path.join(current_app.config['ASSET_STORAGE_PATH'], folder)
    
    # Securely serve the file
    file_path = os.path.join(directory, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path): # Check if file exists and is a file
        current_app.logger.warning(f"Asset not found: {file_path}")
        return jsonify({"message": "Asset not found"}), 404
    
    # Final security check: ensure the resolved absolute path of the file
    # is still within the intended base 'directory'. This helps prevent directory traversal attacks
    # if 'filename' somehow contains '..' or similar. os.path.normpath can also be useful.
    if not os.path.abspath(file_path).startswith(os.path.abspath(directory)):
        current_app.logger.error(f"Security: Attempt to access asset outside designated directory. Path: {file_path}")
        return jsonify({"message": "Forbidden"}), 403 # Or abort(403)

    return send_from_directory(directory, filename)
