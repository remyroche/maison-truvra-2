# backend/database.py
import sqlite3
import click
from flask import current_app, g # g is a context-local object for request lifetime

def get_db_connection():
    """Establishes a new database connection or returns an existing one for the current app context."""
    if 'db_conn' not in g:
        db_path = current_app.config['DATABASE_NAME']
        # Ensure the directory for the database exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            current_app.logger.info(f"Created database directory: {db_dir}")

        g.db_conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db_conn.row_factory = sqlite3.Row # Access columns by name
        current_app.logger.debug(f"Database connection established to {db_path}")
    return g.db_conn

def close_db_connection(e=None):
    """Closes the database connection at the end of the request."""
    db_conn = g.pop('db_conn', None)
    if db_conn is not None:
        db_conn.close()
        current_app.logger.debug("Database connection closed.")

def init_db_schema():
    """Initializes the database schema based on schema.sql."""
    db = get_db_connection()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    try:
        with open(schema_path, 'r') as f:
            db.executescript(f.read())
        db.commit()
        current_app.logger.info("Database schema initialized successfully from schema.sql.")
    except FileNotFoundError:
        current_app.logger.error(f"schema.sql not found at {schema_path}. Database not initialized.")
    except sqlite3.Error as e:
        current_app.logger.error(f"Error initializing database schema: {e}")
        raise # Re-raise to indicate failure

@click.command('init-db')
def init_db_command():
    """CLI command to clear existing data and create new tables."""
    # This command should be run within an app context to access current_app
    from flask.cli import with_appcontext # Local import for CLI context
    
    @with_appcontext
    def _init_db_command_impl():
        try:
            init_db_schema()
            click.echo('Initialized the database.')
        except Exception as e:
            click.echo(f'Failed to initialize database: {e}', err=True)
    
    _init_db_command_impl()


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db_connection) # Close DB connection when app context ends
    app.cli.add_command(init_db_command)     # Add new command to flask CLI

def record_stock_movement(conn, product_id, variant_id, movement_type, quantity_changed, reason, related_item_uid=None):
    """
    Records a stock movement in the inventory_movements table.
    conn: An active sqlite3 connection object. The caller is responsible for transaction management (commit/rollback).
    """
    if not conn:
        current_app.logger.error("Database connection not provided to record_stock_movement.")
        # In a real scenario, you might want to raise an error or handle this more gracefully.
        # For now, let's try to get a connection if one isn't passed, though this is not ideal for transactions.
        conn = get_db_connection() 
        # This is risky as it might not be part of the original transaction.
        # Best practice: ensure conn is always passed and valid.

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory_movements 
            (product_id, variant_id, movement_type, quantity_changed, reason, related_item_uid, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (product_id, variant_id, movement_type, quantity_changed, reason, related_item_uid))
        # The calling function should handle conn.commit() as part of its transaction.
        current_app.logger.info(f"Stock movement recorded: ProdID {product_id}, VarID {variant_id}, Type {movement_type}, Qty {quantity_changed}, ItemUID {related_item_uid}, Reason: {reason}")
    except sqlite3.Error as e:
        current_app.logger.error(f"Failed to record stock movement (ProdID {product_id}, ItemUID {related_item_uid}): {e}", exc_info=True)
        # Re-raise the exception so the calling transaction can be rolled back.
        raise
    except Exception as e: # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error in record_stock_movement (ProdID {product_id}, ItemUID {related_item_uid}): {e}", exc_info=True)
        raise

# You would also need your schema.sql file to define all tables.
# Example of what schema.sql might contain (ensure it's complete for your application):
"""
-- backend/schema.sql (Example structure - ensure this is complete and accurate)

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_weight_options;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS newsletter_subscriptions;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS inventory_movements;
DROP TABLE IF EXISTS serialized_inventory_items;
DROP TABLE IF EXISTS professional_invoices;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT,
    role TEXT NOT NULL DEFAULT 'b2c', -- 'b2c', 'professional', 'admin'
    is_verified INTEGER DEFAULT 0,
    verification_token TEXT,
    email_verified_at TIMESTAMP,
    reset_token TEXT,
    reset_token_expires_at TIMESTAMP,
    company_name TEXT, -- For B2B
    vat_number TEXT,   -- For B2B
    siret_number TEXT, -- For B2B
    kbis_path TEXT,    -- For B2B
    account_status TEXT DEFAULT 'pending', -- For B2B: 'pending', 'approved', 'rejected', 'suspended'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_fr TEXT NOT NULL,
    name_en TEXT,
    description_fr TEXT,
    description_en TEXT,
    image_url TEXT, -- Relative path to image
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_fr TEXT NOT NULL,
    name_en TEXT,
    description_fr TEXT,
    description_en TEXT,
    category_id INTEGER,
    product_type TEXT NOT NULL DEFAULT 'simple', -- 'simple', 'variable'
    base_price REAL, -- For simple products
    stock_quantity INTEGER DEFAULT 0, -- Aggregate stock
    is_active INTEGER DEFAULT 1,
    image_url TEXT, -- Main product image (relative path)
    qr_code_path TEXT, -- Product-level QR (if any, now item-specific)
    label_path TEXT,   -- Product-level label (if any)
    passport_html_path TEXT, -- Product-level passport (if any, now item-specific)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

CREATE TABLE product_weight_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    weight_grams REAL NOT NULL,
    price REAL NOT NULL,
    stock_quantity INTEGER DEFAULT 0, -- Aggregate stock for this variant
    sku TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

CREATE TABLE serialized_inventory_items (
    item_uid TEXT PRIMARY KEY,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    lot_number TEXT,
    status TEXT NOT NULL DEFAULT 'in_stock', -- 'in_stock', 'allocated', 'sold', 'damaged', 'returned', 'archived'
    date_added_to_inventory TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_conditionnement TEXT,
    ddm TEXT,
    purchase_order_id TEXT,
    cost_price REAL,
    passport_html_url TEXT, -- Public URL to the item-specific passport
    qr_code_url TEXT,       -- Asset URL to the item-specific QR code image
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT, -- Prevent product deletion if serialized items exist
    FOREIGN KEY (variant_id) REFERENCES product_weight_options (id) ON DELETE RESTRICT -- Prevent variant deletion
);
CREATE INDEX idx_serialized_items_product_id ON serialized_inventory_items (product_id);
CREATE INDEX idx_serialized_items_variant_id ON serialized_inventory_items (variant_id);
CREATE INDEX idx_serialized_items_status ON serialized_inventory_items (status);
CREATE INDEX idx_serialized_items_lot_number ON serialized_inventory_items (lot_number);


CREATE TABLE addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    address_type TEXT DEFAULT 'shipping', -- 'shipping', 'billing'
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    city TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country TEXT NOT NULL,
    is_default_shipping INTEGER DEFAULT 0,
    is_default_billing INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_payment', -- 'pending_payment', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'
    shipping_address_line1 TEXT,
    shipping_address_line2 TEXT,
    shipping_city TEXT,
    shipping_postal_code TEXT,
    shipping_country TEXT,
    billing_address_line1 TEXT,
    billing_address_line2 TEXT,
    billing_city TEXT,
    billing_postal_code TEXT,
    billing_country TEXT,
    payment_intent_id TEXT, -- For Stripe or other payment gateways
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL, 
    variant_id INTEGER,          
    item_uid TEXT UNIQUE, -- The specific UID of the item sold
    quantity INTEGER NOT NULL DEFAULT 1, -- Should be 1 if item_uid is present and unique per physical item
    price_at_purchase REAL NOT NULL,
    name_fr_at_purchase TEXT, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT, -- Prevent product deletion if in orders
    FOREIGN KEY (variant_id) REFERENCES product_weight_options (id) ON DELETE RESTRICT,
    FOREIGN KEY (item_uid) REFERENCES serialized_inventory_items (item_uid) ON DELETE RESTRICT -- Prevent UID deletion if in orders
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL, -- e.g., 1-5
    comment TEXT,
    is_approved INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE newsletter_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER, -- Can be admin_id or user_id depending on action
    event_type TEXT NOT NULL,
    details TEXT, -- JSON string for additional details
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) -- Optional, if action is by a logged-in user
);

CREATE TABLE inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    variant_id INTEGER, -- Null for simple products
    related_item_uid TEXT, -- Link to specific serialized item if movement is item-specific
    movement_type TEXT NOT NULL, -- e.g., 'initial_stock_serialized', 'sale_serialized', 'stock_received_serialized', 'adjustment_damage', 'return'
    quantity_changed INTEGER NOT NULL, -- Positive for increase, negative for decrease (or always positive and type implies direction)
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id),
    FOREIGN KEY (variant_id) REFERENCES product_weight_options (id),
    FOREIGN KEY (related_item_uid) REFERENCES serialized_inventory_items (item_uid)
);
CREATE INDEX idx_inventory_movements_related_item_uid ON inventory_movements (related_item_uid);

CREATE TABLE professional_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    professional_user_id INTEGER NOT NULL,
    order_id INTEGER, -- Optional: if invoice is directly linked to a specific B2B order
    issue_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    subtotal_ht REAL NOT NULL,
    total_vat_amount REAL NOT NULL,
    total_amount_ttc REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft', -- 'draft', 'sent', 'paid', 'overdue', 'cancelled'
    pdf_path TEXT, -- Filesystem path to the generated PDF
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (professional_user_id) REFERENCES users (id),
    FOREIGN KEY (order_id) REFERENCES orders (id) -- Optional
);

-- Seed initial admin user if needed (example)
-- INSERT INTO users (email, password_hash, role, is_verified, account_status, first_name) 
-- VALUES ('admin@maisontruvra.com', 'hashed_password_for_admin', 'admin', 1, 'approved', 'Admin');
"""
