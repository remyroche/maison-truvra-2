# backend/admin_api/routes.py
from flask import Blueprint, request, jsonify, current_app, send_from_directory
import sqlite3
import os
import json
from werkzeug.utils import secure_filename
from ..database import get_db_connection, record_stock_movement
from ..utils import jwt_required # Import the JWT decorator
from ..audit_log_service import AuditLogService
from ..services.asset_service import AssetService # Assuming this service exists
from ..services.invoice_service import InvoiceService # Assuming this service exists

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')
audit_logger = AuditLogService()
asset_service = AssetService() 
invoice_service = InvoiceService()

# Helper to convert row to dict
def row_to_dict(cursor, row):
    return dict(zip([column[0] for column in cursor.description], row))

# --- Dashboard ---
@admin_api_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required # Protect this route
def get_dashboard_stats():
    # TODO: Implement actual stats fetching
    # For now, returning placeholders as in the original JS
    # This should query orders, users, products, reviews tables
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'b2c' OR role = 'professional'")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]
        
        # Assuming 'orders' table exists with 'order_date' and 'total_amount'
        cursor.execute("SELECT COUNT(*) FROM orders WHERE date(order_date) = date('now')")
        orders_today = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_amount) FROM orders WHERE date(order_date) = date('now')")
        revenue_today_row = cursor.fetchone()
        revenue_today = revenue_today_row[0] if revenue_today_row and revenue_today_row[0] is not None else 0.0


        # Recent Orders (Example: last 5)
        cursor.execute("""
            SELECT o.id, u.email as user_email, o.order_date, o.total_amount, o.status 
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.order_date DESC LIMIT 5
        """)
        recent_orders_rows = cursor.fetchall()
        recent_orders = [row_to_dict(cursor, r) for r in recent_orders_rows]

        # Recent Reviews (Example: last 5, assuming 'reviews' table)
        # ALTER TABLE reviews ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        cursor.execute("""
            SELECT r.id, u.email as user_email, p.name_fr as product_name, r.rating, r.comment, r.created_at 
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            JOIN products p ON r.product_id = p.id
            ORDER BY r.created_at DESC LIMIT 5
        """)
        recent_reviews_rows = cursor.fetchall()
        recent_reviews = [row_to_dict(cursor, r) for r in recent_reviews_rows]
        
        conn.close()

        stats = {
            "totalUsers": total_users,
            "totalProducts": total_products,
            "ordersToday": orders_today,
            "revenueToday": revenue_today,
            "recentOrders": recent_orders,
            "recentReviews": recent_reviews 
        }
        return jsonify(stats), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching dashboard stats: {e}")
        return jsonify({"message": "Failed to fetch dashboard stats", "error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard stats: {e}")
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500


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
        current_app.logger.error(f"Database error fetching categories: {e}")
        return jsonify({"message": "Failed to fetch categories", "error": str(e)}), 500

@admin_api_bp.route('/categories', methods=['POST'])
@jwt_required
def create_category():
    data = request.form.to_dict()
    image_file = request.files.get('image_file')
    
    required_fields = ['name_fr', 'name_en']
    if not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required fields (name_fr, name_en)"}), 400

    image_url = None
    if image_file:
        if not os.path.exists(current_app.config['ASSET_STORAGE_PATH']):
            os.makedirs(current_app.config['ASSET_STORAGE_PATH'])
        filename = secure_filename(image_file.filename)
        # Consider adding a unique prefix to filename to avoid collisions
        image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'category_images', filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image_file.save(image_path)
        image_url = f"/assets_generated/category_images/{filename}" # URL path to serve the image

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO categories (name_fr, name_en, description_fr, description_en, image_url)
            VALUES (?, ?, ?, ?, ?)
        """, (data['name_fr'], data['name_en'], data.get('description_fr'), data.get('description_en'), image_url))
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        audit_logger.log_event('category_created', details={'category_id': category_id, 'name_fr': data['name_fr']})
        return jsonify({"message": "Category created successfully", "category_id": category_id, "image_url": image_url}), 201
    except sqlite3.IntegrityError: # e.g. unique constraint on name
        return jsonify({"message": "Category name might already exist or other integrity constraint failed."}), 409
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error creating category: {e}")
        return jsonify({"message": "Failed to create category", "error": str(e)}), 500

@admin_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required
def update_category(category_id):
    data = request.form.to_dict()
    image_file = request.files.get('image_file')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image_url FROM categories WHERE id = ?", (category_id,))
    category = cursor.fetchone()
    if not category:
        conn.close()
        return jsonify({"message": "Category not found"}), 404

    image_url = category['image_url'] # Keep old image if new one not provided
    if image_file:
        # Optionally, delete old image file from server
        if image_url:
            old_image_path = os.path.join(current_app.root_path, '..', image_url.lstrip('/')) # Adjust path as needed
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except OSError as e:
                    current_app.logger.error(f"Error deleting old category image {old_image_path}: {e}")

        filename = secure_filename(image_file.filename)
        image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'category_images', filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image_file.save(image_path)
        image_url = f"/assets_generated/category_images/{filename}"

    try:
        cursor.execute("""
            UPDATE categories SET name_fr = ?, name_en = ?, description_fr = ?, description_en = ?, image_url = ?
            WHERE id = ?
        """, (data.get('name_fr'), data.get('name_en'), data.get('description_fr'), data.get('description_en'), image_url, category_id))
        conn.commit()
        conn.close()
        audit_logger.log_event('category_updated', details={'category_id': category_id, 'name_fr': data.get('name_fr')})
        return jsonify({"message": "Category updated successfully", "image_url": image_url}), 200
    except sqlite3.Error as e:
        conn.close()
        current_app.logger.error(f"Database error updating category {category_id}: {e}")
        return jsonify({"message": "Failed to update category", "error": str(e)}), 500


@admin_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@jwt_required
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if category is used by products
    cursor.execute("SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,))
    product_count = cursor.fetchone()[0]
    if product_count > 0:
        conn.close()
        return jsonify({"message": f"Cannot delete category: it is associated with {product_count} product(s). Please reassign or delete them first."}), 409

    cursor.execute("SELECT image_url FROM categories WHERE id = ?", (category_id,))
    category = cursor.fetchone()

    try:
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        
        if category and category['image_url']: # Delete image file
            image_path = os.path.join(current_app.root_path, '..', category['image_url'].lstrip('/'))
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError as e:
                    current_app.logger.error(f"Error deleting category image {image_path}: {e}")
        
        conn.close()
        audit_logger.log_event('category_deleted', details={'category_id': category_id})
        return jsonify({"message": "Category deleted successfully"}), 200
    except sqlite3.Error as e:
        conn.close()
        current_app.logger.error(f"Database error deleting category {category_id}: {e}")
        return jsonify({"message": "Failed to delete category", "error": str(e)}), 500


# --- Products ---
@admin_api_bp.route('/products', methods=['GET'])
@jwt_required
def get_products():
    # Add pagination and filtering if needed
    category_id_filter = request.args.get('category_id')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT p.id, p.name_fr, p.name_en, p.description_fr, p.description_en, 
                   p.base_price, p.category_id, c.name_fr as category_name_fr, 
                   p.image_url, p.stock_quantity, p.is_active, p.product_type,
                   p.qr_code_path, p.label_path, p.passport_html_path
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
        """
        params = []
        if category_id_filter:
            query += " WHERE p.category_id = ?"
            params.append(category_id_filter)
        
        query += " ORDER BY p.name_fr"

        cursor.execute(query, params)
        products_rows = cursor.fetchall()
        products = []
        for row in products_rows:
            product_dict = row_to_dict(cursor, row)
            # Fetch variants if it's a variable product
            if product_dict['product_type'] == 'variable':
                cursor.execute("""
                    SELECT id, product_id, weight_grams, price, stock_quantity, sku 
                    FROM product_weight_options 
                    WHERE product_id = ?
                """, (product_dict['id'],))
                variants_rows = cursor.fetchall()
                product_dict['variants'] = [row_to_dict(cursor, v_row) for v_row in variants_rows]
            else: # simple product
                # For simple products, overall stock is p.stock_quantity
                # For variable products, p.stock_quantity could be sum of variants or managed differently.
                # The current schema has p.stock_quantity. Let's ensure it's consistent.
                pass
            products.append(product_dict)
        
        conn.close()
        return jsonify(products), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching products: {e}")
        return jsonify({"message": "Failed to fetch products", "error": str(e)}), 500

@admin_api_bp.route('/products', methods=['POST'])
@jwt_required
def create_product():
    # This is a complex endpoint due to variants and asset generation
    # Using request.form for mixed data (JSON for product_data, files for image)
    try:
        product_data_json = request.form.get('product_data')
        if not product_data_json:
            return jsonify({"message": "Missing 'product_data' in form"}), 400
        
        data = json.loads(product_data_json)
        image_file = request.files.get('image_file')
        
        required_fields = ['name_fr', 'name_en', 'category_id', 'product_type']
        if not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in data]
            return jsonify({"message": f"Missing required fields in product_data: {', '.join(missing)}"}), 400

        product_type = data['product_type']
        base_price = data.get('base_price') if product_type == 'simple' else None
        initial_stock = data.get('initial_stock_quantity') if product_type == 'simple' else 0 # For simple products
        weight_options_data = data.get('weight_options', []) if product_type == 'variable' else []

        if product_type == 'simple' and (base_price is None or initial_stock is None):
            return jsonify({"message": "Simple products require 'base_price' and 'initial_stock_quantity'"}), 400
        if product_type == 'variable' and not weight_options_data:
            return jsonify({"message": "Variable products require at least one 'weight_option'"}), 400
        
        image_url = None
        if image_file:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'product_images', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            image_url = f"/assets_generated/product_images/{filename}"

        conn = get_db_connection()
        cursor = conn.cursor()
        conn.execute("BEGIN") # Start transaction

        try:
            # Insert base product
            cursor.execute("""
                INSERT INTO products (name_fr, name_en, description_fr, description_en, category_id, 
                                      base_price, image_url, product_type, is_active, stock_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data['name_fr'], data['name_en'], data.get('description_fr'), data.get('description_en'),
                  data['category_id'], base_price, image_url, product_type, data.get('is_active', True),
                  initial_stock if product_type == 'simple' else 0)) # Overall stock for simple, 0 for variable initially
            product_id = cursor.lastrowid

            total_variable_stock = 0
            if product_type == 'variable':
                for option in weight_options_data:
                    if not all(k in option for k in ['weight_grams', 'price', 'stock_quantity']):
                        raise ValueError("Each weight option requires 'weight_grams', 'price', and 'stock_quantity'.")
                    
                    cursor.execute("""
                        INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity, sku)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_id, option['weight_grams'], option['price'], option['stock_quantity'], option.get('sku')))
                    variant_id = cursor.lastrowid
                    total_variable_stock += int(option['stock_quantity'])
                    # Record initial stock for variant
                    record_stock_movement(conn, product_id, variant_id, 'initial_stock', option['stock_quantity'], 
                                          f"Initial stock for variant {option['weight_grams']}g")
                
                # Update main product's stock_quantity to sum of variants for variable products
                cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (total_variable_stock, product_id))

            elif product_type == 'simple' and initial_stock > 0:
                # Record initial stock for simple product (variant_id is NULL)
                record_stock_movement(conn, product_id, None, 'initial_stock', initial_stock, "Initial stock for simple product")

            # --- Asset Generation ---
            # Use the first variant for asset details if variable, or base product if simple
            asset_product_name = data['name_fr']
            asset_product_id_display = f"MT{product_id:05d}" # Example display ID
            asset_details_for_generation = {
                'product_id': product_id,
                'product_name': asset_product_name,
                'product_id_display': asset_product_id_display,
                'category_name': '', # Fetch category name
                'composition': data.get('description_fr', ''), # Or a specific field
                'origin': 'France', # Example, make this configurable
                'harvest_date': datetime.date.today().strftime('%Y-%m-%d'), # Example
            }
            if product_type == 'variable' and weight_options_data:
                first_variant = weight_options_data[0]
                asset_details_for_generation['weight_grams'] = first_variant['weight_grams']
                asset_details_for_generation['price_per_kg'] = (float(first_variant['price']) / float(first_variant['weight_grams'])) * 1000
            elif product_type == 'simple' and base_price is not None:
                # Assuming simple products might have a standard weight or it's part of description
                asset_details_for_generation['weight_grams'] = data.get('base_weight_grams', 0) # Add this field if applicable
                asset_details_for_generation['price_per_kg'] = 0 # Calculate if applicable
            
            # Fetch category name for assets
            cat_cursor = conn.cursor()
            cat_cursor.execute("SELECT name_fr FROM categories WHERE id = ?", (data['category_id'],))
            cat_data = cat_cursor.fetchone()
            if cat_data:
                asset_details_for_generation['category_name'] = cat_data['name_fr']


            qr_path, label_path, passport_path = None, None, None
            try:
                qr_path = asset_service.generate_qr_code(product_id, f"{current_app.config['FRONTEND_URL']}/produit-detail.html?id={product_id}")
                label_path = asset_service.generate_product_label(asset_details_for_generation)
                passport_path = asset_service.generate_product_passport(asset_details_for_generation)
                
                cursor.execute("""
                    UPDATE products SET qr_code_path = ?, label_path = ?, passport_html_path = ? 
                    WHERE id = ?
                """, (qr_path, label_path, passport_path, product_id))
                asset_generation_success = True
            except Exception as asset_e:
                current_app.logger.error(f"Asset generation failed for product {product_id}: {asset_e}")
                # Decide if this is a critical failure or if product can be created without assets
                asset_generation_success = False # Or raise to rollback

            conn.commit()
            audit_logger.log_event('product_created', details={'product_id': product_id, 'name_fr': data['name_fr'], 'assets_generated': asset_generation_success})
            return jsonify({
                "message": "Product created successfully" + (" (assets generated)" if asset_generation_success else " (asset generation failed)"), 
                "product_id": product_id, 
                "image_url": image_url,
                "qr_code_path": qr_path,
                "label_path": label_path,
                "passport_html_path": passport_path
            }), 201

        except (sqlite3.Error, ValueError) as e:
            conn.rollback()
            current_app.logger.error(f"Error creating product: {e}")
            return jsonify({"message": "Failed to create product", "error": str(e)}), 500
        finally:
            conn.close()

    except json.JSONDecodeError:
        return jsonify({"message": "Invalid JSON in 'product_data'"}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in create_product: {e}")
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required
def update_product(product_id):
    # Similar complexity to create_product
    try:
        product_data_json = request.form.get('product_data')
        if not product_data_json:
            return jsonify({"message": "Missing 'product_data' in form"}), 400
        
        data = json.loads(product_data_json)
        image_file = request.files.get('image_file')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT image_url, product_type, stock_quantity FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            conn.close()
            return jsonify({"message": "Product not found"}), 404

        current_image_url = product['image_url']
        new_image_url = current_image_url
        if image_file:
            # Optionally delete old image
            if current_image_url:
                old_image_path = os.path.join(current_app.root_path, '..', current_image_url.lstrip('/'))
                if os.path.exists(old_image_path): os.remove(old_image_path)
            
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(current_app.config['ASSET_STORAGE_PATH'], 'product_images', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            new_image_url = f"/assets_generated/product_images/{filename}"

        product_type = data.get('product_type', product['product_type']) # Cannot change product type easily
        base_price = data.get('base_price') if product_type == 'simple' else None
        
        # Stock updates are complex:
        # For simple products, 'initial_stock_quantity' in form might mean 'new_stock_quantity'
        # For variable products, 'weight_options' will contain new stock for each variant.
        
        conn.execute("BEGIN")
        try:
            cursor.execute("""
                UPDATE products SET name_fr = ?, name_en = ?, description_fr = ?, description_en = ?, 
                                   category_id = ?, base_price = ?, image_url = ?, is_active = ?
                WHERE id = ?
            """, (data.get('name_fr'), data.get('name_en'), data.get('description_fr'), data.get('description_en'),
                  data.get('category_id'), base_price, new_image_url, data.get('is_active', True),
                  product_id))

            total_variable_stock_after_update = 0
            if product_type == 'variable':
                # Manage variants: delete old, add new/update existing. This is complex.
                # Simpler: Assume frontend sends ALL variants. Delete existing, then re-add.
                # More robust: Identify existing, new, deleted variants.
                
                # Get current variants' stock
                cursor.execute("SELECT id, stock_quantity FROM product_weight_options WHERE product_id = ?", (product_id,))
                old_variants_stock = {v['id']: v['stock_quantity'] for v in cursor.fetchall()}

                # For simplicity here: delete all existing variants for this product and re-add from `data`
                # This means SKUs might change if not careful, or IDs.
                # A more sophisticated diff and update/insert/delete is better for production.
                cursor.execute("DELETE FROM product_weight_options WHERE product_id = ?", (product_id,))
                # Also clear related stock movements or handle them carefully.
                # For now, we'll just record new movements.

                weight_options_data = data.get('weight_options', [])
                if not weight_options_data: # If variable product now has no variants, this is an issue.
                     # conn.rollback()
                     # return jsonify({"message": "Variable product must have at least one weight option"}), 400
                     # Or convert to simple? For now, assume frontend sends valid data.
                     pass


                for option in weight_options_data:
                    cursor.execute("""
                        INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity, sku)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_id, option['weight_grams'], option['price'], option['stock_quantity'], option.get('sku')))
                    variant_id = cursor.lastrowid # New variant ID
                    new_stock = int(option['stock_quantity'])
                    total_variable_stock_after_update += new_stock
                    
                    # Determine stock change for movement record
                    # This is simplified because we deleted old ones. A diff would be better.
                    # For now, consider this as setting new stock level.
                    # If we had old_variant_stock_for_this_sku, change = new_stock - old_variant_stock_for_this_sku
                    # Since we deleted, we treat it as a new 'adjustment' or 'initial_variant_stock_update'
                    record_stock_movement(conn, product_id, variant_id, 'stock_update', new_stock,
                                          f"Stock update for variant {option['weight_grams']}g during product update")
                
                cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (total_variable_stock_after_update, product_id))

            elif product_type == 'simple':
                new_simple_stock = data.get('initial_stock_quantity') # Assuming this field name from form
                if new_simple_stock is not None:
                    new_simple_stock = int(new_simple_stock)
                    old_simple_stock = product['stock_quantity'] if product['stock_quantity'] is not None else 0
                    stock_change = new_simple_stock - old_simple_stock
                    
                    cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (new_simple_stock, product_id))
                    if stock_change != 0:
                         record_stock_movement(conn, product_id, None, 
                                              'stock_adjustment' if stock_change > 0 else 'stock_reduction', 
                                              abs(stock_change), "Stock update for simple product via admin edit")
            
            # --- Asset Re-Generation (Optional, or only if relevant fields changed) ---
            # For simplicity, let's assume assets might need regeneration if product name/details change
            asset_product_name = data.get('name_fr', product['name_fr']) # Use new name if provided
            asset_product_id_display = f"MT{product_id:05d}"
            asset_details_for_generation = {
                'product_id': product_id,
                'product_name': asset_product_name,
                'product_id_display': asset_product_id_display,
                'category_name': '', 
                'composition': data.get('description_fr', ''),
                'origin': 'France', 
                'harvest_date': datetime.date.today().strftime('%Y-%m-%d'),
            }
            # ... (fetch category, set weight/price as in create_product) ...
            cat_cursor = conn.cursor() # Use a new cursor or ensure the main one is not in use
            cat_cursor.execute("SELECT name_fr FROM categories WHERE id = ?", (data.get('category_id', product['category_id']),))
            cat_data = cat_cursor.fetchone()
            if cat_data: asset_details_for_generation['category_name'] = cat_data['name_fr']
            
            # Add weight/price for asset generation (similar logic to create)
            # ...

            qr_path, label_path, passport_path = product.get('qr_code_path'), product.get('label_path'), product.get('passport_html_path')
            asset_regeneration_success = True # Assume true, set false on error
            try:
                # Potentially only regenerate if key data changed, or always regenerate
                new_qr_path = asset_service.generate_qr_code(product_id, f"{current_app.config['FRONTEND_URL']}/produit-detail.html?id={product_id}")
                new_label_path = asset_service.generate_product_label(asset_details_for_generation)
                new_passport_path = asset_service.generate_product_passport(asset_details_for_generation)
                
                if new_qr_path != qr_path or new_label_path != label_path or new_passport_path != passport_path:
                    cursor.execute("""
                        UPDATE products SET qr_code_path = ?, label_path = ?, passport_html_path = ? 
                        WHERE id = ?
                    """, (new_qr_path, new_label_path, new_passport_path, product_id))
                    qr_path, label_path, passport_path = new_qr_path, new_label_path, new_passport_path
            except Exception as asset_e:
                current_app.logger.error(f"Asset re-generation failed for product {product_id}: {asset_e}")
                asset_regeneration_success = False


            conn.commit()
            audit_logger.log_event('product_updated', details={'product_id': product_id, 'name_fr': data.get('name_fr'), 'assets_regenerated': asset_regeneration_success})
            return jsonify({
                "message": "Product updated successfully" + (" (assets re-generated)" if asset_regeneration_success else " (asset re-generation failed/skipped)"),
                "product_id": product_id, 
                "image_url": new_image_url,
                "qr_code_path": qr_path,
                "label_path": label_path,
                "passport_html_path": passport_path
            }), 200

        except (sqlite3.Error, ValueError) as e:
            conn.rollback()
            current_app.logger.error(f"Error updating product {product_id}: {e}")
            return jsonify({"message": "Failed to update product", "error": str(e)}), 500
        finally:
            conn.close()

    except json.JSONDecodeError:
        return jsonify({"message": "Invalid JSON in 'product_data'"}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in update_product {product_id}: {e}")
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute("BEGIN")
    try:
        cursor = conn.cursor()
        # Check if product is in any orders (more complex check needed if order_items table exists)
        # For now, basic check. A real system would check order_items.
        # cursor.execute("SELECT COUNT(*) FROM order_items WHERE product_id = ? OR variant_id IN (SELECT id FROM product_weight_options WHERE product_id = ?)", (product_id, product_id))
        # if cursor.fetchone()[0] > 0:
        #     conn.rollback()
        #     return jsonify({"message": "Cannot delete product: it is part of existing orders."}), 409

        # Delete assets (QR, label, passport files)
        cursor.execute("SELECT image_url, qr_code_path, label_path, passport_html_path FROM products WHERE id = ?", (product_id,))
        product_assets = cursor.fetchone()
        if product_assets:
            for asset_key in ['image_url', 'qr_code_path', 'label_path', 'passport_html_path']:
                if product_assets[asset_key]:
                    asset_file_path = os.path.join(current_app.root_path, '..', product_assets[asset_key].lstrip('/'))
                    if os.path.exists(asset_file_path):
                        try:
                            os.remove(asset_file_path)
                        except OSError as e:
                             current_app.logger.error(f"Error deleting asset file {asset_file_path} for product {product_id}: {e}")
        
        # Delete variants and their stock movements first
        cursor.execute("DELETE FROM inventory_movements WHERE product_id = ?", (product_id,)) # Deletes for simple and variable
        cursor.execute("DELETE FROM product_weight_options WHERE product_id = ?", (product_id,))
        # Delete product
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        
        # Delete reviews for this product
        cursor.execute("DELETE FROM reviews WHERE product_id = ?", (product_id,))

        conn.commit()
        audit_logger.log_event('product_deleted', details={'product_id': product_id})
        return jsonify({"message": "Product deleted successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error deleting product {product_id}: {e}")
        return jsonify({"message": "Failed to delete product", "error": str(e)}), 500
    finally:
        conn.close()


# --- Users ---
@admin_api_bp.route('/users', methods=['GET'])
@jwt_required
def get_users():
    # Add pagination and filtering (e.g., by role, status)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetching more details including address for B2C and company for B2B
        # This could be multiple queries or a more complex join
        cursor.execute("""
            SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.is_verified, u.account_status, 
                   u.created_at, u.company_name, u.vat_number,
                   a.address_line1, a.city, a.postal_code, a.country 
            FROM users u
            LEFT JOIN addresses a ON u.id = a.user_id AND (a.is_default_shipping = 1 OR a.is_default_billing = 1)
            ORDER BY u.created_at DESC
        """) # Simplified address join, might pick one if multiple defaults
        users_rows = cursor.fetchall()
        users = [row_to_dict(cursor, r) for r in users_rows]
        conn.close()
        return jsonify(users), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching users: {e}")
        return jsonify({"message": "Failed to fetch users", "error": str(e)}), 500

@admin_api_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required
def update_user(user_id):
    data = request.get_json()
    # Admin can update role, verification status, account_status (for B2B)
    # Be careful about updating passwords here - should be a separate flow or require confirmation.
    
    allowed_updates = {}
    if 'role' in data and data['role'] in ['b2c', 'professional', 'admin']:
        allowed_updates['role'] = data['role']
    if 'is_verified' in data: # boolean
        allowed_updates['is_verified'] = 1 if data['is_verified'] else 0
    if 'account_status' in data and data['account_status'] in ['pending', 'approved', 'rejected', 'suspended']:
         allowed_updates['account_status'] = data['account_status']
    
    # Potentially update other fields like name, company info if provided
    if 'first_name' in data: allowed_updates['first_name'] = data['first_name']
    if 'last_name' in data: allowed_updates['last_name'] = data['last_name']
    if 'company_name' in data: allowed_updates['company_name'] = data['company_name']
    # etc. for other fields an admin might edit

    if not allowed_updates:
        return jsonify({"message": "No valid fields provided for update"}), 400

    set_clause = ", ".join([f"{key} = ?" for key in allowed_updates.keys()])
    values = list(allowed_updates.values())
    values.append(user_id)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", tuple(values))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "User not found or no changes made"}), 404

        conn.close()
        audit_logger.log_event('user_updated_by_admin', admin_user_id=None, # Get admin_id from JWT if passed
                               details={'target_user_id': user_id, 'changes': allowed_updates})
        
        # If account_status changed to 'approved' or 'rejected' for B2B, send email
        if 'account_status' in allowed_updates and allowed_updates['account_status'] in ['approved', 'rejected']:
            cursor = get_db_connection().cursor() # Re-open for read
            cursor.execute("SELECT email, first_name, role FROM users WHERE id = ?", (user_id,))
            user_info = cursor.fetchone()
            get_db_connection().close()

            if user_info and user_info['role'] == 'professional':
                status_translation = {
                    'approved': 'approuvé',
                    'rejected': 'rejeté'
                }
                email_subject = f"Mise à jour du statut de votre compte professionnel - Maison Trüvra"
                email_body = f"Bonjour {user_info['first_name']},\n\nLe statut de votre compte professionnel Maison Trüvra a été mis à jour : {status_translation.get(allowed_updates['account_status'], allowed_updates['account_status'])}."
                if allowed_updates['account_status'] == 'approved':
                    email_body += "\nVous pouvez maintenant vous connecter et accéder à nos tarifs professionnels."
                elif allowed_updates['account_status'] == 'rejected':
                     email_body += "\nPour plus d'informations, veuillez contacter notre support."
                email_body += "\n\nCordialement,\nL'équipe Maison Trüvra"
                send_email_alert(email_subject, email_body, user_info['email'])


        return jsonify({"message": "User updated successfully"}), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error updating user {user_id}: {e}")
        return jsonify({"message": "Failed to update user", "error": str(e)}), 500


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
        current_app.logger.error(f"Database error fetching reviews: {e}")
        return jsonify({"message": "Failed to fetch reviews", "error": str(e)}), 500

@admin_api_bp.route('/reviews/<int:review_id>/approve', methods=['PUT'])
@jwt_required
def approve_review(review_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE reviews SET is_approved = 1 WHERE id = ?", (review_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Review not found"}), 404
        conn.close()
        audit_logger.log_event('review_approved', details={'review_id': review_id})
        return jsonify({"message": "Review approved successfully"}), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error approving review {review_id}: {e}")
        return jsonify({"message": "Failed to approve review", "error": str(e)}), 500

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
        current_app.logger.error(f"Database error deleting review {review_id}: {e}")
        return jsonify({"message": "Failed to delete review", "error": str(e)}), 500

# --- Orders ---
@admin_api_bp.route('/orders', methods=['GET'])
@jwt_required
def get_orders():
    # Add pagination and filtering
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch order details along with user email and items
        cursor.execute("""
            SELECT o.id as order_id, u.email as user_email, o.order_date, o.total_amount, o.status,
                   o.shipping_address_line1, o.shipping_city, o.shipping_postal_code, o.shipping_country,
                   o.billing_address_line1, o.billing_city, o.billing_postal_code, o.billing_country
            FROM orders o
            JOIN users u ON o.user_id = u.id
            ORDER BY o.order_date DESC
        """)
        orders_rows = cursor.fetchall()
        orders = []
        for row in orders_rows:
            order_dict = row_to_dict(cursor, row)
            # Fetch order items for each order
            cursor.execute("""
                SELECT oi.id as item_id, oi.product_id, p.name_fr as product_name, 
                       oi.variant_id, pv.weight_grams as variant_weight, 
                       oi.quantity, oi.price_at_purchase
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                LEFT JOIN product_weight_options pv ON oi.variant_id = pv.id
                WHERE oi.order_id = ?
            """, (order_dict['order_id'],))
            items_rows = cursor.fetchall()
            order_dict['items'] = [row_to_dict(cursor, i_row) for i_row in items_rows]
            orders.append(order_dict)
        conn.close()
        return jsonify(orders), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching orders: {e}")
        return jsonify({"message": "Failed to fetch orders", "error": str(e)}), 500

@admin_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')
    if not new_status or new_status not in ['pending_payment', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']:
        return jsonify({"message": "Invalid or missing status"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, order_id))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Order not found"}), 404
        
        # Send email notification to user about status change
        cursor.execute("SELECT u.email, u.first_name FROM orders o JOIN users u ON o.user_id = u.id WHERE o.id = ?", (order_id,))
        user_info = cursor.fetchone()
        conn.close()

        if user_info:
            email_subject = f"Mise à jour de votre commande #{order_id} - Maison Trüvra"
            email_body = f"Bonjour {user_info['first_name']},\n\nLe statut de votre commande #{order_id} a été mis à jour : {new_status}.\n\nVous pouvez consulter les détails de votre commande sur votre compte.\n\nCordialement,\nL'équipe Maison Trüvra"
            send_email_alert(email_subject, email_body, user_info['email'])

        audit_logger.log_event('order_status_updated', details={'order_id': order_id, 'new_status': new_status})
        return jsonify({"message": f"Order {order_id} status updated to {new_status}"}), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error updating order status for {order_id}: {e}")
        return jsonify({"message": "Failed to update order status", "error": str(e)}), 500

# --- Professional Invoices ---
@admin_api_bp.route('/invoices/professional', methods=['POST'])
@jwt_required
def generate_professional_invoice_admin():
    data = request.form # Assuming form data for file and other fields
    invoice_details_json = data.get('invoice_details')
    if not invoice_details_json:
        return jsonify({"message": "Missing 'invoice_details' in form data"}), 400
    
    try:
        invoice_data = json.loads(invoice_details_json)
    except json.JSONDecodeError:
        return jsonify({"message": "Invalid JSON in 'invoice_details'"}), 400

    # invoice_data should contain: professional_user_id, items, invoice_id_display, issue_date, due_date, etc.
    # And potentially company_info_override (template_ fields from JS)
    company_info_override = {k.replace('template_', ''): v for k, v in data.items() if k.startswith('template_')}

    if not all(k in invoice_data for k in ['professional_user_id', 'items', 'invoice_id_display', 'issue_date', 'due_date']):
        return jsonify({"message": "Missing required fields in invoice_details"}), 400

    try:
        pdf_path, invoice_number_db = invoice_service.create_and_save_professional_invoice(
            invoice_data, 
            company_info_override=company_info_override if company_info_override else None
        )
        
        # pdf_path is the absolute path on server. We need a URL to serve it.
        # Assuming INVOICE_PDF_PATH is 'assets_generated/invoices'
        # and it's served under '/assets_generated/invoices/filename.pdf'
        pdf_filename = os.path.basename(pdf_path)
        pdf_url = f"/{current_app.config['INVOICE_PDF_PATH'].split('assets_generated/')[-1]}/{pdf_filename}"
        
        audit_logger.log_event('professional_invoice_generated_admin', details={'invoice_number': invoice_number_db, 'professional_user_id': invoice_data['professional_user_id']})
        return jsonify({"message": "Professional invoice generated successfully", "pdf_url": pdf_url, "invoice_number": invoice_number_db}), 201
    except ValueError as ve: # For data validation errors from service
        current_app.logger.warning(f"Validation error generating prof invoice: {ve}")
        return jsonify({"message": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Error generating professional invoice: {e}")
        return jsonify({"message": "Failed to generate professional invoice", "error": str(e)}), 500

@admin_api_bp.route('/invoices', methods=['GET'])
@jwt_required
def get_all_invoices():
    # This should fetch both B2C (from orders) and B2B (from professional_invoices)
    # For now, focusing on professional invoices table
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch professional invoices
        cursor.execute("""
            SELECT pi.id, pi.invoice_number, pi.professional_user_id, u.company_name, u.email as user_email,
                   pi.issue_date, pi.due_date, pi.total_amount, pi.status, pi.pdf_path
            FROM professional_invoices pi
            JOIN users u ON pi.professional_user_id = u.id
            ORDER BY pi.issue_date DESC
        """)
        prof_invoices_rows = cursor.fetchall()
        prof_invoices = []
        for row in prof_invoices_rows:
            inv_dict = row_to_dict(cursor, row)
            if inv_dict['pdf_path']:
                pdf_filename = os.path.basename(inv_dict['pdf_path'])
                # Ensure this path construction is correct based on how assets are served
                inv_dict['pdf_url'] = f"/{current_app.config['INVOICE_PDF_PATH'].split('assets_generated/')[-1]}/{pdf_filename}"
            else:
                inv_dict['pdf_url'] = None
            prof_invoices.append(inv_dict)
        
        # TODO: Fetch B2C invoices (which are essentially order confirmations, maybe generate on demand or store)
        
        conn.close()
        return jsonify({"professional_invoices": prof_invoices, "b2c_invoices": []}), 200 # Add B2C later
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching invoices: {e}")
        return jsonify({"message": "Failed to fetch invoices", "error": str(e)}), 500

# Serve generated assets (QR codes, labels, passports, invoices)
# This requires careful path setup.
# Example: /assets_generated/product_labels/label_1.png
@admin_api_bp.route('/assets/<path:folder>/<path:filename>')
# No JWT required for assets if they are meant to be publicly accessible via URL (e.g. in emails, QR codes)
# If they need protection, add @jwt_required or a more specific one
def serve_generated_asset(folder, filename):
    # Ensure folder is one of the allowed asset types to prevent directory traversal
    allowed_folders = ['product_labels', 'product_passports', 'product_qr_codes', 'invoices', 'product_images', 'category_images']
    if folder not in allowed_folders:
        return jsonify({"message": "Invalid asset folder"}), 403
    
    directory = os.path.join(current_app.config['ASSET_STORAGE_PATH'], folder)
    current_app.logger.debug(f"Attempting to serve asset from: {directory} / {filename}")
    if not os.path.exists(os.path.join(directory, filename)):
        current_app.logger.error(f"Asset not found: {os.path.join(directory, filename)}")
        return jsonify({"message": "Asset not found"}), 404
    return send_from_directory(directory, filename)

