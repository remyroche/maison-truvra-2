# backend/config.py
import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) # Project Root

    DATABASE_PATH = os.path.join(BASE_DIR, 'maison_truvra.db')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'une-cle-secrete-tres-difficile-a-deviner-pour-jwt-et-flask'
    DEBUG = True 
    
    JWT_EXPIRATION_HOURS = 24
    
    # Admin credentials for initial setup (consider moving to instance config or env vars)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@maisontruvra.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'SecureAdminP@ss1')

    # --- Asset Generation Configuration ---
    # Ensure the 'static' folder exists at the same level as the 'backend' folder, or adjust paths.
    # If your Flask app's static_folder is configured differently, these paths should align with that.
    # For Flask, `current_app.static_folder` usually points to a 'static' directory in your app's root or instance path.
    # Let's assume a 'static' folder in the project root (alongside 'backend' and 'website').
    # If Flask's static folder is `backend/static`, then adjust these.
    # For simplicity, let's assume `current_app.static_folder` is correctly set by Flask.
    # If `current_app.static_folder` is None (e.g. running script outside app context), provide a default.
    
    # These paths will be joined with `current_app.static_folder`
    PASSPORTS_SUBDIR = 'passports'
    QR_CODES_SUBDIR = 'qrcodes'
    LABELS_SUBDIR = 'labels'

    # Base URL for accessing passports (used for QR code data)
    # This should be your publicly accessible domain + path to passports.
    # For local dev, if passports are in static/passports, it might be:
    # http://127.0.0.1:5001/static/passports/
    # Or if you set up a route: http://127.0.0.1:5001/passports/
    # For now, let's assume they are served from a /passports/ route relative to site base.
    PASSPORT_BASE_URL = os.environ.get('PASSPORT_BASE_URL', 'http://127.0.0.1:5001/passports/') # Adjust if served differently

    SITE_BASE_URL = os.environ.get('SITE_BASE_URL', 'http://127.0.0.1:5001') # Used in passport footer
    CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', 'contact@maisontruvra.com')

    # Paths to font and logo for label generation (relative to app root or absolute)
    # These are used if `current_app.config` is accessed directly by scripts.
    # It's better if asset_generators.py uses `current_app.config`
    LABEL_FONT_PATH = os.environ.get('LABEL_FONT_PATH', os.path.join(BASE_DIR, 'backend', 'static', 'fonts', 'arial.ttf')) # Example path
    LABEL_LOGO_PATH = os.environ.get('LABEL_LOGO_PATH', os.path.join(BASE_DIR, 'backend', 'static', 'images', 'image_6b84ab.png')) # Example path for label logo

    # Dynamically set these in create_app based on current_app.static_folder
    PASSPORTS_OUTPUT_DIR = None
    QR_CODES_OUTPUT_DIR = None
    LABELS_OUTPUT_DIR = None


AppConfig = Config

def configure_asset_paths(app):
    """Helper to configure asset paths once app.static_folder is available."""
    static_folder = app.static_folder or os.path.join(app.root_path, 'static')
    if not os.path.exists(static_folder):
        os.makedirs(static_folder, exist_ok=True)
        
    app.config['PASSPORTS_OUTPUT_DIR'] = os.path.join(static_folder, app.config['PASSPORTS_SUBDIR'])
    app.config['QR_CODES_OUTPUT_DIR'] = os.path.join(static_folder, app.config['QR_CODES_SUBDIR'])
    app.config['LABELS_OUTPUT_DIR'] = os.path.join(static_folder, app.config['LABELS_SUBDIR'])

    # Ensure these directories exist
    os.makedirs(app.config['PASSPORTS_OUTPUT_DIR'], exist_ok=True)
    os.makedirs(app.config['QR_CODES_OUTPUT_DIR'], exist_ok=True)
    os.makedirs(app.config['LABELS_OUTPUT_DIR'], exist_ok=True)

    # Ensure font and logo paths are absolute or resolvable
    # If LABEL_FONT_PATH and LABEL_LOGO_PATH are relative, make them absolute from app.root_path
    if not os.path.isabs(app.config['LABEL_FONT_PATH']):
        app.config['LABEL_FONT_PATH'] = os.path.join(app.root_path, app.config['LABEL_FONT_PATH'])
    if not os.path.isabs(app.config['LABEL_LOGO_PATH']):
        app.config['LABEL_LOGO_PATH'] = os.path.join(app.root_path, app.config['LABEL_LOGO_PATH'])

    # You might need to create a 'fonts' and 'images' directory in 'static' if they don't exist
    # and place arial.ttf and image_6b84ab.png there.
    font_dir = os.path.dirname(app.config['LABEL_FONT_PATH'])
    logo_dir = os.path.dirname(app.config['LABEL_LOGO_PATH'])
    os.makedirs(font_dir, exist_ok=True)
    os.makedirs(logo_dir, exist_ok=True)

    app.logger.info(f"Passport output dir: {app.config['PASSPORTS_OUTPUT_DIR']}")
    app.logger.info(f"QR Code output dir: {app.config['QR_CODES_OUTPUT_DIR']}")
    app.logger.info(f"Label output dir: {app.config['LABELS_OUTPUT_DIR']}")
