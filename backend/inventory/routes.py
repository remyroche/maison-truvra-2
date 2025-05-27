# backend/inventory/routes.py
from flask import Blueprint, request, jsonify, current_app
import sqlite3
from ..database import get_db_connection, record_stock_movement
from ..utils import jwt_required # Admin JWT protection
from ..audit_log_service import AuditLogService
from ..services.asset_service import AssetService # Import AssetService

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/admin/inventory')
audit_logger = AuditLogService()
asset_service = AssetService() # Instantiate AssetService

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
                im.timestamp,
                im.related_item_uid -- Include related_item_uid if you add it to inventory_movements
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
    # Provides current stock levels for all products and their variants (aggregate)
    # AND a count of 'in_stock' serialized items.
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch aggregate product stocks (from products and product_weight_options)
        # Simple products
        cursor.execute("""
            SELECT p.id as product_id, p.name_fr as product_name, p.stock_quantity as aggregate_stock, p.product_type, 
                   NULL as variant_id, NULL as variant_details
            FROM products p
            WHERE p.product_type = 'simple'
        """)
        simple_stocks_rows = cursor.fetchall()
        
        # Variable product variant stocks
        cursor.execute("""
            SELECT p.id as product_id, p.name_fr as product_name, pwo.stock_quantity as aggregate_stock, p.product_type, 
                   pwo.id as variant_id, pwo.weight_grams || 'g (' || IFNULL(pwo.sku, 'N/A') || ')' as variant_details
            FROM products p
            JOIN product_weight_options pwo ON p.id = pwo.product_id
            WHERE p.product_type = 'variable'
        """)
        variant_stocks_rows = cursor.fetchall()
        
        aggregate_stocks = [row_to_dict(cursor, r) for r in simple_stocks_rows] + \
                           [row_to_dict(cursor, r) for r in variant_stocks_rows]

        # Fetch count of 'in_stock' serialized items per product/variant
        cursor.execute("""
            SELECT product_id, variant_id, COUNT(item_uid) as serialized_in_stock_count
            FROM serialized_inventory_items
            WHERE status = 'in_stock'
            GROUP BY product_id, variant_id
        """)
        serialized_counts_rows = cursor.fetchall()
        serialized_counts_map = {}
        for row_tuple in serialized_counts_rows:
            row = row_to_dict(cursor, row_tuple)
            key = (row['product_id'], row['variant_id'])
            serialized_counts_map[key] = row['serialized_in_stock_count']

        # Combine aggregate stock with serialized counts
        for stock_item in aggregate_stocks:
            key = (stock_item['product_id'], stock_item['variant_id'])
            stock_item['serialized_in_stock_count'] = serialized_counts_map.get(key, 0)
            
        conn.close()
        return jsonify(aggregate_stocks), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching stock levels: {e}")
        return jsonify({"message": "Failed to fetch stock levels", "error": str(e)}), 500

@inventory_bp.route('/receive_serialized_stock', methods=['POST'])
@jwt_required
def receive_serialized_stock():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id') # Optional
    quantity_received = data.get('quantity_received')
    lot_number = data.get('lot_number') # Optional
    # Item-specific details if they vary per item in the batch, otherwise use product defaults
    date_conditionnement_batch = data.get('date_conditionnement') # For the batch
    ddm_batch = data.get('ddm') # For the batch

    if not product_id or quantity_received is None:
        return jsonify({"message": "product_id and quantity_received are required"}), 400
    try:
        quantity_received = int(quantity_received)
        if quantity_received <= 0:
            return jsonify({"message": "quantity_received must be positive"}), 400
    except ValueError:
        return jsonify({"message": "quantity_received must be an integer"}), 400

    conn = get_db_connection()
    conn.execute("BEGIN")
    try:
        cursor = conn.cursor()
        # Fetch product details to enrich item_details for passport/label
        base_product_details = {}
        if variant_id:
            cursor.execute("""
                SELECT p.name_fr, p.description_fr as ingredients, p.category_id, 
                       pwo.weight_grams, pwo.price, c.name_fr as category_name
                FROM products p 
                JOIN product_weight_options pwo ON p.id = pwo.product_id
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = ? AND pwo.id = ?
            """, (product_id, variant_id))
            base_product_details = cursor.fetchone()
        else: # Simple product
            cursor.execute("""
                SELECT p.name_fr, p.description_fr as ingredients, p.category_id, 
                       p.base_price as price, NULL as weight_grams, c.name_fr as category_name 
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = ? AND p.product_type = 'simple'
            """, (product_id,))
            base_product_details = cursor.fetchone()

        if not base_product_details:
            conn.rollback()
            return jsonify({"message": "Product or Variant not found"}), 404
        
        base_product_details = dict(base_product_details) # Convert from sqlite3.Row

        generated_items_info = []
        for _ in range(quantity_received):
            item_uid = asset_service.generate_item_uid()
            
            # Construct the public URL for the passport page (scanned from QR)
            # This URL will be handled by a new public-facing route e.g. /passport/<item_uid>
            item_passport_public_url = f"{current_app.config.get('FRONTEND_URL', 'http://127.0.0.1:8000')}/passport/{item_uid}"

            qr_code_fs_path, qr_code_asset_url = asset_service.generate_item_qr_code(item_uid, item_passport_public_url)
            if not qr_code_fs_path: # Check if QR generation failed
                # Decide on error handling: stop all, or skip this item?
                current_app.logger.error(f"Failed to generate QR code for a new item of product {product_id}. Skipping this item.")
                # For now, we might skip or raise an error to stop the batch.
                # Let's assume we want to stop if a critical asset fails.
                raise Exception(f"QR code generation failed for an item of product {product_id}")


            item_details_for_passport = {
                **base_product_details, # Spread common product details
                "item_uid": item_uid,
                "product_id": product_id, # For AssetService if needed
                "lot_number": lot_number,
                "date_conditionnement": date_conditionnement_batch, # Use batch date or allow per-item
                "ddm": ddm_batch, # Use batch DDM or allow per-item
                # Add other details like truffle_species if available in base_product_details
                "truffle_species": base_product_details.get('category_name', 'N/A'), # Example
                "product_id_display": f"MT{product_id:05d}" # Product type display ID
            }
            passport_asset_url = asset_service.generate_item_passport(item_details_for_passport)
            if not passport_asset_url:
                 raise Exception(f"Passport generation failed for item UID {item_uid}")

            # Optional: Generate item-specific label (if labels are unique per item)
            # For now, labels are more product-type based, but QR on label should be item-specific
            # label_asset_url = asset_service.generate_product_label(item_details_for_passport, qr_code_fs_path)


            # Insert into serialized_inventory_items
            cursor.execute("""
                INSERT INTO serialized_inventory_items 
                (item_uid, product_id, variant_id, lot_number, status, 
                 date_conditionnement, ddm, passport_html_url, qr_code_url)
                VALUES (?, ?, ?, ?, 'in_stock', ?, ?, ?, ?)
            """, (item_uid, product_id, variant_id, lot_number, 
                  date_conditionnement_batch, ddm_batch, item_passport_public_url, # Store public URL for passport
                  qr_code_asset_url # Store asset URL for QR image
                 ))
            generated_items_info.append({
                "item_uid": item_uid,
                "passport_url": item_passport_public_url, # The URL encoded in QR
                "qr_code_image_url": qr_code_asset_url # URL to the QR image file itself
            })

        # Update aggregate stock counts
        if variant_id:
            cursor.execute("UPDATE product_weight_options SET stock_quantity = stock_quantity + ? WHERE id = ?",
                           (quantity_received, variant_id))
            # Update parent product's total stock (sum of variants)
            cursor.execute("""
                UPDATE products SET stock_quantity = (SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = ?)
                WHERE id = ?
            """, (product_id, product_id))
        else: # Simple product
            cursor.execute("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                           (quantity_received, product_id))
        
        # Record one aggregate stock movement for the batch received
        # The `record_stock_movement` might need adjustment if it expects variant_id for all movements
        # or if it should log per item_uid. For receiving, batch is often fine.
        record_stock_movement(conn, product_id, variant_id, 
                              'stock_received_serialized', quantity_received, 
                              f"Received {quantity_received} serialized items. Lot: {lot_number or 'N/A'}")
        
        conn.commit()
        audit_logger.log_event('serialized_stock_received', details={
            'product_id': product_id, 'variant_id': variant_id, 
            'quantity_received': quantity_received, 'lot_number': lot_number,
            'num_items_processed': len(generated_items_info)
        })
        return jsonify({
            "message": f"{len(generated_items_info)} serialized items received and processed successfully.",
            "items": generated_items_info
        }), 201

    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error receiving serialized stock: {e}", exc_info=True)
        return jsonify({"message": "Failed to receive stock due to database error", "error": str(e)}), 500
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Unexpected error receiving serialized stock: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route('/adjust_stock', methods=['POST'])
@jwt_required
def adjust_stock():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id') # Optional, for variable products
    new_stock_level = data.get('new_stock_level') # This refers to aggregate stock
    reason = data.get('reason', 'Manual stock adjustment by admin')

    # This route adjusts AGGREGATE stock. For serialized items, status changes (e.g. 'damaged')
    # would be handled differently, perhaps via a separate endpoint or by updating item status directly.
    # This current endpoint is less relevant for serialized items unless you're reconciling aggregate counts.

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
        
        if variant_id is not None: 
            cursor.execute("SELECT stock_quantity FROM product_weight_options WHERE id = ? AND product_id = ?", (variant_id, product_id))
            variant_stock_row = cursor.fetchone()
            if not variant_stock_row:
                conn.rollback(); return jsonify({"message": "Variant not found"}), 404
            current_stock = variant_stock_row['stock_quantity'] or 0
            quantity_changed = new_stock_level - current_stock
            cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE id = ?", (new_stock_level, variant_id))
            cursor.execute("UPDATE products SET stock_quantity = (SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = ?) WHERE id = ?", (product_id, product_id))
        else: 
            cursor.execute("SELECT stock_quantity, product_type FROM products WHERE id = ?", (product_id,))
            product_row = cursor.fetchone()
            if not product_row:
                conn.rollback(); return jsonify({"message": "Product not found"}), 404
            if product_row['product_type'] == 'variable':
                conn.rollback(); return jsonify({"message": "For variable products, specify variant_id for aggregate adjustment."}), 400
            current_stock = product_row['stock_quantity'] or 0
            quantity_changed = new_stock_level - current_stock
            cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (new_stock_level, product_id))

        if quantity_changed != 0:
            movement_type = 'stock_adj_increase' if quantity_changed > 0 else 'stock_adj_decrease'
            record_stock_movement(conn, product_id, variant_id, movement_type, abs(quantity_changed), reason)
        
        conn.commit()
        audit_logger.log_event('aggregate_stock_adjusted', details={'product_id': product_id, 'variant_id': variant_id, 'old_stock': current_stock, 'new_stock': new_stock_level, 'reason': reason})
        return jsonify({"message": "Aggregate stock adjusted successfully"}), 200
    except sqlite3.Error as e:
        conn.rollback(); current_app.logger.error(f"DB error adjusting stock: {e}"); return jsonify({"message": "DB error", "error": str(e)}), 500
    except Exception as e:
        conn.rollback(); current_app.logger.error(f"Unexpected error adjusting stock: {e}"); return jsonify({"message": "Unexpected error", "error": str(e)}), 500
    finally:
        if conn: conn.close()

# New endpoint to list serialized items
@inventory_bp.route('/serialized_items', methods=['GET'])
@jwt_required
def get_serialized_items():
    # Add filters: product_id, variant_id, status, lot_number
    product_id_filter = request.args.get('product_id', type=int)
    status_filter = request.args.get('status')
    
    query = "SELECT sii.*, p.name_fr as product_name FROM serialized_inventory_items sii JOIN products p ON sii.product_id = p.id"
    filters = []
    params = {}

    if product_id_filter:
        filters.append("sii.product_id = :product_id")
        params['product_id'] = product_id_filter
    if status_filter:
        filters.append("sii.status = :status")
        params['status'] = status_filter
    
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY sii.date_added_to_inventory DESC"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        items_rows = cursor.fetchall()
        items = [row_to_dict(cursor, r) for r in items_rows]
        conn.close()
        return jsonify(items), 200
    except sqlite3.Error as e:
        current_app.logger.error(f"Database error fetching serialized items: {e}")
        return jsonify({"message": "Failed to fetch serialized items", "error": str(e)}), 500
