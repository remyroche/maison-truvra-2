# backend/orders/routes.py
from flask import Blueprint, request, jsonify, current_app
import sqlite3
import stripe # Assuming Stripe will be used eventually
import datetime
from ..database import get_db_connection, record_stock_movement # Import record_stock_movement
from ..utils import user_jwt_required, send_email_alert # For user authentication and email
from ..audit_log_service import AuditLogService

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')
audit_logger = AuditLogService()

# Configure Stripe (from app config) - payment is out of scope for this update
# stripe.api_key = current_app.config['STRIPE_SECRET_KEY']


@orders_bp.route('/create', methods=['POST'])
@user_jwt_required # Protect this route, get current_user_id
def create_order(current_user_id, current_user_role): # current_user_id from decorator
    data = request.get_json()
    # Required data: items, shipping_address_id, billing_address_id, (payment_intent_id if Stripe)
    # items: [{"product_id": int, "variant_id": int (optional), "quantity": int}]
    
    items = data.get('items')
    shipping_address_id = data.get('shipping_address_id')
    billing_address_id = data.get('billing_address_id')
    # payment_method_id = data.get('payment_method_id') # For Stripe

    if not items or not shipping_address_id or not billing_address_id: # or not payment_method_id:
        return jsonify({"message": "Missing required order information (items, addresses)"}), 400

    conn = get_db_connection()
    conn.execute("BEGIN") # Start transaction
    try:
        cursor = conn.cursor()
        total_amount = 0
        order_items_details = [] # To store details for insertion and email

        # 1. Validate items and calculate total_amount, check stock
        for item_req in items:
            product_id = item_req.get('product_id')
            variant_id = item_req.get('variant_id') # Can be None for simple products
            quantity = item_req.get('quantity')

            if not product_id or not quantity or quantity <= 0:
                raise ValueError("Invalid item data (product_id, quantity).")

            if variant_id:
                cursor.execute("""
                    SELECT p.name_fr, p.name_en, pwo.price, pwo.stock_quantity, pwo.weight_grams 
                    FROM product_weight_options pwo
                    JOIN products p ON pwo.product_id = p.id
                    WHERE pwo.id = ? AND pwo.product_id = ?
                """, (variant_id, product_id))
                db_item = cursor.fetchone()
                if not db_item:
                    raise ValueError(f"Variant ID {variant_id} for product ID {product_id} not found.")
                item_name = f"{db_item['name_fr']} ({db_item['weight_grams']}g)"
            else: # Simple product
                cursor.execute("SELECT name_fr, name_en, base_price, stock_quantity FROM products WHERE id = ?", (product_id,))
                db_item = cursor.fetchone()
                if not db_item:
                    raise ValueError(f"Product ID {product_id} not found.")
                item_name = db_item['name_fr']
            
            price_at_purchase = db_item['price'] if variant_id else db_item['base_price']
            if price_at_purchase is None: # Should not happen if data is clean
                 raise ValueError(f"Price not found for product/variant ID {product_id}/{variant_id}.")

            current_stock = db_item['stock_quantity'] if db_item['stock_quantity'] is not None else 0
            if current_stock < quantity:
                raise ValueError(f"Not enough stock for {item_name}. Available: {current_stock}, Requested: {quantity}")

            total_amount += price_at_purchase * quantity
            order_items_details.append({
                "product_id": product_id, "variant_id": variant_id, "quantity": quantity,
                "price_at_purchase": price_at_purchase, "name_fr_at_purchase": item_name
            })
        
        # 2. Add shipping, taxes if applicable (simplified for now)
        # shipping_cost = 0 # Calculate based on address/cart total
        # if total_amount > 0 and total_amount < current_app.config.get('FREE_SHIPPING_THRESHOLD', 75):
        #     shipping_cost = current_app.config.get('DEFAULT_SHIPPING_COST', 7.50)
        # total_amount += shipping_cost
        # tax_amount = total_amount * current_app.config.get('VAT_RATE', 0.20) # Example VAT
        # total_amount += tax_amount
        # For now, total_amount is just sum of item prices. Implement full calculation later.

        # 3. Fetch addresses
        cursor.execute("SELECT * FROM addresses WHERE id = ? AND user_id = ?", (shipping_address_id, current_user_id))
        shipping_addr = cursor.fetchone()
        cursor.execute("SELECT * FROM addresses WHERE id = ? AND user_id = ?", (billing_address_id, current_user_id))
        billing_addr = cursor.fetchone()

        if not shipping_addr or not billing_addr:
            raise ValueError("Invalid shipping or billing address ID, or address does not belong to user.")

        # 4. Create Order Record
        # Payment processing would happen here. For now, assume payment is successful.
        # payment_status = 'succeeded' # Placeholder
        order_status = 'processing' # Or 'pending_payment' if payment is separate step

        cursor.execute("""
            INSERT INTO orders (user_id, order_date, total_amount, status, 
                                shipping_address_line1, shipping_address_line2, shipping_city, shipping_postal_code, shipping_country,
                                billing_address_line1, billing_address_line2, billing_city, billing_postal_code, billing_country)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (current_user_id, total_amount, order_status,
              shipping_addr['address_line1'], shipping_addr.get('address_line2'), shipping_addr['city'], shipping_addr['postal_code'], shipping_addr['country'],
              billing_addr['address_line1'], billing_addr.get('address_line2'), billing_addr['city'], billing_addr['postal_code'], billing_addr['country']
              ))
        order_id = cursor.lastrowid

        # 5. Create Order Items and Update Stock
        for item_detail in order_items_details:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, variant_id, quantity, price_at_purchase, name_fr_at_purchase)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (order_id, item_detail['product_id'], item_detail.get('variant_id'), item_detail['quantity'], 
                  item_detail['price_at_purchase'], item_detail['name_fr_at_purchase']))
            
            # Update stock
            if item_detail.get('variant_id'):
                cursor.execute("UPDATE product_weight_options SET stock_quantity = stock_quantity - ? WHERE id = ?",
                               (item_detail['quantity'], item_detail['variant_id']))
                # Update parent product's total stock (sum of variants)
                cursor.execute("""
                    UPDATE products SET stock_quantity = (SELECT SUM(stock_quantity) FROM product_weight_options WHERE product_id = ?)
                    WHERE id = ?
                """, (item_detail['product_id'], item_detail['product_id']))
            else: # Simple product
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                               (item_detail['quantity'], item_detail['product_id']))
            
            # Record stock movement
            record_stock_movement(conn, item_detail['product_id'], item_detail.get('variant_id'), 
                                  'sale', item_detail['quantity'], f"Order ID: {order_id}")
        
        conn.commit()
        audit_logger.log_event('order_created', user_id=current_user_id, details={'order_id': order_id, 'total_amount': total_amount})
        
        # Send order confirmation email
        try:
            user_email_cursor = conn.cursor()
            user_email_cursor.execute("SELECT email, first_name FROM users WHERE id = ?", (current_user_id,))
            user_info = user_email_cursor.fetchone()
            if user_info:
                email_subject = f"Confirmation de votre commande #{order_id} - Maison Trüvra"
                email_body_text = f"Bonjour {user_info['first_name']},\n\nMerci pour votre commande #{order_id} d'un montant de {total_amount:.2f} €.\n"
                email_body_text += "Détails de la commande:\n"
                for item in order_items_details:
                    email_body_text += f"- {item['name_fr_at_purchase']} x {item['quantity']} @ {item['price_at_purchase']:.2f} €\n"
                email_body_text += f"\nStatut: {order_status}\n\nCordialement,\nL'équipe Maison Trüvra"
                # Add HTML version later
                send_email_alert(email_subject, email_body_text, user_info['email'])
        except Exception as email_e:
            current_app.logger.error(f"Failed to send order confirmation email for order {order_id}: {email_e}")


        return jsonify({"message": "Order created successfully", "order_id": order_id, "total_amount": total_amount, "status": order_status}), 201

    except ValueError as ve: # For stock issues or invalid data
        conn.rollback()
        current_app.logger.warning(f"Order creation validation error: {ve}")
        return jsonify({"message": str(ve)}), 400
    except sqlite3.Error as e:
        conn.rollback()
        current_app.logger.error(f"Database error creating order: {e}")
        return jsonify({"message": "Failed to create order due to database error", "error": str(e)}), 500
    except Exception as e: # Catch-all for other unexpected errors
        conn.rollback()
        current_app.logger.error(f"Unexpected error creating order: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred while creating the order.", "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


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
            order_row = dict(order_row_tuple) # Convert from sqlite3.Row to dict
            # Fetch items for each order
            items_cursor = conn.cursor() # Use a new cursor for nested query
            items_cursor.execute("""
                SELECT product_id, variant_id, quantity, price_at_purchase, name_fr_at_purchase
                FROM order_items 
                WHERE order_id = ?
            """, (order_row['id'],))
            items_rows = items_cursor.fetchall()
            order_row['items'] = [dict(item_row) for item_row in items_rows]
            orders_history.append(order_row)
            
        conn.close()
        return jsonify(orders_history), 200
    except sqlite3.Error as e:
        conn.close()
        current_app.logger.error(f"Database error fetching order history for user {current_user_id}: {e}")
        return jsonify({"message": "Failed to fetch order history", "error": str(e)}), 500

