import sqlite3
import os
import click
from flask import current_app, g
from flask.cli import with_appcontext

# --- Database Initialization and Connection Management ---

def get_db_connection():
    """
    Establishes a new database connection or returns the existing one
    for the current application context.
    Stores the connection in Flask's 'g' object.
    """
    if 'db_conn' not in g or g.db_conn is None: # Removed g.db_conn.closed check, connect will handle it
        try:
            db_path = current_app.config['DATABASE_PATH']
            # Ensure the database directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            g.db_conn = sqlite3.connect(
                db_path,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db_conn.row_factory = sqlite3.Row  # Access columns by name
            g.db_conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
            current_app.logger.info(f"Database connection established to {db_path}")
        except sqlite3.Error as e:
            current_app.logger.error(f"Database connection error: {e}")
            raise
        except Exception as e:
            current_app.logger.error(f"An unexpected error occurred while connecting to the database: {e}")
            raise
    return g.db_conn

def close_db_connection(e=None):
    """
    Closes the database connection at the end of the request.
    This function is typically registered with Flask's app.teardown_appcontext.
    """
    db_conn = g.pop('db_conn', None)
    if db_conn is not None: # No need to check db_conn.closed before closing
        try:
            db_conn.close()
            current_app.logger.info("Database connection closed.")
        except Exception as e:
            current_app.logger.error(f"Error closing database connection: {e}")


def init_db_schema(db_conn=None):
    """
    Initializes the database schema by executing SQL commands from 'schema.sql'.
    If db_conn is not provided, it will attempt to get one using the app context.
    This function is primarily intended to be called from the init-db-schema CLI command.
    """
    connection_managed_internally = False
    if db_conn is None:
        if not current_app:
            # This case should ideally not happen if called from CLI or within app context
            raise RuntimeError("Application context is required to get a database connection.")
        db_conn = get_db_connection() # Use the context-aware connection getter
        connection_managed_internally = True

    try:
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_path):
            current_app.logger.error(f"Schema file not found at {schema_path}")
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, 'r') as f:
            sql_script = f.read()
        
        cursor = db_conn.cursor()
        cursor.executescript(sql_script)
        db_conn.commit() # Commit schema changes
        current_app.logger.info("Database schema initialized successfully.")
    except sqlite3.Error as e:
        current_app.logger.error(f"Error initializing database schema: {e}")
        if db_conn:
            db_conn.rollback()
        raise
    except FileNotFoundError as e:
        current_app.logger.error(f"Schema file error: {e}")
        raise
    except Exception as e:
        current_app.logger.error(f"Unexpected error during schema initialization: {e}")
        if db_conn and hasattr(db_conn, 'rollback'):
            db_conn.rollback()
        raise
    finally:
        # If the connection was obtained internally for this function's scope (e.g. direct call not from CLI)
        # it should not be closed here as it's managed by Flask's 'g' and teardown context.
        # The CLI command `init-db-schema` ensures proper connection handling via app context.
        pass


# --- Flask CLI Commands for Database Management ---

@click.command('init-db-schema')
@with_appcontext
def init_db_schema_command():
    """Clear existing data and create new tables based on schema.sql."""
    db_conn = get_db_connection() # Connection is managed by app context
    init_db_schema(db_conn) # Pass the connection
    click.echo('Initialized the database schema.')

# --- Utility Functions (can be expanded) ---

def query_db(query, args=(), one=False, commit=False, db_conn=None):
    """
    Helper function to query the database.
    :param query: The SQL query string.
    :param args: Arguments to pass to the query.
    :param one: Boolean, whether to fetch one record or all.
    :param commit: Boolean, whether to commit after the query (for INSERT, UPDATE, DELETE).
                 The caller is responsible for overall transaction management if part of a larger operation.
    :param db_conn: Optional. An existing database connection. If None, gets one from context.
    :return: Fetched data or lastrowid for INSERT/rowcount for UPDATE/DELETE.
    """
    connection_provided = db_conn is not None
    if not connection_provided:
        db_conn = get_db_connection()
    
    cursor = None
    try:
        cursor = db_conn.cursor()
        cursor.execute(query, args)
        
        if commit:
            # This commit is for standalone operations using query_db.
            # If part of a larger transaction, the caller should manage the commit.
            if not connection_provided: # Only commit if we got the connection, and it's a commit operation
                 db_conn.commit()
            # For INSERT operations, lastrowid might be useful.
            # For UPDATE/DELETE, rowcount is useful.
            return cursor.lastrowid if "insert" in query.lower() else cursor.rowcount

        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv
    except sqlite3.Error as e:
        current_app.logger.error(f"Database query error: {e} \nQuery: {query} \nArgs: {args}")
        # Rollback only if we initiated the commit and it failed, and we got the connection here.
        if db_conn and commit and not connection_provided: 
            db_conn.rollback()
        raise 
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during query_db: {e}")
        if db_conn and commit and not connection_provided:
            db_conn.rollback()
        raise


def register_db_commands(app):
    """Registers database CLI commands with the Flask application."""
    app.cli.add_command(init_db_schema_command)
    app.teardown_appcontext(close_db_connection)
    app.logger.info("Database commands registered and teardown context set.")


# Example of a more specific data access function (can be in models.py or services)
def get_user_by_email(email, db_conn=None):
    """
    Fetches a user by their email address.
    :param email: The email address to search for.
    :param db_conn: Optional. An existing database connection.
    :return: User data as a dictionary or None if not found.
    """
    sql = "SELECT * FROM users WHERE email = ?"
    # Pass db_conn to query_db. query_db will get a connection if db_conn is None.
    user_data_row = query_db(sql, [email], one=True, db_conn=db_conn)
    return dict(user_data_row) if user_data_row else None

def record_stock_movement(db_conn, product_id, movement_type, quantity_change=None, weight_change_grams=None,
                          variant_id=None, serialized_item_id=None, reason=None,
                          related_order_id=None, related_user_id=None, notes=None):
    """
    Records a stock movement using the provided database connection.
    The caller is responsible for transaction management (commit/rollback).

    :param db_conn: Mandatory. The active database connection.
    :param product_id: ID of the product.
    :param movement_type: Type of stock movement (e.g., 'sale', 'return').
    :param quantity_change: Change in quantity (for simple products).
    :param weight_change_grams: Change in weight (for variable_weight products).
    :param variant_id: ID of the product variant, if applicable.
    :param serialized_item_id: ID of the serialized item, if applicable.
    :param reason: Reason for the stock movement.
    :param related_order_id: Related order ID, if applicable.
    :param related_user_id: User ID performing the action, if applicable.
    :param notes: Additional notes.
    :return: The lastrowid of the inserted stock movement record.
    :raises: sqlite3.Error if database execution fails.
    """
    if db_conn is None:
        # This check is more for development-time safety; in practice, callers must provide it.
        current_app.logger.error("record_stock_movement called without a database connection.")
        raise ValueError("A database connection (db_conn) is required for record_stock_movement.")

    sql = """
        INSERT INTO stock_movements (
            product_id, variant_id, serialized_item_id, movement_type,
            quantity_change, weight_change_grams, reason,
            related_order_id, related_user_id, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    args = (
        product_id, variant_id, serialized_item_id, movement_type,
        quantity_change, weight_change_grams, reason,
        related_order_id, related_user_id, notes
    )
    
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql, args)
        # DO NOT COMMIT HERE. Caller manages the transaction.
        current_app.logger.info(f"Stock movement prepared for recording (pending commit): {movement_type} for product {product_id}")
        return cursor.lastrowid
    except sqlite3.Error as e:
        current_app.logger.error(f"Failed to prepare stock movement record: {e}. Query: {sql}, Args: {args}")
        # DO NOT ROLLBACK HERE. Caller manages the transaction.
        raise
    except Exception as e:
        current_app.logger.error(f"Unexpected error preparing stock movement record: {e}")
        raise

