# backend/passport/routes.py
from flask import Blueprint, current_app, send_from_directory, abort, render_template_string
import os
import sqlite3
from ..database import get_db_connection

passport_bp = Blueprint('passport', __name__, url_prefix='/passport')

# Helper to fetch passport HTML file path from DB
def get_passport_file_path_from_db(item_uid):
    conn = get_db_connection()
    cursor = conn.cursor()
    # We stored the public URL in serialized_inventory_items.passport_html_url
    # This public URL was constructed like: /product_passports/passport_item_{item_uid}.html
    # We need to convert this back to a file system path.
    # The AssetService stores files in current_app.config['PRODUCT_PASSPORT_PATH']
    
    # For security and simplicity, let's assume the passport_html_url field in DB
    # stores the *relative asset URL* (e.g., "/product_passports/passport_item_XYZ.html")
    # OR, we can query for the item and reconstruct the expected filename.
    # Let's query for the item to ensure it exists and get its stored passport_html_url,
    # which should be the relative path from the asset serving root.

    cursor.execute("""
        SELECT passport_html_url 
        FROM serialized_inventory_items 
        WHERE item_uid = ? AND status != 'archived' -- Or other relevant status checks
    """, (item_uid,))
    item = cursor.fetchone()
    conn.close()

    if not item or not item['passport_html_url']:
        return None

    # The passport_html_url is like "/product_passports/passport_item_XYZ.html"
    # We need to find the actual file system path.
    # current_app.config['PRODUCT_PASSPORT_PATH'] is the base directory for these files.
    # e.g., /abs/path/to/assets_generated/product_passports
    
    # The URL stored is relative to the asset serving root.
    # Example: item['passport_html_url'] = "/product_passports/passport_item_ABC.html"
    # Base asset storage: current_app.config['ASSET_STORAGE_PATH'] = ".../assets_generated"
    # Passport specific storage: current_app.config['PRODUCT_PASSPORT_PATH'] = ".../assets_generated/product_passports"
    
    # The filename is the last part of the URL
    relative_path_in_passport_dir = os.path.basename(item['passport_html_url'])
    file_path = os.path.join(current_app.config['PRODUCT_PASSPORT_PATH'], relative_path_in_passport_dir)
    
    return file_path


@passport_bp.route('/<item_uid>', methods=['GET'])
def serve_passport(item_uid):
    """
    Serves the HTML passport page for a given item_uid.
    This is a public-facing route.
    """
    if not item_uid:
        current_app.logger.warning("Attempt to access passport with no item_uid.")
        abort(400, description="Item UID is required.")

    current_app.logger.debug(f"Request for passport for item_uid: {item_uid}")
    
    file_path = get_passport_file_path_from_db(item_uid)

    if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
        current_app.logger.info(f"Serving passport for UID {item_uid} from {file_path}")
        # Serve the HTML file directly
        # For security, ensure the path is within the expected directory.
        # send_from_directory handles this by taking directory and filename separately.
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        # Ensure the directory is the configured passport path to prevent traversal
        if directory != current_app.config['PRODUCT_PASSPORT_PATH']:
            current_app.logger.error(f"Security: Attempt to access passport outside designated directory. UID: {item_uid}, Path: {file_path}")
            abort(403) # Forbidden

        return send_from_directory(directory, filename, mimetype='text/html')
    else:
        current_app.logger.warning(f"Passport not found for item_uid: {item_uid}. Checked path: {file_path}")
        # You can return a custom "not found" HTML page here
        # For example: return render_template_string("<html><body><h1>Passeport non trouvé</h1><p>Le passeport pour l'article avec UID {{uid}} n'a pas été trouvé.</p></body></html>", uid=item_uid), 404
        abort(404, description=f"Passport not found for item UID: {item_uid}")
