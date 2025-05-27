# backend/database.py
import sqlite3
import os
import datetime
from werkzeug.security import generate_password_hash
from flask import current_app 

# --- Fonctions d'aide pour la base de données ---
def get_db():
    db_path = current_app.config['DATABASE_PATH']
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row 
    return db

def init_db_command(app_context):
    with app_context: 
        init_db()
        current_app.logger.info("Base de données initialisée via la commande CLI.")

def init_db():
    db = get_db()
    cursor = db.cursor()

    # Table des utilisateurs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom TEXT,
        prenom TEXT,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Table des abonnements à la newsletter
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS newsletter_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        nom TEXT,
        prenom TEXT,
        consentement TEXT CHECK(consentement IN ('Y', 'N')) NOT NULL,
        subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Table des produits (ensure asset paths are included)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        short_description TEXT,
        long_description TEXT,
        image_url_main TEXT,
        image_urls_thumb TEXT, -- JSON string array
        species TEXT,
        origin TEXT,
        seasonality TEXT,
        ideal_uses TEXT,
        sensory_description TEXT,
        pairing_suggestions TEXT,
        base_price REAL,
        stock_quantity INTEGER DEFAULT 0,
        is_published BOOLEAN DEFAULT TRUE,
        passport_url TEXT,          -- For public URL of the passport HTML
        qr_code_path TEXT,          -- Relative path to QR code image in static folder
        label_path TEXT,            -- Relative path to label image in static folder
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_products_updated_at
        AFTER UPDATE ON products FOR EACH ROW
        BEGIN
            UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
    """)

    # Table des options de poids des produits
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_weight_options (
        option_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        weight_grams INTEGER NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
    )
    ''')

    # Table des commandes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, 
        customer_email TEXT NOT NULL,
        customer_name TEXT, -- Added for easier display
        shipping_address TEXT NOT NULL,
        total_amount REAL NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'Pending', 
        tracking_number TEXT, -- Added for shipping
        carrier TEXT,         -- Added for shipping
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
    )
    ''')

    # Table des articles de commande
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL, 
        quantity INTEGER NOT NULL,
        price_at_purchase REAL NOT NULL,
        variant TEXT, 
        variant_option_id INTEGER, 
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT,
        FOREIGN KEY (variant_option_id) REFERENCES product_weight_options (option_id) ON DELETE RESTRICT
    )
    ''')

    # Table pour les mouvements d'inventaire
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory_movements (
        movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        variant_option_id INTEGER, 
        quantity_change INTEGER NOT NULL, 
        movement_type TEXT NOT NULL CHECK(movement_type IN ('initial_stock', 'addition', 'vente', 'ajustement_manuel', 'creation_lot', 'retour_client', 'perte', 'correction')),
        movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        order_id INTEGER, 
        notes TEXT, 
        user_id INTEGER, 
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
        FOREIGN KEY (variant_option_id) REFERENCES product_weight_options (option_id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # Table for order notes (NEW)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_notes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        admin_user_id INTEGER, -- User who added the note (can be NULL for system notes)
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (admin_user_id) REFERENCES users (id) ON DELETE SET NULL
    )
    ''')

    db.commit()
    current_app.logger.info("Base de données initialisée (tables vérifiées/créées).")

def populate_initial_data():
    db = get_db()
    cursor = db.cursor()
    populated_something = False

    # Admin User
    admin_email_config = current_app.config.get('ADMIN_EMAIL', 'admin@maisontruvra.com')
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (admin_email_config,))
    if cursor.fetchone()[0] == 0:
        try:
            admin_password_config = current_app.config.get('ADMIN_PASSWORD', 'SecureAdminP@ss1')
            cursor.execute(
                "INSERT INTO users (email, password_hash, nom, prenom, is_admin) VALUES (?, ?, ?, ?, ?)",
                (admin_email_config, generate_password_hash(admin_password_config), "Admin", "MaisonTrüvra", True)
            )
            current_app.logger.info(f"Utilisateur Admin créé ({admin_email_config}).")
            populated_something = True
        except sqlite3.IntegrityError:
            current_app.logger.info("L'utilisateur Admin existe déjà.")
    
    # Initial Products (example, ensure IDs are unique and asset paths make sense if pre-generated)
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products_data = [
            {"id": "tuber-melanosporum-frais", "name": "Truffe Noire Fraîche (Tuber Melanosporum)", "category": "Fresh Truffles", 
             "short_description": "Le diamant noir de la gastronomie, récolté à pleine maturité.", 
             "image_url_main": "https://placehold.co/600x500/7D6A4F/F5EEDE?text=Truffe+Noire", 
             "base_price": None, "stock_quantity": 0, "is_published": True,
             "passport_url": None, "qr_code_path": None, "label_path": None}, # Asset paths will be filled on creation
            {"id": "huile-truffe-noire", "name": "Huile d'Olive Vierge Extra à la Truffe Noire", "category": "Truffle Oils", 
             "short_description": "Notre huile d'olive infusée avec l'arôme délicat de la truffe noire.", 
             "image_url_main": "https://placehold.co/400x300/A28C6A/F5EEDE?text=Huile+Truffe", 
             "base_price": 25.00, "stock_quantity": 50, "is_published": True,
             "passport_url": None, "qr_code_path": None, "label_path": None}
        ]
        for p_data in products_data:
            cursor.execute('''
            INSERT INTO products (id, name, category, short_description, image_url_main, 
                                  base_price, stock_quantity, is_published, 
                                  passport_url, qr_code_path, label_path, updated_at)
            VALUES (:id, :name, :category, :short_description, :image_url_main, 
                    :base_price, :stock_quantity, :is_published,
                    :passport_url, :qr_code_path, :label_path, CURRENT_TIMESTAMP)
            ''', p_data)
            if p_data['base_price'] is not None and p_data['stock_quantity'] > 0:
                record_stock_movement(cursor, p_data['id'], p_data['stock_quantity'], 'initial_stock', notes="Stock initial")
        current_app.logger.info("Données initiales des produits (basiques) peuplées.")
        populated_something = True

    # Initial Weight Options
    cursor.execute("SELECT COUNT(*) FROM product_weight_options WHERE product_id = 'tuber-melanosporum-frais'")
    if cursor.fetchone()[0] == 0: 
        weight_options_data = [
            {"product_id": "tuber-melanosporum-frais", "weight_grams": 20, "price": 75.00, "stock_quantity": 10},
            {"product_id": "tuber-melanosporum-frais", "weight_grams": 30, "price": 110.00, "stock_quantity": 15},
        ]
        for wo_data in weight_options_data:
            cursor.execute('''
            INSERT INTO product_weight_options (product_id, weight_grams, price, stock_quantity)
            VALUES (:product_id, :weight_grams, :price, :stock_quantity)
            ''', wo_data)
            # Record initial stock for variants
            record_stock_movement(cursor, wo_data['product_id'], wo_data['stock_quantity'], 'initial_stock', 
                                  variant_option_id=cursor.lastrowid, 
                                  notes=f"Stock initial variante {wo_data['weight_grams']}g")
        current_app.logger.info("Options de poids initiales pour 'tuber-melanosporum-frais' peuplées.")
        populated_something = True
    
    if populated_something:
        db.commit()

def record_stock_movement(db_cursor, product_id, quantity_change, movement_type, 
                          variant_option_id=None, order_id=None, notes=None, user_id=None):
    """
    Enregistre un mouvement de stock et met à jour la quantité en stock du produit/variante.
    Lève une ValueError si le stock devient négatif ou si le produit/variante n'est pas trouvé.
    """
    current_stock = 0
    new_stock = 0

    if variant_option_id:
        db_cursor.execute("SELECT stock_quantity FROM product_weight_options WHERE option_id = ? AND product_id = ?", 
                          (variant_option_id, product_id))
        current_stock_row = db_cursor.fetchone()
        if not current_stock_row:
            raise ValueError(f"Option de produit (ID: {variant_option_id} pour Produit ID: {product_id}) non trouvée.")
        
        current_stock = current_stock_row['stock_quantity']
        new_stock = current_stock + quantity_change
        
        if new_stock < 0:
             raise ValueError(f"Stock insuffisant pour l'option de produit ID {variant_option_id}. Actuel: {current_stock}, Tentative de retrait: {abs(quantity_change)}")

        db_cursor.execute("UPDATE product_weight_options SET stock_quantity = ? WHERE option_id = ?", 
                       (new_stock, variant_option_id))
    else: 
        db_cursor.execute("SELECT stock_quantity, base_price FROM products WHERE id = ?", (product_id,))
        current_stock_row = db_cursor.fetchone()
        if not current_stock_row:
            raise ValueError(f"Produit (ID: {product_id}) non trouvé.")
        if current_stock_row['base_price'] is None and movement_type != 'initial_stock':
             # This check is important: simple stock adjustments should not happen on products managed by variants
             # unless it's a special case like summing up variant stocks to the parent (which should be handled carefully)
             # For now, we prevent direct stock changes on parent if it's variant-based, except for initial_stock.
             db_cursor.execute("SELECT COUNT(*) FROM product_weight_options WHERE product_id = ?", (product_id,))
             if db_cursor.fetchone()[0] > 0: # If variants exist
                raise ValueError(f"Tentative de modification de stock sur produit principal '{product_id}' qui est géré par variantes. Ajustez les variantes.")

        current_stock = current_stock_row['stock_quantity']
        new_stock = current_stock + quantity_change

        if new_stock < 0:
            raise ValueError(f"Stock insuffisant pour le produit ID {product_id}. Actuel: {current_stock}, Tentative de retrait: {abs(quantity_change)}")

        db_cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", 
                       (new_stock, product_id))

    db_cursor.execute('''
        INSERT INTO inventory_movements (product_id, variant_option_id, quantity_change, movement_type, order_id, notes, user_id, movement_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) 
    ''', (product_id, variant_option_id, quantity_change, movement_type, order_id, notes, user_id))
    
    current_app.logger.info(f"Mouvement de stock: Produit {product_id}, Variante {variant_option_id or 'N/A'}, Qté Changement {quantity_change}, Type {movement_type}, Nouveau Stock: {new_stock}, User: {user_id or 'System'}")

