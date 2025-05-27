# backend/inventory/routes.py
from flask import Blueprint, request, jsonify, current_app
import sqlite3
from ..database import get_db_connection, record_stock_movement
from ..utils import jwt_required # Admin JWT protection
from ..audit_log_service import AuditLogService

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/admin/inventory')
audit_logger = AuditLogService()

def row_to_dict(cursor, row):
    return dict(zip([column[0] for column in cursor.description], row))

@inventory_bp.route('/movements', methods=['GET'])
@jwt_required
def get_inventory_movements():
    # Add pagination and filtering (e.g., by product_id, date range)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch movement details along with product/variant names
        cursor.execute("""
            SELECT 
                im.id, 
                im.product_id, 
                p.name_fr as product_name,
                im.variant_id,
                pwo.weight_grams || 'g' as variant_details, 
                im.movement_type, 
                im.quantity_changed, 
                im.reason, 
                im.timestamp
            FROM inventory_movements im
            JOIN products p ON im.product_id = p.id
            LEFT JOIN product_weight_options pwo ON im.variant_id = pwo.id
            ORDER BY im.timestamp DESC
        """)
        movements_rows = cursor.fetchall()
        movements = [row_to_dict(cursor, r) for r in movements_rows]
        conn.close()
        return jsonify(movements), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching inventory movements: {e}")
        return jsonify({"message": "Failed to fetch inventory movements", "error": str(e)}), 500

@inventory_bp.route('/stock_levels', methods=['GET'])
@jwt_required
def get_stock_levels():
    # Provides current stock levels for all products and their variants
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch simple product stocks
        cursor.execute("""
            SELECT p.id as product_id, p.name_fr as product_name, p.stock_quantity, p.product_type, NULL as variant_id, NULL as variant_details
            FROM products p
            WHERE p.product_type = 'simple'
        """)
        simple_stocks_rows = cursor.fetchall()
        
        # Fetch variable product variant stocks
        cursor.execute("""
            SELECT p.id as product_id, p.name_fr as product_name, pwo.stock_quantity, p.product_type, 
                   pwo.id as variant_id, pwo.weight_grams || 'g (' || IFNULL(pwo.sku, 'N/A') || ')' as variant_details
            FROM products p
            JOIN product_weight_options pwo ON p.id = pwo.product_id
            WHERE p.product_type = 'variable'
        """)
        variant_stocks_rows = cursor.fetchall()
        
        conn.close()
        
        all_stocks = [row_to_dict(cursor, r) for r in simple_stocks_rows] + \
                     [row_to_dict(cursor, r) for r in variant_stocks_rows]
        
        return jsonify(all_stocks), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching stock levels: {e}")
        return jsonify({"message": "Failed to fetch stock levels", "error": str(e)}), 500

@inventory_bp.route('/adjust_stock', methods=['POST'])
@jwt_required
def adjust_stock():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id') # Optional, for variable products
    new_stock_level = data.get('new_stock_level')
    reason = data.get('reason', 'Manual stock adjustment by admin')

    if product_id is None or new_stock_level is None:
        return jsonify({"message": "product_id and new_stock_level are required"}), 400
    
    try:
        new_stock_level = int(new_stock_level)
        if new_stock_level < 0:
            return jsonify({"message": "New stock level cannot be negative"}), 400
    except ValueError:
        return jsonify({"message": "new_stock_level must be an integer"}), 400

    conn = get_db_connection()
    conn.execute("BEGIN")
    try:
        cursor = conn.cursor()
        current_stock = 0
        
        if variant_id is not None: # Adjusting stock for a specific variant
            cursor.execute("SELECT stock_quantity FROM product_weight_options WHERE id = ? AND product_id = ?", (variant_id, product_id))
            variant_stock_row = cursor.fetchone()
            if not variant_stock_row:
                conn.rollback()
                return jsonify({"message": "Variant not found for the given product"}), 404
            current_stock = variant_stock_row['stock_quantity'] if variant_stock_row['stock_quantity'] is not None else 0
            
            quantity_changed = new_stock_level - current_stock
            cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE id = ?", (new_stock_level, variant_id))
            
            # Update overall product stock (sum of variants)
            cursor.execute("SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = ?", (product_id,))
            total_variant_stock = cursor.fetchone()[0]
            cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (total_variant_stock if total_variant_stock is not None else 0, product_id))

        else: # Adjusting stock for a simple product
            cursor.execute("SELECT stock_quantity, product_type FROM products WHERE id = ?", (product_id,))
            product_row = cursor.fetchone()
            if not product_row:
                conn.rollback()
                return jsonify({"message": "Product not found"}), 404
            if product_row['product_type'] == 'variable':
                conn.rollback()
                return jsonify({"message": "For variable products, please specify a variant_id to adjust stock."}), 400
            
            current_stock = product_row['stock_quantity'] if product_row['stock_quantity'] is not None else 0
            quantity_changed = new_stock_level - current_stock
            cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (new_stock_level, product_id))

        if quantity_changed != 0:
            movement_type = 'stock_increase_manual' if quantity_changed > 0 else 'stock_decrease_manual'
            record_stock_movement(conn, product_id, variant_id, movement_type, abs(quantity_changed), reason)
        
        conn.commit()
        audit_logger.log_event('stock_adjusted_manual', details={
            'product_id': product_id, 
            'variant_id': variant_id, 
            'old_stock': current_stock,
            'new_stock': new_stock_level,
            'reason': reason
        })
        return jsonify({"message": "Stock adjusted successfully", "product_id": product_id, "variant_id": variant_id, "new_stock_level": new_stock_level}), 200

    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error adjusting stock: {e}")
        return jsonify({"message": "Failed to adjust stock due to database error", "error": str(e)}), 500
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Unexpected error adjusting stock: {e}")
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()
