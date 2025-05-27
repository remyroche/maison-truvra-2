# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-and-hard-to-guess-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY # Can use the same as Flask's SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES_PROFESSIONAL = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_PROFESSIONAL', 3600 * 24 * 7)) # 7 days for professionals
    JWT_ACCESS_TOKEN_EXPIRES_ADMIN = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_ADMIN', 3600 * 8)) # 8 hours for admin
    JWT_ACCESS_TOKEN_EXPIRES_DEFAULT = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_DEFAULT', 3600)) # 1 hour for others

    # Admin user credentials from environment variables or defaults
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'StrongAdminP@ssw0rd!' # Change this!
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@maisontruvra.com'

    # Asset paths - these will be relative to the 'backend' directory's parent (project root)
    # and then joined with app.static_folder or app.instance_path as appropriate
    # For example, if static_folder is '../static_assets' (relative to backend dir)
    
    # Directory names within the static folder
    PASSPORTS_DIR_NAME = 'passports'
    QR_CODES_DIR_NAME = 'qrcodes'
    LABELS_DIR_NAME = 'labels'
    INVOICES_DIR_NAME = 'invoices' # For storing generated/uploaded invoices

    # Base URL for assets served statically (ensure your static serving is set up)
    # This assumes static_url_path is '/static_assets'
    STATIC_ASSETS_URL_BASE = '/static_assets' # Matches static_url_path in create_app

    # Full output directories - these are constructed in configure_asset_paths
    PASSPORTS_OUTPUT_DIR = os.path.join('..', 'static_assets', PASSPORTS_DIR_NAME) # Relative to backend dir
    QR_CODES_OUTPUT_DIR = os.path.join('..', 'static_assets', QR_CODES_DIR_NAME)   # Relative to backend dir
    LABELS_OUTPUT_DIR = os.path.join('..', 'static_assets', LABELS_DIR_NAME)       # Relative to backend dir
    INVOICES_UPLOAD_DIR = os.path.join('..', 'static_assets', INVOICES_DIR_NAME)   # Relative to backend dir

    # URLs for assets (used in QR codes, etc.)
    # These need to be absolute URLs for external use (like QR codes)
    # In a real deployment, this would be your actual domain.
    # For development, if running on localhost:5000, it would be http://localhost:5000
    APP_BASE_URL = os.environ.get('APP_BASE_URL') or 'http://localhost:5000' # Change for production
    
    PASSPORT_BASE_URL = f"{APP_BASE_URL}{STATIC_ASSETS_URL_BASE}/{PASSPORTS_DIR_NAME}/"
    QR_CODE_BASE_URL = f"{APP_BASE_URL}{STATIC_ASSETS_URL_BASE}/{QR_CODES_DIR_NAME}/"
    LABEL_BASE_URL = f"{APP_BASE_URL}{STATIC_ASSETS_URL_BASE}/{LABELS_DIR_NAME}/"
    INVOICE_DOWNLOAD_BASE_URL = f"{APP_BASE_URL}{STATIC_ASSETS_URL_BASE}/{INVOICES_DIR_NAME}/"


    # Font and Logo paths for asset generation (labels, invoices)
    # These should be paths accessible by the backend server.
    # Example: place them in a 'resources' folder within 'backend' or 'static_assets'
    # Ensure these paths are correct for your project structure.
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Parent of 'backend'

    LABEL_FONT_PATH = os.environ.get('LABEL_FONT_PATH') or os.path.join(PROJECT_ROOT, 'static_assets', 'fonts', 'DejaVuSans.ttf') # Example path
    LABEL_LOGO_PATH = os.environ.get('LABEL_LOGO_PATH') or os.path.join(PROJECT_ROOT, 'static_assets', 'logos', 'maison_truvra_logo_small.png') # Example path
    
    INVOICE_COMPANY_LOGO_PATH = os.environ.get('INVOICE_COMPANY_LOGO_PATH') or os.path.join(PROJECT_ROOT, 'static_assets', 'logos', 'maison_truvra_logo_invoice.png') # Example path for invoice logo
    INVOICE_FONT_REGULAR_PATH = os.environ.get('INVOICE_FONT_REGULAR_PATH') or os.path.join(PROJECT_ROOT, 'static_assets', 'fonts', 'DejaVuSans.ttf')
    INVOICE_FONT_BOLD_PATH = os.environ.get('INVOICE_FONT_BOLD_PATH') or os.path.join(PROJECT_ROOT, 'static_assets', 'fonts', 'DejaVuSans-Bold.ttf')

    # Password Reset Salt
    PASSWORD_RESET_SALT = os.environ.get('PASSWORD_RESET_SALT') or 'your-secure-password-reset-salt'

    # Email configuration (example using SendGrid, replace with your provider)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@maisontruvra.com'
    ADMIN_EMAIL_RECIPIENT = os.environ.get('ADMIN_EMAIL_RECIPIENT') or ADMIN_EMAIL # For notifications

    # Stripe API Keys
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_ENDPOINT_SECRET = os.environ.get('STRIPE_ENDPOINT_SECRET') # For webhook verification

    # Other configurations
    ITEMS_PER_PAGE = 10
    LANGUAGES = ['en', 'fr']
    DEFAULT_LANGUAGE = 'fr'


def configure_asset_paths(app):
    """
    Ensures that asset output directories exist.
    This should be called after the app is created and config is loaded.
    """
    # These paths are relative to the 'backend' directory where create_app is typically called.
    # We need to make them absolute or relative to a consistent root like app.static_folder's parent.
    # app.static_folder is '../static_assets' relative to 'backend'.
    # app.root_path is the absolute path to the 'backend' directory.

    static_assets_abs_path = os.path.abspath(os.path.join(app.root_path, app.static_folder))

    dirs_to_create = [
        os.path.join(static_assets_abs_path, Config.PASSPORTS_DIR_NAME),
        os.path.join(static_assets_abs_path, Config.QR_CODES_DIR_NAME),
        os.path.join(static_assets_abs_path, Config.LABELS_DIR_NAME),
        os.path.join(static_assets_abs_path, Config.INVOICES_DIR_NAME),
    ]

    for dir_path in dirs_to_create:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
                app.logger.info(f"Created directory: {dir_path}")
            except OSError as e:
                app.logger.error(f"Error creating directory {dir_path}: {e}")

    # Update config with absolute paths for backend use if needed,
    # but generally, keep them relative for flexibility and use app.root_path or app.static_folder to resolve.
    # The current PASSPORTS_OUTPUT_DIR etc. are already relative to backend dir, which is fine for use with os.path.join(app.root_path, ...)

    # Verify font and logo paths
    paths_to_check = [
        app.config.get('LABEL_FONT_PATH'),
        app.config.get('LABEL_LOGO_PATH'),
        app.config.get('INVOICE_COMPANY_LOGO_PATH'),
        app.config.get('INVOICE_FONT_REGULAR_PATH'),
        app.config.get('INVOICE_FONT_BOLD_PATH')
    ]
    for path in paths_to_check:
        if path and not os.path.exists(path):
            app.logger.warning(f"Resource file not found: {path}. Asset generation might fail.")
        elif not path:
            app.logger.warning(f"A resource path (font/logo) is not configured. Asset generation might fail.")

# Example: Call this in create_app after app.config.from_object(config_class)
# with app.app_context():
#     configure_asset_paths(current_app)
# Or, more simply, if create_app has the app object:
# In create_app:
#   app.config.from_object(config_class)
#   configure_asset_paths(app) # Call it here
