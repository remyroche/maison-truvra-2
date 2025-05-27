# backend/database.py
import sqlite3
import os
import logging
from werkzeug.security import generate_password_hash
from backend.config import current_config # Import the loaded configuration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = current_config.DATABASE_PATH

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    # Ensure the directory for the database file exists
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        logger.info(f"Created database directory: {db_dir}")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Access columns by name
    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def initialize_database():
    """Initializes the database with the required schema and some seed data."""
    logger.info(f"Initializing database at {DATABASE_PATH}...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop tables if they exist (for a clean setup during development)
    # In production, you would use migrations instead of dropping tables.
    # cursor.execute("DROP TABLE IF EXISTS product_reviews;")
    # cursor.execute("DROP TABLE IF EXISTS order_items;")
    # cursor.execute("DROP TABLE IF EXISTS orders;")
    # cursor.execute("DROP TABLE IF EXISTS product_options;")
    # cursor.execute("DROP TABLE IF EXISTS products;")
    # cursor.execute("DROP TABLE IF EXISTS categories;") # Added categories
    # cursor.execute("DROP TABLE IF EXISTS users;")
    # cursor.execute("DROP TABLE IF EXISTS newsletter_subscriptions;")
    # cursor.execute("DROP TABLE IF EXISTS inventory_movements;")
    # cursor.execute("DROP TABLE IF EXISTS admin_users;")


    # Create Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_fr TEXT NOT NULL UNIQUE,
        name_en TEXT NOT NULL UNIQUE,
        description_fr TEXT,
        description_en TEXT,
        slug TEXT NOT NULL UNIQUE,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    logger.info("Table 'categories' created or already exists.")

    # Create Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_fr TEXT NOT NULL,
        name_en TEXT NOT NULL,
        description_fr TEXT,
        description_en TEXT,
        category_id INTEGER, -- New column for category
        base_price REAL NOT NULL,
        sku TEXT UNIQUE,
        image_url_main TEXT,
        image_urls_additional TEXT, -- JSON string of image URLs
        is_featured BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        meta_title_fr TEXT,
        meta_title_en TEXT,
        meta_description_fr TEXT,
        meta_description_en TEXT,
        slug TEXT UNIQUE,
        -- Fields for truffle passport/label
        species_fr TEXT,
        species_en TEXT,
        origin_fr TEXT,
        origin_en TEXT,
        quality_grade_fr TEXT,
        quality_grade_en TEXT,
        harvest_date DATE,
        packaging_date DATE,
        best_before_date DATE,
        lot_number TEXT UNIQUE,
        qr_code_url TEXT, -- URL to the generated QR code image
        label_url TEXT, -- URL to the generated label image
        passport_url TEXT, -- URL to the generated passport HTML
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL -- Link to categories
    );
    """)
    logger.info("Table 'products' created or already exists.")

    # Create Product Options Table (for variants like weight)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        name_fr TEXT NOT NULL, -- e.g., "Poids"
        name_en TEXT NOT NULL, -- e.g., "Weight"
        value_fr TEXT NOT NULL, -- e.g., "10g", "20g", "Truffle entiere 15g"
        value_en TEXT NOT NULL, -- e.g., "10g", "20g", "Whole truffle 15g"
        price_modifier REAL DEFAULT 0, -- Price difference from base_price, can be negative for discount
        absolute_price REAL, -- If set, this price is used instead of base_price + price_modifier
        stock_quantity INTEGER NOT NULL DEFAULT 0,
        sku_suffix TEXT, -- To be appended to product SKU for variant SKU
        image_url TEXT, -- Specific image for this variant if different from main product
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    """)
    logger.info("Table 'product_options' created or already exists.")

    # Create Users Table (for B2C and B2B customers)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        phone_number TEXT,
        role TEXT NOT NULL DEFAULT 'B2C', -- 'B2C', 'B2B_PENDING', 'B2B_APPROVED'
        company_name TEXT, -- For B2B
        vat_number TEXT,   -- For B2B
        siret_number TEXT, -- For B2B
        billing_address_line1 TEXT,
        billing_address_line2 TEXT,
        billing_city TEXT,
        billing_postal_code TEXT,
        billing_country TEXT,
        shipping_address_line1 TEXT,
        shipping_address_line2 TEXT,
        shipping_city TEXT,
        shipping_postal_code TEXT,
        shipping_country TEXT,
        is_active BOOLEAN DEFAULT 1,
        is_admin BOOLEAN DEFAULT 0, -- Differentiates site admins from regular users
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    );
    """)
    logger.info("Table 'users' created or already exists.")

    # Create Admin Users Table (for backend admin panel access)
    # This table is distinct from the general 'users' table to separate customer accounts from admin accounts.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin', -- e.g., 'superadmin', 'editor', 'viewer'
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    );
    """)
    logger.info("Table 'admin_users' created or already exists.")


    # Create Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, -- Can be NULL for guest checkouts if implemented
        order_reference TEXT NOT NULL UNIQUE,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING', -- e.g., PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELED, REFUNDED
        payment_method TEXT,
        payment_status TEXT DEFAULT 'UNPAID', -- e.g., UNPAID, PAID, FAILED
        transaction_id TEXT,
        shipping_address_line1 TEXT,
        shipping_address_line2 TEXT,
        shipping_city TEXT,
        shipping_postal_code TEXT,
        shipping_country TEXT,
        shipping_cost REAL DEFAULT 0,
        tracking_number TEXT,
        customer_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)
    logger.info("Table 'orders' created or already exists.")

    # Create Order Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_option_id INTEGER, -- If the item is a specific variant
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL, -- Price per unit at the time of purchase
        total_price REAL NOT NULL, -- quantity * unit_price
        product_name_fr TEXT, -- Denormalized for historical data
        product_name_en TEXT,
        option_value_fr TEXT,
        option_value_en TEXT,
        sku TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT, -- Prevent product deletion if in an order
        FOREIGN KEY (product_option_id) REFERENCES product_options(id) ON DELETE RESTRICT
    );
    """)
    logger.info("Table 'order_items' created or already exists.")

    # Create Product Reviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        title TEXT,
        comment TEXT,
        status TEXT DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    logger.info("Table 'product_reviews' created or already exists.")

    # Create Newsletter Subscriptions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS newsletter_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    );
    """)
    logger.info("Table 'newsletter_subscriptions' created or already exists.")

    # Create Inventory Movements Table (for tracking stock changes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        product_option_id INTEGER, -- If movement is for a specific variant
        change_quantity INTEGER NOT NULL, -- Positive for stock in, negative for stock out
        reason TEXT, -- e.g., 'NEW_STOCK', 'SALE', 'RETURN', 'ADJUSTMENT'
        order_id INTEGER, -- Optional: link to order if it's a sale or return
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
        FOREIGN KEY (product_option_id) REFERENCES product_options(id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
    );
    """)
    logger.info("Table 'inventory_movements' created or already exists.")

    # Create an initial admin user if it doesn't exist
    try:
        cursor.execute("SELECT * FROM admin_users WHERE username = ?", ('admin',))
        if cursor.fetchone() is None:
            hashed_password = generate_password_hash('adminpassword') # Change this default password!
            cursor.execute("""
                INSERT INTO admin_users (username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, ('admin', 'admin@example.com', hashed_password, 'superadmin', 1))
            logger.info("Default admin user 'admin' created.")
    except sqlite3.Error as e:
        logger.error(f"Error creating default admin user: {e}")


    # Seed initial categories if the table is empty
    try:
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            initial_categories = [
                ('Truffe Fraîche', 'Fresh Truffle', 'Nos meilleures truffes fraîches de saison.', 'Our best seasonal fresh truffles.', 'truffe-fraiche', 'images/categories/fresh_truffle.jpg'),
                ('Huiles & Condiments', 'Oils & Condiments', 'Huiles et condiments aromatisés à la truffe.', 'Truffle-flavored oils and condiments.', 'huiles-condiments', 'images/categories/oils_condiments.jpg'),
                ('Produits d\'Épicerie Fine', 'Delicatessen Products', 'Une sélection de produits d\'épicerie fine à la truffe.', 'A selection of truffle delicatessen products.', 'epicerie-fine', 'images/categories/delicatessen.jpg'),
                ('Coffrets Cadeaux', 'Gift Boxes', 'Des coffrets cadeaux parfaits pour les amateurs de truffes.', 'Perfect gift boxes for truffle lovers.', 'coffrets-cadeaux', 'images/categories/gift_boxes.jpg')
            ]
            cursor.executemany("""
                INSERT INTO categories (name_fr, name_en, description_fr, description_en, slug, image_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, initial_categories)
            logger.info(f"Inserted {len(initial_categories)} initial categories.")
    except sqlite3.Error as e:
        logger.error(f"Error seeding categories: {e}")


    # Seed initial products if the table is empty (example)
    try:
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            # Get category IDs (assuming they were just inserted)
            cursor.execute("SELECT id, name_fr FROM categories")
            category_map = {name: cat_id for cat_id, name in cursor.fetchall()}

            fresh_truffle_cat_id = category_map.get('Truffe Fraîche')

            if fresh_truffle_cat_id:
                initial_products = [
                    ('Truffe Noire Extra (Tuber Melanosporum)', 'Black Truffle Extra (Tuber Melanosporum)',
                     'La reine des truffes, la Tuber Melanosporum, qualité extra.', 'The queen of truffles, Tuber Melanosporum, extra quality.',
                     fresh_truffle_cat_id, 50.00, 'TN-EXTRA-001', 'images/products/truffle_noire_1.jpg', '[]', 1, 1,
                     'Truffe Noire Extra', 'Black Truffle Extra', 'Acheter truffe noire extra', 'Buy black truffle extra', 'truffe-noire-extra',
                     'Tuber Melanosporum', 'Tuber Melanosporum', 'Provence, France', 'Provence, France', 'Extra', 'Extra',
                     '2023-12-01', '2023-12-05', '2023-12-20', 'LOT20231205A'),
                    ('Truffe Blanche d\'Alba (Tuber Magnatum Pico)', 'Alba White Truffle (Tuber Magnatum Pico)',
                     'La prestigieuse truffe blanche d\'Alba, un arôme incomparable.', 'The prestigious Alba white truffle, an incomparable aroma.',
                     fresh_truffle_cat_id, 200.00, 'TB-ALBA-001', 'images/products/truffle_blanche_1.jpg', '[]', 1, 1,
                     'Truffe Blanche d\'Alba', 'Alba White Truffle', 'Acheter truffe blanche d\'Alba', 'Buy Alba white truffle', 'truffe-blanche-alba',
                     'Tuber Magnatum Pico', 'Tuber Magnatum Pico', 'Alba, Italie', 'Alba, Italy', 'Premium', 'Premium',
                     '2023-11-15', '2023-11-18', '2023-11-28', 'LOT20231118B')
                ]
                cursor.executemany("""
                    INSERT INTO products (name_fr, name_en, description_fr, description_en, category_id, base_price, sku, image_url_main, image_urls_additional, is_featured, is_active, meta_title_fr, meta_title_en, meta_description_fr, meta_description_en, slug, species_fr, species_en, origin_fr, origin_en, quality_grade_fr, quality_grade_en, harvest_date, packaging_date, best_before_date, lot_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, initial_products)
                logger.info(f"Inserted {len(initial_products)} initial products.")

                # Seed product options for the first product (Truffe Noire Extra)
                cursor.execute("SELECT id FROM products WHERE sku = 'TN-EXTRA-001'")
                product1_id_row = cursor.fetchone()
                if product1_id_row:
                    product1_id = product1_id_row[0]
                    initial_options_p1 = [
                        (product1_id, 'Poids', 'Weight', '15g', '15g', 0, None, 100, '15G'),
                        (product1_id, 'Poids', 'Weight', '30g', '30g', 45.00, None, 50, '30G'), # 50 (base) + 45 = 95
                        (product1_id, 'Poids', 'Weight', '50g', '50g', None, 150.00, 30, '50G') # Absolute price
                    ]
                    cursor.executemany("""
                        INSERT INTO product_options (product_id, name_fr, name_en, value_fr, value_en, price_modifier, absolute_price, stock_quantity, sku_suffix)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, initial_options_p1)
                    logger.info(f"Inserted {len(initial_options_p1)} options for product TN-EXTRA-001.")

                    # Update inventory for these options
                    for opt in initial_options_p1:
                        cursor.execute("""
                            INSERT INTO inventory_movements (product_id, product_option_id, change_quantity, reason)
                            SELECT ?, po.id, ?, 'INITIAL_STOCK'
                            FROM product_options po
                            WHERE po.product_id = ? AND po.sku_suffix = ?
                        """, (product1_id, opt[7], product1_id, opt[8]))
                    logger.info(f"Created initial inventory movements for product TN-EXTRA-001 options.")

    except sqlite3.Error as e:
        logger.error(f"Error seeding products or product options: {e}")


    conn.commit()
    conn.close()
    logger.info("Database initialization complete.")

if __name__ == '__main__':
    # This allows you to run `python backend/database.py` to initialize/reset the DB.
    # Be cautious with this in a production environment.
    logger.info("Running database initialization directly.")
    # db_dir = os.path.dirname(DATABASE_PATH)
    # if db_dir and not os.path.exists(db_dir):
    # os.makedirs(db_dir)
    # logger.info(f"Created database directory: {db_dir}")
    
    # Potentially drop the DB file for a complete reset if needed for development
    # if os.path.exists(DATABASE_PATH) and current_config.DEBUG:
    #     logger.warning(f"Development mode: Removing existing database at {DATABASE_PATH} for re-initialization.")
    #     os.remove(DATABASE_PATH)
            
    initialize_database()
