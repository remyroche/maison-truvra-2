# backend/database.py
import sqlite3
import os
import datetime
from werkzeug.security import generate_password_hash 
from flask import current_app import sqlite3
import os
import hashlib
import click
from flask import current_app
from flask.cli import AppGroup

# This script is now simplified. The core logic is in backend/database.py
# It can be used to explicitly call the init/seed commands if needed outside of `flask init-db`.

# Get the absolute path to the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(os.path.dirname(BASE_DIR), 'db') # db folder at project root/db
DB_PATH = os.path.join(DB_DIR, 'maison_truvra.db')


def get_db():
    """
    Connects to the SQLite database.
    Ensures the database directory exists.
    """
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database_from_script():
    """
    Initializes the database schema and seeds data.
    This function is intended to be callable if you're not running within a Flask app context.
    However, it's better to use `flask init-db` from `backend.database`.
    """
    print("Attempting to initialize database from db_init_seed.py (standalone)...")
    print(f"Using database path: {DB_PATH}")
    
    # For standalone execution, we need to import and call the core functions
    # from backend.database. This is a bit circular, ideally, backend.database
    # would be structured to allow this more cleanly if truly needed.
    # For now, this script primarily serves as a way to trigger flask commands.
    
    # This standalone execution is discouraged. Use `flask init-db`.
    # from .database import init_schema as core_init_schema, seed_data as core_seed_data
    
    # conn = get_db()
    # try:
    #     print("Dropping existing tables (if any)...")
    #     cursor = conn.cursor()
    #     tables = ['audit_log', 'professional_invoice_items', 'professional_invoices', 'newsletter_subscriptions', 'reviews', 'order_items', 'orders', 'inventory_movements', 'product_variants', 'products', 'categories', 'users', 'professional_quotes']
    #     for table in tables:
    #         cursor.execute(f"DROP TABLE IF EXISTS {table}")
    #     conn.commit()
    #     print("Existing tables dropped.")

    #     core_init_schema(conn)
    #     core_seed_data(conn)
    #     print("Database initialized and seeded successfully via db_init_seed.py (standalone).")
    # except Exception as e:
    #     print(f"Error during standalone database initialization: {e}")
    # finally:
    #     if conn:
    #         conn.close()
    print("Standalone initialization from db_init_seed.py is mostly deprecated.")
    print("Please use 'flask init-db' or 'flask seed-db' commands from backend.database.")


# Flask CLI command group for database operations
db_cli = AppGroup('db_script')

@db_cli.command('init')
def init_db_command_script():
    """Initializes the database: drops existing tables, creates new ones, and seeds data."""
    # This now effectively tells the user to use the main command
    click.echo("This command is a wrapper. The main database initialization is via 'flask init-db'.")
    click.echo("Please run 'flask init-db' from your Flask application context.")
    # If you absolutely need to run it from here (e.g. no flask app context available for CLI)
    # you would call initialize_database_from_script(), but it's not recommended.
    # initialize_database_from_script()


@db_cli.command('seed')
def seed_data_command_script():
    """Seeds the database with initial/test data."""
    click.echo("This command is a wrapper. The main database seeding is via 'flask seed-db'.")
    click.echo("Please run 'flask seed-db' from your Flask application context.")
    # from .database import seed_data as core_seed_data
    # conn = get_db()
    # try:
    #     core_seed_data(conn)
    #     print("Data seeded successfully via db_init_seed.py script.")
    # except Exception as e:
    #     print(f"Error during data seeding via script: {e}")
    # finally:
    #     if conn:
    #         conn.close()


def register_cli_commands(app):
    """Registers the CLI commands with the Flask app."""
    app.cli.add_command(db_cli)

if __name__ == '__main__':
    # This allows running `python -m backend.db_init_seed init` or `python -m backend.db_init_seed seed`
    # but it won't have the Flask app context.
    # It's better to run these commands through the Flask CLI: `flask db_script init`
    # However, the primary commands are now `flask init-db` and `flask seed-db` from database.py
    
    # For direct script execution (e.g. `python backend/db_init_seed.py init`):
    # This part is tricky because it runs outside Flask app context.
    # The click commands are usually run via Flask CLI.
    # To make `python backend/db_init_seed.py init` work, you'd need a more complex setup.
    # It's simpler to guide users to use `flask init-db`.
    print("This script is primarily for registering CLI commands with Flask.")
    print("Use 'flask init-db' or 'flask seed-db' to manage the database.")
