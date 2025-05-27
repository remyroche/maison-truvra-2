# backend/database.py
import sqlite3
import os
import logging
from werkzeug.security import generate_password_hashimport sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext
import os
import hashlib
import json # For storing list of image URLs

# --- Database Connection Handling ---
def get_db_connection():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db_conn' not in g:
        db_path = current_app.config['DATABASE_PATH']
        # Ensure the directory for the database exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        g.db_conn = sqlite3.connect(db_path)
        g.db_conn.row_factory = sqlite3.Row  # Access columns by name
    return g.db_conn

def close_connection(exception=None):
    """Closes the database connection at the end of the request."""
    db_conn = g.pop('db_conn', None)
    if db_conn is not None:
        db_conn.close()

# --- Schema Definition and Initialization ---
def init_schema(db):
    """Defines and creates database tables if they don't exist."""
    cursor = db.cursor()

    # Users Table (B2C and B2B Customers, Admins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            phone_number TEXT,
            is_admin BOOLEAN DEFAULT FALSE,
            is_professional BOOLEAN DEFAULT FALSE,
            professional_status TEXT DEFAULT 'pending', -- e.g., pending, approved, rejected
            company_name TEXT,
            vat_number TEXT,
            siret_number TEXT,
            billing_address TEXT, -- JSON string for address object
            shipping_address TEXT, -- JSON string for address object
            preferred_language TEXT DEFAULT 'fr',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP,
            is_verified BOOLEAN DEFAULT FALSE, -- For email verification
            verification_token TEXT,
            reset_token TEXT,
            reset_token_expires TIMESTAMP
        )
    ''')

    # Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_fr TEXT NOT NULL,
            name_en TEXT NOT NULL,
            description_fr TEXT,
            description_en TEXT,
            slug TEXT UNIQUE NOT NULL,
            image_url TEXT, -- Optional category image
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_fr TEXT NOT NULL,
            name_en TEXT NOT NULL,
            description_fr TEXT,
            description_en TEXT,
            category_id INTEGER,
            sku TEXT UNIQUE NOT NULL, -- Stock Keeping Unit
            base_price REAL NOT NULL, -- Price for the base variant/unit
            currency TEXT DEFAULT 'EUR',
            main_image_url TEXT, -- Primary image for the product
            additional_image_urls TEXT, -- JSON list of strings for other images
            tags TEXT, -- Comma-separated tags
            is_active BOOLEAN DEFAULT TRUE, -- Whether the product is visible in the store
            is_featured BOOLEAN DEFAULT FALSE,
            meta_title_fr TEXT,
            meta_title_en TEXT,
            meta_description_fr TEXT,
            meta_description_en TEXT,
            slug TEXT UNIQUE NOT NULL,
            qr_code_url TEXT,
            product_passport_url TEXT,
            label_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # Product Variants Table (e.g., different sizes, weights)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            sku TEXT UNIQUE NOT NULL, -- Variant specific SKU
            name_fr TEXT, -- e.g., "50g", "100g"
            name_en TEXT,
            price_modifier REAL DEFAULT 0, -- Amount to add/subtract from base_price, or could be absolute price
            stock_quantity INTEGER DEFAULT 0,
            weight_grams INTEGER, -- For shipping calculations
            dimensions TEXT, -- JSON string for L x W x H
            image_url TEXT, -- Specific image for this variant
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        )
    ''')

    # Inventory / Stock Movements Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_variant_id INTEGER NOT NULL,
            change_quantity INTEGER NOT NULL, -- Positive for stock in, negative for stock out
            reason TEXT, -- e.g., 'initial_stock', 'sale', 'return', 'adjustment'
            movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            related_order_id INTEGER, -- Optional, link to order if it's a sale/return
            notes TEXT,
            FOREIGN KEY (product_variant_id) REFERENCES product_variants (id)
            -- FOREIGN KEY (related_order_id) REFERENCES orders (id) -- Add if orders table is defined
        )
    ''')
    
    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, -- Can be NULL for guest checkouts if allowed
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending', -- e.g., pending, processing, shipped, delivered, cancelled, refunded
            total_amount REAL NOT NULL,
            currency TEXT DEFAULT 'EUR',
            shipping_address TEXT NOT NULL, -- JSON string
            billing_address TEXT NOT NULL, -- JSON string
            shipping_method TEXT,
            shipping_cost REAL DEFAULT 0,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'pending', -- e.g., pending, paid, failed
            transaction_id TEXT, -- From payment gateway
            customer_notes TEXT,
            admin_notes TEXT,
            invoice_url TEXT, -- Path to generated invoice for B2C if applicable
            tracking_number TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Order Items Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_variant_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL, -- Price at the time of purchase
            total_price REAL NOT NULL,
            product_name_fr TEXT, -- Denormalized for easier invoice generation/history
            product_name_en TEXT,
            variant_name_fr TEXT,
            variant_name_en TEXT,
            sku TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
            FOREIGN KEY (product_variant_id) REFERENCES product_variants (id) -- Consider ON DELETE SET NULL or RESTRICT
        )
    ''')

    # Professional Invoices Table (B2B)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professional_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professional_user_id INTEGER NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            issue_date DATE NOT NULL,
            due_date DATE,
            total_amount REAL NOT NULL,
            vat_amount REAL,
            status TEXT DEFAULT 'draft', -- e.g., draft, sent, paid, overdue, cancelled
            pdf_url TEXT, -- Path to the generated PDF invoice
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (professional_user_id) REFERENCES users (id)
        )
    ''')
    
    # Professional Invoice Items
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professional_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES professional_invoices (id) ON DELETE CASCADE
        )
    ''')

    # Reviews Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_approved BOOLEAN DEFAULT FALSE, -- Admin approval for reviews
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Newsletter Subscriptions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS newsletter_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            opt_out_token TEXT
        )
    ''')

    # Audit Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER, -- User performing the action (can be admin or customer)
            username TEXT, -- Denormalized for easier viewing
            action TEXT NOT NULL, -- e.g., 'product_created', 'user_login', 'order_status_changed'
            target_type TEXT, -- e.g., 'product', 'user', 'order'
            target_id INTEGER,
            details TEXT, -- JSON string for additional details
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Professional B2B Quotes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professional_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_name TEXT,
            contact_name TEXT,
            email TEXT NOT NULL,
            phone_number TEXT,
            project_description TEXT NOT NULL,
            estimated_budget REAL,
            status TEXT DEFAULT 'pending_review', -- e.g., pending_review, contacted, proposal_sent, accepted, rejected
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            admin_notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')


    db.commit()
    print("Database schema initialized.")

def seed_data(db):
    """Seeds the database with initial data if tables are empty."""
    cursor = db.cursor()

    # Check if admin user already exists
    cursor.execute("SELECT id FROM users WHERE email = ?", ('admin@maisontruvra.com',))
    if cursor.fetchone() is None:
        password = 'adminpassword' # Change this for a real deployment!
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        cursor.execute('''
            INSERT INTO users (email, password_hash, first_name, last_name, is_admin, is_professional, professional_status, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('admin@maisontruvra.com', password_hash, 'Admin', 'User', True, False, 'not_applicable', True))
        print("Admin user created.")

    # Check if categories exist
    cursor.execute("SELECT id FROM categories WHERE slug = ?", ('truffes-fraiches',))
    if cursor.fetchone() is None:
        categories_data = [
            ('Truffe Fraîche', 'Fresh Truffle', 'Découvrez nos truffes fraîches de saison.', 'Discover our seasonal fresh truffles.', 'truffes-fraiches', 'images/categories/truffes_fraiches.jpg'),
            ('Huiles & Condiments', 'Oils & Condiments', 'Huiles aromatisées à la truffe et autres condiments.', 'Truffle-flavored oils and other condiments.', 'huiles-condiments', 'images/categories/huiles_condiments.jpg'),
            ('Produits d\'Épicerie Fine', 'Delicatessen Products', 'Sélection de produits d\'épicerie fine à base de truffe.', 'Selection of truffle-based delicatessen products.', 'epicerie-fine', 'images/categories/epicerie_fine.jpg')
        ]
        cursor.executemany('''
            INSERT INTO categories (name_fr, name_en, description_fr, description_en, slug, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', categories_data)
        print(f"{len(categories_data)} categories seeded.")
    
    # Example: Seed a basic product if none exist
    cursor.execute("SELECT id FROM products WHERE sku = ?", ('TF-NOIRE-T1-50G',))
    if cursor.fetchone() is None:
        # Get category_id for 'truffes-fraiches'
        cursor.execute("SELECT id FROM categories WHERE slug = ?", ('truffes-fraiches',))
        category_row = cursor.fetchone()
        if category_row:
            category_id_truffes = category_row['id']
            product_data = (
                'Truffe Noire Fraîche Tuber Melanosporum', 
                'Fresh Black Truffle Tuber Melanosporum',
                'La reine des truffes, la Tuber Melanosporum, récoltée à maturité.',
                'The queen of truffles, Tuber Melanosporum, harvested at maturity.',
                category_id_truffes,
                'TF-NOIRE-BASE', # Base product SKU
                150.00, # Base price (e.g. per 100g, variants will adjust)
                'EUR',
                'images/products/truffe_noire_1.jpg',
                json.dumps(['images/products/truffe_noire_2.jpg', 'images/products/truffe_noire_3.jpg']),
                'truffe noire,melanosporum,frais,luxe',
                True, True,
                'Truffe Noire Fraîche | Tuber Melanosporum | Maison Trüvra',
                'Fresh Black Truffle | Tuber Melanosporum | Maison Trüvra',
                'Achetez la meilleure truffe noire fraîche Tuber Melanosporum, directement du producteur.',
                'Buy the best fresh black truffle Tuber Melanosporum, direct from the producer.',
                'truffe-noire-melanosporum'
            )
            cursor.execute('''
                INSERT INTO products (name_fr, name_en, description_fr, description_en, category_id, sku, base_price, currency, main_image_url, additional_image_urls, tags, is_active, is_featured, meta_title_fr, meta_title_en, meta_description_fr, meta_description_en, slug)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', product_data)
            product_id = cursor.lastrowid

            # Seed a variant for this product
            variant_data = (
                product_id,
                'TF-NOIRE-T1-50G',
                '50g', 
                '50g',
                75.00, # Absolute price for this variant
                50, # Stock
                50 # Weight
            )
            cursor.execute('''
                INSERT INTO product_variants (product_id, sku, name_fr, name_en, price_modifier, stock_quantity, weight_grams)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', variant_data)
            print("Example product and variant seeded.")

    db.commit()
    print("Data seeding completed (if tables were empty).")


# --- Flask CLI Commands ---
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    db = get_db_connection()
    # Drop tables if they exist (optional, for a clean start)
    # cursor = db.cursor()
    # tables = ['audit_log', 'professional_invoice_items', 'professional_invoices', 'newsletter_subscriptions', 'reviews', 'order_items', 'orders', 'inventory_movements', 'product_variants', 'products', 'categories', 'users', 'professional_quotes']
    # for table in tables:
    #     cursor.execute(f"DROP TABLE IF EXISTS {table}")
    # print("Dropped existing tables.")
    
    init_schema(db)
    seed_data(db) # Seed initial data
    click.echo('Initialized and seeded the database.')

@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Seed the database with initial data."""
    db = get_db_connection()
    seed_data(db)
    click.echo('Seeded the database.')


def init_app(app):
    """Register database functions with the Flask app. This is called by the application factory."""
    app.teardown_appcontext(close_connection)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)


