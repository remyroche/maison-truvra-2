# backend/config.py
import os
from dotenv import load_dotenv# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    DEBUG = False
    TESTING = False
    
    # Database configuration (using sqlite3 directly, not SQLAlchemy)
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'db/maison_truvra.db')

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-super-secret-jwt-key') # CHANGE THIS!
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 30)
    JWT_REFRESH_TOKEN_EXPIRES_DAYS = os.environ.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 7) # For potential refresh token implementation

    # Email Configuration (Placeholders - configure with your actual email service)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your-email@example.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your-email-password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@maisontruvra.com')
    
    # Stripe API Keys (Placeholder - payment integration is out of scope for this update)
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', 'pk_test_your_stripe_public_key')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_your_stripe_secret_key')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_your_stripe_webhook_secret')

    # Application specific settings
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://127.0.0.1:8000') # Assuming frontend served on port 8000
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@maisontruvra.com') # Default admin email if needed

    # Asset generation paths (ensure these directories exist and are writable)
    ASSET_STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets_generated')
    PRODUCT_LABEL_PATH = os.path.join(ASSET_STORAGE_PATH, 'product_labels')
    PRODUCT_PASSPORT_PATH = os.path.join(ASSET_STORAGE_PATH, 'product_passports')
    PRODUCT_QR_CODE_PATH = os.path.join(ASSET_STORAGE_PATH, 'product_qr_codes')
    INVOICE_PDF_PATH = os.path.join(ASSET_STORAGE_PATH, 'invoices')


class DevelopmentConfig(Config):
    DEBUG = True
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = 120 # Longer for dev
    # Example: Use a local SQLite file for development
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'dev.db')


class TestingConfig(Config):
    TESTING = True
    # Example: Use an in-memory SQLite database for tests
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = 1 


class ProductionConfig(Config):
    # Ensure JWT_SECRET_KEY is strong and set via environment variable in production
    if Config.JWT_SECRET_KEY == 'your-super-secret-jwt-key':
        raise ValueError("JWT_SECRET_KEY must be set to a strong secret in production!")
    # Add other production-specific settings, e.g., logging, database URI from env
    pass

config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig,
    default=DevelopmentConfig
)

# Ensure asset directories exist
if not os.path.exists(Config.ASSET_STORAGE_PATH):
    os.makedirs(Config.ASSET_STORAGE_PATH)
if not os.path.exists(Config.PRODUCT_LABEL_PATH):
    os.makedirs(Config.PRODUCT_LABEL_PATH)
if not os.path.exists(Config.PRODUCT_PASSPORT_PATH):
    os.makedirs(Config.PRODUCT_PASSPORT_PATH)
if not os.path.exists(Config.PRODUCT_QR_CODE_PATH):
    os.makedirs(Config.PRODUCT_QR_CODE_PATH)
if not os.path.exists(Config.INVOICE_PDF_PATH):
    os.makedirs(Config.INVOICE_PDF_PATH)

# Get current config
current_config_name = os.getenv('FLASK_ENV', 'default')
current_config = config_by_name[current_config_name]


def get_config_by_name(config_name):
    return config_by_name.get(config_name, DevelopmentConfig)
