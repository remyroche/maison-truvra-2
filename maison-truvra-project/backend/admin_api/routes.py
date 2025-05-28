import os
import json
import uuid
import sqlite3 # Added for explicit error handling
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..database import get_db_connection, query_db, record_stock_movement
from ..services.asset_service import generate_qr_code_for_item, generate_item_passport, generate_product_label
from ..utils import (
    allowed_file, get_file_extension, generate_slug, 
    format_datetime_for_display, parse_datetime_from_iso
)
# Assuming AuditLogService is initialized in create_app and available via current_app
# from ..audit_log_service import AuditLogService # Not needed if accessed via current_app

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

def admin_required(fn):
    """Decorator to ensure the user is an admin."""
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify(message="Administration rights required"), 403
        # Add a check for user being active if necessary
        # current_user_id = get_jwt_identity()
        # user = query_db("SELECT is_active FROM users WHERE id = ? AND role = 'admin'", [current_user_id], db_conn=get_db_connection(), one=True)
        # if not user or not user['is_active']:
        #     return jsonify(message="Admin account is not active."), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__ # Preserve original function name for Flask
    return wrapper

# --- Dashboard ---
@admin_api_bp.route('/dashboard/stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    db = get_db_connection()
    try:
        total_users = query_db("SELECT COUNT(*) FROM users", db_conn=db, one=True)[0]
        total_products = query_db("SELECT COUNT(*) FROM products", db_conn=db, one=True)[0]
        total_orders = query_db("SELECT COUNT(*) FROM orders", db_conn=db, one=True)[0]
        # Add more stats as needed (e.g., total sales, pending reviews)
        return jsonify({
            "total_users": total_users,
            "total_products": total_products,
            "total_orders": total_orders,
            # "total_sales": 0, # Placeholder
            # "pending_reviews": 0 # Placeholder
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard stats: {e}")
        return jsonify(message="Failed to fetch dashboard statistics"), 500

# --- Category Management ---
@admin_api_bp.route('/categories', methods=['POST'])
@admin_required
def create_category():
    data = request.form.to_dict()
    name = data.get('name')
    description = data.get('description', '')
    parent_id = data.get('parent_id')
    image_file = request.files.get('image_url')
    
    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service


    if not name:
        audit_logger.log_action(user_id=current_user_id, action='create_category_fail', details="Name is required.", status='failure')
        return jsonify(message="Name is required"), 400

    slug = generate_slug(name)
    db = get_db_connection()
    image_filename = None

    try:
        # Check if category name or slug already exists
        existing_category_name = query_db("SELECT id FROM categories WHERE name = ?", [name], db_conn=db, one=True)
        if existing_category_name:
            audit_logger.log_action(user_id=current_user_id, action='create_category_fail', details=f"Category name '{name}' already exists.", status='failure')
            return jsonify(message=f"Category name '{name}' already exists"), 409
        
        existing_category_slug = query_db("SELECT id FROM categories WHERE slug = ?", [slug], db_conn=db, one=True)
        if existing_category_slug:
            # This case should be rare if slug generation is robust and names are unique
            audit_logger.log_action(user_id=current_user_id, action='create_category_fail', details=f"Category slug '{slug}' already exists.", status='failure')
            return jsonify(message=f"Category slug '{slug}' already exists. Try a different name."), 409


        if image_file and allowed_file(image_file.filename, current_app.config['ALLOWED_EXTENSIONS']):
            filename = secure_filename(f"category_{slug}_{uuid.uuid4().hex[:8]}.{get_file_extension(image_file.filename)}")
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            image_file.save(image_path)
            image_filename = f"categories/{filename}" # Store relative path for serving

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO categories (name, description, parent_id, slug, image_url) VALUES (?, ?, ?, ?, ?)",
            (name, description, parent_id if parent_id else None, slug, image_filename)
        )
        category_id = cursor.lastrowid
        db.commit()
        
        audit_logger.log_action(
            user_id=current_user_id, 
            action='create_category', 
            target_type='category', 
            target_id=category_id,
            details=f"Category '{name}' created.",
            status='success'
        )
        return jsonify(message="Category created successfully", category_id=category_id, slug=slug, image_url=image_filename), 201
    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"Category creation integrity error: {e}")
        # This might happen if slug is not unique despite checks (race condition, though unlikely with SQLite's typical concurrency)
        audit_logger.log_action(user_id=current_user_id, action='create_category_fail', details=f"Database integrity error: {e}", status='failure')
        return jsonify(message="Category name or slug likely already exists."), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error creating category: {e}")
        audit_logger.log_action(user_id=current_user_id, action='create_category_fail', details=str(e), status='failure')
        return jsonify(message="Failed to create category"), 500


@admin_api_bp.route('/categories', methods=['GET'])
@admin_required 
def get_categories():
    db = get_db_connection()
    try:
        # Basic query, can be expanded with hierarchy building
        categories_data = query_db("SELECT id, name, description, parent_id, slug, image_url, created_at, updated_at FROM categories ORDER BY name", db_conn=db)
        categories = [dict(row) for row in categories_data] if categories_data else []
        
        # Convert datetimes to ISO format string for JSON serialization
        for category in categories:
            category['created_at'] = format_datetime_for_display(category['created_at'])
            category['updated_at'] = format_datetime_for_display(category['updated_at'])
            if category.get('image_url'):
                 # Construct full URL based on how assets are served.
                 # If serve_asset is protected, this URL is also protected.
                 category['image_full_url'] = f"{request.host_url.rstrip('/')}{admin_api_bp.url_prefix}/assets/{category['image_url']}"


        return jsonify(categories), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching categories: {e}")
        return jsonify(message="Failed to fetch categories"), 500

@admin_api_bp.route('/categories/<int:category_id>', methods=['GET'])
@admin_required
def get_category(category_id):
    db = get_db_connection()
    try:
        category_data = query_db("SELECT * FROM categories WHERE id = ?", [category_id], db_conn=db, one=True)
        if category_data:
            category = dict(category_data)
            category['created_at'] = format_datetime_for_display(category['created_at'])
            category['updated_at'] = format_datetime_for_display(category['updated_at'])
            if category.get('image_url'):
                 category['image_full_url'] = f"{request.host_url.rstrip('/')}{admin_api_bp.url_prefix}/assets/{category['image_url']}"
            return jsonify(category), 200
        return jsonify(message="Category not found"), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching category {category_id}: {e}")
        return jsonify(message="Failed to fetch category details"), 500


@admin_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@admin_required
def update_category(category_id):
    data = request.form.to_dict()
    name = data.get('name')
    description = data.get('description')
    parent_id = data.get('parent_id') # Can be empty string if unsetting parent
    image_file = request.files.get('image_url')
    remove_image = data.get('remove_image') == 'true'

    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service

    if not name:
        audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details="Name is required.", status='failure')
        return jsonify(message="Name is required for update"), 400

    db = get_db_connection()
    try:
        current_category = query_db("SELECT * FROM categories WHERE id = ?", [category_id], db_conn=db, one=True)
        if not current_category:
            audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details="Category not found.", status='failure')
            return jsonify(message="Category not found"), 404

        new_slug = generate_slug(name)
        image_filename_to_update = current_category['image_url'] # Keep old image by default

        # Check for name/slug conflicts (excluding current category)
        existing_category_name = query_db("SELECT id FROM categories WHERE name = ? AND id != ?", [name, category_id], db_conn=db, one=True)
        if existing_category_name:
            audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details=f"Category name '{name}' already exists.", status='failure')
            return jsonify(message=f"Another category with the name '{name}' already exists"), 409
        
        existing_category_slug = query_db("SELECT id FROM categories WHERE slug = ? AND id != ?", [new_slug, category_id], db_conn=db, one=True)
        if existing_category_slug:
            audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details=f"Category slug '{new_slug}' already exists.", status='failure')
            return jsonify(message=f"Another category with the generated slug '{new_slug}' already exists. Try a different name."), 409


        if remove_image and current_category['image_url']:
            old_image_path_segment = current_category['image_url']
            # Construct full path carefully based on how UPLOAD_FOLDER and image_filename_to_update are structured
            # Assuming image_filename_to_update is 'categories/filename.ext'
            full_old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_image_path_segment)
            if os.path.exists(full_old_image_path):
                try:
                    os.remove(full_old_image_path)
                    current_app.logger.info(f"Removed old category image: {full_old_image_path}")
                except OSError as e:
                    current_app.logger.error(f"Error removing old category image {full_old_image_path}: {e}")
            image_filename_to_update = None
        elif image_file and allowed_file(image_file.filename, current_app.config['ALLOWED_EXTENSIONS']):
            # Remove old image if a new one is uploaded and an old one exists
            if current_category['image_url']:
                old_image_path_segment = current_category['image_url']
                full_old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_image_path_segment)
                if os.path.exists(full_old_image_path):
                    try:
                        os.remove(full_old_image_path)
                    except OSError as e:
                         current_app.logger.error(f"Error removing old category image before new upload {full_old_image_path}: {e}")
            
            filename = secure_filename(f"category_{new_slug}_{uuid.uuid4().hex[:8]}.{get_file_extension(image_file.filename)}")
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            image_file.save(image_path)
            image_filename_to_update = f"categories/{filename}"

        # Handle parent_id: if empty string, set to NULL, otherwise convert to int
        parent_id_to_update = None
        if parent_id and parent_id.strip():
            try:
                parent_id_to_update = int(parent_id)
                if parent_id_to_update == category_id: # Prevent self-parenting
                    audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details="Category cannot be its own parent.", status='failure')
                    return jsonify(message="Category cannot be its own parent."), 400
            except ValueError:
                audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details="Invalid parent ID format.", status='failure')
                return jsonify(message="Invalid parent ID format."), 400
        
        description_to_update = description if description is not None else current_category['description']

        cursor = db.cursor()
        cursor.execute(
            """UPDATE categories SET 
               name = ?, description = ?, parent_id = ?, slug = ?, image_url = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (name, description_to_update, parent_id_to_update, new_slug, image_filename_to_update, category_id)
        )
        db.commit()
        
        audit_logger.log_action(
            user_id=current_user_id, 
            action='update_category', 
            target_type='category', 
            target_id=category_id,
            details=f"Category '{name}' updated.",
            status='success'
        )
        return jsonify(message="Category updated successfully", slug=new_slug, image_url=image_filename_to_update), 200
    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"Category update integrity error for ID {category_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details=f"Database integrity error: {e}", status='failure')
        return jsonify(message="Category name or slug likely conflicts with an existing one."), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating category {category_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='update_category_fail', target_type='category', target_id=category_id, details=str(e), status='failure')
        return jsonify(message="Failed to update category"), 500

@admin_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()

    try:
        # Check if category exists
        category_to_delete = query_db("SELECT image_url, name FROM categories WHERE id = ?", [category_id], db_conn=db, one=True)
        if not category_to_delete:
            audit_logger.log_action(user_id=current_user_id, action='delete_category_fail', target_type='category', target_id=category_id, details="Category not found.", status='failure')
            return jsonify(message="Category not found"), 404

        # Check if category is used by products
        products_in_category = query_db("SELECT COUNT(*) FROM products WHERE category_id = ?", [category_id], db_conn=db, one=True)[0]
        if products_in_category > 0:
            audit_logger.log_action(user_id=current_user_id, action='delete_category_fail', target_type='category', target_id=category_id, details=f"Category '{category_to_delete['name']}' is in use by {products_in_category} products.", status='failure')
            return jsonify(message=f"Category '{category_to_delete['name']}' is in use by products and cannot be deleted. Reassign products first."), 409
        
        # Check if category is a parent to other subcategories
        subcategories = query_db("SELECT COUNT(*) FROM categories WHERE parent_id = ?", [category_id], db_conn=db, one=True)[0]
        if subcategories > 0:
            # Option 1: Prevent deletion
            # audit_logger.log_action(user_id=current_user_id, action='delete_category_fail', target_type='category', target_id=category_id, details=f"Category '{category_to_delete['name']}' has subcategories.", status='failure')
            # return jsonify(message=f"Category '{category_to_delete['name']}' has subcategories. Delete or reassign them first."), 409
            # Option 2: Set parent_id of subcategories to NULL (as per schema ON DELETE SET NULL for parent_id)
            # This will happen automatically due to schema if we just delete.
            pass


        # Delete image if exists
        if category_to_delete['image_url']:
            image_path_segment = category_to_delete['image_url']
            full_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_path_segment)
            if os.path.exists(full_image_path):
                try:
                    os.remove(full_image_path)
                    current_app.logger.info(f"Deleted category image: {full_image_path}")
                except OSError as e:
                    current_app.logger.error(f"Error deleting category image {full_image_path}: {e}")
        
        cursor = db.cursor()
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        db.commit()

        if cursor.rowcount > 0:
            audit_logger.log_action(
                user_id=current_user_id, 
                action='delete_category', 
                target_type='category', 
                target_id=category_id,
                details=f"Category '{category_to_delete['name']}' (ID: {category_id}) deleted.",
                status='success'
            )
            return jsonify(message=f"Category '{category_to_delete['name']}' deleted successfully"), 200
        else:
            # Should have been caught by the initial check, but as a safeguard
            audit_logger.log_action(user_id=current_user_id, action='delete_category_fail', target_type='category', target_id=category_id, details="Category not found during delete operation.", status='failure')
            return jsonify(message="Category not found during delete operation"), 404

    except sqlite3.IntegrityError as e: # Should be caught by product/subcategory checks mostly
        db.rollback()
        current_app.logger.error(f"Integrity error deleting category {category_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='delete_category_fail', target_type='category', target_id=category_id, details=f"Database integrity error: {e}. Category might still be in use.", status='failure')
        return jsonify(message="Failed to delete category due to integrity constraints. It might be in use."), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error deleting category {category_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='delete_category_fail', target_type='category', target_id=category_id, details=str(e), status='failure')
        return jsonify(message="Failed to delete category"), 500


# --- Product Management ---
@admin_api_bp.route('/products', methods=['POST'])
@admin_required
def create_product():
    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()

    try:
        data = request.form.to_dict()
        main_image_file = request.files.get('main_image_url')
        # For multiple additional images: request.files.getlist('additional_images[]')

        required_fields = ['name', 'sku_prefix', 'type']
        for field in required_fields:
            if not data.get(field):
                audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details=f"Missing required field: {field}", status='failure')
                return jsonify(message=f"Missing required field: {field}"), 400

        name = data['name']
        sku_prefix = data['sku_prefix']
        product_type = data['type']
        description = data.get('description', '')
        category_id = data.get('category_id')
        brand = data.get('brand', '')
        base_price = data.get('base_price')
        currency = data.get('currency', 'EUR')
        aggregate_stock_quantity = data.get('aggregate_stock_quantity', 0)
        aggregate_stock_weight_grams = data.get('aggregate_stock_weight_grams')
        unit_of_measure = data.get('unit_of_measure')
        is_active = data.get('is_active', 'true').lower() == 'true'
        is_featured = data.get('is_featured', 'false').lower() == 'true'
        meta_title = data.get('meta_title', '')
        meta_description = data.get('meta_description', '')
        
        slug = generate_slug(name)

        # Validate SKU prefix uniqueness
        existing_sku = query_db("SELECT id FROM products WHERE sku_prefix = ?", [sku_prefix], db_conn=db, one=True)
        if existing_sku:
            audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details=f"SKU prefix '{sku_prefix}' already exists.", status='failure')
            return jsonify(message=f"SKU prefix '{sku_prefix}' already exists."), 409

        # Validate slug uniqueness (though name uniqueness should mostly cover this)
        existing_slug = query_db("SELECT id FROM products WHERE slug = ?", [slug], db_conn=db, one=True)
        if existing_slug:
            audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details=f"Product name/slug '{slug}' already exists.", status='failure')
            return jsonify(message=f"Product name (slug: '{slug}') already exists. Choose a different name."), 409


        main_image_filename = None
        if main_image_file and allowed_file(main_image_file.filename, current_app.config['ALLOWED_EXTENSIONS']):
            filename = secure_filename(f"product_{slug}_{uuid.uuid4().hex[:8]}.{get_file_extension(main_image_file.filename)}")
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            main_image_file.save(image_path)
            main_image_filename = f"products/{filename}" # Relative path

        # Type conversions and validations
        try:
            base_price = float(base_price) if base_price is not None else None
            category_id = int(category_id) if category_id else None
            aggregate_stock_quantity = int(aggregate_stock_quantity) if aggregate_stock_quantity is not None else 0
            aggregate_stock_weight_grams = float(aggregate_stock_weight_grams) if aggregate_stock_weight_grams else None
        except ValueError as ve:
            audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details=f"Invalid data type for price, category ID, or stock: {ve}", status='failure')
            return jsonify(message=f"Invalid data type for price, category ID, or stock: {ve}"), 400

        if product_type == 'simple' and base_price is None:
            audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details="Base price is required for simple products.", status='failure')
            return jsonify(message="Base price is required for simple products."), 400
        
        if product_type == 'variable_weight' and not unit_of_measure:
            audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details="Unit of measure is required for variable weight products.", status='failure')
            return jsonify(message="Unit of measure is required for variable weight products."), 400


        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO products (name, description, category_id, brand, sku_prefix, type, 
                                   base_price, currency, main_image_url, aggregate_stock_quantity, 
                                   aggregate_stock_weight_grams, unit_of_measure, is_active, is_featured, 
                                   meta_title, meta_description, slug)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, description, category_id, brand, sku_prefix, product_type, 
             base_price, currency, main_image_filename, aggregate_stock_quantity, 
             aggregate_stock_weight_grams, unit_of_measure, is_active, is_featured, 
             meta_title, meta_description, slug)
        )
        product_id = cursor.lastrowid

        # Handle product weight options if provided (for 'variable_weight' products)
        if product_type == 'variable_weight' and 'weight_options' in data:
            try:
                weight_options_str = data.get('weight_options', '[]') # Expecting a JSON string from form data
                weight_options = json.loads(weight_options_str)
                for option in weight_options:
                    if not all(k in option for k in ('weight_grams', 'price', 'sku_suffix')):
                        raise ValueError("Missing fields in weight option.")
                    cursor.execute(
                        """INSERT INTO product_weight_options 
                           (product_id, weight_grams, price, sku_suffix, aggregate_stock_quantity, is_active)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (product_id, float(option['weight_grams']), float(option['price']), option['sku_suffix'],
                         int(option.get('aggregate_stock_quantity', 0)), option.get('is_active', True))
                    )
            except (json.JSONDecodeError, ValueError) as e:
                db.rollback() # Rollback product creation if options are bad
                current_app.logger.error(f"Error processing product weight options: {e}")
                audit_logger.log_action(user_id=current_user_id, action='create_product_fail', target_type='product', target_id=product_id, details=f"Invalid weight options format: {e}", status='failure')
                return jsonify(message=f"Invalid format for weight options: {e}"), 400
        
        db.commit()
        audit_logger.log_action(
            user_id=current_user_id, 
            action='create_product', 
            target_type='product', 
            target_id=product_id,
            details=f"Product '{name}' (SKU: {sku_prefix}) created.",
            status='success'
        )
        return jsonify(message="Product created successfully", product_id=product_id, slug=slug), 201

    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"Product creation integrity error: {e}")
        audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details=f"Database integrity error (e.g. SKU or slug conflict): {e}", status='failure')
        return jsonify(message="Product SKU prefix or name (slug) likely already exists."), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error creating product: {e}")
        audit_logger.log_action(user_id=current_user_id, action='create_product_fail', details=str(e), status='failure')
        return jsonify(message="Failed to create product"), 500

@admin_api_bp.route('/products', methods=['GET'])
@admin_required 
def get_products():
    db = get_db_connection()
    try:
        # Add query params for filtering, sorting, pagination
        query = """
            SELECT p.*, c.name as category_name 
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.name
        """
        products_data = query_db(query, db_conn=db)
        products = [dict(row) for row in products_data] if products_data else []

        for product in products:
            product['created_at'] = format_datetime_for_display(product['created_at'])
            product['updated_at'] = format_datetime_for_display(product['updated_at'])
            if product.get('main_image_url'):
                product['main_image_full_url'] = f"{request.host_url.rstrip('/')}{admin_api_bp.url_prefix}/assets/{product['main_image_url']}"
            
            # Fetch weight options if variable_weight
            if product['type'] == 'variable_weight':
                options_data = query_db("SELECT * FROM product_weight_options WHERE product_id = ? AND is_active = TRUE ORDER BY weight_grams", [product['id']], db_conn=db)
                product['weight_options'] = [dict(opt_row) for opt_row in options_data] if options_data else []
            
            # Fetch additional images
            images_data = query_db("SELECT id, image_url, alt_text, is_primary FROM product_images WHERE product_id = ? ORDER BY is_primary DESC, id ASC", [product['id']], db_conn=db)
            product['additional_images'] = []
            if images_data:
                for img_row in images_data:
                    img_dict = dict(img_row)
                    img_dict['image_full_url'] = f"{request.host_url.rstrip('/')}{admin_api_bp.url_prefix}/assets/{img_dict['image_url']}"
                    product['additional_images'].append(img_dict)


        return jsonify(products), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {e}")
        return jsonify(message="Failed to fetch products"), 500

@admin_api_bp.route('/products/<int:product_id>', methods=['GET'])
@admin_required
def get_product(product_id):
    db = get_db_connection()
    try:
        product_data = query_db("SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = ?", [product_id], db_conn=db, one=True)
        if product_data:
            product = dict(product_data)
            product['created_at'] = format_datetime_for_display(product['created_at'])
            product['updated_at'] = format_datetime_for_display(product['updated_at'])
            if product.get('main_image_url'):
                product['main_image_full_url'] = f"{request.host_url.rstrip('/')}{admin_api_bp.url_prefix}/assets/{product['main_image_url']}"

            if product['type'] == 'variable_weight':
                options_data = query_db("SELECT * FROM product_weight_options WHERE product_id = ? ORDER BY weight_grams", [product_id], db_conn=db)
                product['weight_options'] = [dict(opt_row) for opt_row in options_data] if options_data else []
            
            images_data = query_db("SELECT id, image_url, alt_text, is_primary FROM product_images WHERE product_id = ? ORDER BY is_primary DESC, id ASC", [product_id], db_conn=db)
            product['additional_images'] = []
            if images_data:
                for img_row in images_data:
                    img_dict = dict(img_row)
                    img_dict['image_full_url'] = f"{request.host_url.rstrip('/')}{admin_api_bp.url_prefix}/assets/{img_dict['image_url']}"
                    product['additional_images'].append(img_dict)

            return jsonify(product), 200
        return jsonify(message="Product not found"), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching product {product_id}: {e}")
        return jsonify(message="Failed to fetch product details"), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()

    try:
        current_product = query_db("SELECT * FROM products WHERE id = ?", [product_id], db_conn=db, one=True)
        if not current_product:
            audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details="Product not found.", status='failure')
            return jsonify(message="Product not found"), 404

        data = request.form.to_dict()
        main_image_file = request.files.get('main_image_url')
        remove_main_image = data.get('remove_main_image') == 'true'

        name = data.get('name', current_product['name'])
        new_slug = generate_slug(name) if data.get('name') else current_product['slug']
        
        # Check for SKU prefix conflict (if changed)
        new_sku_prefix = data.get('sku_prefix')
        if new_sku_prefix and new_sku_prefix != current_product['sku_prefix']:
            existing_sku = query_db("SELECT id FROM products WHERE sku_prefix = ? AND id != ?", [new_sku_prefix, product_id], db_conn=db, one=True)
            if existing_sku:
                audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details=f"SKU prefix '{new_sku_prefix}' already exists.", status='failure')
                return jsonify(message=f"SKU prefix '{new_sku_prefix}' already exists."), 409
        else:
            new_sku_prefix = current_product['sku_prefix'] # Keep old if not provided or same

        # Check for slug conflict (if name changed)
        if data.get('name') and new_slug != current_product['slug']:
            existing_slug = query_db("SELECT id FROM products WHERE slug = ? AND id != ?", [new_slug, product_id], db_conn=db, one=True)
            if existing_slug:
                audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details=f"Product name/slug '{new_slug}' already exists.", status='failure')
                return jsonify(message=f"Product name (slug: '{new_slug}') already exists."), 409
        
        main_image_filename_to_update = current_product['main_image_url']
        if remove_main_image and current_product['main_image_url']:
            full_old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_product['main_image_url'])
            if os.path.exists(full_old_image_path):
                try: os.remove(full_old_image_path)
                except OSError as e: current_app.logger.error(f"Error removing old product image {full_old_image_path}: {e}")
            main_image_filename_to_update = None
        elif main_image_file and allowed_file(main_image_file.filename, current_app.config['ALLOWED_EXTENSIONS']):
            if current_product['main_image_url']: # Remove old if new one is uploaded
                full_old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_product['main_image_url'])
                if os.path.exists(full_old_image_path):
                    try: os.remove(full_old_image_path)
                    except OSError as e: current_app.logger.error(f"Error removing old product image for update {full_old_image_path}: {e}")

            filename = secure_filename(f"product_{new_slug}_{uuid.uuid4().hex[:8]}.{get_file_extension(main_image_file.filename)}")
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, filename)
            main_image_file.save(image_path)
            main_image_filename_to_update = f"products/{filename}"

        # Prepare fields for update
        update_fields = {
            'name': name,
            'description': data.get('description', current_product['description']),
            'category_id': int(data['category_id']) if data.get('category_id') else current_product['category_id'],
            'brand': data.get('brand', current_product['brand']),
            'sku_prefix': new_sku_prefix,
            'type': data.get('type', current_product['type']),
            'base_price': float(data['base_price']) if data.get('base_price') is not None else current_product['base_price'],
            'currency': data.get('currency', current_product['currency']),
            'main_image_url': main_image_filename_to_update,
            'aggregate_stock_quantity': int(data['aggregate_stock_quantity']) if data.get('aggregate_stock_quantity') is not None else current_product['aggregate_stock_quantity'],
            'aggregate_stock_weight_grams': float(data['aggregate_stock_weight_grams']) if data.get('aggregate_stock_weight_grams') is not None else current_product['aggregate_stock_weight_grams'],
            'unit_of_measure': data.get('unit_of_measure', current_product['unit_of_measure']),
            'is_active': data.get('is_active', str(current_product['is_active'])).lower() == 'true',
            'is_featured': data.get('is_featured', str(current_product['is_featured'])).lower() == 'true',
            'meta_title': data.get('meta_title', current_product['meta_title']),
            'meta_description': data.get('meta_description', current_product['meta_description']),
            'slug': new_slug
        }
        
        # Validation for updated type
        if update_fields['type'] == 'simple' and update_fields['base_price'] is None:
            audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details="Base price is required for simple products.", status='failure')
            return jsonify(message="Base price is required for simple products."), 400
        if update_fields['type'] == 'variable_weight' and not update_fields['unit_of_measure']:
            audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details="Unit of measure is required for variable weight products.", status='failure')
            return jsonify(message="Unit of measure is required for variable weight products."), 400

        # Construct SET clause and arguments for SQL query
        set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
        sql_args = list(update_fields.values())
        sql_args.append(product_id)

        cursor = db.cursor()
        cursor.execute(f"UPDATE products SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", sql_args)

        # Handle product weight options (full replace for simplicity, or more granular add/update/delete)
        if update_fields['type'] == 'variable_weight' and 'weight_options' in data:
            try:
                weight_options_str = data.get('weight_options', '[]')
                weight_options = json.loads(weight_options_str)
                
                # First, delete existing options for this product
                cursor.execute("DELETE FROM product_weight_options WHERE product_id = ?", (product_id,))
                
                # Then, insert the new/updated options
                for option in weight_options:
                    if not all(k in option for k in ('weight_grams', 'price', 'sku_suffix')):
                        raise ValueError("Missing fields in weight option.")
                    cursor.execute(
                        """INSERT INTO product_weight_options 
                           (product_id, weight_grams, price, sku_suffix, aggregate_stock_quantity, is_active)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (product_id, float(option['weight_grams']), float(option['price']), option['sku_suffix'],
                         int(option.get('aggregate_stock_quantity', 0)), option.get('is_active', True))
                    )
            except (json.JSONDecodeError, ValueError) as e:
                db.rollback()
                current_app.logger.error(f"Error processing product weight options for update: {e}")
                audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details=f"Invalid weight options format: {e}", status='failure')
                return jsonify(message=f"Invalid format for weight options: {e}"), 400
        elif update_fields['type'] == 'simple': # If changed to simple, remove any existing weight options
            cursor.execute("DELETE FROM product_weight_options WHERE product_id = ?", (product_id,))


        db.commit()
        audit_logger.log_action(
            user_id=current_user_id, 
            action='update_product', 
            target_type='product', 
            target_id=product_id,
            details=f"Product '{update_fields['name']}' (SKU: {update_fields['sku_prefix']}) updated.",
            status='success'
        )
        return jsonify(message="Product updated successfully", product=update_fields), 200

    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"Product update integrity error for ID {product_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details=f"Database integrity error (e.g. SKU or slug conflict): {e}", status='failure')
        return jsonify(message="Product SKU prefix or name (slug) likely conflicts with an existing one."), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating product {product_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='update_product_fail', target_type='product', target_id=product_id, details=str(e), status='failure')
        return jsonify(message="Failed to update product"), 500

@admin_api_bp.route('/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()

    try:
        product_to_delete = query_db("SELECT name, main_image_url, sku_prefix FROM products WHERE id = ?", [product_id], db_conn=db, one=True)
        if not product_to_delete:
            audit_logger.log_action(user_id=current_user_id, action='delete_product_fail', target_type='product', target_id=product_id, details="Product not found.", status='failure')
            return jsonify(message="Product not found"), 404

        # Check for active serialized inventory items (status != 'sold', 'damaged', 'returned', 'recalled')
        active_serialized_items = query_db(
            "SELECT COUNT(*) FROM serialized_inventory_items WHERE product_id = ? AND status NOT IN (?, ?, ?, ?)",
            [product_id, 'sold', 'damaged', 'returned', 'recalled'], 
            db_conn=db, one=True
        )[0]
        if active_serialized_items > 0:
            audit_logger.log_action(user_id=current_user_id, action='delete_product_fail', target_type='product', target_id=product_id, details=f"Product has {active_serialized_items} active serialized items.", status='failure')
            return jsonify(message=f"Product '{product_to_delete['name']}' has active serialized inventory items and cannot be deleted."), 409

        # Check if product is in any order items (even if serialized item is sold, the order history refers to product)
        # ON DELETE RESTRICT on order_items.product_id will prevent this.
        # We might want to allow "soft delete" (is_active=False) instead of hard delete for products in orders.
        # For now, let's assume the RESTRICT constraint handles this. If it fails, IntegrityError will be caught.

        # Delete main image
        if product_to_delete['main_image_url']:
            full_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], product_to_delete['main_image_url'])
            if os.path.exists(full_image_path):
                try: os.remove(full_image_path)
                except OSError as e: current_app.logger.error(f"Error deleting product image {full_image_path}: {e}")
        
        # Delete additional images
        additional_images = query_db("SELECT image_url FROM product_images WHERE product_id = ?", [product_id], db_conn=db)
        if additional_images:
            for img in additional_images:
                full_add_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], img['image_url'])
                if os.path.exists(full_add_image_path):
                    try: os.remove(full_add_image_path)
                    except OSError as e: current_app.logger.error(f"Error deleting additional product image {full_add_image_path}: {e}")
        
        # Note: Associated assets like QR codes, passports for serialized items are NOT deleted here.
        # They remain for historical record if the serialized items are kept.
        # If serialized items were also deleted, their assets would need separate cleanup.

        cursor = db.cursor()
        # Related data like product_weight_options, product_images will be deleted by CASCADE if set in schema.
        # Serialized items are RESTRICTED. Stock movements CASCADE. Reviews CASCADE.
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()

        if cursor.rowcount > 0:
            audit_logger.log_action(
                user_id=current_user_id, 
                action='delete_product', 
                target_type='product', 
                target_id=product_id,
                details=f"Product '{product_to_delete['name']}' (SKU: {product_to_delete['sku_prefix']}) deleted.",
                status='success'
            )
            return jsonify(message=f"Product '{product_to_delete['name']}' deleted successfully"), 200
        else: # Should be caught by initial check
            audit_logger.log_action(user_id=current_user_id, action='delete_product_fail', target_type='product', target_id=product_id, details="Product not found during delete operation.", status='failure')
            return jsonify(message="Product not found during delete operation"), 404

    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"Integrity error deleting product {product_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='delete_product_fail', target_type='product', target_id=product_id, details=f"Database integrity error: {e}. Product might be in use by orders or non-deleted serialized items.", status='failure')
        return jsonify(message="Failed to delete product due to integrity constraints (e.g., referenced in orders or active serialized items)."), 409
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error deleting product {product_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='delete_product_fail', target_type='product', target_id=product_id, details=str(e), status='failure')
        return jsonify(message="Failed to delete product"), 500

# --- Product Image Management ---
@admin_api_bp.route('/products/<int:product_id>/images', methods=['POST'])
@admin_required
def add_product_image(product_id):
    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()

    if 'image' not in request.files:
        audit_logger.log_action(user_id=current_user_id, action='add_product_image_fail', target_type='product', target_id=product_id, details="No image file provided.", status='failure')
        return jsonify(message="No image file provided"), 400
    
    image_file = request.files['image']
    alt_text = request.form.get('alt_text', '')
    is_primary = request.form.get('is_primary', 'false').lower() == 'true'

    product = query_db("SELECT slug FROM products WHERE id = ?", [product_id], db_conn=db, one=True)
    if not product:
        audit_logger.log_action(user_id=current_user_id, action='add_product_image_fail', target_type='product', target_id=product_id, details="Product not found.", status='failure')
        return jsonify(message="Product not found"), 404

    if not allowed_file(image_file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        audit_logger.log_action(user_id=current_user_id, action='add_product_image_fail', target_type='product', target_id=product_id, details="Invalid image file type.", status='failure')
        return jsonify(message="Invalid image file type"), 400

    try:
        filename = secure_filename(f"product_{product['slug']}_img_{uuid.uuid4().hex[:8]}.{get_file_extension(image_file.filename)}")
        # Store additional images in a subfolder like 'products/additional/'
        image_folder_segment = os.path.join('products', 'additional')
        upload_folder_full = os.path.join(current_app.config['UPLOAD_FOLDER'], image_folder_segment)
        os.makedirs(upload_folder_full, exist_ok=True)
        
        image_path = os.path.join(upload_folder_full, filename)
        image_file.save(image_path)
        image_url_to_store = f"{image_folder_segment}/{filename}" # e.g. products/additional/image.jpg

        cursor = db.cursor()
        if is_primary: # Ensure only one primary image
            cursor.execute("UPDATE product_images SET is_primary = FALSE WHERE product_id = ?", (product_id,))
        
        cursor.execute(
            "INSERT INTO product_images (product_id, image_url, alt_text, is_primary) VALUES (?, ?, ?, ?)",
            (product_id, image_url_to_store, alt_text, is_primary)
        )
        image_id = cursor.lastrowid
        db.commit()

        audit_logger.log_action(
            user_id=current_user_id, 
            action='add_product_image', 
            target_type='product_image', 
            target_id=image_id,
            details=f"Added image to product ID {product_id}.",
            status='success'
        )
        return jsonify(message="Image added successfully", image_id=image_id, image_url=image_url_to_store), 201
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error adding image to product {product_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='add_product_image_fail', target_type='product', target_id=product_id, details=str(e), status='failure')
        return jsonify(message="Failed to add image"), 500

@admin_api_bp.route('/products/<int:product_id>/images/<int:image_id>', methods=['DELETE'])
@admin_required
def delete_product_image(product_id, image_id):
    current_user_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()

    try:
        image_data = query_db("SELECT image_url FROM product_images WHERE id = ? AND product_id = ?", [image_id, product_id], db_conn=db, one=True)
        if not image_data:
            audit_logger.log_action(user_id=current_user_id, action='delete_product_image_fail', target_type='product_image', target_id=image_id, details="Image not found or does not belong to product.", status='failure')
            return jsonify(message="Image not found or does not belong to this product"), 404
        
        # Delete image file from filesystem
        full_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_data['image_url'])
        if os.path.exists(full_image_path):
            try: os.remove(full_image_path)
            except OSError as e: current_app.logger.error(f"Error deleting product image file {full_image_path}: {e}")

        cursor = db.cursor()
        cursor.execute("DELETE FROM product_images WHERE id = ?", (image_id,))
        db.commit()

        audit_logger.log_action(
            user_id=current_user_id, 
            action='delete_product_image', 
            target_type='product_image', 
            target_id=image_id,
            details=f"Deleted image ID {image_id} from product ID {product_id}.",
            status='success'
        )
        return jsonify(message="Image deleted successfully"), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error deleting product image {image_id}: {e}")
        audit_logger.log_action(user_id=current_user_id, action='delete_product_image_fail', target_type='product_image', target_id=image_id, details=str(e), status='failure')
        return jsonify(message="Failed to delete image"), 500

# --- User Management ---
@admin_api_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    db = get_db_connection()
    try:
        # Add query params for filtering by role, status, pagination
        users_data = query_db("SELECT id, email, first_name, last_name, role, is_active, is_verified, company_name, vat_number, siret_number, professional_status, created_at FROM users ORDER BY created_at DESC", db_conn=db)
        users = [dict(row) for row in users_data] if users_data else []
        for user in users:
            user['created_at'] = format_datetime_for_display(user['created_at'])
        return jsonify(users), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {e}")
        return jsonify(message="Failed to fetch users"), 500

@admin_api_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    current_admin_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()
    data = request.json

    if not data:
        audit_logger.log_action(user_id=current_admin_id, action='update_user_fail', target_type='user', target_id=user_id, details="No data provided.", status='failure')
        return jsonify(message="No data provided"), 400

    allowed_fields = ['first_name', 'last_name', 'role', 'is_active', 'is_verified', 
                      'company_name', 'vat_number', 'siret_number', 'professional_status']
    update_payload = {k: data[k] for k in data if k in allowed_fields}

    if not update_payload:
        audit_logger.log_action(user_id=current_admin_id, action='update_user_fail', target_type='user', target_id=user_id, details="No valid fields to update.", status='failure')
        return jsonify(message="No valid fields to update"), 400
    
    # Type conversions for boolean fields
    if 'is_active' in update_payload:
        update_payload['is_active'] = bool(update_payload['is_active'])
    if 'is_verified' in update_payload:
        update_payload['is_verified'] = bool(update_payload['is_verified'])


    set_clause = ", ".join([f"{key} = ?" for key in update_payload.keys()])
    sql_args = list(update_payload.values())
    sql_args.append(user_id)

    try:
        # Fetch current user info for logging and notifications
        user_info_before = query_db("SELECT email, role, professional_status, first_name, last_name FROM users WHERE id = ?", [user_id], db_conn=db, one=True)
        if not user_info_before:
            audit_logger.log_action(user_id=current_admin_id, action='update_user_fail', target_type='user', target_id=user_id, details="User not found.", status='failure')
            return jsonify(message="User not found"), 404

        cursor = db.cursor()
        cursor.execute(f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", sql_args)
        
        if cursor.rowcount == 0:
            # This case should be caught by user_info_before check, but as a safeguard
            audit_logger.log_action(user_id=current_admin_id, action='update_user_fail', target_type='user', target_id=user_id, details="User not found or no changes made.", status='failure')
            return jsonify(message="User not found or no changes made"), 404

        db.commit()
        
        # B2B Professional Status Change Notification (Example)
        if 'professional_status' in update_payload and \
           update_payload['professional_status'] != user_info_before.get('professional_status') and \
           user_info_before.get('role') == 'b2b_professional':
            
            new_status = update_payload['professional_status']
            user_email = user_info_before['email']
            user_first_name = update_payload.get('first_name', user_info_before.get('first_name', 'User'))

            # from ..services.email_service import send_email # Import when email service is ready
            try:
                # send_email(
                #     to_email=user_email,
                #     subject=f"Your Professional Account Status Update - Maison Trüvra",
                #     body_html=f"<p>Dear {user_first_name},</p>"
                #               f"<p>Your professional account status has been updated to: <strong>{new_status.upper()}</strong>.</p>"
                #               f"<p>If you have any questions, please contact us.</p>"
                #               f"<p>Regards,<br/>Maison Trüvra Team</p>"
                # )
                current_app.logger.info(f"Professional status for user {user_id} ({user_email}) changed to {new_status}. Email notification simulated.")
                audit_logger.log_action(user_id=current_admin_id, action='notify_user_b2b_status', target_type='user', target_id=user_id, details=f"Notified {user_email} of status change to {new_status}.", status='success')
            except Exception as email_error:
                current_app.logger.error(f"Failed to send B2B status update email to {user_email}: {email_error}")
                audit_logger.log_action(user_id=current_admin_id, action='notify_user_b2b_status_fail', target_type='user', target_id=user_id, details=f"Failed to email {user_email} about status {new_status}: {email_error}", status='failure')
        
        audit_logger.log_action(
            user_id=current_admin_id, 
            action='update_user', 
            target_type='user', 
            target_id=user_id,
            details=f"User {user_id} updated. Fields: {', '.join(update_payload.keys())}",
            status='success'
        )
        return jsonify(message="User updated successfully"), 200
    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Database error updating user {user_id}: {e}")
        audit_logger.log_action(user_id=current_admin_id, action='update_user_fail', target_type='user', target_id=user_id, details=f"Database error: {e}", status='failure')
        return jsonify(message="Failed to update user due to database error"), 500
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating user {user_id}: {e}")
        audit_logger.log_action(user_id=current_admin_id, action='update_user_fail', target_type='user', target_id=user_id, details=str(e), status='failure')
        return jsonify(message="Failed to update user"), 500

# --- Order Management ---
@admin_api_bp.route('/orders', methods=['GET'])
@admin_required
def get_orders():
    db = get_db_connection()
    try:
        # Add query params for filtering by status, user, date range, pagination
        orders_data = query_db(
            """SELECT o.*, u.email as user_email, u.first_name, u.last_name 
               FROM orders o
               JOIN users u ON o.user_id = u.id
               ORDER BY o.order_date DESC""", db_conn=db)
        orders = [dict(row) for row in orders_data] if orders_data else []
        for order in orders:
            order['order_date'] = format_datetime_for_display(order['order_date'])
            order['created_at'] = format_datetime_for_display(order['created_at'])
            order['updated_at'] = format_datetime_for_display(order['updated_at'])
            # Fetch order items
            items_data = query_db(
                """SELECT oi.*, p.name as product_name_current, p.sku_prefix, si.item_uid as serialized_item_uid_actual
                   FROM order_items oi
                   LEFT JOIN products p ON oi.product_id = p.id
                   LEFT JOIN serialized_inventory_items si ON oi.serialized_item_id = si.id
                   WHERE oi.order_id = ?""", [order['id']], db_conn=db)
            order['items'] = [dict(item_row) for item_row in items_data] if items_data else []
        return jsonify(orders), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching orders: {e}")
        return jsonify(message="Failed to fetch orders"), 500

@admin_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id):
    current_admin_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()
    data = request.json

    new_status = data.get('status')
    if not new_status:
        audit_logger.log_action(user_id=current_admin_id, action='update_order_status_fail', target_type='order', target_id=order_id, details="New status not provided.", status='failure')
        return jsonify(message="New status not provided"), 400
    
    # Add validation for allowed status transitions if needed

    try:
        order_info = query_db("SELECT status, user_id FROM orders WHERE id = ?", [order_id], db_conn=db, one=True)
        if not order_info:
            audit_logger.log_action(user_id=current_admin_id, action='update_order_status_fail', target_type='order', target_id=order_id, details="Order not found.", status='failure')
            return jsonify(message="Order not found"), 404

        cursor = db.cursor()
        cursor.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, order_id))
        db.commit()

        # Potentially trigger email notification to customer about status change
        # user_email_row = query_db("SELECT email FROM users WHERE id = ?", [order_info['user_id']], db_conn=db, one=True)
        # if user_email_row:
        #    user_email = user_email_row['email']
        #    send_email(to_email=user_email, subject=f"Order #{order_id} Status Update", body_html=f"Your order status is now: {new_status}")

        audit_logger.log_action(
            user_id=current_admin_id, 
            action='update_order_status', 
            target_type='order', 
            target_id=order_id,
            details=f"Order {order_id} status changed from '{order_info['status']}' to '{new_status}'.",
            status='success'
        )
        return jsonify(message=f"Order status updated to {new_status}"), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating order status for {order_id}: {e}")
        audit_logger.log_action(user_id=current_admin_id, action='update_order_status_fail', target_type='order', target_id=order_id, details=str(e), status='failure')
        return jsonify(message="Failed to update order status"), 500

# --- Review Management ---
@admin_api_bp.route('/reviews', methods=['GET'])
@admin_required
def get_reviews():
    db = get_db_connection()
    # Param for status (pending, approved)
    status_filter = request.args.get('status') # 'pending', 'approved', or None for all
    
    query_sql = """
        SELECT r.id, r.product_id, p.name as product_name, r.user_id, u.email as user_email, 
               r.rating, r.comment, r.review_date, r.is_approved
        FROM reviews r
        JOIN products p ON r.product_id = p.id
        JOIN users u ON r.user_id = u.id
    """
    params = []
    if status_filter == 'pending':
        query_sql += " WHERE r.is_approved = FALSE"
    elif status_filter == 'approved':
        query_sql += " WHERE r.is_approved = TRUE"
    
    query_sql += " ORDER BY r.review_date DESC"

    try:
        reviews_data = query_db(query_sql, params, db_conn=db)
        reviews = [dict(row) for row in reviews_data] if reviews_data else []
        for review in reviews:
            review['review_date'] = format_datetime_for_display(review['review_date'])
        return jsonify(reviews), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching reviews: {e}")
        return jsonify(message="Failed to fetch reviews"), 500

@admin_api_bp.route('/reviews/<int:review_id>/approve', methods=['PUT'])
@admin_required
def approve_review(review_id):
    return _update_review_approval(review_id, True)

@admin_api_bp.route('/reviews/<int:review_id>/unapprove', methods=['PUT'])
@admin_required
def unapprove_review(review_id):
    return _update_review_approval(review_id, False)

def _update_review_approval(review_id, is_approved_status):
    current_admin_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()
    action_verb = "approve" if is_approved_status else "unapprove"

    try:
        review_exists = query_db("SELECT id FROM reviews WHERE id = ?", [review_id], db_conn=db, one=True)
        if not review_exists:
            audit_logger.log_action(user_id=current_admin_id, action=f'{action_verb}_review_fail', target_type='review', target_id=review_id, details="Review not found.", status='failure')
            return jsonify(message="Review not found"), 404

        cursor = db.cursor()
        cursor.execute("UPDATE reviews SET is_approved = ? WHERE id = ?", (is_approved_status, review_id))
        db.commit()
        
        audit_logger.log_action(
            user_id=current_admin_id, 
            action=f'{action_verb}_review', 
            target_type='review', 
            target_id=review_id,
            details=f"Review {review_id} status set to {is_approved_status}.",
            status='success'
        )
        return jsonify(message=f"Review {'approved' if is_approved_status else 'unapproved'} successfully"), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating review {review_id} approval: {e}")
        audit_logger.log_action(user_id=current_admin_id, action=f'{action_verb}_review_fail', target_type='review', target_id=review_id, details=str(e), status='failure')
        return jsonify(message=f"Failed to {action_verb} review"), 500

@admin_api_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@admin_required
def delete_review(review_id):
    current_admin_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()
    try:
        review_exists = query_db("SELECT id FROM reviews WHERE id = ?", [review_id], db_conn=db, one=True)
        if not review_exists:
            audit_logger.log_action(user_id=current_admin_id, action='delete_review_fail', target_type='review', target_id=review_id, details="Review not found.", status='failure')
            return jsonify(message="Review not found"), 404

        cursor = db.cursor()
        cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        db.commit()

        audit_logger.log_action(
            user_id=current_admin_id, 
            action='delete_review', 
            target_type='review', 
            target_id=review_id,
            details=f"Review {review_id} deleted.",
            status='success'
        )
        return jsonify(message="Review deleted successfully"), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error deleting review {review_id}: {e}")
        audit_logger.log_action(user_id=current_admin_id, action='delete_review_fail', target_type='review', target_id=review_id, details=str(e), status='failure')
        return jsonify(message="Failed to delete review"), 500


# --- Asset Serving (for images, QR codes, passports, labels) ---
# The `filename` parameter can include subdirectories, e.g., "products/image.jpg" or "qr_codes/item_qr.png"
@admin_api_bp.route('/assets/<path:asset_relative_path>')
@admin_required 
def serve_asset(asset_relative_path):
    """
    Serves assets. `asset_relative_path` is the path relative to either
    UPLOAD_FOLDER (for 'categories', 'products', 'professional_documents')
    or ASSET_STORAGE_PATH (for 'qr_codes', 'passports', 'labels', 'invoices').
    Example: /api/admin/assets/categories/cat_image.jpg
             /api/admin/assets/qr_codes/item_uid_qr.png
    """
    # Determine the base directory based on the first part of the path
    path_parts = asset_relative_path.split(os.sep, 1)
    top_level_folder = path_parts[0]
    
    # Default to UPLOAD_FOLDER, then check for generated asset types
    base_directory_config_key = 'UPLOAD_FOLDER' 
    
    if top_level_folder in ['qr_codes', 'passports', 'labels', 'invoices']:
        base_directory_config_key = 'ASSET_STORAGE_PATH'
    elif top_level_folder not in ['categories', 'products', 'professional_documents']:
        # If it's not a known generated asset type and not a known upload type,
        # it might be an attempt to access an unexpected path.
        current_app.logger.warning(f"Asset serving attempt for unknown top-level folder: {top_level_folder} in path {asset_relative_path}")
        return jsonify(message="Forbidden: Invalid asset category"), 403

    # Get the full base path from config (e.g., /app/instance/uploads or /app/instance/uploads/generated_assets)
    configured_base_path = current_app.config[base_directory_config_key]

    # The full path to the asset file
    # asset_relative_path already contains the top_level_folder, e.g., "categories/image.jpg"
    # So, configured_base_path is /instance/uploads, and we join it with "categories/image.jpg"
    # Or, configured_base_path is /instance/uploads/generated_assets, and we join it with "qr_codes/item.png"
    # This means asset_relative_path should NOT repeat the base part of ASSET_STORAGE_PATH if it's already in there.
    # Let's simplify: UPLOAD_FOLDER for user uploads, ASSET_STORAGE_PATH for our generated ones.
    # The asset_relative_path should be the path *within* these.

    # Correct logic:
    # If asset_relative_path = "categories/mycat.jpg", base is UPLOAD_FOLDER
    # If asset_relative_path = "qr_codes/myqr.png", base is ASSET_STORAGE_PATH
    
    # The `asset_relative_path` *is* the path segment that gets appended to the chosen base.
    # Example: UPLOAD_FOLDER / categories/image.jpg -> asset_relative_path = categories/image.jpg
    # Example: ASSET_STORAGE_PATH / qr_codes/item.png -> asset_relative_path = qr_codes/item.png

    full_file_path = os.path.abspath(os.path.join(configured_base_path, asset_relative_path))

    # Security check: Ensure the resolved path is still within the configured base directory
    # This helps prevent directory traversal if asset_relative_path contains '..'
    if not full_file_path.startswith(os.path.abspath(configured_base_path) + os.sep):
        current_app.logger.warning(f"Directory traversal attempt or invalid asset path. Base: {configured_base_path}, Relative: {asset_relative_path}, Resolved: {full_file_path}")
        return jsonify(message="Forbidden: Invalid path"), 403

    if not os.path.isfile(full_file_path):
        current_app.logger.warning(f"Asset not found: {full_file_path} (Relative: {asset_relative_path})")
        return jsonify(message="Asset not found"), 404

    # send_from_directory needs the directory and the filename separately.
    directory_to_serve_from = os.path.dirname(full_file_path)
    actual_filename = os.path.basename(full_file_path)
    
    current_app.logger.debug(f"Serving asset: Dir='{directory_to_serve_from}', File='{actual_filename}'")
    return send_from_directory(directory_to_serve_from, actual_filename)


# --- Settings Management (Example) ---
@admin_api_bp.route('/settings', methods=['GET'])
@admin_required
def get_settings():
    db = get_db_connection()
    try:
        settings_data = query_db("SELECT key, value, description FROM settings", db_conn=db)
        settings = {row['key']: {'value': row['value'], 'description': row['description']} for row in settings_data} if settings_data else {}
        return jsonify(settings), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching settings: {e}")
        return jsonify(message="Failed to fetch settings"), 500

@admin_api_bp.route('/settings', methods=['POST']) # Or PUT
@admin_required
def update_settings():
    current_admin_id = get_jwt_identity()
    audit_logger = current_app.audit_log_service
    db = get_db_connection()
    data = request.json # Expecting {"key1": "value1", "key2": "value2"}

    if not data:
        audit_logger.log_action(user_id=current_admin_id, action='update_settings_fail', details="No settings data provided.", status='failure')
        return jsonify(message="No settings data provided"), 400
    
    updated_keys = []
    try:
        cursor = db.cursor()
        for key, value in data.items():
            # Basic sanitization or validation for key/value can be added here
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, str(value)) # Ensure value is stored as text
            )
            updated_keys.append(key)
        db.commit()
        audit_logger.log_action(
            user_id=current_admin_id, 
            action='update_settings', 
            target_type='application_settings',
            details=f"Settings updated: {', '.join(updated_keys)}",
            status='success'
        )
        return jsonify(message="Settings updated successfully", updated_settings=updated_keys), 200
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating settings: {e}")
        audit_logger.log_action(user_id=current_admin_id, action='update_settings_fail', details=str(e), status='failure')
        return jsonify(message="Failed to update settings"), 500