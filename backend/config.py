# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:import os

class Config:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Points to the project root

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_very_secret_key_here' # Change this in production!
    
    # Database configuration
    DATABASE_PATH = os.path.join(BASE_DIR, 'db', 'maison_truvra.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File Uploads / Generation Paths
    # Ensure these directories exist or are created by your application startup logic
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'website', 'static', 'uploads', 'products')
    QR_CODES_OUTPUT_DIR = os.path.join(BASE_DIR, 'website', 'static', 'assets', 'qr_codes')
    PRODUCT_PASSPORTS_OUTPUT_DIR = os.path.join(BASE_DIR, 'website', 'static', 'assets', 'product_passports')
    LABELS_OUTPUT_DIR = os.path.join(BASE_DIR, 'website', 'static', 'assets', 'labels')
    INVOICES_UPLOAD_DIR = os.path.join(BASE_DIR, 'invoices', 'professional') # Server-side storage for generated invoices

    # Paths for assets used in generation (e.g., PDFs)
    LOGO_PATH = os.path.join(BASE_DIR, 'website', 'static', 'images', 'logo', 'logo-TRUVRA-noir.png')
    FONT_PATH_REGULAR = os.path.join(BASE_DIR, 'website', 'static', 'fonts', 'Montserrat', 'Montserrat-Regular.ttf') # Example path
    FONT_PATH_BOLD = os.path.join(BASE_DIR, 'website', 'static', 'fonts', 'Montserrat', 'Montserrat-Bold.ttf') # Example path
    
    # JWT Configuration (Example)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'another_super_secret_jwt_key' # Change this!
    JWT_ACCESS_TOKEN_EXPIRES = 3600 # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000 # 30 days

    # Email Configuration (Placeholder - Configure with your email service)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@maisontruvra.com'

    # Stripe API Keys (Placeholder)
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_ENDPOINT_SECRET = os.environ.get('STRIPE_ENDPOINT_SECRET') # For webhook

    # Application specific settings
    ITEMS_PER_PAGE = 10
    B2B_APPROVAL_REQUIRED = True

    # Ensure directories exist
    DIRECTORIES_TO_CREATE = [
        DATABASE_PATH.replace(os.path.basename(DATABASE_PATH), ''), # DB directory
        UPLOAD_FOLDER,
        QR_CODES_OUTPUT_DIR,
        PRODUCT_PASSPORTS_OUTPUT_DIR,
        LABELS_OUTPUT_DIR,
        INVOICES_UPLOAD_DIR
    ]

    @staticmethod
    def create_directories():
        for directory in Config.DIRECTORIES_TO_CREATE:
            if directory and not os.path.exists(directory): # Check if directory string is not empty
                try:
                    os.makedirs(directory, exist_ok=True)
                    print(f"Created directory: {directory}")
                except OSError as e:
                    print(f"Error creating directory {directory}: {e}")


# Call this once at application startup, e.g., in run.py or backend/__init__.py
Config.create_directories()

class DevelopmentConfig(Config):
    DEBUG = True
    # SQLALCHEMY_ECHO = True # Useful for debugging SQL queries

class ProductionConfig(Config):
    DEBUG = False
    # Add any production specific settings here
    # For example, more secure secrets, different database URI if not SQLite

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory SQLite for tests
    DATABASE_PATH = ':memory:'
    WTF_CSRF_ENABLED = False # Disable CSRF forms for testing
    # Ensure test-specific directories if needed, or mock file system operations

config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig
)

def get_config_by_name(config_name):
    return config_by_name.get(config_name, DevelopmentConfig)
