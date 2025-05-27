# backend/orders/routes.py
from flask import Blueprint, request, jsonify, current_app
import sqlite3
# import stripe # Assuming Stripe will be used eventually
import datetime
from ..database import get_db_connection, record_stock_movement 
from ..utils import user_jwt_required, send_email_alert 
from ..audit_log_service import AuditLogService

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')
audit_logger = AuditLogService()

# stripe.api_key = current_app.config['STRIPE_SECRET_KEY'] # If using Stripe

def row_to_dict(cursor, row):
    if row:
        return dict(zip([column[0] for column in cursor.description], row))
    return {}

@orders_bp.route('/create', methods=['POST'])
@user_jwt_required 
def create_order(current_user_id, current_user_role): 
    data = request.get_json()
    
    requested_items_from_cart = data.get('items') # items: [{"product_id": int, "variant_id": int (optional), "quantity": int}]
    shipping_address_id = data.get('shipping_address_id')
    billing_address_id = data.get('billing_address_id')
    
    if not requested_items_from_cart or not shipping_address_id or not billing_address_id:
        return jsonify({"message": "Missing required order information (items, addresses)"}), 400

    conn = get_db_connection()
    conn.execute("BEGIN")
    try:
        cursor = conn.cursor()
        total_order_amount = 0.0
        order_items_to_insert_in_db = [] # Stores details for order_items table, including allocated item_uid
        allocated_item_uids_for_status_update = [] # Keep track of UIDs to mark as 'sold'

        # 1. Allocate Serialized Items and Calculate Price
        for req_item_from_cart in requested_items_from_cart:
            product_id = req_item_from_cart.get('product_id')
            variant_id = req_item_from_cart.get('variant_id') # Can be None
            quantity_requested_for_product_line = int(req_item_from_cart.get('quantity', 0))

            if not product_id or quantity_requested_for_product_line <= 0:
                raise ValueError(f"Invalid item data for product ID {product_id} (quantity).")

            # Find available serialized items for this product/variant line
            query_serialized_items = """
                SELECT sii.item_uid, p.name_fr, 
                       COALESCE(pwo.price, p.base_price) as price_at_purchase, -- Use variant price if available, else base product price
                       pwo.weight_grams
                FROM serialized_inventory_items sii
                JOIN products p ON sii.product_id = p.id
                LEFT JOIN product_weight_options pwo ON sii.variant_id = pwo.id
                WHERE sii.product_id = ? AND sii.status = 'in_stock'
            """
            params_serialized_items = [product_id]
            if variant_id:
                query_serialized_items += " AND sii.variant_id = ?"
                params_serialized_items.append(variant_id)
            else: # Simple product
                query_serialized_items += " AND sii.variant_id IS NULL"
            
            query_serialized_items += " LIMIT ?" # Limit by quantity requested for this line
            params_serialized_items.append(quantity_requested_for_product_line)
            
            cursor.execute(query_serialized_items, tuple(params_serialized_items))
            available_physical_items = [row_to_dict(cursor, r) for r in cursor.fetchall()]


            if len(available_physical_items) < quantity_requested_for_product_line:
                name_for_error_msg = available_physical_items[0]['name_fr'] if available_physical_items else f"Product ID {product_id}"
                raise ValueError(f"Not enough stock for {name_for_error_msg}. Requested: {quantity_requested_for_product_line}, Available: {len(available_physical_items)}")

            # Allocate each physical item and add to order_items_to_insert_in_db
            for allocated_physical_item in available_physical_items:
                item_uid = allocated_physical_item['item_uid']
                price_at_purchase = float(allocated_physical_item['price_at_purchase'])
                
                if price_at_purchase is None: # Should be caught by COALESCE, but double check
                    raise ValueError(f"Price not found for allocated item UID {item_uid}.")

                item_name_at_purchase = allocated_physical_item['name_fr']
                if variant_id and allocated_physical_item.get('weight_grams'):
                    item_name_at_purchase += f" ({allocated_physical_item['weight_grams']}g)"
                
                total_order_amount += price_at_purchase 
                
                order_items_to_insert_in_db.append({
                    "product_id": product_id, 
                    "variant_id": variant_id, 
                    "item_uid": item_uid, 
                    "quantity": 1, # Each serialized item is quantity 1 in order_items
                    "price_at_purchase": price_at_purchase, 
                    "name_fr_at_purchase": item_name_at_purchase
                })
                allocated_item_uids_for_status_update.append(item_uid)
                # Mark item as 'allocated' to prevent double-selling during this transaction
                cursor.execute("UPDATE serialized_inventory_items SET status = 'allocated', updated_at = CURRENT_TIMESTAMP WHERE item_uid = ?", (item_uid,))
        
        if not order_items_to_insert_in_db: # Should not happen if validation passes, but good check
            raise ValueError("No items were allocated for the order.")

        # 2. Fetch addresses
        cursor.execute("SELECT * FROM addresses WHERE id = ? AND user_id = ?", (shipping_address_id, current_user_id))
        shipping_addr = row_to_dict(cursor, cursor.fetchone())
        cursor.execute("SELECT * FROM addresses WHERE id = ? AND user_id = ?", (billing_address_id, current_user_id))
        billing_addr = row_to_dict(cursor, cursor.fetchone())
        if not shipping_addr or not billing_addr:
            raise ValueError("Invalid shipping or billing address.")

        # 3. Create Order Record
        order_status = 'processing' # Assume payment is handled or will be updated
        cursor.execute("""
            INSERT INTO orders (user_id, order_date, total_amount, status, 
                                shipping_address_line1, shipping_address_line2, shipping_city, shipping_postal_code, shipping_country,
                                billing_address_line1, billing_address_line2, billing_city, billing_postal_code, billing_country)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (current_user_id, total_order_amount, order_status,
              shipping_addr.get('address_line1'), shipping_addr.get('address_line2'), shipping_addr.get('city'), shipping_addr.get('postal_code'), shipping_addr.get('country'),
              billing_addr.get('address_line1'), billing_addr.get('address_line2'), billing_addr.get('city'), billing_addr.get('postal_code'), billing_addr.get('country')))
        order_id = cursor.lastrowid

        # 4. Create Order Items and Finalize Stock Update for Serialized Items
        for item_detail_for_db in order_items_to_insert_in_db:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, variant_id, item_uid, quantity, price_at_purchase, name_fr_at_purchase)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (order_id, item_detail_for_db['product_id'], item_detail_for_db.get('variant_id'), item_detail_for_db['item_uid'],
                  item_detail_for_db['quantity'], item_detail_for_db['price_at_purchase'], item_detail_for_db['name_fr_at_purchase']))
            
            # Update serialized item status to 'sold' (was 'allocated')
            cursor.execute("UPDATE serialized_inventory_items SET status = 'sold', updated_at = CURRENT_TIMESTAMP WHERE item_uid = ?", (item_detail_for_db['item_uid'],))
            
            # Update aggregate stock counts in products/product_weight_options
            if item_detail_for_db.get('variant_id'):
                cursor.execute("UPDATE product_weight_options SET stock_quantity = stock_quantity - 1 WHERE id = ?", (item_detail_for_db['variant_id'],))
                # Also update parent product's aggregate stock_quantity
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - 1 WHERE id = ?", (item_detail_for_db['product_id'],))
            else: # Simple product
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - 1 WHERE id = ?", (item_detail_for_db['product_id'],))
            
            record_stock_movement(conn, item_detail_for_db['product_id'], item_detail_for_db.get('variant_id'), 
                                  'sale_serialized', 1, f"Order ID: {order_id}", related_item_uid=item_detail_for_db['item_uid'])
        
        conn.commit()
        audit_logger.log_event('order_created_serialized', user_id=current_user_id, details={'order_id': order_id, 'total_amount': total_order_amount, 'num_items': len(order_items_to_insert_in_db)})
        
        try:
            user_email_cursor = get_db_connection().cursor() # Use a new connection/cursor for safety if needed, or ensure main conn is fine
            user_email_cursor.execute("SELECT email, first_name FROM users WHERE id = ?", (current_user_id,))
            user_info = row_to_dict(user_email_cursor, user_email_cursor.fetchone())
            user_email_cursor.connection.close() # Close the new cursor's connection
            if user_info and user_info.get('email'):
                email_subject = f"Confirmation de votre commande #{order_id} - Maison Trüvra"
                email_body_text = f"Bonjour {user_info.get('first_name', 'Client')},\n\nMerci pour votre commande #{order_id} d'un montant de {total_order_amount:.2f} €.\n"
                email_body_text += "Articles commandés:\n"
                for item in order_items_to_insert_in_db:
                    email_body_text += f"- {item['name_fr_at_purchase']} (UID: {item['item_uid']}) x {item['quantity']} @ {item['price_at_purchase']:.2f} €\n"
                email_body_text += f"\nStatut: {order_status}\n\nCordialement,\nL'équipe Maison Trüvra"
                send_email_alert(email_subject, email_body_text, user_info['email'])
        except Exception as email_e:
            current_app.logger.error(f"Failed to send order confirmation email for order {order_id}: {email_e}", exc_info=True)

        return jsonify({"message": "Order created successfully", "order_id": order_id, "total_amount": total_order_amount, "status": order_status}), 201

    except ValueError as ve: 
        conn.rollback()
        current_app.logger.warning(f"Order creation validation error: {ve}")
        return jsonify({"message": str(ve)}), 400
    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error creating order: {e}", exc_info=True)
        return jsonify({"message": "Failed to create order due to database error", "error": str(e)}), 500
    except Exception as e: 
        conn.rollback()
        current_app.logger.error(f"Unexpected error creating order: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred while creating the order.", "error": str(e)}), 500
    finally:
        if conn: conn.close()


@orders_bp.route('/history', methods=['GET'])
@user_jwt_required
def get_order_history(current_user_id, current_user_role):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, order_date, total_amount, status 
            FROM orders 
            WHERE user_id = ? 
            ORDER BY order_date DESC
        """, (current_user_id,))
        orders_rows = cursor.fetchall()
        
        orders_history = []
        for order_row_tuple in orders_rows:
            order_row = row_to_dict(cursor, order_row_tuple)
            if not order_row: continue # Should not happen if orders_rows is populated

            items_cursor = conn.cursor() # Use a new cursor for nested query
            items_cursor.execute("""
                SELECT product_id, variant_id, item_uid, quantity, price_at_purchase, name_fr_at_purchase
                FROM order_items 
                WHERE order_id = ?
            """, (order_row['id'],))
            items_rows_tuples = items_cursor.fetchall()
            order_row['items'] = [row_to_dict(items_cursor, item_row_tuple) for item_row_tuple in items_rows_tuples]
            orders_history.append(order_row)
            
        conn.close()
        return jsonify(orders_history), 200
    except sqlite3.Error as e:
        conn.close()
        current_app.logger.error(f"DB error fetching order history for user {current_user_id}: {e}", exc_info=True)
        return jsonify({"message": "Failed to fetch order history", "error": str(e)}), 500
