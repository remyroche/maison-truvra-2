# backend/admin_api/routes.py
from flask import Blueprint, request, jsonify, current_app, g, send_file, url_for
import sqlite3 # Retained for direct DB interaction if that's a specific choice, but ORM is preferred for consistency
import os
import datetime
from datetime import timedelta # Added
import json # Added
from sqlalchemy import func, or_ # Added for SQLAlchemy ORM queries

# Assuming 'db' is your SQLAlchemy instance, e.g., from flask_sqlalchemy import SQLAlchemy; db = SQLAlchemy()
# And models are defined elsewhere, e.g., from ..models import Product, User, Invoice, Order, StockMovement, ProductVariant
# For get_db, it's usually a helper for direct DB connections, often used without an ORM.
# To maintain consistency with Product.query, User.query, etc., we should aim to use the ORM (db.session) throughout.
from ..database import get_db # If you have a mix, ensure it's intentional. Refactoring to full ORM is cleaner.

from ..auth.routes import admin_required # Decorator from auth_bp
from ..utils import log_error, is_valid_email # Assuming you have these

# New Imports - These would need to be implemented in your project
from ..email_utils import send_b2b_approval_email # Placeholder for email sending
from ..services.audit_service import AuditLogService # Placeholder for audit logging

# Import the invoice generation function and calculation
# Ensure this path is correct relative to your project structure.
# This import suggests generate_professional_invoice.py is two levels up from the current package.
from ...generate_professional_invoice import generate_invoice_pdf, calculate_invoice_totals

from werkzeug.utils import secure_filename # For file uploads

admin_api_bp = Blueprint('admin_api_bp', __name__)

# --- Model Placeholders (These should be defined in your models.py or equivalent) ---
# class Product(db.Model): ...
# class User(db.Model): ...
# class Invoice(db.Model): ...
# class Order(db.Model): ...
# class StockMovement(db.Model): ...
# class ProductVariant(db.Model): ...
# class db: # Placeholder for db.session, db.Model etc.
#     session = None 

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper to get full URL for static assets (if served via Flask's static route)
def get_static_url(filename, dir_name):
    if not filename:
        return None
    # Constructs URL like /static/dir_name/filename if 'dir_name' is a subfolder of static
    # Or just /static/filename if dir_name is incorporated into filename path already
    # This depends on how current_app.static_folder and current_app.config['QR_CODES_DIR_NAME'] etc. are set up.
    # A common pattern is to have asset-specific static routes or serve them from a dedicated asset server/CDN.
    try:
        return url_for('static', filename=os.path.join(dir_name, filename), _external=True)
    except RuntimeError: # If outside application context
        return f"/static/{dir_name}/{filename}" # Fallback, adjust as needed




# --- Dashboard ---
@admin_api_bp.route('/dashboard-stats', methods=['GET'])
@token_required_admin
def get_dashboard_stats(current_admin_user):
    """Provides statistics for the admin dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {}
    try:
        # Total Sales (sum of total_amount from paid orders)
        cursor.execute("SELECT SUM(total_amount) FROM orders WHERE payment_status = 'PAID'")
        total_sales = cursor.fetchone()[0]
        stats['total_sales'] = total_sales if total_sales is not None else 0

        # Total Orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        stats['total_orders'] = cursor.fetchone()[0]

        # New Customers (B2C users created in the last 30 days)
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'B2C' AND created_at >= date('now', '-30 days')")
        stats['new_customers_last_30_days'] = cursor.fetchone()[0]

        # Pending B2B Approvals
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'B2B_PENDING'")
        stats['pending_b2b_approvals'] = cursor.fetchone()[0]
        
        # Total Products
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        stats['total_active_products'] = cursor.fetchone()[0]

    except sqlite3.Error as e:
        logger.error(f"Database error in get_dashboard_stats: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        conn.close()
    return jsonify(stats), 200

# --- User Management ---
@admin_api_bp.route('/users', methods=['GET'])
@token_required_admin
def get_users(current_admin_user):
    """Fetches all users (B2C and B2B)."""
    # Implement pagination and filtering as needed
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, first_name, last_name, role, company_name, vat_number, siret_number, is_active, created_at FROM users ORDER BY created_at DESC")
        users_rows = cursor.fetchall()
        users = [row_to_dict(cursor, row) for row in users_rows]
        return jsonify(users), 200
    except sqlite3.Error as e:
        logger.error(f"Database error fetching users: {e}")
        return jsonify({"error": "Failed to fetch users", "details": str(e)}), 500
    finally:
        conn.close()

@admin_api_bp.route('/users/<int:user_id>/approve-b2b', methods=['POST'])
@token_required_admin
def approve_b2b_user(current_admin_user, user_id):
    """Approves a B2B user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET role = 'B2B_APPROVED', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND role = 'B2B_PENDING'", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "User not found or not pending B2B approval"}), 404
        # Placeholder for AuditLogService.log_event(...)
        logger.info(f"Admin {current_admin_user.get('username')} approved B2B user ID {user_id}")
        return jsonify({"message": "B2B user approved successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error approving B2B user {user_id}: {e}")
        return jsonify({"error": "Failed to approve B2B user", "details": str(e)}), 500
    finally:
        conn.close()

@admin_api_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@token_required_admin
def toggle_user_active_status(current_admin_user, user_id):
    """Toggles the active status of a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT is_active FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"error": "User not found"}), 404
        
        new_status = not user_row['is_active']
        cursor.execute("UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, user_id))
        conn.commit()
        
        action = "activated" if new_status else "deactivated"
        logger.info(f"Admin {current_admin_user.get('username')} {action} user ID {user_id}")
        return jsonify({"message": f"User status toggled successfully. User is now {action}.", "new_status": new_status}), 200
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error toggling active status for user {user_id}: {e}")
        return jsonify({"error": "Failed to toggle user active status", "details": str(e)}), 500
    finally:
        conn.close()


# --- Order Management ---
@admin_api_bp.route('/orders', methods=['GET'])
@token_required_admin
def get_orders(current_admin_user):
    """Fetches B2C orders with pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', current_config.ITEMS_PER_PAGE_ADMIN, type=int)
        if page < 1: page = 1
        if per_page < 1: per_page = current_config.ITEMS_PER_PAGE_ADMIN
        if per_page > 100: per_page = 100 # Max limit

        offset = (page - 1) * per_page

        # Get total number of orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        total_pages = math.ceil(total_orders / per_page)

        # Fetch orders for the current page
        # Joined with users to get customer email/name if available
        query = """
            SELECT 
                o.id, o.order_reference, o.total_amount, o.status, o.payment_status, o.created_at,
                o.shipping_address_line1, o.shipping_city, o.shipping_postal_code, o.shipping_country,
                o.tracking_number,
                u.email AS customer_email, 
                u.first_name AS customer_first_name, 
                u.last_name AS customer_last_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, (per_page, offset))
        orders_rows = cursor.fetchall()
        orders = [row_to_dict(cursor, row) for row in orders_rows]

        return jsonify({
            "orders": orders,
            "page": page,
            "per_page": per_page,
            "total_orders": total_orders,
            "total_pages": total_pages
        }), 200

    except sqlite3.Error as e:
        logger.error(f"Database error fetching orders: {e}")
        return jsonify({"error": "Failed to fetch orders", "details": str(e)}), 500
    finally:
        conn.close()

@admin_api_bp.route('/orders/<int:order_id>', methods=['GET'])
@token_required_admin
def get_order_details(current_admin_user, order_id):
    """Fetches details for a specific order, including its items."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch order details
        cursor.execute("""
            SELECT o.*, u.email as user_email, u.first_name, u.last_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        """, (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            return jsonify({"error": "Order not found"}), 404
        order = row_to_dict(cursor, order_row)

        # Fetch order items
        cursor.execute("""
            SELECT oi.*, p.name_fr as product_name_fr_current, p.name_en as product_name_en_current,
                   po.value_fr as option_value_fr_current, po.value_en as option_value_en_current
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            LEFT JOIN product_options po ON oi.product_option_id = po.id
            WHERE oi.order_id = ?
        """, (order_id,))
        order_items_rows = cursor.fetchall()
        order['items'] = [row_to_dict(cursor, row) for row in order_items_rows]

        return jsonify(order), 200
    except sqlite3.Error as e:
        logger.error(f"Database error fetching order details for order {order_id}: {e}")
        return jsonify({"error": "Failed to fetch order details", "details": str(e)}), 500
    finally:
        conn.close()


@admin_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@token_required_admin
def update_order_status(current_admin_user, order_id):
    """Updates the status of an order."""
    data = request.get_json()
    new_status = data.get('status')
    tracking_number = data.get('tracking_number', None) # Optional tracking number

    if not new_status:
        return jsonify({"error": "New status is required"}), 400
    
    # Basic validation for allowed statuses (expand as needed)
    allowed_statuses = ['PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELED', 'REFUNDED']
    if new_status.upper() not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Allowed statuses are: {', '.join(allowed_statuses)}"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if order exists
        cursor.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Order not found"}), 404

        if tracking_number and new_status.upper() == 'SHIPPED':
            cursor.execute("UPDATE orders SET status = ?, tracking_number = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                           (new_status.upper(), tracking_number, order_id))
        else:
            cursor.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                           (new_status.upper(), order_id))
        conn.commit()

        if cursor.rowcount == 0: # Should not happen if previous check passed
             return jsonify({"error": "Order not found or status not updated"}), 404

        logger.info(f"Admin {current_admin_user.get('username')} updated order ID {order_id} to status {new_status.upper()}")
        # Potentially trigger email notification to customer here
        return jsonify({"message": "Order status updated successfully", "new_status": new_status.upper()}), 200
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error updating status for order {order_id}: {e}")
        return jsonify({"error": "Failed to update order status", "details": str(e)}), 500
    finally:
        conn.close()

# --- Category Management ---
@admin_api_bp.route('/categories', methods=['POST'])
@token_required_admin
def create_category(current_admin_user):
    """Creates a new category."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['name_fr', 'name_en']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    name_fr = data['name_fr']
    name_en = data['name_en']
    description_fr = data.get('description_fr', '')
    description_en = data.get('description_en', '')
    image_url = data.get('image_url', '')
    
    # Generate slug from French name if not provided, or use provided slug
    custom_slug = data.get('slug')
    if custom_slug:
        slug = slugify(custom_slug)
    else:
        slug = slugify(name_fr)


    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO categories (name_fr, name_en, description_fr, description_en, slug, image_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name_fr, name_en, description_fr, description_en, slug, image_url))
        conn.commit()
        category_id = cursor.lastrowid
        logger.info(f"Admin {current_admin_user.get('username')} created category ID {category_id} ('{name_fr}')")
        
        # Fetch the created category to return it
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        new_category = row_to_dict(cursor, cursor.fetchone())
        return jsonify({"message": "Category created successfully", "category": new_category}), 201
    except sqlite3.IntegrityError as e: # Handles UNIQUE constraint violations
        conn.rollback()
        logger.error(f"Database integrity error creating category '{name_fr}': {e}")
        error_detail = str(e).lower()
        if "unique constraint failed: categories.name_fr" in error_detail:
            return jsonify({"error": "Category name (French) already exists."}), 409
        elif "unique constraint failed: categories.name_en" in error_detail:
            return jsonify({"error": "Category name (English) already exists."}), 409
        elif "unique constraint failed: categories.slug" in error_detail:
            return jsonify({"error": "Category slug already exists. Try a different name or custom slug."}), 409
        return jsonify({"error": "Failed to create category due to a conflict.", "details": str(e)}), 409
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error creating category '{name_fr}': {e}")
        return jsonify({"error": "Failed to create category", "details": str(e)}), 500
    finally:
        conn.close()

@admin_api_bp.route('/categories', methods=['GET'])
@token_required_admin
def get_categories(current_admin_user):
    """Fetches all categories with optional pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 0, type=int) # 0 means all, otherwise paginate

        if page < 1: page = 1
        
        if per_page > 0 : # Paginate
            if per_page > 100: per_page = 100 # Max limit
            offset = (page - 1) * per_page

            cursor.execute("SELECT COUNT(*) FROM categories")
            total_categories = cursor.fetchone()[0]
            total_pages = math.ceil(total_categories / per_page) if per_page > 0 else 1

            cursor.execute("SELECT * FROM categories ORDER BY name_fr LIMIT ? OFFSET ?", (per_page, offset))
            categories_rows = cursor.fetchall()
            categories = [row_to_dict(cursor, row) for row in categories_rows]
            
            return jsonify({
                "categories": categories,
                "page": page,
                "per_page": per_page,
                "total_categories": total_categories,
                "total_pages": total_pages
            }), 200
        else: # Get all categories
            cursor.execute("SELECT * FROM categories ORDER BY name_fr")
            categories_rows = cursor.fetchall()
            categories = [row_to_dict(cursor, row) for row in categories_rows]
            return jsonify({"categories": categories, "total_categories": len(categories)}), 200

    except sqlite3.Error as e:
        logger.error(f"Database error fetching categories: {e}")
        return jsonify({"error": "Failed to fetch categories", "details": str(e)}), 500
    finally:
        conn.close()

@admin_api_bp.route('/categories/<int:category_id>', methods=['GET'])
@token_required_admin
def get_category(current_admin_user, category_id):
    """Fetches a single category by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category_row = cursor.fetchone()
        if not category_row:
            return jsonify({"error": "Category not found"}), 404
        category = row_to_dict(cursor, category_row)
        return jsonify(category), 200
    except sqlite3.Error as e:
        logger.error(f"Database error fetching category {category_id}: {e}")
        return jsonify({"error": "Failed to fetch category", "details": str(e)}), 500
    finally:
        conn.close()

@admin_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@token_required_admin
def update_category(current_admin_user, category_id):
    """Updates an existing category."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if category exists
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category_row = cursor.fetchone()
        if not category_row:
            return jsonify({"error": "Category not found"}), 404
        
        current_category = row_to_dict(cursor, category_row)

        name_fr = data.get('name_fr', current_category['name_fr'])
        name_en = data.get('name_en', current_category['name_en'])
        description_fr = data.get('description_fr', current_category['description_fr'])
        description_en = data.get('description_en', current_category['description_en'])
        image_url = data.get('image_url', current_category['image_url'])
        
        # Regenerate slug if name_fr changed and no custom slug provided, or use provided/existing slug
        custom_slug = data.get('slug')
        if custom_slug:
            slug = slugify(custom_slug)
        elif 'name_fr' in data and data['name_fr'] != current_category['name_fr']: # name_fr changed, no custom slug
            slug = slugify(name_fr)
        else: # name_fr not changed or custom slug not provided, use existing
            slug = current_category['slug']


        if not name_fr or not name_en: # Basic validation
             return jsonify({"error": "Category names (French and English) cannot be empty"}), 400


        cursor.execute("""
            UPDATE categories SET
            name_fr = ?, name_en = ?, description_fr = ?, description_en = ?, slug = ?, image_url = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name_fr, name_en, description_fr, description_en, slug, image_url, category_id))
        conn.commit()

        if cursor.rowcount == 0: # Should not happen if previous check passed
             return jsonify({"error": "Category not found or not updated"}), 404
        
        logger.info(f"Admin {current_admin_user.get('username')} updated category ID {category_id} ('{name_fr}')")
        
        # Fetch the updated category to return it
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        updated_category = row_to_dict(cursor, cursor.fetchone())
        return jsonify({"message": "Category updated successfully", "category": updated_category}), 200
    except sqlite3.IntegrityError as e: # Handles UNIQUE constraint violations
        conn.rollback()
        logger.error(f"Database integrity error updating category {category_id}: {e}")
        error_detail = str(e).lower()
        if "unique constraint failed: categories.name_fr" in error_detail:
            return jsonify({"error": "Category name (French) already exists."}), 409
        elif "unique constraint failed: categories.name_en" in error_detail:
            return jsonify({"error": "Category name (English) already exists."}), 409
        elif "unique constraint failed: categories.slug" in error_detail:
            return jsonify({"error": "Category slug already exists. Try a different name or custom slug."}), 409
        return jsonify({"error": "Failed to update category due to a conflict.", "details": str(e)}), 409
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error updating category {category_id}: {e}")
        return jsonify({"error": "Failed to update category", "details": str(e)}), 500
    finally:
        conn.close()

@admin_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@token_required_admin
def delete_category(current_admin_user, category_id):
    """Deletes a category."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if category exists
        cursor.execute("SELECT name_fr FROM categories WHERE id = ?", (category_id,))
        category_row = cursor.fetchone()
        if not category_row:
            return jsonify({"error": "Category not found"}), 404
        
        category_name = category_row['name_fr']

        # Products linked to this category will have their category_id set to NULL due to ON DELETE SET NULL
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()

        if cursor.rowcount == 0: # Should not happen
            return jsonify({"error": "Category not found or not deleted"}), 404

        logger.info(f"Admin {current_admin_user.get('username')} deleted category ID {category_id} ('{category_name}')")
        return jsonify({"message": f"Category '{category_name}' (ID: {category_id}) deleted successfully. Associated products now have no category."}), 200
    except sqlite3.Error as e: # Catch other potential errors, though ON DELETE SET NULL should prevent FK issues here
        conn.rollback()
        logger.error(f"Database error deleting category {category_id}: {e}")
        return jsonify({"error": "Failed to delete category", "details": str(e)}), 500
    finally:
        conn.close()


# --- Product Management (Placeholder - to be expanded) ---
@admin_api_bp.route('/products', methods=['GET'])
@token_required_admin
def get_products_admin(current_admin_user):
    # This is a simplified version. You'll need pagination, filtering, sorting, etc.
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Example: Fetch products with their category names
        cursor.execute("""
            SELECT p.*, c.name_fr as category_name_fr, c.name_en as category_name_en
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY p.created_at DESC
        """)
        products_rows = cursor.fetchall()
        products = [row_to_dict(cursor, row) for row in products_rows]
        return jsonify(products), 200
    except sqlite3.Error as e:
        logger.error(f"Database error fetching products for admin: {e}")
        return jsonify({"error": "Failed to fetch products", "details": str(e)}), 500
    finally:
        conn.close()


@admin_api_bp.route('/products', methods=['POST'])
@admin_required
def create_product():
    # Assuming db.session is available from Flask-SQLAlchemy
    # And Product, ProductVariant, StockMovement are defined SQLAlchemy models
    data = request.form.to_dict()
    current_app.logger.info(f"Received data for new product: {data}")

    required_fields = ['name_fr', 'name_en', 'sku', 'category_fr', 'category_en', 'base_price']
    for field in required_fields:
        if field not in data or not data[field]:
            AuditLogService.log_event(action="ADMIN_CREATE_PRODUCT_FAIL", details={"error": f"Missing field: {field}"}, success=False)
            return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

    try:
        base_price_str = data.get('base_price')
        base_price = float(base_price_str) if base_price_str and not (data.get('has_variants') == 'true') else None
        initial_stock_quantity = int(data.get('initial_stock_quantity', 0))
    except ValueError:
        AuditLogService.log_event(action="ADMIN_CREATE_PRODUCT_FAIL", details={"error": "Invalid number format"}, success=False)
        return jsonify({'success': False, 'message': 'Invalid number format for price or stock.'}), 400

    # Placeholder for actual Model classes
    # from ..models import Product, ProductVariant, StockMovement 

    new_product_params = {
        'name_fr': data['name_fr'], 'name_en': data['name_en'],
        'description_fr': data.get('description_fr'), 'description_en': data.get('description_en'),
        'sku': data['sku'], 'category_fr': data['category_fr'], 'category_en': data['category_en'],
        'base_price': base_price,
        'is_featured': data.get('is_featured') == 'true',
        'is_active': data.get('is_active', 'true') == 'true',
        'meta_title_fr': data.get('meta_title_fr'), 'meta_title_en': data.get('meta_title_en'),
        'meta_description_fr': data.get('meta_description_fr'), 'meta_description_en': data.get('meta_description_en'),
        'slug_fr': data.get('slug_fr'), 'slug_en': data.get('slug_en'),
        'species_fr': data.get('species_fr'), 'species_en': data.get('species_en'),
        'origin_fr': data.get('origin_fr'), 'origin_en': data.get('origin_en'),
        'quality_grade_fr': data.get('quality_grade_fr'), 'quality_grade_en': data.get('quality_grade_en'),
        'nett_weight_g': int(data['nett_weight_g']) if data.get('nett_weight_g') else None,
        'harvest_date': datetime.datetime.strptime(data.get('harvest_date'), '%Y-%m-%d').date() if data.get('harvest_date') else None,
        'best_before_date': datetime.datetime.strptime(data.get('best_before_date'), '%Y-%m-%d').date() if data.get('best_before_date') else None,
        'has_variants': data.get('has_variants') == 'true',
        'generate_assets_on_update': data.get('generate_assets_on_update', 'true') == 'true'
    }
    # new_product = Product(**new_product_params) # Replace with your actual Product model initialization

    # --- Mocking ORM for demonstration as models are not defined ---
    class MockProduct:
        def __init__(self, **kwargs):
            self.id = 1 # Mock ID
            self.variants = []
            self.stock_quantity = 0
            for key, value in kwargs.items():
                setattr(self, key, value)
        def to_dict(self, lang): return self.__dict__

    class MockVariant:
        def __init__(self, **kwargs):
            self.id = 2 # Mock ID
            for key, value in kwargs.items():
                setattr(self, key, value)

    class MockStockMovement:
        def __init__(self, **kwargs): pass
    
    db = type('obj', (object,), {'session': type('obj', (object,), {'add': lambda x: None, 'flush': lambda: None, 'commit': lambda: None, 'rollback': lambda: None})()})()
    Product = MockProduct
    ProductVariant = MockVariant
    StockMovement = MockStockMovement
    new_product = Product(**new_product_params)
    # --- End Mocking ---


    uploaded_image_paths = []
    uploaded_thumb_paths = []

    # Ensure current_app.static_folder is configured and writable
    # And config keys like 'PRODUCTS_MAIN_IMAGES_DIR_NAME' are set
    main_image_dir_name = current_app.config.get('PRODUCTS_MAIN_IMAGES_DIR_NAME', 'products/main')
    thumb_image_dir_name = current_app.config.get('PRODUCTS_THUMB_IMAGES_DIR_NAME', 'products/thumbnails')

    if 'images' in request.files:
        for file_item in request.files.getlist('images'):
            if file_item and file_item.filename != '':
                filename = secure_filename(file_item.filename)
                save_dir = os.path.join(current_app.static_folder, main_image_dir_name)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file_item.save(file_path)
                uploaded_image_paths.append(os.path.join(main_image_dir_name, filename))

    if 'thumbnails' in request.files:
        for file_item in request.files.getlist('thumbnails'):
            if file_item and file_item.filename != '':
                filename = secure_filename(file_item.filename)
                save_dir = os.path.join(current_app.static_folder, thumb_image_dir_name)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file_item.save(file_path)
                uploaded_thumb_paths.append(os.path.join(thumb_image_dir_name, filename))

    new_product.image_urls = json.dumps(uploaded_image_paths) if uploaded_image_paths else None
    new_product.image_urls_thumb = json.dumps(uploaded_thumb_paths) if uploaded_thumb_paths else None
    
    db.session.add(new_product)
    db.session.flush() 

    if new_product.has_variants:
        weight_options_str = data.get('weight_options', '[]')
        try:
            weight_options = json.loads(weight_options_str)
            for option in weight_options:
                variant = ProductVariant(
                    product_id=new_product.id,
                    weight_grams=int(option['weight']),
                    price=float(option['price']),
                    stock_quantity=int(option.get('stock', 0))
                )
                db.session.add(variant)
                db.session.flush() # Get variant.id if needed for stock movement
                if variant.stock_quantity > 0:
                    stock_movement = StockMovement(
                        product_id=new_product.id, variant_id=variant.id,
                        quantity_change=variant.stock_quantity, reason="initial_stock_variant",
                        notes=f"Initial stock for variant {variant.weight_grams}g"
                    )
                    db.session.add(stock_movement)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            db.session.rollback()
            log_error(f"Error processing product variants: {e}")
            AuditLogService.log_event(action="ADMIN_CREATE_PRODUCT_FAIL", details={"error": f"Variant error: {e}"}, success=False)
            return jsonify({'success': False, 'message': f'Invalid format for weight options: {e}'}), 400
    elif initial_stock_quantity > 0:
        new_product.stock_quantity = initial_stock_quantity
        stock_movement = StockMovement(
            product_id=new_product.id, quantity_change=initial_stock_quantity,
            reason="initial_stock", notes="Initial stock for product"
        )
        db.session.add(stock_movement)

    if new_product.generate_assets_on_update:
        try:
            # Asset generation functions (generate_product_qr_code_image, etc.) need to be defined/imported
            # and config paths like QR_CODES_OUTPUT_DIR, APP_BASE_URL need to be set.
            # Example (conceptual, actual implementation depends on your functions):
            # asset_product_data_fr = new_product.to_dict(lang='fr')
            # qr_filename = f"qr_{new_product.sku}.png"
            # qr_code_content = f"{current_app.config['APP_BASE_URL']}/produit/{new_product.slug_fr or new_product.id}"
            # qr_code_path_abs = os.path.join(current_app.config['QR_CODES_OUTPUT_DIR'], qr_filename) # Ensure this dir exists
            # generate_product_qr_code_image(qr_code_content, qr_code_path_abs)
            # new_product.qr_code_path = os.path.join(current_app.config.get('QR_CODES_DIR_NAME_STATIC', 'qrcodes'), qr_filename) # Relative to static for URL
            pass # Placeholder for asset generation logic
        except Exception as e:
            db.session.rollback() # Rollback if asset generation critical and fails
            log_error(f"Error generating assets for new product {new_product.sku}: {e}")
            AuditLogService.log_event(action="ADMIN_CREATE_PRODUCT_ASSET_FAIL", target_id=new_product.sku, details={"error": str(e)}, success=False)
            return jsonify({'success': False, 'message': f'Product data potentially saved, but asset generation failed: {e}'}), 500 # 207 could also be used

    try:
        db.session.commit()
        AuditLogService.log_event(action="ADMIN_CREATED_PRODUCT", target_type="PRODUCT", target_id=new_product.id, details={"sku": new_product.sku})
        return jsonify({'success': True, 'message': 'Product created successfully', 'product_id': new_product.id}), 201
    except Exception as e:
        db.session.rollback()
        log_error(f"Error saving product to database: {e}")
        AuditLogService.log_event(action="ADMIN_CREATE_PRODUCT_DB_FAIL", details={"error": str(e)}, success=False)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    # product = Product.query.get_or_404(product_id) # Using ORM
    # --- Mocking ORM ---
    class MockProduct:
        def __init__(self, id): self.id = id; self.variants = []; self.stock_quantity=0; self.image_urls=None; self.image_urls_thumb=None; self.generate_assets_on_update=True; self.sku=f"SKU{id}"
        def to_dict(self, lang, include_variants=False, include_stock_movements=False): return self.__dict__
    product = MockProduct(product_id)
    # --- End Mocking ---
    
    data = request.form.to_dict()
    current_app.logger.info(f"Received data for updating product {product_id}: {data}")

    # Update simple fields
    for field in ['name_fr', 'name_en', 'description_fr', 'description_en', 'sku', 
                  'category_fr', 'category_en', 'meta_title_fr', 'meta_title_en',
                  'meta_description_fr', 'meta_description_en', 'slug_fr', 'slug_en',
                  'species_fr', 'species_en', 'origin_fr', 'origin_en', 
                  'quality_grade_fr', 'quality_grade_en']:
        if field in data:
            setattr(product, field, data[field])

    if 'is_featured' in data: product.is_featured = data.get('is_featured') == 'true'
    if 'is_active' in data: product.is_active = data.get('is_active') == 'true'
    if 'generate_assets_on_update' in data: product.generate_assets_on_update = data.get('generate_assets_on_update') == 'true'
    
    if data.get('nett_weight_g'): product.nett_weight_g = int(data['nett_weight_g'])
    if data.get('harvest_date'): product.harvest_date = datetime.datetime.strptime(data['harvest_date'], '%Y-%m-%d').date()
    if data.get('best_before_date'): product.best_before_date = datetime.datetime.strptime(data['best_before_date'], '%Y-%m-%d').date()
    
    product.has_variants = data.get('has_variants') == 'true'
    if product.has_variants:
        product.base_price = None
        product.stock_quantity = 0 # Stock managed by variants
    else:
        if data.get('base_price'): product.base_price = float(data['base_price'])
        if data.get('initial_stock_quantity'): # This should ideally be handled by a separate stock adjustment
            product.stock_quantity = int(data['initial_stock_quantity'])

    # Image handling (simplified: replaces if new ones are uploaded)
    main_image_dir_name = current_app.config.get('PRODUCTS_MAIN_IMAGES_DIR_NAME', 'products/main')
    thumb_image_dir_name = current_app.config.get('PRODUCTS_THUMB_IMAGES_DIR_NAME', 'products/thumbnails')

    if 'images' in request.files:
        uploaded_image_paths = []
        # Consider deleting old images if replacing
        for file_item in request.files.getlist('images'):
            if file_item and file_item.filename != '':
                filename = secure_filename(file_item.filename)
                save_dir = os.path.join(current_app.static_folder, main_image_dir_name)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file_item.save(file_path)
                uploaded_image_paths.append(os.path.join(main_image_dir_name, filename))
        if uploaded_image_paths: product.image_urls = json.dumps(uploaded_image_paths)

    if 'thumbnails' in request.files:
        uploaded_thumb_paths = []
        for file_item in request.files.getlist('thumbnails'):
            if file_item and file_item.filename != '':
                filename = secure_filename(file_item.filename)
                save_dir = os.path.join(current_app.static_folder, thumb_image_dir_name)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                file_path = os.path.join(save_dir, filename)
                file_item.save(file_path)
                uploaded_thumb_paths.append(os.path.join(thumb_image_dir_name, filename))
        if uploaded_thumb_paths: product.image_urls_thumb = json.dumps(uploaded_thumb_paths)

    # Variant update logic (complex, needs careful implementation with ORM)
    if product.has_variants:
        weight_options_str = data.get('weight_options', '[]')
        try:
            weight_options = json.loads(weight_options_str)
            # existing_variants_map = {v.weight_grams: v for v in product.variants} # ORM
            # new_variant_weights = [int(opt['weight']) for opt in weight_options]

            # # Update existing or add new
            # for option in weight_options:
            #     weight = int(option['weight'])
            #     price = float(option['price'])
            #     stock = int(option.get('stock', 0))
            #     if weight in existing_variants_map:
            #         variant = existing_variants_map[weight]
            #         # Update stock and price, record movement
            #     else:
            #         # new_variant = ProductVariant(...)
            #         # db.session.add(new_variant)
            #         pass # Add new variant logic
            
            # # Remove old variants
            # for weight, variant in existing_variants_map.items():
            #     if weight not in new_variant_weights:
            #         # db.session.delete(variant)
            #         pass # Delete variant logic
            pass # Placeholder for variant update logic
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            db.session.rollback()
            log_error(f"Error updating product variants for {product_id}: {e}")
            return jsonify({'success': False, 'message': f'Invalid format for weight options: {e}'}), 400

    db.session.flush()

    if product.generate_assets_on_update:
        try:
            # Asset regeneration logic (similar to create_product)
            pass
        except Exception as e:
            log_error(f"Error regenerating assets for product {product.sku}: {e}")
            # Decide if this is a partial success or full failure
            # return jsonify({'success': False, 'message': f'Product updated, but asset regeneration failed: {e}'}), 500


    try:
        db.session.commit()
        AuditLogService.log_event(action="ADMIN_UPDATED_PRODUCT", target_type="PRODUCT", target_id=product_id, details={"sku": product.sku})
        return jsonify({'success': True, 'message': 'Product updated successfully', 'product': product.to_dict(lang=data.get('lang', 'fr'))}), 200
    except Exception as e:
        db.session.rollback()
        log_error(f"Error committing product update {product_id}: {e}")
        AuditLogService.log_event(action="ADMIN_UPDATE_PRODUCT_DB_FAIL", target_id=product_id, details={"error": str(e)}, success=False)
        return jsonify({'success': False, 'message': f'Database error on commit: {e}'}), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    # product = Product.query.get_or_404(product_id) # ORM
    # --- Mocking ORM ---
    class MockProduct:
        def __init__(self, id): self.id = id; self.qr_code_path=None
    product = MockProduct(product_id)
    # --- End Mocking ---
    try:
        # Add logic for deleting related entities (variants, stock movements) if cascade is not set up
        # Delete associated assets from filesystem
        if product.qr_code_path and current_app.config.get('QR_CODES_OUTPUT_DIR'):
             qr_abs_path = os.path.join(current_app.config['QR_CODES_OUTPUT_DIR'], os.path.basename(product.qr_code_path))
             if os.path.exists(qr_abs_path): os.remove(qr_abs_path)
        # ... similar for passport, label, images ...

        # db.session.delete(product) # ORM
        # db.session.commit() # ORM
        AuditLogService.log_event(action="ADMIN_DELETED_PRODUCT", target_type="PRODUCT", target_id=product_id)
        return jsonify({'success': True, 'message': 'Product deleted successfully'}), 200
    except Exception as e:
        # db.session.rollback() # ORM
        log_error(f"Error deleting product {product_id}: {e}")
        AuditLogService.log_event(action="ADMIN_DELETE_PRODUCT_FAIL", target_id=product_id, details={"error": str(e)}, success=False)
        return jsonify({'success': False, 'message': f'Error deleting product: {e}'}), 500


@admin_api_bp.route('/products', methods=['GET'])
@admin_required
def get_products():
    # Assuming Product model with a query attribute and to_dict method
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        lang = request.args.get('lang', current_app.config.get('DEFAULT_LANGUAGE', 'fr'))

        # products_query = Product.query.order_by(Product.created_at.desc()) # ORM
        # products_pagination = products_query.paginate(page=page, per_page=per_page, error_out=False) # ORM
        # products_data = [p.to_dict(lang=lang) for p in products_pagination.items] # ORM
        
        # --- Mocking ORM ---
        products_data = [{"id":1, "name_fr":"Mock Product", "sku":"MCK001"}]
        products_pagination_total = 1
        products_pagination_pages = 1
        # --- End Mocking ---

        AuditLogService.log_event(action="ADMIN_VIEWED_PRODUCTS_LIST", details={"page": page, "per_page": per_page})
        return jsonify({
            'success': True,
            'products': products_data,
            'total': products_pagination_total, # products_pagination.total,
            'pages': products_pagination_pages, # products_pagination.pages,
            'current_page': page # products_pagination.page
        })
    except Exception as e:
        log_error(f"Error fetching products: {e}")
        AuditLogService.log_event(action="ADMIN_VIEW_PRODUCTS_ERROR", details={"error": str(e)}, success=False)
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_api_bp.route('/products/<int:product_id>', methods=['GET'])
@admin_required
def get_admin_product_details(product_id):
    # product = Product.query.get_or_404(product_id) # ORM
    # --- Mocking ORM ---
    class MockProduct:
        def __init__(self, id): self.id = id
        def to_dict(self, lang, include_variants=False, include_stock_movements=False): return {"id": self.id, "name_fr": "Mock Detail", "image_urls": "[]", "image_urls_thumb": "[]"}
    product = MockProduct(product_id)
    # --- End Mocking ---
    lang = request.args.get('lang', current_app.config.get('DEFAULT_LANGUAGE', 'fr'))
    product_dict = product.to_dict(lang=lang, include_variants=True, include_stock_movements=True)

    for key in ['image_urls', 'image_urls_thumb']: # Ensure these are lists
        raw_val = product_dict.get(key)
        if isinstance(raw_val, str):
            try: product_dict[key] = json.loads(raw_val)
            except json.JSONDecodeError: product_dict[key] = []
        elif not isinstance(raw_val, list): product_dict[key] = []
    
    AuditLogService.log_event(action="ADMIN_VIEWED_PRODUCT_DETAILS", target_type="PRODUCT", target_id=product_id)
    return jsonify({'success': True, 'product': product_dict})





@admin_api_bp.route('/stock-movements', methods=['POST'])
@admin_required
def add_stock_movement():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id') 
    quantity_change = data.get('quantity_change')
    reason = data.get('reason')
    notes = data.get('notes')

    if not product_id or quantity_change is None or not reason:
        return jsonify({'success': False, 'message': 'Missing required fields: product_id, quantity_change, reason.'}), 400
    
    try:
        quantity_change = int(quantity_change)
    except ValueError:
        return jsonify({'success': False, 'message': 'quantity_change must be an integer.'}), 400

    # product = Product.query.get(product_id) # ORM
    # if not product: return jsonify({'success': False, 'message': 'Product not found.'}), 404
    # --- Mocking ---
    class MockProduct:
        def __init__(self, id): self.id = id; self.has_variants=False; self.stock_quantity=0
    product = MockProduct(product_id)
    # --- End Mocking ---
    
    target_variant = None
    if variant_id:
        # target_variant = ProductVariant.query.filter_by(id=variant_id, product_id=product_id).first() # ORM
        # if not target_variant: return jsonify({'success': False, 'message': 'Variant not found for this product.'}), 404
        # --- Mocking ---
        class MockPV:
            def __init__(self,id): self.id=id; self.stock_quantity=0
        target_variant = MockPV(variant_id) if product.has_variants else None # Simple mock
        if product.has_variants and not target_variant : return jsonify({'success': False, 'message': 'Mock Variant not found'}), 404
        # --- End Mocking ---
    elif product.has_variants:
        return jsonify({'success': False, 'message': 'This product has variants. Please specify a variant_id.'}), 400

    # movement = StockMovement(...) # ORM
    # db.session.add(movement) # ORM

    if target_variant:
        target_variant.stock_quantity += quantity_change
    else:
        product.stock_quantity += quantity_change
    
    try:
        # db.session.commit() # ORM
        AuditLogService.log_event(action="ADMIN_ADDED_STOCK_MOVEMENT", target_type="PRODUCT", target_id=product_id, details={"variant":variant_id, "qty":quantity_change, "reason":reason})
        return jsonify({'success': True, 'message': 'Stock movement recorded successfully.'}), 201
    except Exception as e:
        # db.session.rollback() # ORM
        log_error(f"Error recording stock movement: {e}")
        AuditLogService.log_event(action="ADMIN_ADD_STOCK_FAIL", details={"error": str(e)}, success=False)
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500


@admin_api_bp.route('/invoices/upload', methods=['POST'])
@admin_required
def upload_invoice():
    if 'invoice_file' not in request.files:
        return jsonify({'success': False, 'message': 'No invoice file part'}), 400
    file = request.files['invoice_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected invoice file'}), 400

    user_id_str = request.form.get('user_id')
    invoice_number = request.form.get('invoice_number')
    issue_date_str = request.form.get('issue_date')
    total_amount_str = request.form.get('total_amount')

    if not all([user_id_str, invoice_number, issue_date_str, total_amount_str]):
        return jsonify({'success': False, 'message': 'Missing required fields for invoice upload.'}), 400

    if file and allowed_file(file.filename):
        filename_base = secure_filename(f"{invoice_number}_{user_id_str}_{os.path.splitext(file.filename)[0]}")
        filename = f"{filename_base}{os.path.splitext(file.filename)[1]}" # Keep original extension
        
        invoices_upload_dir_config = current_app.config.get('INVOICES_UPLOAD_DIR') # Absolute path from config
        if not invoices_upload_dir_config:
            log_error("INVOICES_UPLOAD_DIR is not configured.")
            return jsonify({'success': False, 'message': 'Server configuration error for invoice uploads.'}), 500
        
        if not os.path.exists(invoices_upload_dir_config):
            os.makedirs(invoices_upload_dir_config)
        
        file_path_abs = os.path.join(invoices_upload_dir_config, filename)
        file.save(file_path_abs)
        
        # Store relative path or just filename if INVOICES_UPLOAD_DIR is web-accessible
        # For DB, often just filename is stored, and path is constructed.
        # file_path_db = filename 

        try:
            # new_invoice = Invoice( # ORM
            #     user_id=int(user_id_str),
            #     order_id=int(request.form.get('order_id')) if request.form.get('order_id') else None,
            #     invoice_number=invoice_number,
            #     issue_date=datetime.datetime.strptime(issue_date_str, '%Y-%m-%d').date(),
            #     due_date=datetime.datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None,
            #     total_amount=float(total_amount_str),
            #     status='unpaid', 
            #     file_path=file_path_db, 
            #     is_uploaded=True
            # )
            # db.session.add(new_invoice) # ORM
            # db.session.commit() # ORM
            # new_invoice_id = new_invoice.id # ORM
            new_invoice_id = 1 # Mock
            
            AuditLogService.log_event(action="ADMIN_UPLOADED_INVOICE", target_type="INVOICE", target_id=new_invoice_id, details={"user_id": user_id_str, "filename": filename})
            return jsonify({'success': True, 'message': 'Invoice uploaded successfully', 'invoice_id': new_invoice_id, 'file_path': filename}), 201
        except Exception as e:
            # db.session.rollback() # ORM
            log_error(f"Error saving uploaded invoice to DB: {e}")
            if os.path.exists(file_path_abs): os.remove(file_path_abs) # Clean up
            AuditLogService.log_event(action="ADMIN_UPLOAD_INVOICE_DB_FAIL", details={"error": str(e)}, success=False)
            return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    else:
        return jsonify({'success': False, 'message': 'File type not allowed. Only PDF is accepted.'}), 400

# This route seems to duplicate /invoices/b2b (POST). Consolidating.
# @admin_api_bp.route('/invoices/generate', methods=['POST'])
# @admin_required
# def generate_and_save_invoice(): ...


@admin_api_bp.route('/invoices', methods=['GET']) # General invoice listing
@admin_required
def get_invoices():
    # Assuming Invoice model
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        user_id_filter = request.args.get('user_id', type=int)

        # query = Invoice.query # ORM
        # if user_id_filter: query = query.filter_by(user_id=user_id_filter) # ORM
        # invoices_pagination = query.order_by(Invoice.issue_date.desc()).paginate(page=page, per_page=per_page, error_out=False) # ORM
        # invoices_data = [] # ORM
        # for inv in invoices_pagination.items: # ORM
        #     inv_dict = inv.to_dict() # ORM
        #     inv_dict['user'] = inv.user.to_dict() if inv.user else None # ORM
        #     # Construct download URL based on how files are served
        #     if inv.file_path:
        #         # Example: inv_dict['download_url'] = url_for('professional_bp_routes.download_professional_invoice', invoice_id=inv.id, _external=False)
        #         # Or if served statically: inv_dict['download_url'] = get_static_url(inv.file_path, current_app.config.get('INVOICES_DIR_NAME_STATIC', 'invoices'))
        #         inv_dict['download_url'] = f"/download/invoice/{inv.id}" # Placeholder for a dedicated download route
        #     invoices_data.append(inv_dict) # ORM

        # --- Mocking ORM ---
        invoices_data = [{"id":1, "invoice_number":"INV2025-001", "user":{"email":"b2b@example.com"}, "status":"pending", "download_url":"#"}]
        invoices_pagination_total = 1
        invoices_pagination_pages = 1
         # --- End Mocking ---

        AuditLogService.log_event(action="ADMIN_VIEWED_INVOICES_LIST", details={"page": page, "user_id": user_id_filter})
        return jsonify({
            'success': True, 'invoices': invoices_data,
            'total': invoices_pagination_total, # invoices_pagination.total,
            'pages': invoices_pagination_pages, # invoices_pagination.pages,
            'current_page': page # invoices_pagination.page
        })
    except Exception as e:
        log_error(f"Error fetching invoices: {e}")
        AuditLogService.log_event(action="ADMIN_VIEW_INVOICES_ERROR", details={"error": str(e)}, success=False)
        return jsonify({'success': False, 'message': str(e)}), 500

# --- B2B User Management (Consolidated and using ORM style) ---
@admin_api_bp.route('/users/b2b/pending', methods=['GET'])
@admin_required
def get_pending_b2b_users():
    # Assuming User model with appropriate fields
    try:
        # pending_b2b_users = User.query.filter_by(user_type='b2b', status='pending_approval') \
        #                               .order_by(User.created_at.desc()).all() # ORM
        # users_data = [user.to_dict() for user in pending_b2b_users] # ORM (adjust to_dict as needed)
        
        # --- Mocking ORM ---
        users_data = [{"id": 2, "email":"pending@example.com", "company_name":"Pending Corp", "nom":"P.", "prenom":"User", "phone_number":"123", "created_at":datetime.datetime.utcnow().isoformat()}]
        # --- End Mocking ---

        AuditLogService.log_event(action="ADMIN_VIEWED_PENDING_B2B_USERS", target_type="ADMIN_PANEL")
        return jsonify({"success": True, "users": users_data}), 200
    except Exception as e:
        log_error(f"Erreur récupération utilisateurs B2B en attente: {e}")
        AuditLogService.log_event(action="ADMIN_VIEW_PENDING_B2B_ERROR", details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors de la récupération des utilisateurs en attente."}), 500

@admin_api_bp.route('/users/b2b/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_b2b_user(user_id):
    # user = User.query.filter_by(id=user_id, user_type='b2b').first() # ORM
    # --- Mocking ORM ---
    class MockUserB2B:
        def __init__(self, id, email, company_name, status): self.id=id; self.email=email; self.company_name=company_name; self.status=status
    _mock_user = MockUserB2B(user_id, "b2b@example.com", "B2B Company", "pending_approval")
    user = _mock_user if _mock_user.id == user_id else None
    # --- End Mocking ---

    if not user:
        AuditLogService.log_event(action="ADMIN_APPROVE_B2B_NOT_FOUND", target_type="USER", target_id=user_id, success=False)
        return jsonify({"success": False, "message": "Utilisateur B2B non trouvé."}), 404
    if user.status == 'active':
        AuditLogService.log_event(action="ADMIN_APPROVE_B2B_ALREADY_ACTIVE", target_type="USER", target_id=user_id, success=False)
        return jsonify({"success": False, "message": "Ce compte est déjà actif."}), 400

    user.status = 'active'
    try:
        # db.session.commit() # ORM
        email_sent = send_b2b_approval_email(user.email, user.company_name) # Ensure this function is implemented
        log_detail = {"email": user.email, "company": user.company_name}
        if email_sent:
            log_detail["email_notification_sent"] = True
            message = f"Compte B2B pour {user.company_name} approuvé. Email de notification envoyé."
        else:
            log_detail["email_notification_failed"] = True
            message = f"Compte B2B pour {user.company_name} approuvé, mais l'email de notification n'a pas pu être envoyé."
        
        AuditLogService.log_event(action="ADMIN_APPROVED_B2B_USER", target_type="USER", target_id=user_id, details=log_detail)
        return jsonify({"success": True, "message": message}), 200
    except Exception as e:
        # db.session.rollback() # ORM
        log_error(f"Erreur lors de l'approbation du compte B2B {user_id}: {e}")
        AuditLogService.log_event(action="ADMIN_APPROVE_B2B_ERROR", target_type="USER", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors de l'approbation."}), 500

@admin_api_bp.route('/users/b2b/<int:user_id>/status', methods=['PUT'])
@admin_required
def update_b2b_user_status(user_id):
    data = request.get_json()
    new_status = data.get('status')

    if not new_status or new_status not in ['active', 'suspended', 'pending_approval']:
        return jsonify({"success": False, "message": "Statut invalide fourni."}), 400

    # user = User.query.filter_by(id=user_id, user_type='b2b').first() # ORM
    # --- Mocking ORM ---
    class MockUserB2B:
        def __init__(self, id, email, company_name, status): self.id=id; self.email=email; self.company_name=company_name; self.status=status
    _mock_user = MockUserB2B(user_id, "b2b@example.com", "B2B Company", "pending_approval")
    user = _mock_user if _mock_user.id == user_id else None
    # --- End Mocking ---

    if not user:
        AuditLogService.log_event(action="ADMIN_UPDATE_B2B_STATUS_NOT_FOUND", target_type="USER", target_id=user_id, success=False)
        return jsonify({"success": False, "message": "Utilisateur B2B non trouvé."}), 404

    old_status = user.status
    if old_status == new_status:
        return jsonify({"success": True, "message": "Le statut est déjà à jour."}), 200

    user.status = new_status
    try:
        # db.session.commit() # ORM
        AuditLogService.log_event(
            action="ADMIN_UPDATED_B2B_USER_STATUS", target_type="USER", target_id=user_id,
            details={"email": user.email, "old_status": old_status, "new_status": new_status, "admin_id": g.current_user_id}
        )
        # Optionally send email if status changes significantly (e.g., suspended)
        return jsonify({"success": True, "message": f"Statut du compte pour {user.company_name} mis à jour à '{new_status}'."}), 200
    except Exception as e:
        # db.session.rollback() # ORM
        log_error(f"Erreur MAJ statut B2B user {user_id}: {e}")
        AuditLogService.log_event(action="ADMIN_UPDATE_B2B_STATUS_ERROR", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur lors de la mise à jour du statut."}), 500


# --- B2B Invoice Management (Consolidated and using ORM style) ---
@admin_api_bp.route('/invoices/b2b', methods=['POST'])
@admin_required
def create_b2b_invoice():
    data = request.form 
    user_id_str = data.get('user_id_for_creation')
    invoice_number = data.get('invoice_number_create')
    # ... (rest of data extraction as in the original snippet) ...
    client_company_name = data.get('client_company_name') 
    client_contact_person = data.get('client_contact_person') 
    client_address_lines_str = data.get('client_address_lines', '')
    client_vat_number = data.get('client_vat_number', '')
    discount_percentage_str = data.get('discount_percentage_create', "0")
    vat_rate_percent_str = data.get('vat_rate_percent_create', "20")
    invoice_date_str = data.get('invoice_date_create')
    invoice_due_date_str = data.get('invoice_due_date_create')


    if not all([user_id_str, invoice_number, invoice_date_str, invoice_due_date_str]):
        return jsonify({"success": False, "message": "Champs de facture requis manquants (user_id, number, dates)."}), 400
    
    try:
        user_id = int(user_id_str)
        invoice_date = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
        invoice_due_date = datetime.datetime.strptime(invoice_due_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "message": "Format ID utilisateur ou date invalide."}), 400

    items_data = []
    item_index = 0
    while True:
        desc = data.get(f'items[{item_index}][description]')
        if not desc: break
        try:
            qty = int(data.get(f'items[{item_index}][quantity]', 0))
            price = float(data.get(f'items[{item_index}][unit_price_ht]', 0.0))
            if qty <= 0 or price < 0: return jsonify({"success": False, "message": f"Qté/prix invalide pour article '{desc}'."}), 400
            items_data.append({"description": desc, "quantity": qty, "unit_price_ht": price, "total_ht": qty * price})
        except (ValueError, TypeError): return jsonify({"success": False, "message": f"Données d'article invalides pour '{desc}'."}), 400
        item_index += 1
    
    if not items_data: return jsonify({"success": False, "message": "Aucun article fourni pour la facture."}), 400

    calculated_totals = calculate_invoice_totals(items_data, discount_percentage_str, vat_rate_percent_str)

    # b2b_user = User.query.filter_by(id=user_id, user_type='b2b').first() # ORM
    # --- Mocking ORM ---
    class MockUserB2B:
        def __init__(self, id, company_name, prenom, nom): self.id=id; self.company_name=company_name; self.prenom=prenom; self.nom=nom;
    b2b_user = MockUserB2B(user_id, "B2B Client Inc.", "Client", "Contact") if user_id else None
    # --- End Mocking ---
    if not b2b_user: return jsonify({"success": False, "message": "Client B2B non trouvé."}), 404
    
    client_data_for_pdf = {
        "company_name": client_company_name or b2b_user.company_name,
        "contact_person": client_contact_person or f"{b2b_user.prenom} {b2b_user.nom}",
        "address_lines": [line.strip() for line in client_address_lines_str.split('\n') if line.strip()],
        "vat_number": client_vat_number
    }
    invoice_data_for_pdf = { "number": invoice_number, "date": invoice_date_str, "due_date": invoice_due_date_str, **calculated_totals }

    invoices_dir = current_app.config.get('INVOICES_UPLOAD_DIR')
    if not invoices_dir:
        log_error("INVOICES_UPLOAD_DIR n'est pas configuré."); return jsonify({"success": False, "message": "Config serveur erronée (factures)."}), 500
    os.makedirs(invoices_dir, exist_ok=True)
    
    safe_invoice_filename_base = secure_filename(f"Facture_{invoice_number.replace('/', '_')}") # Ensure no slashes from invoice_number
    pdf_filename = f"{safe_invoice_filename_base}.pdf"
    pdf_filepath = os.path.join(invoices_dir, pdf_filename)

    # Company info for PDF can be passed as a dictionary
    company_info_for_pdf_override = {}
    template_fields_map = { # Maps form field name to company_info key in generate_professional_invoice
        'template_company_name': 'name',
        'template_company_address_lines': 'address_lines', # Needs parsing if multiline from form
        'template_company_siret': 'siret',
        'template_company_vat_number': 'vat_number',
        'template_company_contact_info': 'contact_info',
        'template_invoice_footer_text': 'footer_text',
        'template_bank_details': 'bank_details',
        # 'template_company_logo_path': 'logo_path', # Handle logo path carefully
    }
    for form_key, info_key in template_fields_map.items():
        if data.get(form_key):
            if info_key == 'address_lines':
                company_info_for_pdf_override[info_key] = [line.strip() for line in data.get(form_key).split('\n') if line.strip()]
            else:
                company_info_for_pdf_override[info_key] = data.get(form_key)


    try:
        generate_invoice_pdf(pdf_filepath, client_data_for_pdf, invoice_data_for_pdf, items_data, company_info_override=company_info_for_pdf_override)
    except Exception as e:
        log_error(f"Erreur génération PDF facture {invoice_number}: {e}")
        return jsonify({"success": False, "message": f"Erreur génération PDF: {str(e)}"}), 500

    try:
        # new_invoice = Invoice( # ORM
        #     user_id=user_id, invoice_number=invoice_number, invoice_date=invoice_date, due_date=invoice_due_date,
        #     total_amount_ht=calculated_totals['total_ht_after_discount'], total_amount_ttc=calculated_totals['total_ttc'],
        #     vat_amount=calculated_totals['vat_amount'], discount_amount=calculated_totals['discount_amount_ht'],
        #     status='pending', file_path=pdf_filename, created_by_admin_id=g.current_user_id
        # )
        # db.session.add(new_invoice) # ORM
        # db.session.commit() # ORM
        # invoice_id = new_invoice.id # ORM
        invoice_id = 1 # Mock ID

        AuditLogService.log_event(action="ADMIN_CREATED_B2B_INVOICE", target_type="INVOICE", target_id=invoice_id, details={"user_id": user_id, "num": invoice_number})
        return jsonify({
            "success": True, "message": "Facture B2B créée et PDF généré.", "invoice_id": invoice_id,
            "pdf_filename": pdf_filename,
            "pdf_download_url": url_for('professional_bp_routes.download_professional_invoice', invoice_id=invoice_id, _external=False)
        }), 201
    except Exception as e: # Catch specific IntegrityError for duplicate invoice_number if constraint exists
        # db.session.rollback() # ORM
        log_error(f"Erreur sauvegarde facture B2B en DB: {e}")
        if os.path.exists(pdf_filepath): os.remove(pdf_filepath) # Cleanup
        AuditLogService.log_event(action="ADMIN_CREATE_B2B_INVOICE_DB_FAIL", details={"error": str(e)}, success=False)
        if "UNIQUE constraint" in str(e) or "Duplicate entry" in str(e): # Basic check for duplicate
             return jsonify({"success": False, "message": "Erreur: Numéro de facture déjà existant pour ce client."}), 409
        return jsonify({"success": False, "message": "Erreur serveur sauvegarde facture."}), 500


@admin_api_bp.route('/invoices/b2b/<int:invoice_id>/status', methods=['PUT'])
@admin_required
def update_b2b_invoice_status(invoice_id):
    data = request.get_json()
    new_status = data.get('status')
    paid_date_str = data.get('paid_date')

    valid_statuses = ['pending', 'paid', 'overdue', 'cancelled']
    if not new_status or new_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Statut invalide. Valides: {', '.join(valid_statuses)}."}), 400

    paid_date = None
    if new_status == 'paid':
        if paid_date_str:
            try: paid_date = datetime.datetime.strptime(paid_date_str, '%Y-%m-%d').date()
            except ValueError: return jsonify({"success": False, "message": "Format date paiement invalide (AAAA-MM-JJ)."}), 400
        else: paid_date = datetime.date.today()
    
    # invoice = Invoice.query.get(invoice_id) # ORM
    # --- Mocking ORM ---
    class MockInvoice:
        def __init__(self, id, status, user_id, invoice_number): self.id=id; self.status=status; self.user_id=user_id; self.invoice_number=invoice_number; self.paid_date=None
    _mock_invoice = MockInvoice(invoice_id, "pending", 1, "INV001")
    invoice = _mock_invoice if _mock_invoice.id == invoice_id else None
    # --- End Mocking ---

    if not invoice: return jsonify({"success": False, "message": "Facture non trouvée."}), 404

    old_status = invoice.status
    # Avoid update if status is same and it's not 'paid' being updated with a new date
    if old_status == new_status and not (new_status == 'paid' and invoice.paid_date != paid_date):
        return jsonify({"success": True, "message": "Statut facture déjà à jour."}), 200

    invoice.status = new_status
    invoice.paid_date = paid_date if new_status == 'paid' else None
    # invoice.last_updated_by_admin_id = g.current_user_id # ORM
    # invoice.last_updated_at = datetime.datetime.utcnow() # ORM
    
    try:
        # db.session.commit() # ORM
        AuditLogService.log_event(
            action="ADMIN_UPDATED_INVOICE_STATUS", target_type="INVOICE", target_id=invoice_id,
            details={"num": invoice.invoice_number, "user": invoice.user_id, "old": old_status, "new": new_status, "paid_on": str(paid_date) if paid_date else None}
        )
        return jsonify({"success": True, "message": f"Statut facture {invoice.invoice_number} mis à jour."}), 200
    except Exception as e:
        # db.session.rollback() # ORM
        log_error(f"Erreur MAJ statut facture {invoice_id}: {e}")
        AuditLogService.log_event(action="ADMIN_UPDATE_INVOICE_STATUS_DB_FAIL", target_id=invoice_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur MAJ statut."}), 500


@admin_api_bp.route('/invoices/b2b/for-user/<int:user_id>', methods=['GET'])
@admin_required
def get_b2b_invoices_for_user(user_id):
    # Assuming Invoice model
    try:
        # invoices = Invoice.query.filter_by(user_id=user_id).order_by(Invoice.invoice_date.desc()).all() # ORM
        # invoices_data = [inv.to_dict() for inv in invoices] # ORM (ensure to_dict includes status, paid_date, file_path)
        # --- Mocking ORM ---
        invoices_data = [{"id":1, "invoice_number":"INV001", "invoice_date": "2023-01-01", "due_date":"2023-02-01", "total_amount_ttc":100.0, "status":"pending", "paid_date":None, "file_path":"file.pdf"}]
        # --- End Mocking ---
        AuditLogService.log_event(action="ADMIN_VIEWED_B2B_USER_INVOICES", target_type="USER", target_id=user_id)
        return jsonify({"success": True, "invoices": invoices_data}), 200
    except Exception as e:
        log_error(f"Erreur récupération factures pour B2B user {user_id}: {e}")
        AuditLogService.log_event(action="ADMIN_VIEW_B2B_USER_INVOICES_ERROR", target_id=user_id, details={"error": str(e)}, success=False)
        return jsonify({"success": False, "message": "Erreur serveur."}), 500


@admin_api_bp.route('/settings/invoice-template', methods=['GET'])
@admin_required
def get_invoice_template_settings():
    # These should ideally be fetched from a persistent store (e.g., app_settings DB table)
    # or fallback to current_app.config defaults.
    settings = {
        "company_name": current_app.config.get('INVOICE_COMPANY_NAME', "Maison Trüvra SARL (Config Default)"),
        "company_address_lines": current_app.config.get('INVOICE_COMPANY_ADDRESS_LINES', ["123 Rue de la Truffe (Config)", "75001 Paris, France"]),
        "company_siret": current_app.config.get('INVOICE_COMPANY_SIRET', "SIRET: (Config)"),
        "company_vat_number": current_app.config.get('INVOICE_COMPANY_VAT_NUMBER', "TVA: (Config)"),
        "company_contact_info": current_app.config.get('INVOICE_COMPANY_CONTACT_INFO', "contact@config.com"),
        "company_logo_path": current_app.config.get('INVOICE_COMPANY_LOGO_PATH', "../website/image_6be700.png"), # Path for generate_professional_invoice.py
        "invoice_footer_text": current_app.config.get('INVOICE_FOOTER_TEXT', "Footer (Config)."),
        "bank_details": current_app.config.get('INVOICE_BANK_DETAILS', "Bank (Config)")
    }
    AuditLogService.log_event(action="ADMIN_VIEWED_INVOICE_TEMPLATE_SETTINGS", target_type="ADMIN_PANEL")
    return jsonify({"success": True, "settings": settings}), 200

@admin_api_bp.route('/settings/invoice-template', methods=['POST'])
@admin_required
def update_invoice_template_settings():
    data = request.get_json()
    # Here, you would validate and save these settings to your persistent store (e.g., app_settings DB table).
    # For each key in data, update the corresponding setting.
    # Example:
    # for key, value in data.items():
    #   if key in VALID_INVOICE_SETTINGS_KEYS_IN_DB:
    #       AppSetting.query.filter_by(setting_key=key).update({"setting_value": value})
    # db.session.commit()
    AuditLogService.log_event(action="ADMIN_UPDATED_INVOICE_TEMPLATE_SETTINGS", target_type="ADMIN_PANEL", details=data)
    return jsonify({"success": True, "message": "Paramètres du modèle de facture (conceptuellement) mis à jour."}), 200


